"""Modelos Taller y Usuario."""

import pytest
from django.conf import settings
from django.db import IntegrityError, transaction

from cuentas.models import Usuario
from tests import fabricas


def test_el_proyecto_usa_su_propio_usuario():
    assert settings.AUTH_USER_MODEL == "cuentas.Usuario"


def test_una_usuaria_pertenece_a_su_taller(taller):
    usuaria = fabricas.crear_usuaria(taller, rol=Usuario.Rol.COSTURERA)

    assert usuaria.taller == taller
    assert list(taller.usuarias.all()) == [usuaria]
    assert usuaria.get_rol_display() == "Costurera"


@pytest.mark.django_db
def test_una_duena_o_costurera_sin_taller_no_se_puede_guardar():
    with pytest.raises(IntegrityError), transaction.atomic():
        Usuario.objects.create_user(username="sin-taller", password="x")


def test_el_administrador_no_necesita_taller(administrador):
    assert administrador.taller is None
    assert administrador.is_superuser


@pytest.mark.django_db
def test_el_rol_por_defecto_es_costurera():
    assert Usuario._meta.get_field("rol").default == Usuario.Rol.COSTURERA


def test_el_nombre_para_mostrar(taller):
    con_nombre = fabricas.crear_usuaria(taller, nombre_visible="Marta")
    sin_nombre = fabricas.crear_usuaria(taller, username="yolima", nombre_visible="")

    assert str(con_nombre) == "Marta"
    assert sin_nombre.nombre == "yolima"


def test_el_taller_se_muestra_por_su_nombre(db):
    assert str(fabricas.crear_taller(nombre="Taller de prueba")) == "Taller de prueba"


def test_un_taller_con_usuarias_no_se_borra_por_accidente(taller, duena):
    with pytest.raises(Exception), transaction.atomic():
        taller.delete()
    assert Usuario.objects.filter(pk=duena.pk).exists()
