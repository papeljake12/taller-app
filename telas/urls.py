"""Direcciones de telas. Archivo compartido: después de la tanda 2 solo lo cambia el
coordinador."""

from django.urls import path

from telas import vistas

app_name = "telas"

urlpatterns = [
    path("", vistas.inicio, name="inicio"),
    path("nueva/", vistas.nueva, name="nueva"),
    path("<int:pk>/movimiento/", vistas.movimiento, name="movimiento"),
    path("<int:pk>/quitar/", vistas.quitar, name="quitar"),
]
