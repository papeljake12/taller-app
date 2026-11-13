"""Pantalla Hoy (T06): la de entrada, y sus acciones sin recargar la página.

Esqueleto de la tanda 2: la pantalla abre con sus tarjetas vacías y las acciones responden
"todavía no".
"""

from django.shortcuts import render
from django.utils import timezone
from django.views.decorators.http import require_POST

from config.esqueleto import todavia_no
from cuentas.aislamiento import obtener_o_404
from pedidos.models import Pedido


def hoy(request):
    return render(request, "pedidos/hoy.html", {"hoy": timezone.localdate()})


@require_POST
def accion(request, pk, accion):
    """Marcar como listo, marcar como entregado... desde "Qué hacer hoy"."""
    obtener_o_404(request, Pedido, pk=pk)
    return todavia_no("T06")
