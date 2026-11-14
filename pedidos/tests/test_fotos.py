"""T13. Fotos: la foto del pedido (subir, cambiar y quitar) y "Trabajos del taller" en Hoy."""

import json
from io import BytesIO
from pathlib import Path

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse
from PIL import Image

from pedidos import fotos
from pedidos.models import Pedido
from tests import fabricas

pytestmark = pytest.mark.django_db

HTMX = {"HX-Request": "true", "HX-Target": "pedido-foto"}


@pytest.fixture(autouse=True)
def carpeta_de_fotos(settings, tmp_path):
    """Las fotos de las pruebas se guardan en una carpeta temporal, nunca en media/."""
    settings.MEDIA_ROOT = tmp_path
    return tmp_path


@pytest.fixture
def pedido(taller):
    return fabricas.crear_pedido(taller, detalle="12 vestidos de fantasía de prueba")


def foto_de_prueba(ancho=300, alto=200, formato="JPEG", modo="RGB", color=(37, 99, 201),
                   nombre="foto.jpg", **opciones):
    """Una foto de verdad, hecha en memoria, como la que manda el navegador."""
    salida = BytesIO()
    Image.new(modo, (ancho, alto), color).save(salida, formato, **opciones)
    return SimpleUploadedFile(nombre, salida.getvalue(), content_type="image/jpeg")


def foto_guardada(pedido):
    """La foto del pedido como quedó en el disco: (ancho, alto, formato)."""
    pedido.refresh_from_db()
    with pedido.foto.open("rb") as archivo, Image.open(archivo) as imagen:
        return imagen.width, imagen.height, imagen.format


def subir(cliente, pedido, archivo, **extra):
    return cliente.post(reverse("pedidos:foto", args=[pedido.pk]), {"foto": archivo}, **extra)


def url_quitar(pedido):
    return reverse("pedidos:foto_quitar", args=[pedido.pk])


def _existe(ruta):
    return Path(ruta).exists()


def poner_foto(pedido):
    """El pedido con una foto ya guardada (como si se hubiera subido)."""
    fotos.guardar(pedido, fotos.reducir(foto_de_prueba()))
    return pedido.foto.path


# --- Reducir la foto ---------------------------------------------------------------------------


def test_una_foto_grande_se_reduce_a_1600_de_lado_largo(sesion_duena, pedido, carpeta_de_fotos):
    respuesta = subir(sesion_duena, pedido, foto_de_prueba(3000, 2000))

    assert respuesta.status_code == 302
    assert respuesta.url == reverse("pedidos:detalle", args=[pedido.pk]) + "#pedido-foto"
    assert foto_guardada(pedido) == (1600, 1067, "JPEG")
    assert pedido.foto.name.startswith("pedidos/fotos/")
    assert (carpeta_de_fotos / pedido.foto.name).exists()


def test_una_foto_pequena_no_se_agranda(pedido):
    contenido = fotos.reducir(foto_de_prueba(800, 600, formato="PNG", nombre="foto.png"))
    fotos.guardar(pedido, contenido)

    assert foto_guardada(pedido) == (800, 600, "JPEG")


def test_el_nombre_del_archivo_es_al_azar(pedido):
    primero = fotos.reducir(foto_de_prueba(nombre="vestido.jpg"))
    segundo = fotos.reducir(foto_de_prueba(nombre="vestido.jpg"))

    assert primero.name != segundo.name
    assert "vestido" not in primero.name
    assert primero.name.endswith(".jpg") and len(primero.name) == 36


def test_la_foto_se_endereza_segun_el_celular(pedido):
    # La cámara la guardó acostada (300 x 200) y anotó "girar 90 grados" (orientación 6).
    exif = Image.Exif()
    exif[0x0112] = 6

    fotos.guardar(pedido, fotos.reducir(foto_de_prueba(300, 200, exif=exif)))

    assert foto_guardada(pedido)[:2] == (200, 300)


def test_lo_transparente_queda_blanco(pedido):
    transparente = foto_de_prueba(40, 40, formato="PNG", modo="RGBA", color=(0, 0, 0, 0))

    fotos.guardar(pedido, fotos.reducir(transparente))

    with pedido.foto.open("rb") as archivo, Image.open(archivo) as imagen:
        assert all(canal > 245 for canal in imagen.getpixel((20, 20)))


# --- Lo que no es una foto se rechaza ----------------------------------------------------------


def test_un_texto_con_nombre_de_foto_se_rechaza(sesion_duena, pedido):
    falsa = SimpleUploadedFile("foto.jpg", b"esto es un texto, no una foto", "image/jpeg")

    respuesta = subir(sesion_duena, pedido, falsa, headers=HTMX)

    assert respuesta.status_code == 422
    assert "Ese archivo no es una foto." in respuesta.text
    assert 'id="pedido-foto"' in respuesta.text and "<html" not in respuesta.text
    pedido.refresh_from_db()
    assert not pedido.foto


def test_una_foto_cortada_se_rechaza(pedido):
    entera = foto_de_prueba().read()
    cortada = SimpleUploadedFile("foto.jpg", entera[: len(entera) // 2], "image/jpeg")

    with pytest.raises(fotos.FotoInvalida, match="Ese archivo no es una foto."):
        fotos.reducir(cortada)


def test_un_formato_que_no_es_de_foto_se_rechaza(pedido):
    # Un PDF hecho por Pillow: es una "imagen" que Pillow sabe escribir, pero no una foto.
    salida = BytesIO()
    Image.new("RGB", (20, 20)).save(salida, "PDF")

    with pytest.raises(fotos.FotoInvalida, match="Ese archivo no es una foto."):
        fotos.reducir(SimpleUploadedFile("foto.jpg", salida.getvalue()))


def test_una_foto_muy_pesada_se_rechaza(sesion_duena, pedido, monkeypatch):
    monkeypatch.setattr(fotos, "PESO_MAXIMO", 1000)

    respuesta = subir(sesion_duena, pedido, foto_de_prueba(1200, 900, quality=100), headers=HTMX)

    assert respuesta.status_code == 422
    assert "La foto pesa más de 10 MB. Elige una más liviana." in respuesta.text
    pedido.refresh_from_db()
    assert not pedido.foto


def test_una_foto_de_demasiados_pixeles_se_rechaza(pedido, monkeypatch):
    monkeypatch.setattr(fotos, "PIXELES_MAXIMOS", 100 * 100)

    with pytest.raises(fotos.FotoInvalida, match="demasiado grande"):
        fotos.reducir(foto_de_prueba(200, 100))


def test_sin_archivo_pide_elegir_una_foto(sesion_duena, pedido):
    respuesta = sesion_duena.post(reverse("pedidos:foto", args=[pedido.pk]), headers=HTMX)

    assert respuesta.status_code == 422
    assert "Elige una foto." in respuesta.text
    assert 'aria-invalid="true"' in respuesta.text


def test_sin_javascript_el_error_sale_en_la_pagina_del_pedido(sesion_duena, pedido):
    falsa = SimpleUploadedFile("foto.jpg", b"no soy una foto", "image/jpeg")

    respuesta = subir(sesion_duena, pedido, falsa)

    assert respuesta.status_code == 422
    assert "<html" in respuesta.text
    assert "Ese archivo no es una foto." in respuesta.text
    assert 'aria-label="Pago"' in respuesta.text


# --- Subir, cambiar y quitar -----------------------------------------------------------------


def test_con_htmx_subir_devuelve_solo_la_tarjeta_con_la_foto(sesion_duena, pedido):
    respuesta = subir(sesion_duena, pedido, foto_de_prueba(), headers=HTMX)

    pedido.refresh_from_db()
    assert respuesta.status_code == 200
    assert "<html" not in respuesta.text
    assert f'src="{pedido.foto.url}"' in respuesta.text
    assert 'alt="Foto del trabajo: 12 vestidos de fantasía de prueba"' in respuesta.text
    assert "Cambiar foto<input" in respuesta.text
    assert ">Quitar</a>" in respuesta.text
    # La miniatura de la tarjeta de la etapa es la misma foto: llega para cambiarla.
    assert 'id="pedido-etapa"' in respuesta.text and 'class="mini mini--grande"><img' in (
        respuesta.text
    )


def test_cambiar_la_foto_borra_la_anterior(sesion_duena, pedido):
    anterior = poner_foto(pedido)

    subir(sesion_duena, pedido, foto_de_prueba(500, 500), headers=HTMX)

    pedido.refresh_from_db()
    assert pedido.foto.path != anterior
    assert not _existe(anterior)
    assert _existe(pedido.foto.path)
    assert foto_guardada(pedido)[:2] == (500, 500)


def test_si_la_nueva_no_sirve_la_anterior_se_queda(sesion_duena, pedido):
    anterior = poner_foto(pedido)

    subir(sesion_duena, pedido, SimpleUploadedFile("otra.jpg", b"texto"), headers=HTMX)

    pedido.refresh_from_db()
    assert pedido.foto.path == anterior and _existe(anterior)


def test_quitar_primero_pregunta(sesion_duena, pedido):
    archivo = poner_foto(pedido)

    respuesta = sesion_duena.get(url_quitar(pedido), headers=HTMX)

    assert "¿Quitar la foto de este pedido?" in respuesta.text
    assert ">Sí, quitar la foto</button>" in respuesta.text
    assert f'hx-get="{url_quitar(pedido)}?cancelar=1"' in respuesta.text
    assert _existe(archivo)


def test_la_pregunta_atiende_solo_el_ultimo_toque(sesion_duena, pedido):
    """"Cancelar" y "Sí, quitar la foto" cambian la misma tarjeta: si se tocan seguidos, el
    último cancela al anterior, para que una respuesta tardía no vuelva a pintar la foto."""
    poner_foto(pedido)

    respuesta = sesion_duena.get(url_quitar(pedido), headers=HTMX)

    sincronizar = 'hx-sync="closest .tarjeta:replace"'
    assert respuesta.text.count(sincronizar) == 2
    assert f'hx-post="{url_quitar(pedido)}" {sincronizar}' in respuesta.text
    assert f'hx-get="{url_quitar(pedido)}?cancelar=1" {sincronizar}' in respuesta.text


def test_cancelar_deja_la_tarjeta_como_estaba(sesion_duena, pedido):
    poner_foto(pedido)

    respuesta = sesion_duena.get(url_quitar(pedido) + "?cancelar=1", headers=HTMX)

    assert "¿Quitar la foto" not in respuesta.text
    assert ">Quitar</a>" in respuesta.text


def test_sin_javascript_la_pregunta_es_una_pagina(sesion_duena, pedido):
    poner_foto(pedido)

    respuesta = sesion_duena.get(url_quitar(pedido))

    assert "<html" in respuesta.text
    assert "¿Quitar la foto del pedido de" in respuesta.text
    assert f'action="{url_quitar(pedido)}"' in respuesta.text


def test_quitar_la_foto_borra_el_archivo(sesion_duena, pedido):
    archivo = poner_foto(pedido)

    respuesta = sesion_duena.post(url_quitar(pedido), headers=HTMX)

    pedido.refresh_from_db()
    assert not pedido.foto
    assert not _existe(archivo)
    assert respuesta.status_code == 200
    assert "Sale en Hoy y en la lista de pedidos" in respuesta.text
    assert "Subir foto<input" in respuesta.text


def test_sin_javascript_quitar_vuelve_al_pedido(sesion_duena, pedido):
    poner_foto(pedido)

    respuesta = sesion_duena.post(url_quitar(pedido))

    assert respuesta.status_code == 302
    assert respuesta.url.endswith("#pedido-foto")
    pedido.refresh_from_db()
    assert not pedido.foto


def test_desde_la_pagina_de_la_pregunta_con_javascript_vuelve_al_pedido(sesion_duena, pedido):
    poner_foto(pedido)

    respuesta = sesion_duena.post(
        url_quitar(pedido), headers={"HX-Request": "true", "HX-Target": "ventana"}
    )

    assert respuesta.headers["HX-Redirect"].endswith(f"/pedidos/{pedido.pk}/#pedido-foto")


def test_quitar_sin_foto_no_hace_nada(sesion_duena, pedido):
    assert sesion_duena.post(url_quitar(pedido), headers=HTMX).status_code == 200
    assert sesion_duena.get(url_quitar(pedido), headers=HTMX).status_code == 200


def test_subir_solo_acepta_envios(sesion_duena, pedido):
    assert sesion_duena.get(reverse("pedidos:foto", args=[pedido.pk])).status_code == 405


# --- Aviso corto y animaciones (ajuste "pantalla fija y animaciones") ------------------------


def aviso(respuesta):
    """El aviso corto que lleva la respuesta de HTMX (config/avisos.py), o None."""
    return json.loads(respuesta.headers.get("HX-Trigger") or "{}").get("aviso")


def test_subir_la_foto_avisa_foto_guardada(sesion_duena, pedido):
    assert aviso(subir(sesion_duena, pedido, foto_de_prueba(), headers=HTMX)) == "Foto guardada."


def test_cambiar_la_foto_tambien_avisa_foto_guardada(sesion_duena, pedido):
    poner_foto(pedido)

    assert aviso(subir(sesion_duena, pedido, foto_de_prueba(), headers=HTMX)) == "Foto guardada."


def test_la_costurera_tambien_recibe_el_aviso(client, costurera, pedido):
    client.force_login(costurera)

    assert aviso(subir(client, pedido, foto_de_prueba(), headers=HTMX)) == "Foto guardada."


def test_una_foto_que_no_sirve_no_avisa(sesion_duena, pedido):
    respuesta = subir(sesion_duena, pedido, SimpleUploadedFile("otra.jpg", b"texto"),
                      headers=HTMX)

    assert respuesta.status_code == 422
    assert aviso(respuesta) is None


def test_quitar_la_foto_avisa_foto_quitada(sesion_duena, pedido):
    poner_foto(pedido)

    assert aviso(sesion_duena.post(url_quitar(pedido), headers=HTMX)) == "Foto quitada."


def test_preguntar_cancelar_o_quitar_sin_foto_no_avisan(sesion_duena, pedido):
    assert aviso(sesion_duena.post(url_quitar(pedido), headers=HTMX)) is None
    poner_foto(pedido)
    assert aviso(sesion_duena.get(url_quitar(pedido), headers=HTMX)) is None
    assert aviso(sesion_duena.get(url_quitar(pedido) + "?cancelar=1", headers=HTMX)) is None


def test_sin_javascript_el_aviso_sale_en_el_pedido(sesion_duena, pedido):
    poner_foto(pedido)

    respuesta = sesion_duena.post(url_quitar(pedido), follow=True)

    assert "<p data-aviso>Foto quitada.</p>" in respuesta.text


def test_la_foto_y_la_invitacion_llevan_su_id_y_la_pregunta_conserva_el_del_formulario(
    sesion_duena, pedido
):
    """Al subir la primera foto la invitación se va y la foto llega; la pregunta "¿Quitar?"
    toma el lugar del formulario sin cerrarse (static/js/app.js, sección 11)."""
    sin_foto = sesion_duena.get(reverse("pedidos:detalle", args=[pedido.pk])).text
    con_foto = subir(sesion_duena, pedido, foto_de_prueba(), headers=HTMX).text
    pregunta = sesion_duena.get(url_quitar(pedido), headers=HTMX).text

    assert '<section class="tarjeta" id="pedido-foto"' in sin_foto
    assert 'id="pedido-foto-vacio"' in sin_foto and 'id="pedido-foto-imagen"' not in sin_foto
    assert 'id="pedido-foto-imagen"' in con_foto and 'id="pedido-foto-vacio"' not in con_foto
    assert '<form id="pedido-foto-acciones"' in con_foto
    assert '<div class="tarjeta__cuerpo" id="pedido-foto-acciones">' in pregunta
    assert pregunta.count('id="pedido-foto-acciones"') == 1


# --- La tarjeta en el pedido por dentro ------------------------------------------------------


def test_el_pedido_sin_foto_invita_a_subirla(sesion_duena, pedido):
    html = sesion_duena.get(reverse("pedidos:detalle", args=[pedido.pk])).text

    assert ">Foto</h2>" in html
    assert 'class="subir"' in html
    assert "Sale en Hoy y en la lista de pedidos" in html
    assert "Trabajos del taller" not in html.split('id="pedido-foto"')[1].split("</section>")[0]
    assert 'type="file" name="foto"' in html and 'accept="image/*"' in html
    assert 'enctype="multipart/form-data"' in html
    assert 'hx-encoding="multipart/form-data"' in html
    assert "Quitar la foto" not in html


def test_el_pedido_con_foto_la_muestra(sesion_duena, pedido):
    poner_foto(pedido)

    html = sesion_duena.get(reverse("pedidos:detalle", args=[pedido.pk])).text

    assert f'<img src="{pedido.foto.url}"' in html
    assert 'class="foto"' in html and "Cambiar foto" in html
    assert "Sale en Hoy y en la lista de pedidos" not in html


# --- Otro taller -----------------------------------------------------------------------------


@pytest.fixture
def ajeno():
    """Un pedido de otro taller, con su foto."""
    pedido = fabricas.crear_pedido(fabricas.crear_taller())
    poner_foto(pedido)
    return pedido


def test_no_se_puede_subir_la_foto_de_otro_taller(sesion_duena, ajeno):
    antes = ajeno.foto.name

    respuesta = subir(sesion_duena, ajeno, foto_de_prueba(), headers=HTMX)

    assert respuesta.status_code == 404
    ajeno.refresh_from_db()
    assert ajeno.foto.name == antes


def test_no_se_puede_quitar_la_foto_de_otro_taller(sesion_duena, ajeno):
    archivo = ajeno.foto.path

    assert sesion_duena.get(url_quitar(ajeno), headers=HTMX).status_code == 404
    assert sesion_duena.post(url_quitar(ajeno), headers=HTMX).status_code == 404

    ajeno.refresh_from_db()
    assert ajeno.foto and _existe(archivo)


# --- Archivos -------------------------------------------------------------------------------


def test_borrar_archivo_no_falla_si_no_hay_archivo(pedido):
    # La primera foto no tiene una anterior que borrar.
    almacen = Pedido._meta.get_field("foto").storage

    fotos.borrar_archivo(almacen, "")
    fotos.borrar_archivo(almacen, "pedidos/fotos/no-existe.jpg")

