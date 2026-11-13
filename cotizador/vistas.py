"""Cotizador (T15): datos a la izquierda, resultado a la derecha, y "Mis prendas".

Esqueleto de la tanda 2: la pantalla abre con sus tarjetas vacías y las acciones responden
"todavía no".
"""

from django.shortcuts import render
from django.views.decorators.http import require_POST

from config.esqueleto import todavia_no
from cotizador.models import PrendaGuardada
from cuentas.aislamiento import obtener_o_404


def inicio(request):
    return render(request, "cotizador/inicio.html")


def calcular(request):
    """El resultado, que se actualiza mientras se escribe."""
    return todavia_no("T15")


@require_POST
def prenda_guardar(request):
    return todavia_no("T15")


@require_POST
def prenda_quitar(request, pk):
    obtener_o_404(request, PrendaGuardada, pk=pk)
    return todavia_no("T15")


@require_POST
def crear_pedido(request):
    return todavia_no("T15")
