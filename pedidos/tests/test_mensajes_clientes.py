"""Clientes (T19): el aviso de dotación y los mensajes de WhatsApp ("Escribirle")."""

import html as html_lib
import re
from datetime import date
from urllib.parse import unquote

import pytest

from pedidos import ejemplos, mensajes
from pedidos.vistas.clientes import aviso_de_dotacion
from tests import fabricas

pytestmark = pytest.mark.django_db

HTMX = {"HX-Request": "true"}
URL = "/clientes/"
URL_EMPRESAS = "/clientes/?escribir=empresas"
DIA = date(2026, 11, 11)  # el día del diseño: faltan 39 días para el 20 de diciembre
FECHAS = "Las empresas entregan dotación el 30 de abril, el 31 de agosto y el 20 de diciembre."


@pytest.fixture
def otro_taller(db):
    return fabricas.crear_taller(nombre="Confecciones Ajenas")


@pytest.fixture
def dia_fijo(monkeypatch):
    """Hoy es el 11 de noviembre de 2026 para la vista (como en el diseño)."""
    monkeypatch.setattr("django.utils.timezone.localdate", lambda *a, **k: DIA)
    return DIA


def fila_de(html, nombre):
    """El HTML de la fila de la tabla de ese cliente."""
    inicio = html.index(f"<strong>{nombre}</strong>")
    return html[inicio:html.index("</tr>", inicio)]


def renglon_de(html, nombre):
    """El HTML del renglón de ese cliente en la ventana "Escribirles"."""
    renglones = html.split('<div class="renglon">')[1:]
    return next(r for r in renglones if f"<strong>{nombre}</strong>" in r)


def texto_del_enlace(enlace):
    return unquote(html_lib.unescape(enlace).split("?text=")[1])


# --- El aviso de dotación ----------------------------------------------------------------------


def test_el_aviso_sale_como_el_diseno(client, dia_fijo):
    taller = ejemplos.cargar(hoy=DIA, con_fotos=False)
    client.force_login(taller.usuarias.filter(rol="duena").first())

    html = client.get(URL).text

    inicio = html.index('class="tarjeta-oscura"')
    aviso = html[inicio:html.index("</section>", inicio)]
    assert "Dotación del 20 de diciembre: faltan 39 días" in aviso
    assert f"{FECHAS} Tienes 2 clientes empresa." in aviso
    assert ">Escribirles a los 2</a>" in aviso
    assert 'class="boton boton--claro"' in aviso
    assert f'hx-get="{URL_EMPRESAS}" hx-target="#ventana"' in aviso
    assert f'href="{URL_EMPRESAS}"' in aviso  # sin JavaScript, abre la lista como página


@pytest.mark.parametrize(
    ("hoy", "titulo"),
    [
        (date(2026, 1, 10), "Dotación del 30 de abril: faltan 110 días"),
        (date(2026, 4, 29), "Dotación del 30 de abril: falta 1 día"),
        (date(2026, 4, 30), "Dotación del 30 de abril: es hoy"),
        (date(2026, 5, 1), "Dotación del 31 de agosto: faltan 122 días"),
        (date(2026, 8, 31), "Dotación del 31 de agosto: es hoy"),
        (date(2026, 9, 1), "Dotación del 20 de diciembre: faltan 110 días"),
        (date(2026, 12, 19), "Dotación del 20 de diciembre: falta 1 día"),
        (date(2026, 12, 20), "Dotación del 20 de diciembre: es hoy"),
        (date(2026, 12, 21), "Dotación del 30 de abril: faltan 130 días"),
    ],
)
def test_los_dias_que_faltan_alrededor_de_cada_fecha(taller, hoy, titulo):
    assert aviso_de_dotacion(taller, hoy).titulo == titulo


def test_el_aviso_usa_la_fecha_de_hoy_en_bogota(sesion_duena, monkeypatch):
    monkeypatch.setattr("django.utils.timezone.localdate", lambda *a, **k: date(2026, 12, 20))

    html = sesion_duena.get(URL).text

    assert "Dotación del 20 de diciembre: es hoy" in html


def test_con_un_solo_cliente_empresa(sesion_duena, taller, dia_fijo):
    fabricas.crear_cliente(taller, nombre="Única empresa", tipo="empresa")
    fabricas.crear_cliente(taller, nombre="Un colegio", tipo="colegio")

    html = sesion_duena.get(URL).text

    assert f"{FECHAS} Tienes 1 cliente empresa." in html
    assert ">Escribirle a tu cliente empresa</a>" in html


def test_sin_clientes_empresa_no_hay_boton(sesion_duena, taller, dia_fijo):
    fabricas.crear_cliente(taller, nombre="Una comparsa", tipo="comparsa")

    html = sesion_duena.get(URL).text

    assert f"{FECHAS} Todavía no tienes clientes empresa." in html
    assert "boton--claro" not in html
    assert "?escribir=empresas" not in html


def test_el_aviso_cuenta_solo_las_empresas_del_taller(sesion_duena, taller, otro_taller,
                                                      dia_fijo):
    fabricas.crear_cliente(taller, nombre="Empresa mía", tipo="empresa")
    fabricas.crear_cliente(otro_taller, nombre="Empresa ajena 1", tipo="empresa")
    fabricas.crear_cliente(otro_taller, nombre="Empresa ajena 2", tipo="empresa")

    html = sesion_duena.get(URL).text

    assert "Tienes 1 cliente empresa." in html


# --- La ventana "Escribirles" ------------------------------------------------------------------


def test_la_ventana_lista_las_empresas_con_su_boton(sesion_duena, taller, dia_fijo):
    fabricas.crear_cliente(taller, nombre="Empresa con número", tipo="empresa",
                           whatsapp="300 123 4567")
    fabricas.crear_cliente(taller, nombre="Empresa sin número", tipo="empresa")
    fabricas.crear_cliente(taller, nombre="Empresa con número malo", tipo="empresa",
                           whatsapp="12345")
    fabricas.crear_cliente(taller, nombre="Un particular", tipo="particular",
                           whatsapp="3009998877")

    respuesta = sesion_duena.get(URL_EMPRESAS, headers=HTMX)
    html = respuesta.text

    assert respuesta.status_code == 200
    assert "<body" not in html  # solo el contenido de la ventana
    assert "Escribirles por la dotación" in html
    assert "Dotación del 20 de diciembre: faltan 39 días." in html
    assert "Un particular" not in html
    assert re.findall(r"<strong>([^<]+)</strong>", html) == [
        "Empresa con número", "Empresa con número malo", "Empresa sin número",
    ]
    texto = mensajes.texto_dotacion(taller, DIA)
    assert texto == (
        f"Hola, le escribimos de {taller.nombre}. Se acerca la entrega de dotación del 20 de "
        "diciembre. ¿Le cotizamos los uniformes para su equipo?"
    )

    con_numero = renglon_de(html, "Empresa con número")
    enlace = re.search(r'href="([^"]+)"', con_numero).group(1)
    assert enlace.startswith("https://wa.me/573001234567?text=")
    assert texto_del_enlace(enlace) == texto
    assert 'target="_blank" rel="noopener"' in con_numero
    assert ">Ofrecerle por WhatsApp</span>" in con_numero
    assert "data-copiar" not in con_numero

    sin_numero = renglon_de(html, "Empresa sin número")
    assert "Sin WhatsApp guardado" in sin_numero
    assert "wa.me" not in sin_numero
    assert f'data-copiar="{html_lib.escape(texto)}"' in sin_numero
    assert ">Copiar mensaje</span>" in sin_numero

    numero_malo = renglon_de(html, "Empresa con número malo")
    assert "El número guardado no sirve para WhatsApp" in numero_malo
    assert "wa.me" not in numero_malo and "data-copiar" in numero_malo


def test_la_ventana_sin_javascript_es_una_pagina(sesion_duena, taller, dia_fijo):
    fabricas.crear_cliente(taller, nombre="Empresa sola", tipo="empresa")

    html = sesion_duena.get(URL_EMPRESAS).text

    assert "<body" in html
    assert "ventana--pagina" in html
    assert "Empresa sola" in html


def test_la_ventana_sin_empresas(sesion_duena, taller, dia_fijo):
    html = sesion_duena.get(URL_EMPRESAS, headers=HTMX).text

    assert "Todavía no tienes clientes de tipo Empresa." in html


def test_la_ventana_no_muestra_empresas_de_otro_taller(sesion_duena, taller, otro_taller,
                                                       dia_fijo):
    fabricas.crear_cliente(taller, nombre="Empresa mía", tipo="empresa")
    fabricas.crear_cliente(otro_taller, nombre="Empresa ajena", tipo="empresa",
                           whatsapp="3001112233")

    html = sesion_duena.get(URL_EMPRESAS, headers=HTMX).text

    assert "Empresa mía" in html
    assert "Empresa ajena" not in html
    assert "3001112233" not in html


# --- "Escribirle" en cada cliente --------------------------------------------------------------


def test_escribirle_abre_whatsapp_con_el_mensaje(sesion_duena, taller):
    fabricas.crear_cliente(taller, nombre="Con número", whatsapp="+57 310-555-0000")

    html = sesion_duena.get(URL).text

    fila = fila_de(html, "Con número")
    enlace = re.search(r'<a class="boton" href="(https://wa\.me/[^"]+)"', fila).group(1)
    assert enlace.startswith("https://wa.me/573105550000?text=")
    assert texto_del_enlace(enlace) == mensajes.texto_oferta(taller) == (
        f"Hola, le escribimos de {taller.nombre}. Cuando necesite uniformes, dotación o "
        "vestidos, con gusto le cotizamos."
    )
    assert " " not in html_lib.unescape(enlace)  # el texto va codificado en el enlace
    assert 'target="_blank" rel="noopener"' in fila
    assert ">Escribirle</a>" in fila
    assert ">Editar</a>" in fila  # T04 sigue igual
    assert "data-copiar" not in fila


def test_sin_whatsapp_escribirle_copia_el_mensaje(sesion_duena, taller):
    fabricas.crear_cliente(taller, nombre="Sin número")
    fabricas.crear_cliente(taller, nombre="Número corto", whatsapp="123")

    html = sesion_duena.get(URL).text

    texto = html_lib.escape(mensajes.texto_oferta(taller))
    for nombre in ("Sin número", "Número corto"):
        fila = fila_de(html, nombre)
        assert "wa.me" not in fila
        assert f'<button type="button" class="boton" data-copiar="{texto}"' in fila
        assert 'title="Copia el mensaje para pegarlo en WhatsApp"' in fila
        assert ">Escribirle</button>" in fila


def test_escribirle_tambien_sale_en_el_buscador(sesion_duena, taller):
    fabricas.crear_cliente(taller, nombre="Buscada", whatsapp="3001234567")
    fabricas.crear_cliente(taller, nombre="Otra")

    respuesta = sesion_duena.get(URL, {"q": "busc"},
                                 headers={**HTMX, "HX-Target": "clientes-lista"})

    assert "tarjeta-oscura" not in respuesta.text  # solo la tabla
    assert "https://wa.me/573001234567?text=" in fila_de(respuesta.text, "Buscada")
    assert "Otra" not in respuesta.text


def test_solo_salen_los_clientes_del_taller(sesion_duena, taller, otro_taller):
    fabricas.crear_cliente(taller, nombre="Cliente mío", whatsapp="3001234567")
    fabricas.crear_cliente(otro_taller, nombre="Cliente ajeno", whatsapp="3007654321")

    html = sesion_duena.get(URL).text

    assert "Cliente mío" in html
    assert "Cliente ajeno" not in html
    assert "573007654321" not in html
    assert "Confecciones Ajenas" not in unquote(html)  # el mensaje firma con su taller
