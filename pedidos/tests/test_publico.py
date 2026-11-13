"""Formulario público de tallas (T11): lo que ve y envía cada persona del grupo con el enlace."""

import re
from decimal import Decimal
from html import unescape

import pytest
from django.core.cache import cache
from django.test import Client
from django.urls import reverse

from pedidos.models import Pedido, Talla
from pedidos.vistas import publico
from tests import fabricas

pytestmark = pytest.mark.django_db

HTMX = {"HX-Request": "true"}


@pytest.fixture(autouse=True)
def sin_envios_contados():
    """Cada prueba empieza sin envíos contados (la cuenta del límite vive en la caché)."""
    cache.clear()
    yield
    cache.clear()


@pytest.fixture
def pedido(taller):
    cliente = fabricas.crear_cliente(taller, nombre="Colegio de prueba")
    return fabricas.crear_pedido(
        taller, cliente=cliente, detalle="24 sudaderas de educación física", total=1_260_000
    )


def direccion(pedido):
    return reverse("pedidos:publico_tallas", args=[pedido.token_tallas])


def enviar(client, pedido, **datos):
    datos.setdefault("nombre", "Ana Gómez")
    datos.setdefault("talla", "M")
    return client.post(direccion(pedido), datos)


def listo(pedido):
    return f"{direccion(pedido)}?listo=1"


def texto(respuesta):
    """El texto de la página sin etiquetas, para buscar frases."""
    return " ".join(unescape(re.sub(r"<[^>]+>", " ", respuesta.text)).split())


# --- Lo que muestra -------------------------------------------------------------------------


def test_abre_sin_sesion_con_el_taller_el_cliente_y_lo_que_pidio(client, pedido, taller):
    respuesta = client.get(direccion(pedido))

    assert respuesta.status_code == 200
    pagina = texto(respuesta)
    assert taller.nombre in pagina
    assert "Envía tu talla" in pagina
    assert "Colegio de prueba" in pagina
    assert "24 sudaderas de educación física" in pagina
    assert "Enviar mi talla" in pagina


def test_ofrece_las_tallas_del_pedido_con_a_la_medida(client, taller):
    pedido = fabricas.crear_pedido(taller, tallaje=Pedido.Tallaje.NINO)

    html = client.get(direccion(pedido)).text

    opciones = re.findall(r'<option value="([^"]*)"', html)
    assert opciones == ["", "4", "6", "8", "10", "12", "14", "16", "medida"]
    assert '<option value="medida">A la medida</option>' in html


def test_no_muestra_precios_ni_las_tallas_de_otros_ni_el_menu(client, pedido):
    fabricas.crear_abono(pedido, valor=500_000)
    fabricas.crear_talla(pedido, nombre="Persona que ya envió", talla="L", nota="Nota secreta")

    respuesta = client.get(direccion(pedido))

    html = respuesta.text
    assert "Persona que ya envió" not in html
    assert "Nota secreta" not in html
    assert "1.260.000" not in html and "1260000" not in html
    assert "500.000" not in html and "500000" not in html
    assert "$" not in html
    assert 'class="menu' not in html
    assert "navegacion-celular" not in html
    assert 'id="ventana"' not in html


def test_sin_javascript_las_medidas_se_ven_con_la_nota(client, pedido):
    html = client.get(direccion(pedido)).text

    noscript = re.search(r"<noscript>(.*?)</noscript>", html, re.S).group(1)
    for campo in ("pecho", "cintura", "cadera", "largo"):
        assert f'name="{campo}"' in noscript
    assert "Solo si eliges «A la medida»" in noscript


def test_al_elegir_a_la_medida_htmx_trae_las_medidas(client, pedido):
    html = client.get(direccion(pedido), {"talla": "medida"}, headers=HTMX).text

    assert html.startswith('<div class="acceso__tarjeta" id="publico-talla">')
    assert "<noscript>" not in html
    assert '<option value="medida" selected>A la medida</option>' in html
    for campo in ("pecho", "cintura", "cadera", "largo"):
        assert f'name="{campo}"' in html
    assert "<form" not in html


def test_al_elegir_otra_talla_htmx_esconde_las_medidas(client, pedido):
    html = client.get(direccion(pedido), {"talla": "M"}, headers=HTMX).text

    assert '<option value="M" selected>M</option>' in html
    medidas_visibles = re.sub(r"<noscript>.*?</noscript>", "", html, flags=re.S)
    assert 'name="pecho"' not in medidas_visibles


def test_el_selector_de_talla_pide_las_medidas_a_la_misma_pagina(client, pedido):
    html = client.get(direccion(pedido)).text

    assert f'hx-get="{direccion(pedido)}"' in html
    assert 'hx-target="#publico-talla"' in html
    # El envío es un formulario normal: así se ven las páginas de 403 y 429.
    assert f'<form class="acceso__tarjeta" method="post" action="{direccion(pedido)}"' in html
    assert "hx-post" not in html


# --- Enviar la talla ------------------------------------------------------------------------


def test_guarda_la_talla_en_ese_pedido_como_enviada_por_el_cliente(client, pedido):
    respuesta = enviar(client, pedido, nombre="  Ana Gómez ", talla="M", nota="Manga larga")

    assert respuesta.status_code == 302
    assert respuesta["Location"] == listo(pedido)
    talla = Talla.objects.get()
    assert talla.pedido == pedido
    assert talla.nombre == "Ana Gómez"
    assert talla.talla == "M"
    assert talla.nota == "Manga larga"
    assert talla.origen == Talla.Origen.ENLACE
    assert talla.pecho is None


def test_muestra_la_confirmacion_y_el_boton_para_otra_persona(client, pedido):
    enviar(client, pedido, nombre="Ana Gómez", talla="M")

    respuesta = client.get(listo(pedido))

    assert respuesta.status_code == 200
    pagina = texto(respuesta)
    assert "¡Listo, Ana Gómez!" in pagina
    assert "Tu talla M quedó registrada para el pedido de Colegio de prueba." in pagina
    assert (
        f'<a class="boton" href="{direccion(pedido)}">Registrar a otra persona</a>'
        in respuesta.text
    )


def test_recargar_la_confirmacion_no_guarda_otra_vez_y_muestra_el_formulario(client, pedido):
    enviar(client, pedido, nombre="Ana Gómez", talla="M")
    client.get(listo(pedido))

    respuesta = client.get(listo(pedido))

    assert respuesta.status_code == 200
    assert Talla.objects.count() == 1
    pagina = texto(respuesta)
    assert "¡Listo" not in pagina
    assert "Enviar mi talla" in pagina


def test_la_confirmacion_no_se_abre_sin_haber_enviado(client, pedido):
    fabricas.crear_talla(pedido, nombre="Persona que ya envió", talla="L")

    respuesta = client.get(listo(pedido))

    assert respuesta.status_code == 200
    assert "Persona que ya envió" not in respuesta.text
    assert "Enviar mi talla" in texto(respuesta)


def test_la_confirmacion_solo_muestra_una_talla_de_ese_pedido(client, pedido):
    ajena = fabricas.crear_talla(
        fabricas.crear_pedido(fabricas.crear_taller()), nombre="Persona de otro pedido"
    )
    sesion = client.session
    sesion["talla_publica"] = ajena.pk
    sesion.save()

    respuesta = client.get(listo(pedido))

    assert "Persona de otro pedido" not in respuesta.text
    assert "Enviar mi talla" in texto(respuesta)


def test_a_la_medida_guarda_las_medidas_con_coma_o_punto(client, pedido):
    respuesta = enviar(
        client, pedido, talla="medida", pecho="92,5", cintura="80.5", cadera="98", largo=""
    )

    assert respuesta.status_code == 302
    talla = Talla.objects.get()
    assert (talla.pecho, talla.cintura, talla.cadera) == (
        Decimal("92.5"), Decimal("80.5"), Decimal("98"),
    )
    assert talla.largo is None
    assert "Tu talla a la medida quedó registrada" in texto(client.get(listo(pedido)))


def test_a_la_medida_sin_pecho_cintura_y_cadera_no_se_guarda(client, pedido):
    respuesta = enviar(client, pedido, talla="medida", pecho="92")

    assert respuesta.status_code == 422
    assert not Talla.objects.exists()
    html = respuesta.text
    assert html.count("Anota esta medida.") == 2  # cintura y cadera
    # Las medidas se ven (sin <noscript>) para poder corregirlas.
    assert "<noscript>" not in html
    assert 'value="92"' in html


def test_una_medida_fuera_de_rango_o_que_no_es_numero_se_rechaza(client, pedido):
    respuesta = enviar(client, pedido, talla="medida", pecho="920", cintura="ochenta", cadera="98")

    assert respuesta.status_code == 422
    assert not Talla.objects.exists()
    assert texto(respuesta).count("Escribe la medida en centímetros, entre 1 y 300.") == 2


def test_con_otra_talla_las_medidas_no_se_guardan_ni_se_revisan(client, pedido):
    respuesta = enviar(client, pedido, talla="L", pecho="esto no es un número", cintura="80")

    assert respuesta.status_code == 302
    talla = Talla.objects.get()
    assert (talla.talla, talla.pecho, talla.cintura) == ("L", None, None)


def test_sin_nombre_ni_talla_responde_422_con_mensajes_claros(client, pedido):
    respuesta = enviar(client, pedido, nombre=" ", talla="")

    assert respuesta.status_code == 422
    assert not Talla.objects.exists()
    pagina = texto(respuesta)
    assert "Escribe tu nombre para saber de quién es la talla." in pagina
    assert "Elige tu talla." in pagina


def test_una_talla_que_no_es_del_pedido_se_rechaza(client, taller):
    pedido = fabricas.crear_pedido(taller, tallaje=Pedido.Tallaje.NINO)

    respuesta = enviar(client, pedido, talla="XL")

    assert respuesta.status_code == 422
    assert not Talla.objects.exists()
    assert "Elige una de las tallas de la lista." in texto(respuesta)


def test_un_nombre_o_unas_observaciones_muy_largos_se_rechazan(client, pedido):
    respuesta = enviar(client, pedido, nombre="A" * 61, nota="B" * 201)

    assert respuesta.status_code == 422
    assert not Talla.objects.exists()
    pagina = texto(respuesta)
    assert "Escribe máximo 60 letras en el nombre." in pagina
    assert "Escribe máximo 200 letras en las observaciones." in pagina


def test_con_errores_el_cursor_va_al_primer_campo_con_error(client, pedido):
    html = enviar(client, pedido, nombre="Ana", talla="").text

    select = re.search(r"<select[^>]*>", html).group(0)
    assert "autofocus" in select
    nombre = re.search(r'<input[^>]*name="nombre"[^>]*>', html).group(0)
    assert "autofocus" not in nombre


# --- La clave del enlace es lo único que dice de qué pedido es la talla -------------------------


def test_un_enlace_inventado_responde_404_con_una_pagina_clara(client):
    respuesta = client.get(reverse("pedidos:publico_tallas", args=["inventado"]))

    assert respuesta.status_code == 404
    pagina = texto(respuesta)
    assert "Este enlace no existe" in pagina
    assert 'class="menu' not in respuesta.text


def test_enviar_a_un_enlace_inventado_responde_404_y_no_guarda(client, pedido):
    respuesta = client.post(
        reverse("pedidos:publico_tallas", args=["inventado"]), {"nombre": "Ana", "talla": "M"}
    )

    assert respuesta.status_code == 404
    assert not Talla.objects.exists()


def test_el_formulario_no_acepta_el_numero_de_otro_pedido(client, pedido):
    otro_taller = fabricas.crear_taller()
    ajeno = fabricas.crear_pedido(otro_taller)

    datos = {"nombre": "Ana", "talla": "M", "pedido": ajeno.pk, "taller": otro_taller.pk,
             "origen": "manual"}

    respuesta = client.post(direccion(pedido), datos)

    assert respuesta.status_code == 302
    talla = Talla.objects.get()
    assert talla.pedido == pedido
    assert talla.origen == Talla.Origen.ENLACE
    assert not ajeno.tallas.exists()


def test_cada_enlace_guarda_solo_en_su_pedido(client, pedido):
    ajeno = fabricas.crear_pedido(fabricas.crear_taller(), detalle="Pedido de otro taller")

    enviar(client, ajeno, nombre="Persona del otro taller")

    assert not pedido.tallas.exists()
    assert ajeno.tallas.get().nombre == "Persona del otro taller"
    # Y la página de un enlace no muestra nada del otro pedido.
    assert "Pedido de otro taller" not in client.get(direccion(pedido)).text


# --- Enlace cerrado -------------------------------------------------------------------------


def test_un_enlace_cerrado_lo_dice_y_no_muestra_el_formulario(client, pedido):
    pedido.tallas_abiertas = False
    pedido.save()

    respuesta = client.get(direccion(pedido))

    assert respuesta.status_code == 200
    assert "Este enlace ya está cerrado" in texto(respuesta)
    assert "<form" not in respuesta.text


def test_un_enlace_cerrado_no_guarda_nada(client, pedido):
    pedido.tallas_abiertas = False
    pedido.save()

    respuesta = enviar(client, pedido)

    assert respuesta.status_code == 403
    assert "Este enlace ya está cerrado" in texto(respuesta)
    assert not Talla.objects.exists()


def test_un_enlace_cerrado_no_trae_las_medidas(client, pedido):
    pedido.tallas_abiertas = False
    pedido.save()

    respuesta = client.get(direccion(pedido), {"talla": "medida"}, headers=HTMX)

    assert 'name="pecho"' not in respuesta.text


def test_si_cierran_el_enlace_con_el_formulario_abierto_la_pagina_se_recarga(client, pedido):
    # HTMX pondría la página entera de "enlace cerrado" dentro del formulario: mejor que el
    # navegador recargue y la muestre completa.
    pedido.tallas_abiertas = False
    pedido.save()

    respuesta = client.get(direccion(pedido), {"talla": "medida"}, headers=HTMX)

    assert respuesta.status_code == 200
    assert respuesta["HX-Refresh"] == "true"
    assert "marco-acceso" not in respuesta.text


def test_si_borran_el_pedido_con_el_formulario_abierto_la_pagina_se_recarga(client, pedido):
    # HTMX no dibuja un 404: sin recargar, cambiar la talla no haría nada.
    url = direccion(pedido)
    pedido.delete()

    respuesta = client.get(url, {"talla": "medida"}, headers=HTMX)

    assert respuesta.status_code == 200
    assert respuesta["HX-Refresh"] == "true"
    assert "marco-acceso" not in respuesta.text


# --- Límite de envíos por minuto ----------------------------------------------------------------


def test_despues_del_limite_en_un_minuto_responde_429_y_no_guarda(client, pedido):
    for numero in range(publico.LIMITE):
        assert enviar(client, pedido, nombre=f"Persona {numero}").status_code == 302

    respuesta = enviar(client, pedido, nombre="Una de más")

    assert respuesta.status_code == 429
    assert respuesta["Retry-After"] == "60"
    assert "Espera un minuto" in texto(respuesta)
    assert Talla.objects.count() == publico.LIMITE
    assert not Talla.objects.filter(nombre="Una de más").exists()


def test_los_envios_con_errores_tambien_cuentan(client, pedido):
    for _ in range(publico.LIMITE):
        assert enviar(client, pedido, nombre="").status_code == 422

    assert enviar(client, pedido).status_code == 429
    assert not Talla.objects.exists()


def test_el_limite_es_por_celular_y_por_enlace(client, pedido, taller):
    otro = fabricas.crear_pedido(taller)
    for numero in range(publico.LIMITE + 1):
        enviar(client, pedido, nombre=f"Persona {numero}")

    assert enviar(client, otro).status_code == 302
    otro_celular = Client(REMOTE_ADDR="10.0.0.2")
    assert enviar(otro_celular, pedido).status_code == 302


def test_abrir_la_pagina_no_cuenta_como_envio(client, pedido):
    for _ in range(publico.LIMITE + 5):
        client.get(direccion(pedido))

    assert enviar(client, pedido).status_code == 302


def test_pasado_el_minuto_vuelve_a_aceptar(client, pedido):
    for numero in range(publico.LIMITE + 1):
        enviar(client, pedido, nombre=f"Persona {numero}")

    cache.clear()  # Lo mismo que pasa cuando se vence el minuto.

    assert enviar(client, pedido).status_code == 302


# --- Protección del formulario ------------------------------------------------------------------


def test_sin_la_ficha_csrf_no_se_guarda(pedido):
    navegador = Client(enforce_csrf_checks=True)

    respuesta = navegador.post(direccion(pedido), {"nombre": "Ana", "talla": "M"})

    assert respuesta.status_code == 403
    assert not Talla.objects.exists()


def test_con_la_ficha_csrf_de_la_pagina_si_se_guarda(pedido):
    navegador = Client(enforce_csrf_checks=True)
    html = navegador.get(direccion(pedido)).text
    ficha = re.search(r'name="csrfmiddlewaretoken" value="([^"]+)"', html).group(1)

    respuesta = navegador.post(
        direccion(pedido), {"nombre": "Ana", "talla": "M", "csrfmiddlewaretoken": ficha}
    )

    assert respuesta.status_code == 302
    assert Talla.objects.get().pedido == pedido


def test_solo_acepta_abrir_y_enviar(client, pedido):
    assert client.put(direccion(pedido)).status_code == 405
    assert client.delete(direccion(pedido)).status_code == 405
