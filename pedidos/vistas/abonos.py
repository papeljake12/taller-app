"""Abonos (T08) y recibo en PDF (T09).

Esqueleto de la tanda 2: cada acción comprueba que el pedido es del taller y responde
"todavía no".
"""

from django.views.decorators.http import require_GET, require_POST

from config.esqueleto import todavia_no
from cuentas.aislamiento import obtener_o_404
from pedidos.models import Pedido


@require_POST
def nuevo(request, pk):
    obtener_o_404(request, Pedido, pk=pk)
    return todavia_no("T08")


@require_POST
def quitar(request, pk, abono):
    obtener_o_404(request, Pedido, pk=pk)
    return todavia_no("T08")


@require_GET
def recibo(request, pk, abono):
    obtener_o_404(request, Pedido, pk=pk)
    return todavia_no("T09")
