"""Pedidos (T05): la lista con filtros y buscador, "Nuevo pedido" y el buscador del menú.

Esqueleto de la tanda 2: la lista abre vacía y "Nuevo pedido" abre una ventana vacía.
"""

from django.shortcuts import render
from django.urls import reverse

from config.ventanas import responder_ventana


def lista(request):
    return render(request, "pedidos/lista.html")


def nuevo(request):
    """Ventana "Nuevo pedido". Se abre desde el botón de cualquier pantalla."""
    contexto = {"accion": reverse("pedidos:nuevo"), "titulo_pagina": "Nuevo pedido"}
    return responder_ventana(request, "pedidos/_nuevo.html", contexto)


def buscar(request):
    """Resultados del buscador del menú: pedidos y clientes."""
    return render(request, "pedidos/buscar.html", {"q": request.GET.get("q", "").strip()})
