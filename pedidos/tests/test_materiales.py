"""Materiales de un pedido (T12): agregar, marcar como comprado y quitar."""

import json

import pytest
from django.urls import reverse

from pedidos.models import Material
from tests import fabricas

pytestmark = pytest.mark.django_db

HTMX = {"HX-Request": "true"}


@pytest.fixture
def pedido(taller):
    return fabricas.crear_pedido(taller)


def url_nuevo(pedido):
    return reverse("pedidos:material_nuevo", args=[pedido.pk])


def url_de(nombre, material, pedido=None):
    pedido = pedido or material.pedido
    return reverse(f"pedidos:material_{nombre}", args=[pedido.pk, material.pk])


# --- La tarjeta ------------------------------------------------------------------------------


def test_la_tarjeta_dice_cuantos_hay_comprados(sesion_duena, pedido):
    fabricas.crear_material(pedido, nombre="Tela piqué de prueba", cantidad="22 m", comprado=True)
    fabricas.crear_material(pedido, nombre="Hilo de prueba", cantidad="6 conos")
    fabricas.crear_material(pedido, nombre="Botones de prueba")

    html = sesion_duena.get(reverse("pedidos:detalle", args=[pedido.pk])).text

    assert 'id="pedido-materiales"' in html
    assert "1 de 3</span>" in html
    assert '<span class="tachado">Tela piqué de prueba</span>' in html
    assert ">Hilo de prueba</label>" in html
    assert '<span class="texto-2">6 conos</span>' in html
    assert 'class="casilla casilla--marcada"' in html
    assert 'aria-label="Quitar Botones de prueba"' in html


def test_sin_materiales_invita_a_anotarlos(sesion_duena, pedido):
    html = sesion_duena.get(reverse("pedidos:detalle", args=[pedido.pk])).text

    assert "Anota aquí la tela y los insumos de este pedido" in html
    assert " de 0</span>" not in html


def test_no_muestra_los_materiales_de_otro_pedido(sesion_duena, taller, pedido):
    fabricas.crear_material(fabricas.crear_pedido(taller), nombre="De otro pedido")
    de_otro_taller = fabricas.crear_pedido(fabricas.crear_taller())
    fabricas.crear_material(de_otro_taller, nombre="De otro taller")

    html = sesion_duena.get(reverse("pedidos:detalle", args=[pedido.pk])).text

    assert "De otro pedido" not in html
    assert "De otro taller" not in html


# --- Agregar ---------------------------------------------------------------------------------


def test_agregar_un_material_devuelve_solo_la_tarjeta(sesion_duena, pedido):
    respuesta = sesion_duena.post(
        url_nuevo(pedido), {"nombre": "  Dril azul ", "cantidad": " 24 m "}, headers=HTMX
    )

    material = Material.objects.get(pedido=pedido)
    assert respuesta.status_code == 200
    assert (material.nombre, material.cantidad, material.comprado) == ("Dril azul", "24 m", False)
    assert respuesta.text.startswith(
        '<section class="tarjeta" id="pedido-materiales"'
    )
    assert "<html" not in respuesta.text
    assert "0 de 1</span>" in respuesta.text


def test_la_cantidad_es_opcional(sesion_duena, pedido):
    sesion_duena.post(url_nuevo(pedido), {"nombre": "Cierres"}, headers=HTMX)

    assert Material.objects.get(pedido=pedido).cantidad == ""


@pytest.mark.parametrize(
    ("datos", "mensaje"),
    [
        ({"nombre": ""}, "Escribe el nombre del material."),
        ({"nombre": "   "}, "Escribe el nombre del material."),
        ({"nombre": "x" * 61}, "Escribe máximo 60 letras."),
        ({"nombre": "Tela", "cantidad": "x" * 31}, "Escribe máximo 30 letras."),
    ],
)
def test_un_material_que_no_sirve_se_rechaza(sesion_duena, pedido, datos, mensaje):
    respuesta = sesion_duena.post(url_nuevo(pedido), datos, headers=HTMX)

    assert respuesta.status_code == 422
    assert mensaje in respuesta.text
    assert not Material.objects.filter(pedido=pedido).exists()


def test_sin_javascript_agregar_vuelve_al_pedido(sesion_duena, pedido):
    respuesta = sesion_duena.post(url_nuevo(pedido), {"nombre": "Cierres"})

    assert respuesta.status_code == 302
    assert respuesta.url == reverse("pedidos:detalle", args=[pedido.pk]) + "#pedido-materiales"
    assert Material.objects.filter(pedido=pedido, nombre="Cierres").exists()


def test_sin_javascript_un_error_muestra_la_pagina_con_el_mensaje(sesion_duena, pedido):
    respuesta = sesion_duena.post(url_nuevo(pedido), {"nombre": ""})

    assert respuesta.status_code == 422
    assert "<html" in respuesta.text
    assert "Escribe el nombre del material." in respuesta.text


def test_no_se_agrega_a_un_pedido_de_otro_taller(sesion_duena):
    ajeno = fabricas.crear_pedido(fabricas.crear_taller())

    respuesta = sesion_duena.post(url_nuevo(ajeno), {"nombre": "Intruso"}, headers=HTMX)

    assert respuesta.status_code == 404
    assert not Material.objects.filter(nombre="Intruso").exists()


# --- Marcar como comprado --------------------------------------------------------------------


def test_marcar_y_desmarcar_como_comprado(sesion_duena, pedido):
    material = fabricas.crear_material(pedido, nombre="Hilo")

    marcar = sesion_duena.post(url_de("comprado", material), {"comprado": "si"}, headers=HTMX)
    material.refresh_from_db()
    assert marcar.status_code == 200
    assert material.comprado is True
    assert "1 de 1</span>" in marcar.text
    assert 'aria-pressed="true"' in marcar.text

    desmarcar = sesion_duena.post(url_de("comprado", material), {"comprado": "no"}, headers=HTMX)
    material.refresh_from_db()
    assert material.comprado is False
    assert "0 de 1</span>" in desmarcar.text


def test_marcar_dos_veces_no_lo_desmarca(sesion_duena, pedido):
    material = fabricas.crear_material(pedido)

    for _ in range(2):
        sesion_duena.post(url_de("comprado", material), {"comprado": "si"}, headers=HTMX)

    material.refresh_from_db()
    assert material.comprado is True


@pytest.mark.parametrize("datos", [{}, {"comprado": ""}, {"comprado": "tal vez"}])
def test_marcar_sin_decir_como_queda_se_rechaza_y_no_cambia(sesion_duena, pedido, datos):
    material = fabricas.crear_material(pedido, comprado=True)

    respuesta = sesion_duena.post(url_de("comprado", material), datos, headers=HTMX)

    material.refresh_from_db()
    assert respuesta.status_code == 422
    assert "No se pudo marcar el material. Toca la casilla otra vez." in respuesta.text
    assert respuesta.text.startswith(
        '<section class="tarjeta" id="pedido-materiales"'
    )
    assert material.comprado is True


def test_sin_javascript_marcar_sin_decir_como_queda_muestra_la_pagina(sesion_duena, pedido):
    material = fabricas.crear_material(pedido)

    respuesta = sesion_duena.post(url_de("comprado", material), {"comprado": "x"})

    assert respuesta.status_code == 422
    assert "<html" in respuesta.text
    assert "No se pudo marcar el material." in respuesta.text


def test_sin_javascript_marcar_vuelve_al_pedido(sesion_duena, pedido):
    material = fabricas.crear_material(pedido)

    respuesta = sesion_duena.post(url_de("comprado", material), {"comprado": "si"})

    material.refresh_from_db()
    assert respuesta.status_code == 302
    assert material.comprado is True


# --- Quitar ----------------------------------------------------------------------------------


def test_quitar_un_material(sesion_duena, pedido):
    queda = fabricas.crear_material(pedido, nombre="Se queda")
    sale = fabricas.crear_material(pedido, nombre="Se va")

    respuesta = sesion_duena.post(url_de("quitar", sale), headers=HTMX)

    assert respuesta.status_code == 200
    assert list(Material.objects.filter(pedido=pedido)) == [queda]
    assert "Se va" not in respuesta.text
    assert "0 de 1</span>" in respuesta.text


# --- Aislamiento: el material tiene que ser de ese pedido y de ese taller --------------------


@pytest.mark.parametrize("accion", ["comprado", "quitar"])
def test_un_material_de_otro_pedido_del_taller_responde_404(sesion_duena, taller, pedido, accion):
    del_otro_pedido = fabricas.crear_material(fabricas.crear_pedido(taller))

    respuesta = sesion_duena.post(
        url_de(accion, del_otro_pedido, pedido=pedido), {"comprado": "si"}, headers=HTMX
    )

    del_otro_pedido.refresh_from_db()
    assert respuesta.status_code == 404
    assert del_otro_pedido.comprado is False


@pytest.mark.parametrize("accion", ["comprado", "quitar"])
def test_un_material_de_otro_taller_responde_404_y_no_cambia(sesion_duena, pedido, accion):
    ajeno = fabricas.crear_material(fabricas.crear_pedido(fabricas.crear_taller()))

    # Con el pedido propio y el material ajeno, y con los dos ajenos.
    for url in (url_de(accion, ajeno, pedido=pedido), url_de(accion, ajeno)):
        respuesta = sesion_duena.post(url, {"comprado": "si"}, headers=HTMX)
        assert respuesta.status_code == 404

    ajeno.refresh_from_db()
    assert ajeno.comprado is False


def test_las_acciones_no_aceptan_get(sesion_duena, pedido):
    material = fabricas.crear_material(pedido)

    for direccion in (url_nuevo(pedido), url_de("comprado", material), url_de("quitar", material)):
        assert sesion_duena.get(direccion).status_code == 405
    assert Material.objects.filter(pk=material.pk).exists()


# --- Aviso corto, animaciones y pantalla fija (ajuste "pantalla fija y animaciones") --------


def aviso(respuesta):
    """El aviso corto que lleva la respuesta de HTMX (config/avisos.py), o None."""
    return json.loads(respuesta.headers.get("HX-Trigger") or "{}").get("aviso")


def test_agregar_avisa_material_agregado(sesion_duena, pedido):
    respuesta = sesion_duena.post(url_nuevo(pedido), {"nombre": "Botones"}, headers=HTMX)

    assert aviso(respuesta) == "Material agregado."


def test_agregar_con_errores_no_avisa(sesion_duena, pedido):
    respuesta = sesion_duena.post(url_nuevo(pedido), {"nombre": ""}, headers=HTMX)

    assert respuesta.status_code == 422
    assert aviso(respuesta) is None


def test_quitar_avisa_material_quitado(sesion_duena, pedido):
    material = fabricas.crear_material(pedido)

    respuesta = sesion_duena.post(url_de("quitar", material), headers=HTMX)

    assert aviso(respuesta) == "Material quitado."


def test_sin_javascript_el_aviso_sale_en_el_pedido(sesion_duena, pedido):
    respuesta = sesion_duena.post(url_nuevo(pedido), {"nombre": "Botones"}, follow=True)

    assert "<p data-aviso>Material agregado.</p>" in respuesta.text


def test_marcar_como_comprado_no_avisa(sesion_duena, pedido):
    """Se ve justo donde se tocó: la casilla se marca."""
    material = fabricas.crear_material(pedido)

    respuesta = sesion_duena.post(url_de("comprado", material), {"comprado": "si"}, headers=HTMX)

    assert respuesta.status_code == 200
    assert aviso(respuesta) is None


def test_cada_material_lleva_su_id_dentro_de_su_lista(sesion_duena, pedido):
    """El id deja que al agregar o quitar solo esa fila entre o salga (static/js/app.js)."""
    material = fabricas.crear_material(pedido, nombre="Botones de prueba")

    html = sesion_duena.post(url_de("comprado", material), {"comprado": "si"}, headers=HTMX).text

    assert '<section class="tarjeta" id="pedido-materiales"' in html
    assert '<div class="materiales__lista">' in html
    assert f'<div class="renglon" id="material-{material.pk}">' in html
    # El formulario para agregar queda fuera de la lista, en el pie de la tarjeta.
    lista = html.index('class="materiales__lista')
    assert html.index(f'id="material-{material.pk}"') > lista
    assert html.index('<form class="tarjeta__pie materiales__agregar"') > lista
