"""Tarjeta "Tallas" del pedido por dentro (T10): ver, agregar y quitar tallas, y abrir o
cerrar el enlace público."""

import re
from decimal import Decimal
from html import unescape

import pytest
from django.template.loader import render_to_string
from django.test import RequestFactory
from django.urls import reverse

from pedidos.formularios.tallas import TallaForm
from pedidos.models import Pedido, Talla
from pedidos.vistas import tallas as vista_tallas
from tests import fabricas

pytestmark = pytest.mark.django_db

HTMX = {"HX-Request": "true"}


@pytest.fixture
def pedido(taller):
    return fabricas.crear_pedido(taller, cantidad=18, detalle="18 camisas tipo polo")


def dibujar(pedido, usuaria, **opciones):
    """La tarjeta como la dibuja la ficha del pedido."""
    request = RequestFactory().get("/")
    request.user = usuaria
    request.taller = usuaria.taller
    contexto = {"pedido": pedido, "tarjeta_tallas": vista_tallas.tarjeta(request, pedido, **opciones)}
    return render_to_string("pedidos/_tallas.html", contexto, request=request)


def agregar(sesion, pedido, **datos):
    datos.setdefault("nombre", "Persona nueva")
    datos.setdefault("talla", "M")
    return sesion.post(reverse("pedidos:talla_nueva", args=[pedido.pk]), datos, headers=HTMX)


# --- Lo que muestra la tarjeta -----------------------------------------------------------------


def test_muestra_recibidas_y_una_barra_por_talla_como_el_diseno(pedido, duena):
    # El diseño: 14 de 18, S 3, M 6, L 3 y XL 2. La barra más larga es la de M.
    for talla, veces in (("S", 3), ("M", 6), ("L", 3), ("XL", 2)):
        for _ in range(veces):
            fabricas.crear_talla(pedido, talla=talla)

    html = dibujar(pedido, duena)

    assert 'id="tarjeta-tallas"' in html
    assert "14 de 18 <span" in html
    assert 'aria-valuenow="78"' in html  # 14 de 18
    assert html.index("<strong>S</strong>") < html.index("<strong>M</strong>") < html.index(
        "<strong>XL</strong>"
    )
    assert 'aria-label="Talla M"' in html
    assert "width: 100%" in html and "width: 50%" in html and "width: 33%" in html
    assert "Copiar enlace para el cliente" in html
    assert "Copiar resumen" in html


@pytest.mark.xfail(
    strict=True,
    reason="Falta que el coordinador ponga tarjeta_tallas en pedidos/vistas/detalle.py. "
    "Cuando lo haga, esta prueba pasa: hay que quitar esta marca y la tarjeta de reserva "
    "({% else %}) de pedidos/_tallas.html.",
)
def test_la_ficha_del_pedido_muestra_la_tarjeta_completa(sesion_duena, pedido):
    fabricas.crear_talla(pedido, talla="M")

    html = sesion_duena.get(reverse("pedidos:detalle", args=[pedido.pk])).text

    assert 'id="tarjeta-tallas"' in html
    assert "1 de 18 <span" in html
    assert "Copiar enlace para el cliente" in html
    assert "Copiar resumen" in html
    assert f'action="{reverse("pedidos:tallas_enlace", args=[pedido.pk])}"' in html
    assert f'action="{reverse("pedidos:talla_nueva", args=[pedido.pk])}"' in html


def test_sin_tallas_invita_a_mandar_el_enlace(pedido, duena):
    html = dibujar(pedido, duena)

    assert "0 de 18 <span" in html
    assert "Nadie ha enviado su talla todavía" in html
    assert "fila-talla" not in html


def test_el_boton_copia_el_enlace_publico_completo(pedido, duena):
    html = dibujar(pedido, duena)
    enlace = "http://testserver" + reverse("pedidos:publico_tallas", args=[pedido.token_tallas])

    assert f'data-copiar="{enlace}"' in html


def test_el_resumen_para_copiar_trae_las_tallas_y_las_que_faltan(pedido, duena):
    fabricas.crear_talla(pedido, talla="S")
    fabricas.crear_talla(pedido, talla="M")
    fabricas.crear_talla(pedido, talla="M")

    html = unescape(dibujar(pedido, duena))

    resumen = f"Tallas: {pedido.cliente.nombre}\n18 camisas tipo polo\n\nS: 1\nM: 2\n\n"
    assert resumen + "Recibidas: 3 de 18 (faltan 15)" in html


def test_la_lista_trae_a_cada_persona_con_sus_medidas_nota_y_origen(pedido, duena):
    fabricas.crear_talla(
        pedido, nombre="Ana Ejemplo", talla="medida", pecho=Decimal("92"),
        cintura=Decimal("80.5"), cadera=Decimal("98"), nota="Manga larga.",
    )
    fabricas.crear_talla(pedido, nombre="Luis Ejemplo", talla="L", origen=Talla.Origen.ENLACE)

    html = dibujar(pedido, duena)

    assert "Ver las 2 personas" in html
    assert "Ana Ejemplo" in html and "Luis Ejemplo" in html
    assert "Pecho 92, cintura 80,5, cadera 98 cm. Manga larga. Agregada en el taller." in html
    assert "La envió el cliente." in html
    assert ">A la medida</span>" in html
    # "A la medida" no lleva barra: va en su propio renglón.
    assert "A la medida: <strong>1</strong> persona" in html
    assert "<strong>medida</strong>" not in html


def test_mas_tallas_que_personas_no_pasa_la_barra_del_100(taller, duena):
    pedido = fabricas.crear_pedido(taller, cantidad=1)
    fabricas.crear_talla(pedido)
    fabricas.crear_talla(pedido)

    html = dibujar(pedido, duena)

    assert "2 de 1 <span" in html
    assert 'aria-valuenow="100"' in html


def test_dice_si_el_enlace_recibe_tallas(pedido, duena):
    assert "Enlace abierto" in dibujar(pedido, duena)
    assert 'value="no">Cerrar el enlace' in dibujar(pedido, duena)

    pedido.tallas_abiertas = False
    html = dibujar(pedido, duena)

    assert "Enlace cerrado" in html
    assert 'value="si">Abrir el enlace' in html


def test_las_opciones_de_talla_son_las_del_pedido(taller):
    nino = fabricas.crear_pedido(taller, tallaje=Pedido.Tallaje.NINO)

    opciones = [valor for valor, _ in TallaForm(pedido=nino).fields["talla"].choices]

    assert opciones == ["", "4", "6", "8", "10", "12", "14", "16", "medida"]
    assert ("medida", "A la medida") in TallaForm(pedido=nino).fields["talla"].choices


# --- Agregar a mano ----------------------------------------------------------------------------


def test_agregar_una_talla_a_mano(sesion_duena, pedido):
    respuesta = agregar(sesion_duena, pedido, nombre="  Carla Ejemplo ", talla="S", nota="Zurda")

    assert respuesta.status_code == 200
    talla = pedido.tallas.get()
    assert (talla.nombre, talla.talla, talla.nota) == ("Carla Ejemplo", "S", "Zurda")
    assert talla.origen == Talla.Origen.MANUAL
    # Vuelve solo la tarjeta, ya con la persona y lista para la siguiente.
    assert respuesta.text.startswith('<section class="tarjeta tarjeta--lista" id="tarjeta-tallas"')
    assert "<html" not in respuesta.text
    assert "1 de 18 <span" in respuesta.text
    assert "<details open>" in respuesta.text
    assert "autofocus" in respuesta.text


def test_a_la_medida_guarda_las_medidas_con_coma_o_punto(sesion_duena, pedido):
    agregar(sesion_duena, pedido, talla="medida", pecho="92,5", cintura="80.25", cadera="98 cm",
            largo="")

    talla = pedido.tallas.get()
    assert (talla.pecho, talla.cintura, talla.cadera) == (
        Decimal("92.5"), Decimal("80.3"), Decimal("98.0"))
    assert talla.largo is None


def test_a_la_medida_sin_medidas_pide_anotarlas(sesion_duena, pedido):
    respuesta = agregar(sesion_duena, pedido, talla="medida", pecho="92")

    assert respuesta.status_code == 422
    assert not pedido.tallas.exists()
    assert respuesta.text.count("Anota esta medida.") == 2  # cintura y cadera


def test_sin_nombre_ni_talla_se_rechaza_con_un_mensaje_claro(sesion_duena, pedido):
    respuesta = agregar(sesion_duena, pedido, nombre=" ", talla="")

    assert respuesta.status_code == 422
    assert "Escribe el nombre de la persona." in respuesta.text
    assert "Elige la talla." in respuesta.text
    assert not pedido.tallas.exists()


def test_una_talla_que_no_es_del_tallaje_se_rechaza(sesion_duena, pedido):
    respuesta = agregar(sesion_duena, pedido, talla="10")  # el pedido es de adulto

    assert respuesta.status_code == 422
    assert "Elige una de las tallas de la lista." in respuesta.text
    assert not pedido.tallas.exists()


@pytest.mark.parametrize("medida", ["abc", "0", "500", "-3", "NaN"])
def test_una_medida_que_no_sirve_se_rechaza(sesion_duena, pedido, medida):
    respuesta = agregar(sesion_duena, pedido, talla="M", pecho=medida)

    assert respuesta.status_code == 422
    assert "Escribe la medida en centímetros, entre 1 y 300." in respuesta.text
    assert not pedido.tallas.exists()


def test_los_errores_vuelven_con_lo_que_se_habia_escrito(sesion_duena, pedido):
    respuesta = agregar(sesion_duena, pedido, nombre="Pedro Ejemplo", talla="medida", pecho="90,5")

    assert 'value="Pedro Ejemplo"' in respuesta.text
    assert 'value="90,5"' in respuesta.text


def test_sin_javascript_agregar_vuelve_al_pedido(sesion_duena, pedido):
    url = reverse("pedidos:talla_nueva", args=[pedido.pk])

    respuesta = sesion_duena.post(url, {"nombre": "Sin JS", "talla": "L"})

    assert respuesta.status_code == 302
    assert respuesta.url == reverse("pedidos:detalle", args=[pedido.pk]) + "#tarjeta-tallas"
    assert pedido.tallas.filter(nombre="Sin JS").exists()


def test_sin_javascript_los_errores_salen_en_una_pagina(sesion_duena, pedido):
    url = reverse("pedidos:talla_nueva", args=[pedido.pk])

    respuesta = sesion_duena.post(url, {"nombre": "", "talla": "L"})

    assert respuesta.status_code == 422
    assert "<html" in respuesta.text
    assert "Escribe el nombre de la persona." in respuesta.text
    assert f'action="{url}"' in respuesta.text


# --- Quitar --------------------------------------------------------------------------------------


def test_quitar_una_talla(sesion_duena, pedido):
    se_va = fabricas.crear_talla(pedido, nombre="Se va")
    se_queda = fabricas.crear_talla(pedido, nombre="Se queda")
    url = reverse("pedidos:talla_quitar", args=[pedido.pk, se_va.pk])

    respuesta = sesion_duena.post(url, headers=HTMX)

    assert respuesta.status_code == 200
    assert list(pedido.tallas.all()) == [se_queda]
    assert "Se va" not in respuesta.text and "Se queda" in respuesta.text


def test_sin_javascript_quitar_vuelve_al_pedido(sesion_duena, pedido):
    talla = fabricas.crear_talla(pedido)

    respuesta = sesion_duena.post(reverse("pedidos:talla_quitar", args=[pedido.pk, talla.pk]))

    assert respuesta.status_code == 302
    assert not pedido.tallas.exists()


def test_no_se_quita_la_talla_de_otro_pedido_del_mismo_taller(sesion_duena, taller, pedido):
    otro_pedido = fabricas.crear_pedido(taller)
    ajena = fabricas.crear_talla(otro_pedido)
    url = reverse("pedidos:talla_quitar", args=[pedido.pk, ajena.pk])

    assert sesion_duena.post(url, headers=HTMX).status_code == 404
    assert Talla.objects.filter(pk=ajena.pk).exists()


def test_no_se_quita_la_talla_de_otro_taller(sesion_duena, pedido):
    otro = fabricas.crear_taller()
    ajena = fabricas.crear_talla(fabricas.crear_pedido(otro))

    # Ni con el pedido propio en la dirección ni con el ajeno.
    for pk in (pedido.pk, ajena.pedido.pk):
        url = reverse("pedidos:talla_quitar", args=[pk, ajena.pk])
        assert sesion_duena.post(url, headers=HTMX).status_code == 404
    assert Talla.objects.filter(pk=ajena.pk).exists()


def test_no_se_agregan_tallas_a_un_pedido_de_otro_taller(sesion_duena):
    ajeno = fabricas.crear_pedido(fabricas.crear_taller())

    respuesta = agregar(sesion_duena, ajeno)

    assert respuesta.status_code == 404
    assert not ajeno.tallas.exists()


def test_quitar_y_agregar_piden_post(sesion_duena, pedido):
    talla = fabricas.crear_talla(pedido)

    assert sesion_duena.get(reverse("pedidos:talla_nueva", args=[pedido.pk])).status_code == 405
    url = reverse("pedidos:talla_quitar", args=[pedido.pk, talla.pk])
    assert sesion_duena.get(url).status_code == 405
    assert pedido.tallas.exists()


def test_sin_sesion_no_se_agrega_nada(client, pedido):
    respuesta = agregar(client, pedido)

    assert respuesta.status_code == 302
    assert not pedido.tallas.exists()


# --- Abrir y cerrar el enlace ----------------------------------------------------------------


def test_cerrar_y_abrir_el_enlace(sesion_duena, pedido):
    url = reverse("pedidos:tallas_enlace", args=[pedido.pk])

    cerrado = sesion_duena.post(url, {"abiertas": "no"}, headers=HTMX)
    pedido.refresh_from_db()
    assert pedido.tallas_abiertas is False
    assert "Enlace cerrado" in cerrado.text

    abierto = sesion_duena.post(url, {"abiertas": "si"}, headers=HTMX)
    pedido.refresh_from_db()
    assert pedido.tallas_abiertas is True
    assert "Enlace abierto" in abierto.text


def test_el_enlace_sin_decir_abierto_o_cerrado_no_cambia(sesion_duena, pedido):
    url = reverse("pedidos:tallas_enlace", args=[pedido.pk])

    assert sesion_duena.post(url, {"abiertas": "quizas"}, headers=HTMX).status_code == 400
    pedido.refresh_from_db()
    assert pedido.tallas_abiertas is True


def test_sin_javascript_el_enlace_vuelve_al_pedido(sesion_duena, pedido):
    url = reverse("pedidos:tallas_enlace", args=[pedido.pk])

    respuesta = sesion_duena.post(url, {"abiertas": "no"})

    assert respuesta.status_code == 302
    pedido.refresh_from_db()
    assert pedido.tallas_abiertas is False


def test_no_se_cierra_el_enlace_de_otro_taller(sesion_duena):
    ajeno = fabricas.crear_pedido(fabricas.crear_taller())
    url = reverse("pedidos:tallas_enlace", args=[ajeno.pk])

    assert sesion_duena.post(url, {"abiertas": "no"}, headers=HTMX).status_code == 404
    ajeno.refresh_from_db()
    assert ajeno.tallas_abiertas is True


def test_el_formulario_y_la_lista_van_plegados_al_abrir_el_pedido(pedido, duena):
    fabricas.crear_talla(pedido)

    html = dibujar(pedido, duena)

    assert "<details open>" not in html
    assert "Agregar una persona a mano" in html
    assert "autofocus" not in html


def test_con_errores_el_formulario_queda_abierto_y_con_el_cursor_en_el_error(sesion_duena, pedido):
    respuesta = agregar(sesion_duena, pedido, nombre="Ana Ejemplo", talla="")

    assert respuesta.text.count("<details open>") == 1
    select = re.search(r'<select name="talla"[^>]*>', respuesta.text).group(0)
    assert "autofocus" in select
    assert respuesta.text.count("autofocus") == 1
