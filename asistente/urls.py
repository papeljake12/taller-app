"""Direcciones del asistente (docs/11-plan-tanda-7.md, sección 1.5, y docs/13-plan-tanda-8.md,
sección 1.3). Archivo congelado."""

from django.urls import path

from asistente import vistas

app_name = "asistente"

urlpatterns = [
    path("", vistas.panel, name="panel"),
    path("preguntar/", vistas.preguntar, name="preguntar"),
    path("nueva/", vistas.nueva, name="nueva"),
    path("confirmar/", vistas.confirmar, name="confirmar"),
]
