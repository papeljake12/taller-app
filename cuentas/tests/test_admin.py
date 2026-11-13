"""Panel de administración: crear talleres y usuarias."""

import io

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from PIL import Image

from cuentas.models import Taller, Usuario
from tests import fabricas

CLAVE_NUEVA = "Una-clave-larga-2026"


def imagen_png():
    contenido = io.BytesIO()
    Image.new("RGB", (4, 4), "white").save(contenido, format="PNG")
    return SimpleUploadedFile("logo.png", contenido.getvalue(), content_type="image/png")


def datos_nueva_usuaria(**cambios):
    datos = {
        "username": "nueva",
        "usable_password": "true",
        "password1": CLAVE_NUEVA,
        "password2": CLAVE_NUEVA,
        "rol": Usuario.Rol.COSTURERA,
        "nombre_visible": "Nueva",
    }
    datos.update(cambios)
    return datos


@pytest.mark.parametrize(
    "direccion",
    ["/admin/", "/admin/cuentas/taller/", "/admin/cuentas/taller/add/",
     "/admin/cuentas/usuario/", "/admin/cuentas/usuario/add/"],
)
def test_el_administrador_abre_el_panel(sesion_administrador, direccion):
    assert sesion_administrador.get(direccion).status_code == 200


def test_una_duena_no_entra_al_panel(sesion_duena):
    respuesta = sesion_duena.get("/admin/")

    assert respuesta.status_code == 302
    assert "/admin/login/" in respuesta.url


def test_crear_un_taller_con_logo(sesion_administrador, settings, tmp_path):
    settings.MEDIA_ROOT = tmp_path

    respuesta = sesion_administrador.post(
        "/admin/cuentas/taller/add/",
        {"nombre": "Taller de prueba", "telefono": "", "logo": imagen_png()},
    )

    assert respuesta.status_code == 302
    taller = Taller.objects.get()
    assert taller.nombre == "Taller de prueba"
    assert taller.logo.name.startswith("talleres/logos/")


def test_un_logo_que_no_es_imagen_se_rechaza(sesion_administrador, settings, tmp_path):
    settings.MEDIA_ROOT = tmp_path
    archivo = SimpleUploadedFile("logo.png", b"esto no es una imagen", content_type="image/png")

    respuesta = sesion_administrador.post(
        "/admin/cuentas/taller/add/", {"nombre": "Taller de prueba", "logo": archivo}
    )

    assert respuesta.status_code == 200
    assert not Taller.objects.exists()


def test_crear_una_costurera_en_su_taller(sesion_administrador, taller):
    respuesta = sesion_administrador.post(
        "/admin/cuentas/usuario/add/", datos_nueva_usuaria(taller=taller.pk)
    )

    assert respuesta.status_code == 302
    nueva = Usuario.objects.get(username="nueva")
    assert nueva.taller == taller
    assert nueva.rol == Usuario.Rol.COSTURERA
    assert nueva.check_password(CLAVE_NUEVA)


def test_no_se_crea_una_usuaria_sin_taller(sesion_administrador):
    respuesta = sesion_administrador.post("/admin/cuentas/usuario/add/", datos_nueva_usuaria())

    assert respuesta.status_code == 200
    assert not Usuario.objects.filter(username="nueva").exists()


def test_al_editar_no_se_le_puede_quitar_el_taller(sesion_administrador, taller):
    costurera = fabricas.crear_usuaria(taller, username="marta", rol=Usuario.Rol.COSTURERA)
    datos = {
        "username": "marta",
        "is_active": "on",
        "date_joined_0": "2026-11-01",
        "date_joined_1": "08:00:00",
        "taller": "",
        "rol": Usuario.Rol.COSTURERA,
        "nombre_visible": "Marta",
    }

    respuesta = sesion_administrador.post(
        f"/admin/cuentas/usuario/{costurera.pk}/change/", datos
    )

    assert respuesta.status_code == 200
    assert "deben pertenecer a un taller" in respuesta.text
    costurera.refresh_from_db()
    assert costurera.taller == taller
