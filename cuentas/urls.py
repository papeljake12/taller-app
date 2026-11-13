"""Direcciones para entrar y salir, y Mi taller (T20).

Archivo compartido: después de la tanda 2 solo lo cambia el coordinador.
"""

from django.urls import path

from cuentas import mi_taller
from cuentas.vistas import Entrar, Salir

app_name = "cuentas"

urlpatterns = [
    path("entrar/", Entrar.as_view(), name="entrar"),
    path("salir/", Salir.as_view(), name="salir"),
    path("mi-taller/", mi_taller.mi_taller, name="mi_taller"),
    path("mi-taller/costureras/", mi_taller.costurera_nueva, name="costurera_nueva"),
    path("mi-taller/costureras/<int:pk>/", mi_taller.costurera_editar, name="costurera_editar"),
]
