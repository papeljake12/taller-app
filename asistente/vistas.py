"""Las direcciones del asistente: abrir el panel, preguntar, empezar de nuevo y guardar un
borrador (tanda 8: `confirmar`, docs/13-plan-tanda-8.md, sección 1.3).

Carril D (T33). Reglas: docs/11-plan-tanda-7.md, secciones 1.4 ("Sesión"), 1.5 y 1.7. Todas
con `@solo_duena` y 404 si `not disponible(request)`. `preguntar` responde siempre 200
(static/js/app.js no pinta las respuestas 4xx ni 5xx).

La conversación vive en la sesión de la usuaria, no en la base de datos:

    request.session["asistente"] = {
        "huella": ...,     # modelo + instrucciones + herramientas; si cambia, conversación nueva
        "mensajes": [...], # el historial que se le manda a Claude; solo se le agrega
        "turnos": [...],   # lo que se pinta: pregunta, texto, qué revisó, tarjetas y enlaces
        "notas": [...],    # lo que guardó con un borrador; va en la siguiente pregunta (tanda 8)
    }

Solo se guarda una respuesta que salió bien (`estado == "ok"`). Las que fallan (servicio
caído, rechazo, respuesta cortada), el límite y los avisos se muestran una vez y no se
guardan: Claude tampoco las recuerda, y al recargar el panel se ve lo mismo que él sabe.

Lo que se registra (logger "asistente") es el taller, el estado, los tokens y si se cobró la
pregunta. Nunca el texto de la pregunta ni el de la respuesta.
"""

import hashlib
import json
import logging
import re
import time
from dataclasses import asdict

from django.conf import settings
from django.core.serializers.json import DjangoJSONEncoder
from django.http import Http404, HttpResponse
from django.shortcuts import redirect, render
from django.template import TemplateDoesNotExist
from django.template.loader import get_template, render_to_string
from django.utils import timezone
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_GET, require_POST

from asistente import borradores, cliente, conversacion, esquemas, guardar, instrucciones, pagina, uso
from asistente.contratos import Contexto
from config.avisos import avisar
from asistente.disponibilidad import disponible
from config.ventanas import es_htmx
from cuentas.permisos import solo_duena

registro = logging.getLogger("asistente")

CLAVE_SESION = "asistente"
MAXIMO_PREGUNTA = 500
# Con más de esto, el panel pide empezar una conversación nueva (el historial nunca se recorta).
MAXIMO_TURNOS = 25
MAXIMO_BYTES = 200 * 1024

SUGERENCIAS = [
    "¿Qué entrego esta semana?",
    "¿Cuánto gasté este mes?",
    "¿Qué tela se está acabando?",
]
PREGUNTA_VACIA = "Escribe tu pregunta."
PREGUNTA_LARGA = f"La pregunta es muy larga. Escríbela en {MAXIMO_PREGUNTA} letras o menos."
MUY_LARGA = "Esta conversación ya está muy larga. Empieza una nueva para seguir preguntando."
SIN_PREGUNTAS = "Por ahora ya usaste todas las preguntas. Vuelvo a contestar pronto."

_PARRAFOS = re.compile(r"\n\s*\n")


def _exigir_disponible(request):
    if not disponible(request):
        raise Http404


# --- La conversación en la sesión -----------------------------------------------------------


def huella():
    """Lo que tiene que seguir igual para que una conversación guardada le sirva a Claude.

    Si cambia el modelo, las instrucciones o las herramientas (un despliegue nuevo), las
    respuestas guardadas ya no se pueden reenviar: se empieza una conversación nueva.
    """
    texto = (
        settings.ASISTENTE_MODELO
        + instrucciones.INSTRUCCIONES
        + json.dumps(esquemas.ESQUEMAS, sort_keys=True)
    )
    return hashlib.sha256(texto.encode("utf-8")).hexdigest()


def _conversacion(request):
    """La conversación guardada, o una vacía si no hay o si es de antes de un despliegue."""
    actual = huella()
    guardada = request.session.get(CLAVE_SESION)
    if isinstance(guardada, dict) and guardada.get("huella") == actual:
        return {
            "huella": actual,
            "mensajes": list(guardada.get("mensajes") or []),
            "turnos": list(guardada.get("turnos") or []),
            "notas": list(guardada.get("notas") or []),
        }
    if guardada is not None:
        del request.session[CLAVE_SESION]
    return {"huella": actual, "mensajes": [], "turnos": [], "notas": []}


def _borrar(request):
    request.session.pop(CLAVE_SESION, None)


def _muy_larga(conv):
    if len(conv["turnos"]) > MAXIMO_TURNOS:
        return True
    return len(json.dumps(conv).encode("utf-8")) > MAXIMO_BYTES


# --- Turnos: una pregunta con su respuesta --------------------------------------------------


def _turno(pregunta, estado, texto, revisado=(), tarjetas=(), enlaces=()):
    return {
        "pregunta": pregunta,
        "estado": estado,
        "texto": texto,
        "revisado": list(revisado),
        "tarjetas": list(tarjetas),
        "enlaces": list(enlaces),
    }


def _solo_json(datos):
    """Los datos de una tarjeta tal como quedan en la sesión (fechas como texto ISO).

    Así la tarjeta se pinta igual la primera vez que al recargar el panel.
    """
    return json.loads(json.dumps(datos, cls=DjangoJSONEncoder))


def _turno_de_respuesta(pregunta, respuesta):
    revisado, tarjetas, enlaces = [], [], []
    for resultado in respuesta.resultados:
        if resultado.revisado and resultado.revisado not in revisado:
            revisado.append(resultado.revisado)
        if resultado.tarjeta is not None:
            tarjetas.append(_solo_json(asdict(resultado.tarjeta)))
        enlace = resultado.enlace
        if enlace is not None and all(e["url"] != enlace.url for e in enlaces):
            enlaces.append({"texto": enlace.texto, "url": enlace.url})
    return _turno(pregunta, respuesta.estado, respuesta.texto, revisado, tarjetas, enlaces)


def _tarjeta_existe(tipo):
    try:
        get_template(f"asistente/tarjetas/{tipo}.html")
    except TemplateDoesNotExist:
        registro.warning("tarjeta sin plantilla tipo=%s", tipo)
        return False
    return True


def _para_pintar(turno):
    """El turno con su texto partido: el primer párrafo va antes de las tarjetas."""
    parrafos = [p for p in _PARRAFOS.split((turno.get("texto") or "").strip()) if p.strip()]
    return {
        **turno,
        "primero": parrafos[0] if parrafos else "",
        "resto": "\n\n".join(parrafos[1:]),
        "tarjetas": [
            t for t in turno.get("tarjetas") or [] if isinstance(t, dict)
            and _tarjeta_existe(t.get("tipo"))
        ],
    }


def _turno_larga():
    return _turno("", "larga", MUY_LARGA)


# --- Lo que se pinta ------------------------------------------------------------------------


def _contexto_panel(request, conv, cupo, extra=None):
    turnos = [_para_pintar(t) for t in conv["turnos"]]
    if extra:
        turnos += [_para_pintar(t) for t in extra]
    return {
        "turnos": turnos,
        "aviso_larga": _para_pintar(_turno_larga()) if _muy_larga(conv) else None,
        "sugerencias": SUGERENCIAS,
        "cupo": cupo,
        "pregunta_inicial": (request.GET.get("pregunta") or "")[:MAXIMO_PREGUNTA],
        # La página completa ya es el asistente: sin el botón del encabezado ni el panel de
        # al lado (config/menu.py los dejaría).
        "asistente": {"disponible": False, "abierto": False},
    }


def _pagina(request, conv, cupo, extra=None):
    return render(request, "asistente/pagina.html", _contexto_panel(request, conv, cupo, extra))


@never_cache
@require_GET
@solo_duena
def panel(request):
    """Con HTMX, lo de adentro del panel (_panel.html); sin JavaScript, la página entera."""
    _exigir_disponible(request)
    conv = _conversacion(request)
    cupo = uso.cupo(request.taller)
    if es_htmx(request):
        return render(request, "asistente/_panel.html", _contexto_panel(request, conv, cupo))
    return _pagina(request, conv, cupo)


def _pregunta(request):
    """La pregunta que llegó. Sin JavaScript, una sugerencia también la trae (es un botón)."""
    for texto in request.POST.getlist("pregunta"):
        if texto.strip():
            return texto.strip()
    return ""


def _tarjetas_de_borrador(conv):
    """Todas las tarjetas de borrador de la conversación guardada, de la más vieja a la nueva."""
    for turno in conv["turnos"]:
        for tarjeta in turno.get("tarjetas") or []:
            if isinstance(tarjeta, dict) and tarjeta.get("tipo") == "borrador":
                yield tarjeta


def _reemplazar(conv, clave):
    """El borrador que se estaba corrigiendo queda "reemplazado": sin botones y sin servir."""
    for tarjeta in _tarjetas_de_borrador(conv):
        datos = tarjeta.get("datos") or {}
        if datos.get("clave") == clave and datos.get("estado") in ("pendiente", "fallido"):
            datos["estado"] = "reemplazado"


def _preguntar_a_claude(request, conv, pregunta, hoy):
    """Una pregunta que ya tiene su cupo apartado. Devuelve (turno, se_guardó)."""
    taller = request.taller
    inicio = time.monotonic()
    try:
        texto_pagina, pedido = pagina.contexto_de_pagina(taller, request.POST.get("pagina") or "")
        ctx = Contexto(
            taller=taller,
            usuaria=request.user,
            hoy=hoy,
            pedido_actual=pedido,
            url_base=request.build_absolute_uri("/"),
        )
        respuesta = conversacion.preguntar(
            cliente=cliente.obtener_cliente(),
            ctx=ctx,
            mensajes=conv["mensajes"],
            pregunta=pregunta,
            pagina=texto_pagina,
            nota="; ".join(conv.get("notas") or []),
        )
    except Exception as error:  # noqa: BLE001 - la dueña ve el aviso amable, nunca un 500
        # Solo el tipo de error: su texto podría traer algo de la pregunta.
        registro.error("pregunta fallida taller=%s error=%s", taller.pk, type(error).__name__)
        uso.devolver(taller, hoy)
        return _turno(pregunta, "error", conversacion.MENSAJE_SIN_SERVICIO), False

    uso.anotar(taller, respuesta.uso, hoy)
    if not respuesta.cobrada:
        uso.devolver(taller, hoy)
    registro.info(
        "pregunta taller=%s estado=%s cobrada=%s vueltas=%s esfuerzo=%s parada=%s modelos=%s "
        "herramientas=%s entrada=%s salida=%s cache_escritura=%s cache_lectura=%s segundos=%.1f",
        taller.pk,
        respuesta.estado,
        respuesta.cobrada,
        respuesta.vueltas,
        respuesta.esfuerzo,
        respuesta.stop_reason,
        ",".join(respuesta.modelos),
        len(respuesta.resultados),
        respuesta.uso.entrada,
        respuesta.uso.salida,
        respuesta.uso.cache_escritura,
        respuesta.uso.cache_lectura,
        time.monotonic() - inicio,
    )

    turno = _turno_de_respuesta(pregunta, respuesta)
    if respuesta.reiniciar:
        _borrar(request)
        return turno, False
    if respuesta.estado != "ok":
        return turno, False
    conv["mensajes"] = list(respuesta.mensajes)
    conv["notas"] = []  # ya se las contó a Claude
    corrige = (request.POST.get("corrige") or "").strip()
    if corrige and any(t.get("tipo") == "borrador" for t in turno["tarjetas"]):
        _reemplazar(conv, corrige)
    conv["turnos"].append(turno)
    request.session[CLAVE_SESION] = conv
    return turno, True


@never_cache
@require_POST
@solo_duena
def preguntar(request):
    """La pregunta de la dueña: valida, aparta el cupo, le pregunta a Claude y pinta el turno.

    Con HTMX devuelve el turno (que reemplaza al #asistente-pendiente que puso app.js) y el
    aviso de uso aparte, con hx-swap-oob. Sin JavaScript vuelve a la página del asistente.
    """
    _exigir_disponible(request)
    taller = request.taller
    hoy = timezone.localdate()
    conv = _conversacion(request)
    pregunta = _pregunta(request)
    guardado = False

    if not pregunta:
        turno = _turno("", "aviso", PREGUNTA_VACIA)
    elif len(pregunta) > MAXIMO_PREGUNTA:
        turno = _turno(pregunta, "aviso", PREGUNTA_LARGA)
    elif _muy_larga(conv):
        turno = _turno(pregunta, "larga", MUY_LARGA)
    elif not uso.reservar(taller, hoy):
        registro.info("pregunta sin cupo taller=%s", taller.pk)
        mensaje = uso.cupo(taller, hoy).mensaje_limite or SIN_PREGUNTAS
        turno = _turno(pregunta, "limite", mensaje)
    else:
        turno, guardado = _preguntar_a_claude(request, conv, pregunta, hoy)

    cupo = uso.cupo(taller, hoy)
    if not es_htmx(request):
        if guardado:
            return redirect("asistente:panel")
        return _pagina(request, _conversacion(request), cupo, extra=[turno])

    partes = [render_to_string("asistente/_turno.html", {"turno": _para_pintar(turno)}, request)]
    if guardado and _muy_larga(conv):
        partes.append(
            render_to_string("asistente/_turno.html", {"turno": _para_pintar(_turno_larga())})
        )
    partes.append(
        render_to_string("asistente/_uso_aviso.html", {"cupo": cupo, "oob": True}, request)
    )
    if cupo.agotado:
        # Se acabaron las preguntas con esta: la caja se apaga sin recargar.
        partes.append(
            render_to_string("asistente/_panel.html", {"cupo": cupo, "solo_caja": True}, request)
        )
    return HttpResponse("".join(partes))


@never_cache
@require_POST
@solo_duena
def nueva(request):
    """Borra la conversación. Con HTMX devuelve la conversación vacía (#asistente-mensajes)."""
    _exigir_disponible(request)
    _borrar(request)
    if es_htmx(request):
        return render(
            request,
            "asistente/_conversacion.html",
            {"turnos": [], "sugerencias": SUGERENCIAS, "cupo": uso.cupo(request.taller)},
        )
    return redirect("asistente:panel")


# --- Guardar un borrador (tanda 8) ------------------------------------------------------------


def _tarjeta_con_firma(conv, firma):
    """La tarjeta del borrador con esa firma en la conversación guardada, o None."""
    if not firma:
        return None
    for tarjeta in _tarjetas_de_borrador(conv):
        if (tarjeta.get("datos") or {}).get("firma") == firma:
            return tarjeta
    return None


def _hora(momento):
    """"10:42 a. m.", como se escribe en Colombia."""
    hora = momento.hour % 12 or 12
    sufijo = "a. m." if momento.hour < 12 else "p. m."
    return f"{hora}:{momento.minute:02d} {sufijo}"


def _pintar_tarjeta(request, tarjeta, status=200):
    html = render_to_string(
        "asistente/tarjetas/borrador.html", {"tarjeta": tarjeta}, request=request
    )
    return HttpResponse(html, status=status)


@never_cache
@require_POST
@solo_duena
def confirmar(request):
    """La dueña tocó Guardar en un borrador: se guarda todo lo que mostraba, o nada.

    Revisa la firma (taller, usuaria, vencimiento, un solo uso) y que el borrador siga vivo en
    la conversación (no reemplazado ni guardado). Guarda con los mismos formularios de las
    pantallas (asistente/guardar.py). No llama a Claude ni gasta preguntas.

    Con HTMX devuelve la tarjeta en su estado nuevo (reemplaza a la que tenía el botón) y el
    aviso corto "Guardado."; sin JavaScript vuelve al panel. Siempre 200.
    """
    _exigir_disponible(request)
    conv = _conversacion(request)
    firma = request.POST.get("firma") or ""
    tarjeta = _tarjeta_con_firma(conv, firma)
    if tarjeta is None:
        registro.info("borrador sin tarjeta taller=%s", request.taller.pk)
        tarjeta = {"tipo": "borrador", "titulo": "Para guardar",
                   "datos": {"estado": "fallido", "filas": [],
                             "mensaje": borradores.MENSAJES["danado"]}}
        return _pintar_tarjeta(request, tarjeta) if es_htmx(request) else redirect("asistente:panel")

    datos = tarjeta["datos"]
    ctx = Contexto(
        taller=request.taller,
        usuaria=request.user,
        hoy=timezone.localdate(),
        pedido_actual=None,
        url_base=request.build_absolute_uri("/"),
    )
    guardados = []
    if datos.get("estado") == "reemplazado":
        datos["mensaje"] = borradores.MENSAJES["reemplazado"]
    elif datos.get("estado") == "guardado":
        pass
    else:
        try:
            clave, acciones = borradores.abrir(firma, ctx)
            guardados = guardar.guardar(ctx, clave, acciones)
        except borradores.BorradorInvalido as error:
            datos["estado"] = "fallido"
            datos["mensaje"] = str(error)
            datos["sin_arreglo"] = True
            registro.info("borrador invalido taller=%s motivo=%s", request.taller.pk, error.motivo)
        except guardar.NoSeGuardo as error:
            datos["estado"] = "fallido"
            datos["mensaje"] = f"No se guardó nada: {error}"
            registro.info("borrador no guardado taller=%s", request.taller.pk)
        else:
            enlaces = []
            for guardado in guardados:
                enlace = guardado.enlace
                if enlace is not None and all(e["url"] != enlace.url for e in enlaces):
                    enlaces.append({"texto": enlace.texto, "url": enlace.url})
            datos.update(
                estado="guardado",
                hora=_hora(timezone.localtime()),
                enlaces=enlaces,
                mensaje="",
            )
            conv.setdefault("notas", []).append(", ".join(g.nota for g in guardados))
            registro.info(
                "borrador guardado taller=%s acciones=%s", request.taller.pk,
                ",".join(sorted({a["tipo"] for a in acciones})),
            )
    request.session[CLAVE_SESION] = conv

    if not es_htmx(request):
        respuesta = redirect("asistente:panel")
    else:
        respuesta = _pintar_tarjeta(request, tarjeta)
    if guardados:
        avisar(request, respuesta, "Guardado.")
    return respuesta
