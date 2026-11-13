"""T20. Mi taller: el nombre, el teléfono y el logo del taller, y las costureras."""

import re
from io import BytesIO

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client
from django.urls import reverse
from PIL import Image

from cuentas import formularios_mi_taller
from cuentas.formularios_mi_taller import reducir_logo
from cuentas.models import Taller, Usuario
from pedidos import fotos, mensajes
from tests import fabricas

pytestmark = pytest.mark.django_db

URL = reverse("cuentas:mi_taller")
URL_NUEVA = reverse("cuentas:costurera_nueva")
HTMX_TALLER = {"HX-Request": "true", "HX-Target": "tu-taller"}
HTMX_COSTURERAS = {"HX-Request": "true", "HX-Target": "costureras"}


@pytest.fixture(autouse=True)
def carpeta_de_logos(settings, tmp_path):
    """Los logos de las pruebas se guardan en una carpeta temporal, nunca en media/."""
    settings.MEDIA_ROOT = tmp_path
    return tmp_path


def imagen_de_prueba(ancho=300, alto=200, formato="PNG", modo="RGB", color=(37, 99, 201),
                     nombre="logo.png"):
    """Una imagen de verdad, hecha en memoria, como la que manda el navegador."""
    salida = BytesIO()
    Image.new(modo, (ancho, alto), color).save(salida, formato)
    return SimpleUploadedFile(nombre, salida.getvalue(), content_type=f"image/{formato.lower()}")


def logo_guardado(taller):
    """El logo como quedó en el disco: (ancho, alto, formato, modo)."""
    taller.refresh_from_db()
    with taller.logo.open("rb") as archivo, Image.open(archivo) as imagen:
        return imagen.width, imagen.height, imagen.format, imagen.mode


def guardar_taller(cliente, taller, headers=None, **datos):
    """Envía la tarjeta "Tu taller" con los datos del taller y los cambios de `datos`."""
    envio = {"nombre": taller.nombre, "telefono": taller.telefono, **datos}
    return cliente.post(URL, envio, headers=headers or {})


def editar(costurera):
    return reverse("cuentas:costurera_editar", args=[costurera.pk])


@pytest.fixture
def marta(taller):
    return fabricas.crear_usuaria(taller, rol=Usuario.Rol.COSTURERA, username="marta",
                                  nombre_visible="Marta")


# --- La pantalla -------------------------------------------------------------------------------


def test_la_pantalla_muestra_el_taller_y_sus_costureras(sesion_duena, taller, duena, marta):
    taller.telefono = "300 000 0000"
    taller.save()
    fabricas.crear_usuaria(taller, rol=Usuario.Rol.COSTURERA, username="yoli",
                           nombre_visible="Yolima", is_active=False)

    html = sesion_duena.get(URL).text

    assert ">Tu taller</h2>" in html and ">Costureras</h2>" in html
    assert f'value="{taller.nombre}"' in html
    assert 'value="300 000 0000"' in html
    assert "Aparece en el menú, en los mensajes de WhatsApp y en los recibos." in html
    assert "<strong>Marta</strong>" in html and "Usuario: marta" in html
    assert "<strong>Yolima</strong>" in html and ">Desactivada</span>" in html
    assert "No puede entrar, pero sus pedidos siguen guardados." in html
    assert ">1 activa</span>" in html
    # La dueña no sale en la lista de costureras.
    assert f"<strong>{duena.nombre}</strong>" not in html
    assert ">Agregar costurera</button>" in html
    assert 'href="#costurera-nueva-nombre_visible"' in html


def test_las_activas_van_primero(sesion_duena, taller):
    fabricas.crear_usuaria(taller, rol="costurera", nombre_visible="Ana", is_active=False)
    fabricas.crear_usuaria(taller, rol="costurera", nombre_visible="Carmen")
    fabricas.crear_usuaria(taller, rol="costurera", nombre_visible="Beatriz")

    html = sesion_duena.get(URL).text

    posiciones = [html.index(f"<strong>{n}</strong>") for n in ("Beatriz", "Carmen", "Ana")]
    assert posiciones == sorted(posiciones)


def test_sin_costureras_invita_a_agregar_la_primera(sesion_duena):
    html = sesion_duena.get(URL).text

    assert "Todavía no has agregado a nadie." in html
    assert "activas</span>" not in html


def test_no_se_ven_las_costureras_de_otro_taller(sesion_duena):
    otro = fabricas.crear_taller(nombre="Otro taller")
    fabricas.crear_usuaria(otro, rol="costurera", username="ajena", nombre_visible="Ajena")

    html = sesion_duena.get(URL).text

    assert "Ajena" not in html and "ajena" not in html
    assert "Otro taller" not in html


# --- Tu taller: nombre y teléfono --------------------------------------------------------------


def test_cambiar_el_nombre_devuelve_la_tarjeta_y_el_nombre_para_el_menu(sesion_duena, taller):
    respuesta = guardar_taller(sesion_duena, taller, HTMX_TALLER,
                               nombre="  Confecciones   de prueba ", telefono="300 123 4567")

    taller.refresh_from_db()
    assert respuesta.status_code == 200
    assert taller.nombre == "Confecciones de prueba"
    assert taller.telefono == "300 123 4567"
    html = respuesta.text
    assert "<html" not in html
    assert 'id="tu-taller"' in html
    assert "Listo: se guardaron los cambios." in html
    assert ('<span class="menu__taller" id="menu-taller" title="Confecciones de prueba" '
            'hx-swap-oob="true">Confecciones de prueba</span>' in html)
    assert "<title>Mi taller · Confecciones de prueba</title>" in html


def test_el_nombre_nuevo_sale_en_el_menu_y_en_los_mensajes(sesion_duena, taller):
    pedido = fabricas.crear_pedido(taller)

    guardar_taller(sesion_duena, taller, nombre="Confecciones de prueba")

    html = sesion_duena.get(reverse("pedidos:hoy")).text
    assert ('<span class="menu__taller" id="menu-taller" title="Confecciones de prueba">'
            'Confecciones de prueba</span>') in html
    pedido.refresh_from_db()
    assert mensajes.firma(pedido.taller) == "de Confecciones de prueba"


def test_sin_javascript_guardar_vuelve_a_mi_taller(sesion_duena, taller):
    respuesta = guardar_taller(sesion_duena, taller, nombre="Confecciones de prueba")

    assert respuesta.status_code == 302
    assert respuesta.url == URL + "#tu-taller"


@pytest.mark.parametrize(
    ("nombre", "mensaje"),
    [
        ("", "Escribe el nombre del taller."),
        ("    ", "Escribe el nombre del taller."),
        ("x" * 51, "Escribe máximo 50 letras en el nombre."),
    ],
)
def test_un_nombre_que_no_sirve_se_rechaza(sesion_duena, taller, nombre, mensaje):
    anterior = taller.nombre

    respuesta = guardar_taller(sesion_duena, taller, HTMX_TALLER, nombre=nombre)

    assert respuesta.status_code == 422
    assert mensaje in respuesta.text
    assert 'aria-invalid="true"' in respuesta.text
    taller.refresh_from_db()
    assert taller.nombre == anterior


def test_con_un_error_el_menu_sigue_con_el_nombre_guardado(sesion_duena, taller):
    anterior = taller.nombre
    falso = SimpleUploadedFile("logo.png", b"no soy una imagen", "image/png")

    respuesta = guardar_taller(sesion_duena, taller, nombre="Nombre que no se guarda",
                               logo=falso)

    assert respuesta.status_code == 422
    assert "<html" in respuesta.text
    assert f'<span class="menu__taller" id="menu-taller" title="{anterior}">{anterior}</span>' in respuesta.text
    taller.refresh_from_db()
    assert taller.nombre == anterior


@pytest.mark.parametrize("telefono", ["abc", "123", "300 123 4567 ext 2", "1" * 16])
def test_un_telefono_que_no_sirve_se_rechaza(sesion_duena, taller, telefono):
    respuesta = guardar_taller(sesion_duena, taller, HTMX_TALLER, telefono=telefono)

    assert respuesta.status_code == 422
    assert "Revisa el teléfono" in respuesta.text
    taller.refresh_from_db()
    assert taller.telefono == ""


def test_el_telefono_es_opcional_y_se_puede_borrar(sesion_duena, taller):
    taller.telefono = "300 123 4567"
    taller.save()

    respuesta = guardar_taller(sesion_duena, taller, HTMX_TALLER, telefono="")

    assert respuesta.status_code == 200
    taller.refresh_from_db()
    assert taller.telefono == ""


def test_guardar_no_toca_otro_taller(sesion_duena, taller):
    otro = fabricas.crear_taller(nombre="Otro taller")

    guardar_taller(sesion_duena, taller, nombre="Confecciones de prueba")

    otro.refresh_from_db()
    assert otro.nombre == "Otro taller"


# --- Tu taller: el logo ------------------------------------------------------------------------


def test_un_logo_grande_se_reduce_a_512_de_lado_largo(sesion_duena, taller, carpeta_de_logos):
    respuesta = guardar_taller(sesion_duena, taller, HTMX_TALLER,
                               logo=imagen_de_prueba(2000, 1000, formato="JPEG",
                                                     nombre="logo.jpg"))

    assert respuesta.status_code == 200
    assert logo_guardado(taller) == (512, 256, "JPEG", "RGB")
    assert taller.logo.name.startswith("talleres/logos/")
    assert (carpeta_de_logos / taller.logo.name).exists()
    # La tarjeta muestra el logo achicado a 160 x 80, sin deformarlo.
    assert f'src="{taller.logo.url}"' in respuesta.text
    assert 'width="160" height="80"' in respuesta.text
    assert ">Cambiar el logo (opcional)</label>" in respuesta.text


def test_un_logo_pequeno_no_se_agranda(taller):
    contenido = reducir_logo(imagen_de_prueba(100, 40))

    formularios_mi_taller.guardar_logo(taller, contenido)

    assert logo_guardado(taller)[:2] == (100, 40)


def test_un_logo_con_transparencia_queda_en_png_transparente(taller):
    transparente = imagen_de_prueba(600, 300, modo="RGBA", color=(0, 0, 0, 0))

    formularios_mi_taller.guardar_logo(taller, reducir_logo(transparente))

    assert logo_guardado(taller) == (512, 256, "PNG", "RGBA")
    assert taller.logo.name.endswith(".png")
    with taller.logo.open("rb") as archivo, Image.open(archivo) as imagen:
        assert imagen.getpixel((10, 10))[3] == 0


def test_el_nombre_del_logo_es_al_azar(taller):
    primero = reducir_logo(imagen_de_prueba(nombre="mi-logo.png"))
    segundo = reducir_logo(imagen_de_prueba(nombre="mi-logo.png"))

    assert primero.name != segundo.name
    assert "mi-logo" not in primero.name


def test_un_archivo_que_no_es_imagen_se_rechaza(sesion_duena, taller):
    falso = SimpleUploadedFile("logo.png", b"esto es un texto, no una imagen", "image/png")

    respuesta = guardar_taller(sesion_duena, taller, HTMX_TALLER, logo=falso)

    assert respuesta.status_code == 422
    assert "Ese archivo no es una imagen. Elige el logo en JPG o PNG." in respuesta.text
    assert 'id="tu-taller"' in respuesta.text and "<html" not in respuesta.text
    taller.refresh_from_db()
    assert not taller.logo


def test_un_logo_muy_pesado_se_rechaza(taller, monkeypatch):
    monkeypatch.setattr(fotos, "PESO_MAXIMO", 100)

    with pytest.raises(fotos.FotoInvalida, match="El logo pesa más de 10 MB"):
        reducir_logo(imagen_de_prueba(400, 400, formato="JPEG"))


def test_cambiar_el_logo_borra_el_anterior(sesion_duena, taller, carpeta_de_logos):
    guardar_taller(sesion_duena, taller, logo=imagen_de_prueba())
    taller.refresh_from_db()
    anterior = carpeta_de_logos / taller.logo.name

    guardar_taller(sesion_duena, taller, logo=imagen_de_prueba(color=(200, 0, 0)))

    taller.refresh_from_db()
    assert not anterior.exists()
    assert (carpeta_de_logos / taller.logo.name).exists()


def test_quitar_el_logo_borra_su_archivo(sesion_duena, taller, carpeta_de_logos):
    guardar_taller(sesion_duena, taller, logo=imagen_de_prueba())
    taller.refresh_from_db()
    archivo = carpeta_de_logos / taller.logo.name
    assert "Quitar el logo" in sesion_duena.get(URL).text

    respuesta = guardar_taller(sesion_duena, taller, HTMX_TALLER, quitar_logo="on")

    assert respuesta.status_code == 200
    taller.refresh_from_db()
    assert not taller.logo
    assert not archivo.exists()
    assert "Quitar el logo" not in respuesta.text


def test_guardar_sin_elegir_logo_deja_el_que_estaba(sesion_duena, taller):
    guardar_taller(sesion_duena, taller, logo=imagen_de_prueba())
    taller.refresh_from_db()
    nombre = taller.logo.name

    guardar_taller(sesion_duena, taller, nombre="Confecciones de prueba")

    taller.refresh_from_db()
    assert taller.logo.name == nombre


# --- Agregar costurera -------------------------------------------------------------------------


def agregar(cliente, headers=None, **datos):
    envio = {"nombre_visible": "Carmen", "username": "carmen",
             "contrasena": "hilo-y-aguja-2026", **datos}
    return cliente.post(URL_NUEVA, envio, headers=headers or {})


def test_agregar_una_costurera_la_crea_en_el_taller(sesion_duena, taller):
    respuesta = agregar(sesion_duena, HTMX_COSTURERAS)

    assert respuesta.status_code == 200
    persona = Usuario.objects.get(username="carmen")
    assert persona.taller == taller
    assert persona.rol == Usuario.Rol.COSTURERA
    assert persona.nombre_visible == "Carmen"
    assert persona.is_active
    assert persona.check_password("hilo-y-aguja-2026")
    html = respuesta.text
    assert "<html" not in html and 'id="costureras"' in html
    assert "<strong>Carmen</strong>" in html
    assert "Listo: Carmen ya puede entrar con el usuario «carmen»." in html
    # La contraseña nunca se vuelve a mostrar.
    assert "hilo-y-aguja-2026" not in html


def test_la_costurera_nueva_puede_entrar(client, sesion_duena):
    agregar(sesion_duena)
    sesion_duena.logout()

    respuesta = client.post(reverse("cuentas:entrar"),
                            {"username": "carmen", "password": "hilo-y-aguja-2026"})

    assert respuesta.status_code == 302
    assert respuesta.url == reverse("pedidos:hoy")


def test_sin_javascript_agregar_vuelve_a_mi_taller(sesion_duena):
    respuesta = agregar(sesion_duena)

    assert respuesta.status_code == 302
    assert respuesta.url == URL + "#costureras"


@pytest.mark.parametrize("usuario", ["marta", "Marta", " MARTA "])
def test_un_usuario_repetido_se_rechaza_con_un_mensaje_claro(sesion_duena, marta, usuario):
    respuesta = agregar(sesion_duena, HTMX_COSTURERAS, username=usuario)

    assert respuesta.status_code == 422
    assert "Ese usuario ya existe. Elige otro, por ejemplo con su apellido." in respuesta.text
    assert Usuario.objects.filter(username__iexact="marta").count() == 1


def test_un_usuario_de_otro_taller_tambien_cuenta_como_repetido(sesion_duena):
    otro = fabricas.crear_taller()
    fabricas.crear_usuaria(otro, rol="costurera", username="carmen")

    respuesta = agregar(sesion_duena, HTMX_COSTURERAS)

    assert respuesta.status_code == 422
    assert "Ese usuario ya existe." in respuesta.text
    assert Usuario.objects.filter(username="carmen").count() == 1


def test_un_usuario_con_espacios_se_rechaza(sesion_duena):
    respuesta = agregar(sesion_duena, HTMX_COSTURERAS, username="carmen lopez")

    assert respuesta.status_code == 422
    assert "Escribe el usuario sin espacios" in respuesta.text
    assert not Usuario.objects.filter(nombre_visible="Carmen").exists()


@pytest.mark.parametrize(
    ("contrasena", "mensaje"),
    [
        ("corta1", "La contraseña es muy corta: escribe por lo menos 8 caracteres."),
        ("12345678", "La contraseña no puede tener solo números."),
        ("password", "Esa contraseña es muy común."),
        ("carmen2026", "La contraseña se parece mucho al usuario."),
        ("", "Escribe una contraseña para ella."),
    ],
)
def test_una_contrasena_debil_se_rechaza(sesion_duena, contrasena, mensaje):
    respuesta = agregar(sesion_duena, HTMX_COSTURERAS, username="carmen2026",
                        contrasena=contrasena)

    assert respuesta.status_code == 422
    assert mensaje in respuesta.text
    assert not Usuario.objects.filter(username="carmen2026").exists()
    # El campo de la contraseña vuelve vacío y con el cursor puesto.
    campo = re.search(r'<input type="password"[^>]*>', respuesta.text).group()
    assert "value=" not in campo
    assert "autofocus" in campo


def test_sin_nombre_se_rechaza(sesion_duena):
    respuesta = agregar(sesion_duena, HTMX_COSTURERAS, nombre_visible="  ")

    assert respuesta.status_code == 422
    assert "Escribe el nombre de la costurera." in respuesta.text


def test_un_nombre_repetido_en_el_taller_se_rechaza(sesion_duena, marta):
    respuesta = agregar(sesion_duena, HTMX_COSTURERAS, nombre_visible="marta")

    assert respuesta.status_code == 422
    assert "Ya hay una persona con ese nombre en tu taller." in respuesta.text


def test_el_mismo_nombre_en_otro_taller_si_se_puede(sesion_duena):
    fabricas.crear_usuaria(fabricas.crear_taller(), rol="costurera", nombre_visible="Carmen")

    assert agregar(sesion_duena, HTMX_COSTURERAS).status_code == 200


def test_sin_javascript_un_error_sale_en_la_pagina_completa(sesion_duena):
    respuesta = agregar(sesion_duena, contrasena="corta1")

    assert respuesta.status_code == 422
    assert "<html" in respuesta.text and ">Tu taller</h2>" in respuesta.text
    assert "La contraseña es muy corta" in respuesta.text


def test_agregar_solo_se_hace_con_post(sesion_duena):
    assert sesion_duena.get(URL_NUEVA).status_code == 405


# --- Cambiar el nombre -------------------------------------------------------------------------


def test_cambiar_nombre_abre_el_formulario_en_su_fila(sesion_duena, marta):
    respuesta = sesion_duena.get(editar(marta), headers=HTMX_COSTURERAS)

    assert respuesta.status_code == 200
    html = respuesta.text
    assert "<html" not in html and 'id="costureras"' in html
    assert 'name="nombre_visible"' in html and 'value="Marta"' in html
    assert 'name="accion" value="nombre"' in html
    assert "autofocus" in html
    assert ">Cancelar</a>" in html


def test_cancelar_deja_la_fila_como_estaba(sesion_duena, marta):
    respuesta = sesion_duena.get(editar(marta) + "?cancelar=1", headers=HTMX_COSTURERAS)

    assert respuesta.status_code == 200
    assert ">Cambiar nombre</a>" in respuesta.text
    assert 'name="accion" value="nombre"' not in respuesta.text


def test_cambiar_el_nombre_lo_guarda(sesion_duena, marta):
    respuesta = sesion_duena.post(editar(marta),
                                  {"accion": "nombre", "nombre_visible": " Marta  Lucía "},
                                  headers=HTMX_COSTURERAS)

    assert respuesta.status_code == 200
    marta.refresh_from_db()
    assert marta.nombre_visible == "Marta Lucía"
    assert "<strong>Marta Lucía</strong>" in respuesta.text
    assert marta.username == "marta"


def test_un_nombre_vacio_o_repetido_no_se_guarda(sesion_duena, taller, marta):
    fabricas.crear_usuaria(taller, rol="costurera", nombre_visible="Carmen")

    vacio = sesion_duena.post(editar(marta), {"accion": "nombre", "nombre_visible": ""},
                              headers=HTMX_COSTURERAS)
    repetido = sesion_duena.post(editar(marta),
                                 {"accion": "nombre", "nombre_visible": "CARMEN"},
                                 headers=HTMX_COSTURERAS)

    assert vacio.status_code == repetido.status_code == 422
    assert "Escribe el nombre de la costurera." in vacio.text
    assert "Ya hay una persona con ese nombre en tu taller." in repetido.text
    marta.refresh_from_db()
    assert marta.nombre_visible == "Marta"


def test_volver_a_guardar_el_mismo_nombre_no_es_repetido(sesion_duena, marta):
    respuesta = sesion_duena.post(editar(marta), {"accion": "nombre", "nombre_visible": "Marta"},
                                  headers=HTMX_COSTURERAS)

    assert respuesta.status_code == 200


def test_sin_javascript_cambiar_nombre_abre_una_pagina(sesion_duena, marta):
    respuesta = sesion_duena.get(editar(marta))

    assert respuesta.status_code == 200
    assert "<html" in respuesta.text
    assert "<h1>Cambiar nombre</h1>" in respuesta.text  # como página, el título va en la hoja
    assert "Usuario: marta. Hoy aparece como Marta." in respuesta.text


def test_sin_javascript_guardar_el_nombre_vuelve_a_mi_taller(sesion_duena, marta):
    respuesta = sesion_duena.post(editar(marta), {"accion": "nombre", "nombre_visible": "Martica"})

    assert respuesta.status_code == 302
    assert respuesta.url == URL + "#costureras"
    marta.refresh_from_db()
    assert marta.nombre_visible == "Martica"


def test_sin_javascript_un_nombre_vacio_vuelve_a_la_pagina_con_el_mensaje(sesion_duena, marta):
    respuesta = sesion_duena.post(editar(marta), {"accion": "nombre", "nombre_visible": ""})

    assert respuesta.status_code == 422
    assert "<html" in respuesta.text
    assert "Escribe el nombre de la costurera." in respuesta.text
    assert "Hoy aparece como Marta." in respuesta.text


# --- Desactivar y volver a activar -------------------------------------------------------------


def test_desactivar_no_borra_a_la_costurera_ni_sus_pedidos(sesion_duena, taller, marta):
    pedido = fabricas.crear_pedido(taller, encargada=marta)

    respuesta = sesion_duena.post(editar(marta), {"accion": "desactivar"},
                                  headers=HTMX_COSTURERAS)

    assert respuesta.status_code == 200
    marta.refresh_from_db()
    assert not marta.is_active
    pedido.refresh_from_db()
    assert pedido.encargada == marta
    assert ">Desactivada</span>" in respuesta.text
    assert 'value="activar"' in respuesta.text


def test_una_costurera_desactivada_no_puede_entrar(client, sesion_duena, marta):
    sesion_duena.post(editar(marta), {"accion": "desactivar"})
    sesion_duena.logout()

    respuesta = client.post(reverse("cuentas:entrar"),
                            {"username": "marta", "password": fabricas.CLAVE})

    assert respuesta.status_code == 200
    assert "El usuario o la contraseña no son correctos." in respuesta.text


def test_desactivarla_cierra_la_sesion_que_tenia_abierta(marta):
    de_marta = Client()
    de_marta.force_login(marta)
    marta.is_active = False
    marta.save()

    respuesta = de_marta.get(reverse("pedidos:hoy"))

    assert respuesta.status_code == 302
    assert respuesta.url.startswith(reverse("cuentas:entrar"))


def test_activar_la_deja_entrar_otra_vez(client, sesion_duena, marta):
    marta.is_active = False
    marta.save()

    respuesta = sesion_duena.post(editar(marta), {"accion": "activar"}, headers=HTMX_COSTURERAS)

    assert respuesta.status_code == 200
    marta.refresh_from_db()
    assert marta.is_active
    assert 'value="desactivar"' in respuesta.text
    sesion_duena.logout()
    entrar = client.post(reverse("cuentas:entrar"),
                         {"username": "marta", "password": fabricas.CLAVE})
    assert entrar.status_code == 302


def test_sin_javascript_desactivar_vuelve_a_mi_taller(sesion_duena, marta):
    respuesta = sesion_duena.post(editar(marta), {"accion": "desactivar"})

    assert respuesta.status_code == 302
    assert respuesta.url == URL + "#costureras"


def test_una_accion_desconocida_no_cambia_nada(sesion_duena, marta):
    respuesta = sesion_duena.post(editar(marta), {"accion": "borrar"}, headers=HTMX_COSTURERAS)

    assert respuesta.status_code == 400
    assert Usuario.objects.filter(pk=marta.pk, is_active=True).exists()


# --- Solo las costureras de su taller ----------------------------------------------------------


def test_una_costurera_de_otro_taller_responde_404_y_no_cambia(sesion_duena):
    ajena = fabricas.crear_usuaria(fabricas.crear_taller(), rol="costurera",
                                   nombre_visible="Ajena")

    get = sesion_duena.get(editar(ajena), headers=HTMX_COSTURERAS)
    desactivar = sesion_duena.post(editar(ajena), {"accion": "desactivar"})
    renombrar = sesion_duena.post(editar(ajena), {"accion": "nombre", "nombre_visible": "Otra"})

    assert get.status_code == desactivar.status_code == renombrar.status_code == 404
    ajena.refresh_from_db()
    assert ajena.is_active and ajena.nombre_visible == "Ajena"


def test_la_duena_no_se_puede_editar_como_costurera(sesion_duena, taller, duena):
    otra_duena = fabricas.crear_usuaria(taller, rol=Usuario.Rol.DUENA, nombre_visible="Socia")

    for persona in (duena, otra_duena):
        respuesta = sesion_duena.post(editar(persona), {"accion": "desactivar"})
        assert respuesta.status_code == 404
        persona.refresh_from_db()
        assert persona.is_active


def test_el_administrador_no_se_puede_editar(sesion_duena, administrador):
    respuesta = sesion_duena.post(editar(administrador), {"accion": "desactivar"})

    assert respuesta.status_code == 404


def test_no_se_puede_poner_la_costurera_en_otro_taller(sesion_duena, taller):
    otro = fabricas.crear_taller()

    agregar(sesion_duena, taller=otro.pk, rol="duena", is_superuser="on", is_staff="on")

    persona = Usuario.objects.get(username="carmen")
    assert persona.taller == taller
    assert persona.rol == Usuario.Rol.COSTURERA
    assert not persona.is_superuser and not persona.is_staff
    assert Taller.objects.get(pk=otro.pk).usuarias.count() == 0
