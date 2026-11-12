"""Direcciones de la app de pedidos."""

from django.urls import path

from pedidos.vistas.hoy import hoy

app_name = "pedidos"

urlpatterns = [
    path("", hoy, name="hoy"),
]
