"""Pantalla "Inicio de sesión" (docs/03-pantallas.md) y bloqueo por intentos fallidos."""

import pytest
from django.conf import settings

from cuentas.formularios import MENSAJE_DATOS_INCORRECTOS
from tests import fabricas
from tests.fabricas import CLAVE

ENTRAR = "/entrar/"
SALIR = "/salir/"
HOY = "/"


def entrar(client, username, password, **extra):
    return client.post(ENTRAR, {"username": username, "password": password}, **extra)


def tiene_sesion(client):
    return "_auth_user_id" in client.session


@pytest.mark.django_db
def test_sin_sesion_una_pantalla_interna_lleva_a_entrar(client):
    respuesta = client.get(HOY)

    assert respuesta.status_code == 302
    assert respuesta.url == f"{ENTRAR}?next=/"


@pytest.mark.django_db
def test_la_pagina_de_entrada_pide_usuario_y_contrasena(client):
    respuesta = client.get(ENTRAR)

    assert respuesta.status_code == 200
    assert "Usuario" in respuesta.text
    assert "Contraseña" in respuesta.text
    assert 'autocomplete="current-password"' in respuesta.text


def test_con_datos_correctos_entra_a_hoy(client, duena):
    respuesta = entrar(client, duena.username, CLAVE)

    assert respuesta.status_code == 302
    assert respuesta.url == HOY
    assert tiene_sesion(client)
    assert client.get(HOY).status_code == 200


def test_con_datos_incorrectos_el_mensaje_no_dice_cual_fallo(client, duena):
    clave_mala = entrar(client, duena.username, "otra-clave")
    usuario_malo = entrar(client, "no-existe", CLAVE)

    assert clave_mala.status_code == 200
    assert usuario_malo.status_code == 200
    assert MENSAJE_DATOS_INCORRECTOS in clave_mala.text
    assert MENSAJE_DATOS_INCORRECTOS in usuario_malo.text
    assert not tiene_sesion(client)


def test_una_usuaria_desactivada_no_puede_entrar(client, taller):
    desactivada = fabricas.crear_usuaria(taller, is_active=False)

    respuesta = entrar(client, desactivada.username, CLAVE)

    assert respuesta.status_code == 200
    assert MENSAJE_DATOS_INCORRECTOS in respuesta.text
    assert not tiene_sesion(client)


def test_con_cuatro_intentos_fallidos_todavia_puede_entrar(client, duena):
    for _ in range(4):
        entrar(client, duena.username, "otra-clave")

    respuesta = entrar(client, duena.username, CLAVE)

    assert respuesta.status_code == 302
    assert tiene_sesion(client)


def test_despues_de_cinco_intentos_fallidos_bloquea_aunque_la_clave_sea_buena(client, duena):
    for _ in range(5):
        entrar(client, duena.username, "otra-clave")

    respuesta = entrar(client, duena.username, CLAVE)

    assert respuesta.status_code == 429
    assert "Acceso bloqueado" in respuesta.text
    assert "espera 15 minutos" in respuesta.text
    assert not tiene_sesion(client)


def test_el_bloqueo_es_solo_para_ese_usuario_en_ese_equipo(client, taller, duena):
    otra = fabricas.crear_usuaria(taller)
    for _ in range(5):
        entrar(client, duena.username, "otra-clave")

    # Otra usuaria desde el mismo equipo sí puede entrar.
    assert entrar(client, otra.username, CLAVE).status_code == 302
    client.logout()
    # La misma usuaria desde otro equipo (otra dirección de internet) también.
    assert entrar(client, duena.username, CLAVE, REMOTE_ADDR="10.0.0.2").status_code == 302


def test_la_espera_del_bloqueo_es_de_15_minutos():
    assert settings.AXES_FAILURE_LIMIT == 5
    assert settings.AXES_COOLOFF_TIME.total_seconds() == 15 * 60


def test_si_ya_tiene_sesion_entrar_la_lleva_a_hoy(sesion_duena):
    respuesta = sesion_duena.get(ENTRAR)

    assert respuesta.status_code == 302
    assert respuesta.url == HOY


def test_no_redirige_a_otro_sitio_despues_de_entrar(client, duena):
    respuesta = client.post(
        f"{ENTRAR}?next=https://sitio-ajeno.example/",
        {"username": duena.username, "password": CLAVE, "next": "https://sitio-ajeno.example/"},
    )

    assert respuesta.status_code == 302
    assert respuesta.url == HOY


def test_salir_cierra_la_sesion(sesion_duena):
    respuesta = sesion_duena.post(SALIR)

    assert respuesta.status_code == 302
    assert respuesta.url == ENTRAR
    assert not tiene_sesion(sesion_duena)
    assert sesion_duena.get(HOY).status_code == 302


def test_salir_no_funciona_con_un_simple_enlace(sesion_duena):
    respuesta = sesion_duena.get(SALIR)

    assert respuesta.status_code == 405
    assert tiene_sesion(sesion_duena)


def test_la_sesion_se_cierra_tras_7_dias_sin_uso(client, duena):
    entrar(client, duena.username, CLAVE)

    assert client.session.get_expiry_age() == 7 * 24 * 60 * 60
    # Cada visita vuelve a empezar la cuenta de los 7 días.
    assert settings.SESSION_SAVE_EVERY_REQUEST is True
