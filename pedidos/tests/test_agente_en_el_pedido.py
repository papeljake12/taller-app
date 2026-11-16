"""Lo que el agente deja ver en el pedido por dentro (tanda 8, T38): "Lo anotó el asistente" en
la cronología y la tarjeta "Tela del pedido" (solo para ver)."""

import pytest
from django.urls import reverse

from tests import fabricas

pytestmark = pytest.mark.django_db


def test_lo_guardado_con_el_agente_dice_lo_anoto_el_asistente(sesion_duena, taller, duena):
    pedido = fabricas.crear_pedido(taller, creado_por=duena, por_asistente=True)
    fabricas.crear_abono(pedido, valor=500_000, por_asistente=True)
    fabricas.crear_abono(pedido, valor=200_000)

    html = sesion_duena.get(reverse("pedidos:detalle", args=[pedido.pk])).content.decode()
    cronologia = html[html.index('id="pedido-cronologia"'):]
    cronologia = cronologia[:cronologia.index("</section>")]

    # El pedido y el primer abono; el segundo abono se anotó en la pantalla.
    assert cronologia.count("Lo anotó el asistente") == 2
    assert cronologia.count('class="cronologia__evento"') == 3


def test_sin_el_agente_la_cronologia_queda_igual(sesion_duena, taller, duena):
    pedido = fabricas.crear_pedido(taller, creado_por=duena)
    fabricas.crear_talla(pedido, origen="manual", nombre="Laura M.")

    html = sesion_duena.get(reverse("pedidos:detalle", args=[pedido.pk])).content.decode()

    assert "Lo anotó el asistente" not in html
    assert "cronologia__que" not in html
    assert "Se agregó a mano la talla de Laura M." in html


def test_la_tela_del_pedido_confirmado_que_no_alcanza(sesion_duena, taller):
    dril = fabricas.crear_tela(taller, nombre="Dril azul", metros=18)
    pedido = fabricas.crear_pedido(taller, estado="confirmado")
    fabricas.crear_tela_pedido(pedido, dril, 66)

    html = sesion_duena.get(reverse("pedidos:detalle", args=[pedido.pk])).content.decode()

    assert "Tela del pedido" in html
    assert "Falta tela" in html
    assert "66 m" in html
    assert "Te faltan 48 m de dril azul: tienes 18 m." in html
    assert reverse("telas:inicio") in html


def test_la_tela_de_un_pedido_en_corte_ya_se_corto(sesion_duena, taller):
    pedido = fabricas.crear_pedido(taller, estado="corte")
    fabricas.crear_tela_pedido(pedido, fabricas.crear_tela(taller, metros=1), 22)

    html = sesion_duena.get(reverse("pedidos:detalle", args=[pedido.pk])).content.decode()

    assert "Ya se cortó" in html
    assert "Falta tela" not in html
    assert "Te faltan" not in html


def test_sin_tela_anotada_no_sale_la_tarjeta(sesion_duena, taller):
    pedido = fabricas.crear_pedido(taller)

    html = sesion_duena.get(reverse("pedidos:detalle", args=[pedido.pk])).content.decode()

    assert "Tela del pedido" not in html


def test_la_costurera_tambien_ve_la_tela(client, taller, costurera):
    pedido = fabricas.crear_pedido(taller, estado="confirmado")
    fabricas.crear_tela_pedido(pedido, fabricas.crear_tela(taller, nombre="Piqué blanco"), 5)
    client.force_login(costurera)

    html = client.get(reverse("pedidos:detalle", args=[pedido.pk])).content.decode()

    assert "Tela del pedido" in html and "Piqué blanco" in html
