"""Prueba de humo: lo mínimo para saber que el proyecto arranca bien."""

from datetime import date

import pytest
from django.conf import settings
from django.db import connection
from django.utils.formats import date_format


@pytest.mark.django_db
def test_la_pagina_de_inicio_responde(client):
    respuesta = client.get("/")

    assert respuesta.status_code == 200
    assert "Hoy" in respuesta.text


@pytest.mark.django_db
def test_la_base_de_datos_es_postgresql_y_responde():
    assert connection.vendor == "postgresql"
    with connection.cursor() as cursor:
        cursor.execute("SELECT 1")
        assert cursor.fetchone() == (1,)


def test_idioma_y_zona_horaria_de_colombia():
    assert settings.LANGUAGE_CODE == "es-co"
    assert settings.TIME_ZONE == "America/Bogota"
    assert settings.USE_TZ is True


def test_las_fechas_salen_en_espanol():
    fecha = date(2026, 11, 11)

    # Las traducciones de Django para Colombia escriben días y meses con mayúscula;
    # aquí solo se comprueba que salgan en español.
    assert date_format(fecha, r"l, j \d\e F").lower() == "miércoles, 11 de noviembre"
