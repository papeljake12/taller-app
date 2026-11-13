"""Foto del pedido (T13): subir, cambiar y quitar.

Esqueleto de la tanda 2: cada acción comprueba que el pedido es del taller y responde
"todavía no".
"""

from django.views.decorators.http import require_POST

from config.esqueleto import todavia_no
from cuentas.aislamiento import obtener_o_404
from pedidos.models import Pedido


@require_POST
def subir(request, pk):
    obtener_o_404(request, Pedido, pk=pk)
    return todavia_no("T13")


@require_POST
def quitar(request, pk):
    obtener_o_404(request, Pedido, pk=pk)
    return todavia_no("T13")
