"""Mi taller (T20): el nombre, el teléfono y el logo del taller, y las costureras.

Solo la usa la dueña (docs/04-permisos.md, T21): la costurera recibe 403 en todas sus
direcciones; el número de una usuaria de otro taller, 404.

- "Tu taller" (cuentas/_mi_taller_taller.html): guardar devuelve la tarjeta y, con
  hx-swap-oob, el nombre del taller en el menú y en la pestaña del navegador.
- "Costureras" (cuentas/_mi_taller_costureras.html): agregar, cambiar el nombre y
  desactivar o volver a activar. Cada acción devuelve la tarjeta entera.

Cada costurera se busca entre las costureras del taller de la usuaria: el número de una
usuaria de otro taller, o el de una dueña, responde 404 y no cambia nada.

Sin JavaScript, los formularios hacen un envío normal y vuelven a Mi taller. Si tienen un
error, sale la página completa con el mensaje (cambiar el nombre, en una página aparte).

Después de guardar sale un aviso corto (config/avisos.py). "Nombre guardado." es el de la
demo; los demás no estaban en la demo y siguen su estilo (docs/bitacora/ajuste-pantalla-fija/
mi-taller.md). Un formulario con errores no lleva aviso.
"""

from dataclasses import dataclass

from django.db import IntegrityError, transaction
from django.db.models.functions import Lower
from django.http import HttpResponse, HttpResponseBadRequest
from django.shortcuts import redirect, render
from django.template.loader import render_to_string
from django.urls import reverse
from django.views.decorators.http import require_http_methods, require_POST

from config.avisos import avisar
from config.menu import iniciales
from config.ventanas import es_htmx, responder_ventana
from cuentas.aislamiento import del_taller, obtener_o_404
from cuentas.formularios_mi_taller import (
    USUARIO_REPETIDO,
    FormularioCostureraNueva,
    FormularioNombre,
    FormularioTaller,
    enfocar,
)
from cuentas.models import Taller, Usuario
from cuentas.permisos import exigir_duena, solo_duena

# El cuadro en el que se muestra el logo en la tarjeta (en px). El logo se achica para
# caber sin deformarse.
ANCHO_DEL_LOGO = 160
ALTO_DEL_LOGO = 80

# Los avisos cortos después de guardar.
NOMBRE_GUARDADO = "Nombre guardado."  # el de la demo
CAMBIOS_GUARDADOS = "Cambios guardados."
COSTURERA_AGREGADA = "Costurera agregada."
COSTURERA_DESACTIVADA = "Costurera desactivada."
COSTURERA_ACTIVADA = "Costurera activada."


@dataclass(frozen=True)
class Logo:
    """El logo como se dibuja en la tarjeta: la dirección y su ancho y alto en pantalla."""

    url: str
    ancho: int
    alto: int


def logo_del_taller(taller):
    """El logo del taller achicado para caber en 160 x 80 px, o None si no tiene.

    El ancho y el alto van en la etiqueta <img>: así se ve en proporción sin estilos
    propios, y la página no salta cuando la imagen termina de cargar.
    """
    if not taller.logo:
        return None
    try:
        ancho, alto = taller.logo.width, taller.logo.height
    except (OSError, ValueError):
        # El archivo ya no está en el disco: mejor no mostrar nada que una imagen rota.
        return None
    escala = min(ANCHO_DEL_LOGO / ancho, ALTO_DEL_LOGO / alto, 1)
    return Logo(
        url=taller.logo.url,
        ancho=max(1, round(ancho * escala)),
        alto=max(1, round(alto * escala)),
    )


def _taller(request):
    """El taller de la usuaria, leído de nuevo de la base.

    El formulario trabaja sobre esta copia y no sobre request.taller: si el formulario
    tiene un error, el menú de la página sigue mostrando el nombre que está guardado.
    """
    return Taller.objects.get(pk=request.taller.pk)


def _costureras(request):
    """Las costureras del taller: primero las activas, cada grupo por nombre."""
    return del_taller(request, Usuario).filter(rol=Usuario.Rol.COSTURERA)


def contexto_taller(taller, form=None, guardado=False):
    """Los datos de la tarjeta "Tu taller"."""
    return {
        "taller": taller,
        "form_taller": form or FormularioTaller(instance=taller),
        "logo": logo_del_taller(taller),
        "iniciales": iniciales(taller.nombre),
        "guardado": guardado,
    }


def _iniciales_de(nombre):
    """Las letras del cuadrito de una persona: "Ana María" -> "AM"; "Carmen" -> "CA"."""
    palabras = nombre.split()
    if len(palabras) >= 2:
        return (palabras[0][0] + palabras[1][0]).upper()
    return (nombre[:2] or "?").upper()


def contexto_costureras(request, form_nueva=None, editando=None, form_nombre=None,
                        agregada=None, enfocar_en=None):
    """Los datos de la tarjeta "Costureras".

    `editando` es la costurera que tiene abierto el formulario para cambiar su nombre, y
    `agregada`, la que se acaba de crear (para el mensaje de listo).
    `enfocar_en` es (costurera, "nombre" o "estado"): después de cancelar, guardar el nombre
    o activar y desactivar, el cursor vuelve a su botón ("Cambiar nombre" o el de activar),
    para no perder el lugar con el teclado.
    """
    costureras = list(
        _costureras(request).order_by("-is_active", Lower("nombre_visible"), "username")
    )
    for costurera in costureras:
        costurera.iniciales = _iniciales_de(costurera.nombre)
    if editando is not None and form_nombre is None:
        form_nombre = FormularioNombre(instance=editando, taller=request.taller)
    if form_nombre is not None:
        enfocar(form_nombre, "nombre_visible")
    return {
        "costureras": costureras,
        "lista_activas": [c for c in costureras if c.is_active],
        "lista_inactivas": [c for c in costureras if not c.is_active],
        "activas": sum(1 for c in costureras if c.is_active),
        "form_nueva": form_nueva or FormularioCostureraNueva(taller=request.taller),
        "editando": editando,
        "form_nombre": form_nombre,
        "agregada": agregada,
        "enfocar_pk": enfocar_en[0].pk if enfocar_en else None,
        "enfocar_que": enfocar_en[1] if enfocar_en else None,
    }


def _con_tarjeta(request):
    """True si la petición viene de una tarjeta (HTMX) y espera la tarjeta de vuelta.

    La página aparte para cambiar el nombre (sin JavaScript) usa la ventana; si alguien la
    abre con JavaScript, su envío apunta a #ventana y se responde volviendo a Mi taller.
    """
    return es_htmx(request) and request.headers.get("HX-Target") != "ventana"


def _volver(request, ancla):
    url = reverse("cuentas:mi_taller") + ancla
    if es_htmx(request):
        return HttpResponse(headers={"HX-Redirect": url})
    return redirect(url)


def _uso_asistente(request):
    """El cupo de preguntas del asistente (asistente.uso.Cupo), o None si no lo tiene."""
    from asistente import uso
    from asistente.disponibilidad import disponible

    return uso.cupo(request.taller) if disponible(request) else None


def _pagina(request, status=200, **contexto):
    """La página completa de Mi taller. Las dos tarjetas toman lo que llegue en `contexto`
    o, si no, sus datos de siempre."""
    datos = contexto_taller(_taller(request))
    datos.update(contexto_costureras(request))
    datos["uso_asistente"] = _uso_asistente(request)
    datos.update(contexto)
    return render(request, "cuentas/mi_taller.html", datos, status=status)


# --- Tu taller ---------------------------------------------------------------------------------


@solo_duena
@require_http_methods(["GET", "POST"])
def mi_taller(request):
    """La pantalla. Con POST guarda la tarjeta "Tu taller" (nombre, teléfono y logo)."""
    if request.method == "GET":
        return _pagina(request)
    taller = _taller(request)
    form = FormularioTaller(request.POST, request.FILES, instance=taller)
    if not form.is_valid():
        enfocar(form)
        if _con_tarjeta(request):
            return render(request, "cuentas/_mi_taller_taller.html",
                          contexto_taller(_taller(request), form), status=422)
        return _pagina(request, status=422, **contexto_taller(_taller(request), form))
    aviso = _aviso_del_taller(form)
    taller = form.guardar()
    if not _con_tarjeta(request):
        return avisar(request, _volver(request, "#tu-taller"), aviso)
    # La tarjeta con el mensaje de listo y, aparte, el nombre nuevo en el menú y en la
    # pestaña del navegador (los dos están fuera de la tarjeta).
    contexto = contexto_taller(taller, guardado=True)
    html = render_to_string("cuentas/_mi_taller_taller.html", contexto, request=request)
    html += render_to_string("cuentas/_mi_taller_nombre_menu.html", contexto, request=request)
    return avisar(request, HttpResponse(html), aviso)


def _aviso_del_taller(form):
    """"Nombre guardado." (el de la demo) si solo cambió el nombre; si cambió el teléfono,
    el logo o varias cosas a la vez, "Cambios guardados."."""
    return NOMBRE_GUARDADO if form.changed_data == ["nombre"] else CAMBIOS_GUARDADOS


# --- Costureras --------------------------------------------------------------------------------


def _tarjeta_costureras(request, status=200, **extra):
    return render(request, "cuentas/_mi_taller_costureras.html",
                  contexto_costureras(request, **extra), status=status)


@solo_duena
@require_POST
def costurera_nueva(request):
    """Agregar una costurera: entra con su usuario y su contraseña desde ese momento."""
    form = FormularioCostureraNueva(request.POST, taller=request.taller)
    agregada = None
    if form.is_valid():
        try:
            with transaction.atomic():
                agregada = form.guardar()
        except IntegrityError:
            # Otra persona creó el mismo usuario justo al mismo tiempo.
            form.add_error("username", USUARIO_REPETIDO)
    if agregada is None:
        enfocar(form)
        if _con_tarjeta(request):
            return _tarjeta_costureras(request, status=422, form_nueva=form)
        return _pagina(request, status=422, **contexto_costureras(request, form_nueva=form))
    if _con_tarjeta(request):
        # El formulario vuelve vacío y con el cursor listo para la siguiente.
        nueva = enfocar(FormularioCostureraNueva(taller=request.taller), "nombre_visible")
        respuesta = _tarjeta_costureras(request, agregada=agregada, form_nueva=nueva)
    else:
        respuesta = _volver(request, "#costureras")
    return avisar(request, respuesta, COSTURERA_AGREGADA)


@require_http_methods(["GET", "POST"])
def costurera_editar(request, pk):
    """Cambiar el nombre de una costurera, o desactivarla y volverla a activar.

    GET abre el formulario del nombre: con HTMX, en su fila de la tarjeta (y con ?cancelar=1
    la fila vuelve a quedar como estaba); sin JavaScript, en una página aparte.
    POST hace lo que diga `accion`: "nombre", "desactivar" o "activar".

    Desactivar no borra nada: ella ya no puede entrar, pero sus pedidos y lo que anotó
    siguen ahí, y se puede volver a activar cuando se quiera.
    """
    exigir_duena(request)  # antes de buscar: así una costurera no averigua qué números existen
    costurera = obtener_o_404(request, _costureras(request), pk=pk)
    if request.method == "GET":
        if "cancelar" in request.GET:
            if _con_tarjeta(request):
                return _tarjeta_costureras(request, enfocar_en=(costurera, "nombre"))
            return _volver(request, "#costureras")
        if _con_tarjeta(request):
            return _tarjeta_costureras(request, editando=costurera)
        return _ventana_nombre(request, costurera, FormularioNombre(
            instance=costurera, taller=request.taller))

    accion = request.POST.get("accion")
    enfocar_en = (costurera, "estado" if accion in ("desactivar", "activar") else "nombre")
    if accion in ("desactivar", "activar"):
        costurera.is_active = accion == "activar"
        costurera.save(update_fields=["is_active"])
        # Su fila se va al grupo de las activas o al de las desactivadas (puede quedar
        # lejos, en una lista larga): el aviso dice qué pasó.
        aviso = COSTURERA_ACTIVADA if costurera.is_active else COSTURERA_DESACTIVADA
    elif accion == "nombre":
        form = FormularioNombre(request.POST, instance=costurera, taller=request.taller)
        if not form.is_valid():
            if _con_tarjeta(request):
                return _tarjeta_costureras(request, status=422, editando=costurera,
                                           form_nombre=form)
            return _ventana_nombre(request, costurera, form, status=422)
        form.save()
        aviso = NOMBRE_GUARDADO
    else:
        return HttpResponseBadRequest("No se entendió qué cambiar.")
    if _con_tarjeta(request):
        respuesta = _tarjeta_costureras(request, enfocar_en=enfocar_en)
    else:
        respuesta = _volver(request, "#costureras")
    return avisar(request, respuesta, aviso)


def _ventana_nombre(request, costurera, form, status=200):
    """Cambiar el nombre en una página aparte (sin JavaScript)."""
    # El nombre que se muestra es el guardado, aunque el formulario traiga otro con error.
    guardada = Usuario.objects.get(pk=costurera.pk)
    contexto = {
        "form": form,
        "costurera": guardada,
        "accion": reverse("cuentas:costurera_editar", args=[costurera.pk]),
        "titulo_pagina": "Cambiar nombre",
    }
    return responder_ventana(request, "cuentas/_mi_taller_nombre.html", contexto,
                             status=status)
