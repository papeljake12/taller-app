"""Direcciones del cotizador. Archivo compartido: después de la tanda 2 solo lo cambia el
coordinador."""

from django.urls import path

from cotizador import vistas

app_name = "cotizador"

urlpatterns = [
    path("", vistas.inicio, name="inicio"),
    path("calcular/", vistas.calcular, name="calcular"),
    path("prendas/", vistas.prenda_guardar, name="prenda_guardar"),
    path("prendas/<int:pk>/quitar/", vistas.prenda_quitar, name="prenda_quitar"),
    path("crear-pedido/", vistas.crear_pedido, name="crear_pedido"),
]
