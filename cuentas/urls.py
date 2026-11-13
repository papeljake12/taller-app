"""Direcciones para entrar y salir."""

from django.urls import path

from cuentas.vistas import Entrar, Salir

app_name = "cuentas"

urlpatterns = [
    path("entrar/", Entrar.as_view(), name="entrar"),
    path("salir/", Salir.as_view(), name="salir"),
]
