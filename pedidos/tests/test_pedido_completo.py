"""El pedido por dentro con las partes de los cuatro carriles unidas (tanda 3).

Cada carril probó su tarjeta por separado. Aquí se prueba lo que solo existe al unirlas:
que la página trae todas las tarjetas con sus datos y que una acción en una tarjeta
actualiza las otras que dependen de ella.
"""

import pytest
from django.urls import reverse

from pedidos.formularios.comun import leer_pesos
from pedidos.recibo import para_la_hoja
from tests import fabricas

pytestmark = pytest.mark.django_db


@pytest.fixture
def pedido(taller):
    cliente = fabricas.crear_cliente(taller, nombre="Ferretería La Esquina", whatsapp="3001234567")
    pedido = fabricas.crear_pedido(taller, cliente=cliente, total=960_000, estado="confeccion")
    fabricas.crear_abono(pedido, valor=480_000)
    fabricas.crear_talla(pedido, talla="M")
    fabricas.crear_material(pedido, nombre="Dril azul", cantidad="24 m")
    return pedido


def test_la_pagina_trae_todas_las_tarjetas_con_sus_datos(sesion_duena, pedido):
    html = sesion_duena.get(reverse("pedidos:detalle", args=[pedido.pk])).text

    assert 'id="pagos"' in html and "Falta por pagar" in html and "$ 480.000" in html
    assert 'id="registrar-abono"' in html  # a donde lleva "Registrar abono" de arriba
    assert 'id="tarjeta-tallas"' in html and "Copiar enlace para el cliente" in html
    assert "Dril azul" in html
    assert 'id="pedido-etapa"' in html and 'id="pedido-avisar"' in html


def test_cambiar_la_etapa_actualiza_tambien_pagos(sesion_duena, pedido):
    respuesta = sesion_duena.post(
        reverse("pedidos:etapa", args=[pedido.pk]), {"estado": "listo"},
        headers={"HX-Request": "true"},
    )

    html = respuesta.text
    assert respuesta.status_code == 200
    assert 'id="pagos" aria-label="Pago" hx-swap-oob="true"' in html


def test_cambiar_el_whatsapp_actualiza_el_recordatorio_de_pagos(sesion_duena, pedido):
    respuesta = sesion_duena.post(
        reverse("pedidos:whatsapp", args=[pedido.pk]), {"whatsapp": "3109876543"},
        headers={"HX-Request": "true"},
    )

    assert 'hx-swap-oob="true"' in respuesta.text
    assert "wa.me/573109876543" in respuesta.text


def test_registrar_un_abono_actualiza_el_boton_avisar_al_cliente(sesion_duena, pedido):
    respuesta = sesion_duena.post(
        reverse("pedidos:abono_nuevo", args=[pedido.pk]), {"valor": "480.000"},
        headers={"HX-Request": "true", "HX-Target": "pagos"},
    )

    html = respuesta.text
    assert respuesta.status_code == 200
    assert "<span>Pagado</span>" in html
    # Ya no debe plata y no está listo: el botón de arriba queda escondido.
    assert '<span id="pedido-avisar" hidden hx-swap-oob="true">' in html


@pytest.mark.parametrize(
    ("texto", "valor"),
    [("380000", 380_000), ("$ 1.260.000", 1_260_000), ("1.260.000", 1_260_000),
     ("380.5", None), ("1,5", None), ("١٢٣", None), ("", None), ("-5", None)],
)
def test_una_sola_forma_de_leer_la_plata(texto, valor):
    assert leer_pesos(texto) == valor


def test_el_recibo_conserva_la_tilde_aunque_llegue_separada():
    separada = "José"  # "José" escrito como e + tilde suelta

    assert para_la_hoja(separada) == "José"
