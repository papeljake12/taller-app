"""Pedido por dentro (T07): la ficha, la etapa, la encargada, la fecha de entrega, el
WhatsApp del cliente y eliminar el pedido.

Esqueleto de la tanda 2: la ficha abre con sus partes vacías y las acciones responden
"todavía no".
"""

from django.shortcuts import render
from django.views.decorators.http import require_POST

from config.esqueleto import todavia_no
from cuentas.aislamiento import obtener_o_404
from pedidos.models import Pedido


def detalle(request, pk):
    pedido = obtener_o_404(request, Pedido.objects.select_related("cliente", "encargada"), pk=pk)
    return render(request, "pedidos/pedido.html", {"pedido": pedido})


@require_POST
def etapa(request, pk):
    obtener_o_404(request, Pedido, pk=pk)
    return todavia_no("T07")


@require_POST
def encargada(request, pk):
    obtener_o_404(request, Pedido, pk=pk)
    return todavia_no("T07")


@require_POST
def entrega(request, pk):
    obtener_o_404(request, Pedido, pk=pk)
    return todavia_no("T07")


@require_POST
def whatsapp(request, pk):
    obtener_o_404(request, Pedido, pk=pk)
    return todavia_no("T07")


@require_POST
def eliminar(request, pk):
    obtener_o_404(request, Pedido, pk=pk)
    return todavia_no("T07")
