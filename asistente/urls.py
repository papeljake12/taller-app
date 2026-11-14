"""Direcciones del asistente (docs/11-plan-tanda-7.md, sección 1.5). Archivo congelado."""

from django.urls import path

from asistente import vistas

app_name = "asistente"

urlpatterns = [
    path("", vistas.panel, name="panel"),
    path("preguntar/", vistas.preguntar, name="preguntar"),
    path("nueva/", vistas.nueva, name="nueva"),
]
