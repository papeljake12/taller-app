"""Tallas internas (T10) y abrir o cerrar el enlace público (T11).

Esqueleto de la tanda 2: cada acción comprueba que el pedido es del taller y responde
"todavía no".
"""

from django.views.decorators.http import require_POST

from config.esqueleto import todavia_no
from cuentas.aislamiento import obtener_o_404
from pedidos.models import Pedido


@require_POST
def nueva(request, pk):
    obtener_o_404(request, Pedido, pk=pk)
    return todavia_no("T10")


@require_POST
def quitar(request, pk, talla):
    obtener_o_404(request, Pedido, pk=pk)
    return todavia_no("T10")


@require_POST
def enlace(request, pk):
    obtener_o_404(request, Pedido, pk=pk)
    return todavia_no("T11")
