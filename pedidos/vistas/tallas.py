"""Tarjeta "Tallas" del pedido por dentro (T10): agregar y quitar tallas a mano, y abrir o
cerrar el enlace público (el formulario del enlace es T11, en pedidos/vistas/publico.py).

Cada acción responde con la tarjeta entera (id "tarjeta-tallas"), que HTMX pone en el lugar
de la vieja. Sin JavaScript, el formulario se envía normal y se vuelve al pedido.

La ficha del pedido (pedidos/vistas/detalle.py) arma la tarjeta con `tarjeta(request,
pedido)`: así la tarjeta sale igual al abrir el pedido y después de cada acción.

Permisos (T21, docs/04-permisos.md): la costurera ve las tallas y las agrega o quita a mano,
pero abrir o cerrar el enlace público es manejar el pedido: solo la dueña.
"""

from django.http import HttpResponseBadRequest
from django.shortcuts import redirect, render
from django.urls import reverse
from django.views.decorators.http import require_POST

from config.ventanas import es_htmx
from cuentas.aislamiento import obtener_o_404
from cuentas.permisos import exigir_duena
from pedidos import calculos, mensajes
from pedidos.formularios.tallas import TallaForm, nombre_de_talla
from pedidos.models import Pedido, Talla

MEDIDAS = (("pecho", "Pecho"), ("cintura", "cintura"), ("cadera", "cadera"), ("largo", "largo"))


def texto_medidas(talla):
    """ "Pecho 92, cintura 80,5, cadera 98 cm", o "" si no tiene medidas."""
    partes = []
    for campo, nombre in MEDIDAS:
        valor = getattr(talla, campo)
        if valor is not None:
            numero = f"{valor.normalize():f}".replace(".", ",")
            partes.append(f"{nombre} {numero}")
    if not partes:
        return ""
    partes[0] = partes[0][0].upper() + partes[0][1:]
    return ", ".join(partes) + " cm"


def detalle_de(talla):
    """La línea bajo el nombre: medidas, nota y de dónde llegó.

    "Pecho 92, cintura 80, cadera 98 cm. Manga larga. Agregada en el taller."
    """
    partes = [texto_medidas(talla), talla.nota.strip().rstrip("."), talla.get_origen_display()]
    return " ".join(f"{p}." for p in partes if p)


def tarjeta(request, pedido, form=None, enfocar=False, ver_personas=False):
    """Todo lo que dibuja la tarjeta "Tallas" (pedidos/_tallas.html).

    - form: el formulario para agregar a mano (con sus errores, si los hubo).
    - enfocar: pone el cursor en el nombre (después de agregar o si hubo errores).
    - ver_personas: deja abierta la lista de personas (después de agregar o quitar).
    """
    recibidas, esperadas = calculos.tallas_recibidas(pedido)
    por_talla = calculos.tallas_por_talla(pedido)
    # La barra más larga es la de la talla con más personas, como en el diseño. "A la
    # medida" no lleva barra: va en su propio renglón, porque no es una talla de la tabla.
    normales = [(talla, n) for talla, n in por_talla if talla != Pedido.MEDIDA]
    mayor = max((n for _, n in normales), default=0)
    personas = [
        {"talla": t, "nombre_talla": nombre_de_talla(t.talla), "detalle": detalle_de(t)}
        for t in pedido.tallas.all()
    ]
    enlace = request.build_absolute_uri(
        reverse("pedidos:publico_tallas", args=[pedido.token_tallas])
    )
    form = form or TallaForm(pedido=pedido)
    if enfocar:
        # El cursor va al primer campo con error o, si no hay, al nombre de la siguiente.
        primero = next(iter(form.errors), "nombre") if form.is_bound else "nombre"
        form.fields.get(primero, form.fields["nombre"]).widget.attrs["autofocus"] = True
    return {
        "recibidas": recibidas,
        "esperadas": esperadas,
        "porcentaje": min(100, calculos.porcentaje(recibidas, esperadas)),
        "filas": [
            {"talla": talla, "cantidad": n, "porcentaje": calculos.porcentaje(n, mayor)}
            for talla, n in normales
        ],
        "a_la_medida": dict(por_talla).get(Pedido.MEDIDA, 0),
        "personas": personas,
        "enlace": enlace,
        "resumen": mensajes.texto_tallas(pedido),
        "form": form,
        "enfocar": enfocar,
        "ver_personas": ver_personas,
    }


def _responder(request, pedido, status=200, **opciones):
    """La tarjeta sola si la pidió HTMX; si no, de vuelta al pedido."""
    if es_htmx(request):
        contexto = {"pedido": pedido, "tarjeta_tallas": tarjeta(request, pedido, **opciones)}
        return render(request, "pedidos/_tallas.html", contexto, status=status)
    return redirect(reverse("pedidos:detalle", args=[pedido.pk]) + "#tarjeta-tallas")


@require_POST
def nueva(request, pk):
    pedido = obtener_o_404(request, Pedido.objects.select_related("cliente"), pk=pk)
    form = TallaForm(request.POST, pedido=pedido)
    if not form.is_valid():
        if es_htmx(request):
            return _responder(request, pedido, status=422, form=form, enfocar=True)
        # Sin JavaScript: el formulario con sus errores, en una página aparte.
        contexto = {
            "pedido": pedido,
            "form": form,
            "plantilla_ventana": "pedidos/_talla_ventana.html",
            "accion": reverse("pedidos:talla_nueva", args=[pedido.pk]),
            "titulo_pagina": "Agregar talla",
        }
        return render(request, "piezas/pagina_ventana.html", contexto, status=422)
    form.save()
    return _responder(request, pedido, enfocar=True, ver_personas=True)


@require_POST
def quitar(request, pk, talla):
    pedido = obtener_o_404(request, Pedido.objects.select_related("cliente"), pk=pk)
    # La talla tiene que ser de este pedido (y por lo tanto de este taller).
    obtener_o_404(request, Talla.objects.filter(pedido=pedido), pk=talla).delete()
    return _responder(request, pedido, ver_personas=True)


@require_POST
def enlace(request, pk):
    pedido = obtener_o_404(request, Pedido.objects.select_related("cliente"), pk=pk)
    exigir_duena(request)
    abiertas = request.POST.get("abiertas")
    if abiertas not in ("si", "no"):
        return HttpResponseBadRequest("Falta decir si el enlace queda abierto o cerrado.")
    pedido.tallas_abiertas = abiertas == "si"
    pedido.save(update_fields=["tallas_abiertas", "actualizado"])
    return _responder(request, pedido)
