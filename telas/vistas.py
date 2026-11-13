"""Telas (T16): inventario, "Entró" y "Usé", agregar y quitar.

Esqueleto de la tanda 2: la pantalla abre con sus tarjetas vacías y las acciones responden
"todavía no".
"""

from django.shortcuts import render
from django.urls import reverse
from django.views.decorators.http import require_POST

from config.esqueleto import todavia_no
from config.ventanas import responder_ventana
from cuentas.aislamiento import obtener_o_404
from telas.models import Tela


def inicio(request):
    return render(request, "telas/inicio.html")


def nueva(request):
    contexto = {"accion": reverse("telas:nueva"), "titulo_pagina": "Nueva tela"}
    return responder_ventana(request, "telas/_nueva.html", contexto)


@require_POST
def movimiento(request, pk):
    """Entró suma metros y Usé resta, sin bajar de 0."""
    obtener_o_404(request, Tela, pk=pk)
    return todavia_no("T16")


@require_POST
def quitar(request, pk):
    obtener_o_404(request, Tela, pk=pk)
    return todavia_no("T16")
