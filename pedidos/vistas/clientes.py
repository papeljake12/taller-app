"""Clientes (T04 y T19): la lista, crear y editar.

Esqueleto de la tanda 2: la lista abre vacía y crear o editar abre una ventana vacía.
"""

from django.shortcuts import render
from django.urls import reverse

from config.ventanas import responder_ventana
from cuentas.aislamiento import obtener_o_404
from pedidos.models import Cliente


def clientes(request):
    return render(request, "pedidos/clientes.html")


def nuevo(request):
    contexto = {"accion": reverse("pedidos:cliente_nuevo"), "titulo_pagina": "Nuevo cliente"}
    return responder_ventana(request, "pedidos/_cliente_form.html", contexto)


def editar(request, pk):
    cliente = obtener_o_404(request, Cliente, pk=pk)
    contexto = {
        "cliente": cliente,
        "accion": reverse("pedidos:cliente_editar", args=[cliente.pk]),
        "titulo_pagina": "Editar cliente",
    }
    return responder_ventana(request, "pedidos/_cliente_form.html", contexto)
