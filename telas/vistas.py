"""Telas (T16): el inventario, "Entró" y "Usé", agregar y quitar una tela.

La pantalla (diseno/telas.html) tiene tres partes que cambian juntas cuando cambia una tela:
el dato de apoyo del encabezado ("4 telas, 60 m en total"), las tres cifras y la tabla.
Las cuentas salen de pedidos/calculos.py (resumen_de_telas, telas_en_orden, tela_baja).

Las acciones se piden en la ventana (<dialog id="ventana"> de base.html):
- GET movimiento?tipo=entro (o uso): cuántos metros entraron (o se usaron). Sin tipo, el
  historial de la tela, con el botón para quitarla.
- POST movimiento: suma o resta los metros y anota el movimiento en el historial.
- nueva: agregar una tela. quitar: pregunta primero y después la quita con su historial.

Con HTMX, al guardar se cierra la ventana y llegan solas la tabla, las cifras y el apoyo
(_cambios), sin recargar la página. Sin JavaScript, cada acción abre su página y al
terminar vuelve a Telas.

Permisos (T21, todavía no): la costurera puede ver y registrar "Usé", pero no "Entró", ni
agregar ni quitar. Por eso "Entró" y "Usé" son dos tipos separados (TIPOS).
"""

from dataclasses import dataclass
from urllib.parse import urlparse

from django.db import transaction
from django.http import HttpResponse, HttpResponseBadRequest
from django.shortcuts import redirect, render
from django.template.loader import render_to_string
from django.urls import reverse
from django.views.decorators.http import require_GET, require_http_methods

from config.piezas import metros as texto_metros
from config.ventanas import es_htmx, responder_ventana
from cuentas.aislamiento import del_taller, obtener_o_404
from pedidos import calculos
from telas.formularios import (
    TOPE_DE_LA_TELA,
    FormularioMovimiento,
    FormularioTela,
)
from telas.models import MovimientoTela, Tela

# "Entró" suma y "Usé" resta. La clave es la que va en la dirección (?tipo=entro).
TIPOS = {"entro": 1, "uso": -1}
TITULOS = {"entro": "Entró", "uso": "Usé"}

# Cuántos movimientos muestra el historial de una tela (los más nuevos).
MOVIMIENTOS_A_LA_VISTA = 30


@dataclass(frozen=True)
class FilaTela:
    """Una tela de la tabla con su estado ya decidido (texto y tono de la etiqueta).

    `enfocar` es "entro" o "uso" en la tela que se acaba de mover: al cerrarse la ventana,
    el cursor vuelve a ese botón (HTMX pone el foco en el que trae `autofocus`).
    """

    tela: Tela
    baja: bool
    estado: str
    tono: str
    enfocar: str | None = None


def fila(tela, enfocar=None):
    baja = calculos.tela_baja(tela)
    if baja:
        return FilaTela(tela, True, "Se está acabando", "ambar", enfocar)
    if not tela.metros:
        # Sin metros y sin aviso: no es "Suficiente". Gris, porque no se pidió aviso.
        return FilaTela(tela, False, "Se acabó", "gris", enfocar)
    return FilaTela(tela, False, "Suficiente", "verde", enfocar)


def nombres_juntos(telas):
    """'Piqué blanco y popelina blanca', como en el diseño: la frase empieza con mayúscula
    y los demás nombres siguen en minúscula."""
    nombres = [t.nombre for t in telas]
    nombres = nombres[:1] + [n[:1].lower() + n[1:] for n in nombres[1:]]
    if len(nombres) <= 1:
        return "".join(nombres)
    return ", ".join(nombres[:-1]) + " y " + nombres[-1]


def contexto_de_telas(request, movida=None, tipo=None):
    """Lo que cambia con cada tela: el apoyo, las cifras y la tabla.

    `movida` y `tipo`: la tela que se acaba de mover y cómo, para devolverle el cursor.
    """
    resumen = calculos.resumen_de_telas(request.taller)
    return {
        "resumen": resumen,
        "acabandose": nombres_juntos(resumen["bajas"]),
        "filas": [
            fila(t, tipo if movida and t.pk == movida.pk else None)
            for t in calculos.telas_en_orden(request.taller)
        ],
    }


@require_GET
def inicio(request):
    return render(request, "telas/inicio.html", contexto_de_telas(request))


# --- Después de cada acción ---------------------------------------------------------------


def _en_la_pantalla(request):
    """True si la acción llegó con HTMX desde la pantalla Telas, que tiene la tabla."""
    if not es_htmx(request):
        return False
    desde = urlparse(request.headers.get("HX-Current-URL", "")).path
    return desde == reverse("telas:inicio")


def _cambios(request, movida=None, tipo=None):
    """Lo que cambió, para la pantalla Telas: cierra la ventana y trae la tabla, las cifras
    y el apoyo, sin recargar. Sin JavaScript (o desde otra página), vuelve a Telas."""
    url = reverse("telas:inicio")
    if not _en_la_pantalla(request):
        if es_htmx(request):
            return HttpResponse(headers={"HX-Redirect": url})
        return redirect(url)
    contexto = contexto_de_telas(request, movida, tipo)
    html = render_to_string("telas/_tabla.html", contexto, request=request)
    contexto["oob"] = True
    html += render_to_string("telas/_cifras.html", contexto, request=request)
    html += render_to_string("telas/_apoyo.html", contexto, request=request)
    html += render_to_string("telas/_cerrar_ventana.html", contexto, request=request)
    # La ventana pidió dibujar la respuesta en sí misma: se cambia por la tabla.
    return HttpResponse(html, headers={"HX-Retarget": "#telas", "HX-Reswap": "outerHTML"})


# --- Nueva tela -----------------------------------------------------------------------------


@require_http_methods(["GET", "POST"])
def nueva(request):
    """Agregar una tela. Si ya trae metros, quedan como su primer "Entró" en el historial."""
    datos = request.POST if request.method == "POST" else None
    form = FormularioTela(datos, taller=request.taller)
    if request.method == "POST" and form.is_valid():
        with transaction.atomic():
            tela = form.save(commit=False)
            tela.taller = request.taller
            tela.save()
            if tela.metros > 0:
                MovimientoTela.objects.create(tela=tela, metros=tela.metros, usuario=request.user)
        return _cambios(request)
    form.enfocar()
    contexto = {"form": form, "accion": reverse("telas:nueva"), "titulo_pagina": "Nueva tela"}
    status = 422 if form.is_bound else 200
    return responder_ventana(request, "telas/_nueva.html", contexto, status=status)


# --- Entró, Usé e historial -----------------------------------------------------------------


def _ventana_movimiento(request, tela, form, status=200):
    contexto = {
        "tela": tela,
        "form": form,
        "tipo": form.tipo,
        "accion": reverse("telas:movimiento", args=[tela.pk]),
        "titulo_pagina": f"{TITULOS[form.tipo]}: {tela.nombre}",
    }
    return responder_ventana(request, "telas/_movimiento.html", contexto, status=status)


def _ventana_historial(request, tela):
    movimientos = (
        del_taller(request, MovimientoTela)
        .filter(tela=tela)
        .select_related("usuario")[:MOVIMIENTOS_A_LA_VISTA]
    )
    contexto = {
        "tela": tela,
        "movimientos": list(movimientos),
        "hay_mas": tela.movimientos.count() > MOVIMIENTOS_A_LA_VISTA,
        "maximo": MOVIMIENTOS_A_LA_VISTA,
        "titulo_pagina": tela.nombre,
    }
    return responder_ventana(request, "telas/_historial.html", contexto)


def _guardar_movimiento(request, tela, form):
    """Suma o resta los metros y anota el movimiento, todo junto o nada.

    La tela se aparta (select_for_update) mientras se cambia: si dos personas anotan al
    mismo tiempo, la segunda espera y cuenta con lo que dejó la primera. "Usé" no puede
    bajar de 0: si piden más de lo que queda, se dice y no se guarda nada.
    Devuelve True si guardó.
    """
    signo = TIPOS[form.tipo]
    cuanto = form.cleaned_data["metros"]
    with transaction.atomic():
        tela = Tela.objects.select_for_update().get(pk=tela.pk)
        quedan = tela.metros + signo * cuanto
        if quedan < 0:
            form.add_error(
                "metros",
                f"Solo quedan {texto_metros(tela.metros)} de esta tela: "
                "no puedes usar más de eso.",
            )
            return False
        if quedan > TOPE_DE_LA_TELA:
            form.add_error("metros", "Revisa los metros: son demasiados.")
            return False
        tela.metros = quedan
        tela.save(update_fields=["metros", "actualizado"])
        MovimientoTela.objects.create(tela=tela, metros=signo * cuanto, usuario=request.user)
    return True


@require_http_methods(["GET", "POST"])
def movimiento(request, pk):
    """"Entró" suma metros y "Usé" resta, sin bajar de 0. Sin tipo, muestra el historial."""
    tela = obtener_o_404(request, Tela, pk=pk)
    if request.method == "GET":
        tipo = request.GET.get("tipo")
        if tipo not in TIPOS:
            return _ventana_historial(request, tela)
        return _ventana_movimiento(request, tela, FormularioMovimiento(tipo=tipo))
    tipo = request.POST.get("tipo")
    if tipo not in TIPOS:
        # Los formularios de la pantalla siempre lo traen: esto solo pasa a mano.
        return HttpResponseBadRequest("Falta decir si la tela entró o se usó.")
    form = FormularioMovimiento(request.POST, tipo=tipo)
    if form.is_valid() and _guardar_movimiento(request, tela, form):
        return _cambios(request, movida=tela, tipo=tipo)
    tela.refresh_from_db()  # para decir cuánto queda de verdad
    return _ventana_movimiento(request, tela, form, status=422)


# --- Quitar ---------------------------------------------------------------------------------


@require_http_methods(["GET", "POST"])
def quitar(request, pk):
    """Quitar una tela, con un paso de confirmación. Se borra también su historial.

    GET pregunta (en la ventana, o en una página sin JavaScript). POST la quita.
    """
    tela = obtener_o_404(request, Tela, pk=pk)
    if request.method == "POST":
        tela.delete()  # sus movimientos se borran con ella (on_delete=CASCADE)
        return _cambios(request)
    contexto = {
        "tela": tela,
        "movimientos": tela.movimientos.count(),
        "accion": reverse("telas:quitar", args=[tela.pk]),
        "titulo_pagina": "Quitar tela",
    }
    return responder_ventana(request, "telas/_quitar.html", contexto)
