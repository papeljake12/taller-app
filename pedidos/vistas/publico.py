"""Formulario público de tallas (T11): lo abre cada persona del grupo con un enlace.

No pide cuenta. Solo sirve para el pedido de ese token.

Esqueleto de la tanda 2: abre la tarjeta vacía.
"""

from django.contrib.auth.decorators import login_not_required
from django.shortcuts import get_object_or_404, render

from pedidos.models import Pedido


@login_not_required
def formulario(request, token):
    pedido = get_object_or_404(
        Pedido.objects.select_related("cliente", "taller"), token_tallas=token
    )
    return render(request, "pedidos/publico.html", {"pedido": pedido})
