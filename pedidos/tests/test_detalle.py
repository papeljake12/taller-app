"""Pedido por dentro (T07): ficha, etapa, entrega, encargada, WhatsApp y eliminar."""

from datetime import timedelta

import pytest
from django.core.files.base import ContentFile
from django.urls import reverse
from django.utils import timezone

from cuentas.models import Usuario
from pedidos.models import Abono, Material, Pedido, Talla
from pedidos.vistas.detalle import frase_de_entrega
from tests import fabricas

pytestmark = pytest.mark.django_db

HTMX = {"HX-Request": "true"}


def hoy():
    """Hoy en Bogotá, en el momento de la prueba.

    Antes era una constante que se calculaba al cargar el archivo. Si las pruebas empezaban
    antes de la medianoche y estas corrían después, la página ya contaba desde el día
    siguiente ("Se entrega en 32 días" en vez de 33) y la prueba fallaba esa única vez (T23).
    """
    return timezone.localdate()


def url(nombre, pedido):
    return reverse(f"pedidos:{nombre}", args=[pedido.pk])


@pytest.fixture
def pedido(taller):
    cliente = fabricas.crear_cliente(taller, nombre="Restaurante de prueba", tipo="empresa")
    return fabricas.crear_pedido(
        taller,
        cliente=cliente,
        detalle="18 camisas polo de prueba",
        estado=Pedido.Estado.CORTE,
        total=2_520_000,
        fecha_entrega=hoy() + timedelta(days=33),
    )


@pytest.fixture
def ajeno():
    """Un pedido de otro taller."""
    otro = fabricas.crear_taller()
    return fabricas.crear_pedido(otro, estado=Pedido.Estado.CORTE)


# --- La página -------------------------------------------------------------------------------


def test_la_ficha_muestra_los_datos_del_pedido(sesion_duena, pedido):
    html = sesion_duena.get(url("detalle", pedido)).text

    titulo = html[html.index('id="pedido-apoyo"') :].split("</div>")[0]
    assert "<h1>Restaurante de prueba" in titulo
    assert '<span class="etiqueta etiqueta--azul etiqueta--medio">En corte</span>' in titulo
    assert "Sin abonos</span>" in titulo
    assert "Se entrega el " in titulo and ", en 33 días" in titulo
    assert "Creado el " in titulo
    assert "18 camisas polo de prueba" in html
    assert "Pasar a En confección" in html
    assert "En 33 días" in html
    assert ">Encargada</label>" in html
    assert "Empresa · 1 pedido" in html
    assert "Sin WhatsApp." in html
    assert 'href="#registrar-abono"' in html
    assert "Número de ejemplo" not in html


def test_los_pasos_marcan_las_etapas_hechas_la_actual_y_las_que_faltan(sesion_duena, pedido):
    html = sesion_duena.get(url("detalle", pedido)).text

    assert 'class="paso paso--hecho" name="estado" value="cotizado"' in html
    assert 'class="paso paso--hecho" name="estado" value="confirmado"' in html
    assert 'class="paso paso--actual" name="estado" value="corte" aria-current="step"' in html
    assert 'class="paso paso--pendiente" name="estado" value="confeccion"' in html
    assert 'class="paso paso--pendiente" name="estado" value="entregado"' in html


def test_el_cliente_dice_cuantos_pedidos_tiene(sesion_duena, taller, pedido):
    fabricas.crear_pedido(taller, cliente=pedido.cliente)

    assert "Empresa · 2 pedidos" in sesion_duena.get(url("detalle", pedido)).text


def test_la_encargada_se_elige_entre_las_usuarias_activas_del_taller(sesion_duena, taller, pedido):
    fabricas.crear_usuaria(taller, rol=Usuario.Rol.COSTURERA, nombre_visible="Marta de prueba")
    fabricas.crear_usuaria(
        taller, rol=Usuario.Rol.COSTURERA, nombre_visible="Inactiva de prueba", is_active=False
    )
    fabricas.crear_usuaria(fabricas.crear_taller(), nombre_visible="Costurera de otro taller")

    html = sesion_duena.get(url("detalle", pedido)).text

    assert "Sin asignar" in html
    assert "Marta de prueba" in html
    assert "Inactiva de prueba" not in html
    assert "Costurera de otro taller" not in html


def test_la_encargada_desactivada_sigue_apareciendo_en_su_pedido(sesion_duena, taller, pedido):
    inactiva = fabricas.crear_usuaria(
        taller, rol=Usuario.Rol.COSTURERA, nombre_visible="Inactiva de prueba", is_active=False
    )
    pedido.encargada = inactiva
    pedido.save()

    html = sesion_duena.get(url("detalle", pedido)).text

    assert f'<option value="{inactiva.pk}" selected>Inactiva de prueba</option>' in html


def test_un_pedido_de_otro_taller_responde_404(sesion_duena, ajeno):
    assert sesion_duena.get(url("detalle", ajeno)).status_code == 404


# --- La frase de la entrega ------------------------------------------------------------------


@pytest.mark.parametrize(
    ("estado", "dias", "frase", "atrasado"),
    [
        ("corte", 33, "Se entrega en 33 días.", False),
        ("corte", 1, "Se entrega mañana.", False),
        ("corte", 0, "Se entrega hoy.", False),
        ("confeccion", -1, "Lleva 1 día de atraso.", True),
        ("confeccion", -2, "Lleva 2 días de atraso.", True),
        ("cotizado", -3, "La fecha de entrega ya pasó.", False),
        ("entregado", -5, "Pedido entregado.", False),
        ("entregado", 4, "Pedido entregado.", False),
    ],
)
def test_frase_de_entrega(taller, estado, dias, frase, atrasado):
    dia = hoy()
    pedido = fabricas.crear_pedido(taller, estado=estado, fecha_entrega=dia + timedelta(days=dias))

    assert frase_de_entrega(pedido, hoy=dia) == (frase, atrasado)


def test_el_atraso_va_en_rojo(sesion_duena, taller):
    pedido = fabricas.crear_pedido(
        taller, estado="confeccion", fecha_entrega=hoy() - timedelta(days=2)
    )

    html = sesion_duena.get(url("detalle", pedido)).text

    assert '<span class="texto-rojo">Lleva 2 días de atraso</span>' in html
    assert "lleva 2 días de atraso" in html


# --- Etapa -----------------------------------------------------------------------------------


def test_tocar_una_etapa_la_guarda_y_devuelve_la_tarjeta_y_lo_que_depende(sesion_duena, pedido):
    respuesta = sesion_duena.post(url("etapa", pedido), {"estado": "listo"}, headers=HTMX)

    pedido.refresh_from_db()
    assert respuesta.status_code == 200
    assert pedido.estado == "listo"
    html = respuesta.text
    assert "<html" not in html
    assert html.startswith('<section class="tarjeta" id="pedido-etapa"')
    assert 'class="paso paso--actual" name="estado" value="listo"' in html
    # La etiqueta de arriba, el botón "Avisar al cliente", la entrega y el cliente cambian.
    assert 'id="pedido-apoyo" hx-swap-oob="true"' in html
    assert '<span class="etiqueta etiqueta--verde etiqueta--lleno">Listo</span>' in html
    assert 'id="pedido-avisar"' in html
    assert 'id="pedido-entrega"' in html
    assert 'id="pedido-cliente"' in html
    assert "Copiar aviso de pedido listo" in html


def test_sin_javascript_la_etapa_vuelve_al_pedido(sesion_duena, pedido):
    respuesta = sesion_duena.post(url("etapa", pedido), {"estado": "confeccion"})

    pedido.refresh_from_db()
    assert pedido.estado == "confeccion"
    assert respuesta.status_code == 302
    assert respuesta.url == url("detalle", pedido) + "#pedido-etapa"


def test_una_etapa_inventada_se_rechaza_con_un_mensaje(sesion_duena, pedido):
    respuesta = sesion_duena.post(url("etapa", pedido), {"estado": "volando"}, headers=HTMX)

    pedido.refresh_from_db()
    assert respuesta.status_code == 422
    assert pedido.estado == "corte"
    assert "Elige una de las seis etapas." in respuesta.text


def test_la_etapa_de_otro_taller_responde_404_y_no_cambia(sesion_duena, ajeno):
    respuesta = sesion_duena.post(url("etapa", ajeno), {"estado": "entregado"}, headers=HTMX)

    ajeno.refresh_from_db()
    assert respuesta.status_code == 404
    assert ajeno.estado == "corte"


# --- Avisar al cliente -----------------------------------------------------------------------


def test_avisar_sin_whatsapp_copia_el_recordatorio_del_saldo(sesion_duena, pedido):
    fabricas.crear_abono(pedido, valor=1_260_000)

    html = sesion_duena.get(url("detalle", pedido)).text

    assert 'id="pedido-avisar" data-copiar="Hola, le escribimos' in html
    assert "saldo pendiente de $ 1.260.000" in html


def test_avisar_con_whatsapp_abre_el_chat_con_el_aviso_de_listo(sesion_duena, pedido):
    pedido.cliente.whatsapp = "300 000 0000"
    pedido.cliente.save()
    pedido.estado = "listo"
    pedido.save()

    html = sesion_duena.get(url("detalle", pedido)).text

    assert 'href="https://wa.me/573000000000?text=' in html
    assert "ya%20est%C3%A1%20listo%20para%20entregar" in html
    assert "Avisar por WhatsApp que está listo" in html
    assert "Copiar aviso de pedido listo" not in html


def test_sin_nada_que_avisar_no_hay_boton_de_avisar(sesion_duena, taller):
    pagado = fabricas.crear_pedido(taller, estado="corte", total=500_000)
    fabricas.crear_abono(pagado, valor=500_000)
    cotizado = fabricas.crear_pedido(taller, estado="cotizado")

    for pedido in (pagado, cotizado):
        html = sesion_duena.get(url("detalle", pedido)).text
        assert '<span id="pedido-avisar" hidden></span>' in html
        assert "Avisar al cliente" not in html


# --- Entrega y encargada ---------------------------------------------------------------------


def test_cambiar_la_fecha_la_guarda_y_dice_los_dias(sesion_duena, pedido):
    nueva = hoy() + timedelta(days=1)

    respuesta = sesion_duena.post(
        url("entrega", pedido), {"fecha_entrega": nueva.isoformat()}, headers=HTMX
    )

    pedido.refresh_from_db()
    assert respuesta.status_code == 200
    assert pedido.fecha_entrega == nueva
    assert respuesta.text.startswith('<section class="tarjeta tarjeta--lado" id="pedido-entrega"')
    assert "Mañana" in respuesta.text
    assert 'id="pedido-apoyo" hx-swap-oob="true"' in respuesta.text
    assert 'id="pedido-avisar" data-copiar' in respuesta.text


def test_la_fecha_tambien_se_acepta_escrita_a_mano(sesion_duena, pedido):
    sesion_duena.post(url("entrega", pedido), {"fecha_entrega": "14/12/2026"}, headers=HTMX)

    pedido.refresh_from_db()
    assert pedido.fecha_entrega.isoformat() == "2026-12-14"


@pytest.mark.parametrize(
    ("valor", "mensaje"),
    [("", "Elige la fecha de entrega."), ("mañana", "Escribe la fecha como día/mes/año.")],
)
def test_una_fecha_que_no_sirve_se_rechaza(sesion_duena, pedido, valor, mensaje):
    antes = pedido.fecha_entrega

    respuesta = sesion_duena.post(url("entrega", pedido), {"fecha_entrega": valor}, headers=HTMX)

    pedido.refresh_from_db()
    assert respuesta.status_code == 422
    assert mensaje in respuesta.text
    assert pedido.fecha_entrega == antes
    assert "En 33 días" in respuesta.text
    # Con el error, el campo de la fecha queda a la vista.
    assert '<div id="entrega-fecha">' in respuesta.text


def test_sin_javascript_una_fecha_que_no_sirve_muestra_la_pagina_con_el_error(
    sesion_duena, pedido
):
    respuesta = sesion_duena.post(url("entrega", pedido), {"fecha_entrega": ""})

    assert respuesta.status_code == 422
    assert "<html" in respuesta.text
    assert "Elige la fecha de entrega." in respuesta.text


def test_elegir_la_encargada(sesion_duena, taller, pedido):
    marta = fabricas.crear_usuaria(taller, rol=Usuario.Rol.COSTURERA, nombre_visible="Marta")

    respuesta = sesion_duena.post(url("encargada", pedido), {"encargada": marta.pk}, headers=HTMX)

    pedido.refresh_from_db()
    assert respuesta.status_code == 200
    assert pedido.encargada == marta
    assert f'<option value="{marta.pk}" selected>Marta</option>' in respuesta.text


def test_quitar_la_encargada(sesion_duena, taller, pedido):
    pedido.encargada = fabricas.crear_usuaria(taller, rol=Usuario.Rol.COSTURERA)
    pedido.save()

    sesion_duena.post(url("encargada", pedido), {"encargada": ""}, headers=HTMX)

    pedido.refresh_from_db()
    assert pedido.encargada is None


def test_no_se_puede_elegir_una_usuaria_de_otro_taller(sesion_duena, pedido):
    de_otro = fabricas.crear_usuaria(fabricas.crear_taller(), rol=Usuario.Rol.COSTURERA)

    respuesta = sesion_duena.post(
        url("encargada", pedido), {"encargada": de_otro.pk}, headers=HTMX
    )

    pedido.refresh_from_db()
    assert respuesta.status_code == 422
    assert "Elige a una persona del taller." in respuesta.text
    assert pedido.encargada is None


def test_no_se_puede_elegir_una_usuaria_desactivada(sesion_duena, taller, pedido):
    inactiva = fabricas.crear_usuaria(taller, rol=Usuario.Rol.COSTURERA, is_active=False)

    respuesta = sesion_duena.post(
        url("encargada", pedido), {"encargada": inactiva.pk}, headers=HTMX
    )

    pedido.refresh_from_db()
    assert respuesta.status_code == 422
    assert pedido.encargada is None


def test_la_entrega_y_la_encargada_de_otro_taller_responden_404(sesion_duena, taller, ajeno):
    antes = ajeno.fecha_entrega
    marta = fabricas.crear_usuaria(taller, rol=Usuario.Rol.COSTURERA)

    fecha = sesion_duena.post(url("entrega", ajeno), {"fecha_entrega": "2030-01-01"})
    encargada = sesion_duena.post(url("encargada", ajeno), {"encargada": marta.pk})

    ajeno.refresh_from_db()
    assert fecha.status_code == encargada.status_code == 404
    assert ajeno.fecha_entrega == antes
    assert ajeno.encargada is None


# --- WhatsApp del cliente --------------------------------------------------------------------


def test_guardar_el_whatsapp_lo_deja_en_el_cliente(sesion_duena, pedido):
    respuesta = sesion_duena.post(
        url("whatsapp", pedido), {"whatsapp": " 300 000 0000 "}, headers=HTMX
    )

    pedido.cliente.refresh_from_db()
    assert respuesta.status_code == 200
    assert pedido.cliente.whatsapp == "300 000 0000"
    assert respuesta.text.startswith('<section class="tarjeta tarjeta--lado" id="pedido-cliente"')
    assert "Número guardado." in respuesta.text
    # Con número, "Avisar al cliente" abre WhatsApp.
    assert 'id="pedido-avisar" href="https://wa.me/573000000000' in respuesta.text


def test_enter_en_el_whatsapp_no_lo_envia_dos_veces(sesion_duena, pedido):
    # Al salir del campo se envía ("change"); Enter dispara "change" y "submit" a la vez:
    # hx-sync deja pasar el primero y descarta el otro.
    html = sesion_duena.get(url("detalle", pedido)).text

    assert 'hx-trigger="change, submit" hx-sync="this:drop"' in html


def test_borrar_el_whatsapp(sesion_duena, pedido):
    pedido.cliente.whatsapp = "300 000 0000"
    pedido.cliente.save()

    respuesta = sesion_duena.post(url("whatsapp", pedido), {"whatsapp": ""}, headers=HTMX)

    pedido.cliente.refresh_from_db()
    assert pedido.cliente.whatsapp == ""
    assert "Número borrado." in respuesta.text


@pytest.mark.parametrize(
    ("valor", "mensaje"),
    [
        ("tres cero cero", "Escribe solo números, sin letras."),
        ("300 12", "Revisa el número: un celular tiene 10 dígitos"),
        ("1" * 41, "Escribe máximo 40 caracteres."),
    ],
)
def test_un_whatsapp_que_no_sirve_se_rechaza(sesion_duena, pedido, valor, mensaje):
    respuesta = sesion_duena.post(url("whatsapp", pedido), {"whatsapp": valor}, headers=HTMX)

    pedido.cliente.refresh_from_db()
    assert respuesta.status_code == 422
    assert mensaje in respuesta.text
    assert pedido.cliente.whatsapp == ""


def test_el_whatsapp_de_otro_taller_responde_404_y_no_cambia(sesion_duena, ajeno):
    respuesta = sesion_duena.post(url("whatsapp", ajeno), {"whatsapp": "300 000 0000"})

    ajeno.cliente.refresh_from_db()
    assert respuesta.status_code == 404
    assert ajeno.cliente.whatsapp == ""


def test_sin_whatsapp_y_listo_se_copia_el_aviso_y_se_explica(sesion_duena, pedido):
    pedido.estado = "listo"
    pedido.save()

    html = sesion_duena.get(url("detalle", pedido)).text

    assert "Copiar aviso de pedido listo" in html
    assert "Escribe el WhatsApp del cliente y aquí aparece el botón" in html


# --- Eliminar --------------------------------------------------------------------------------


def test_eliminar_primero_pregunta(sesion_duena, pedido):
    ventana = sesion_duena.get(url("eliminar", pedido), headers=HTMX)
    pagina = sesion_duena.get(url("eliminar", pedido))

    assert ventana.status_code == pagina.status_code == 200
    assert "<html" not in ventana.text
    assert "¿Eliminar este pedido?" in ventana.text
    assert "Restaurante de prueba" in ventana.text
    assert "Sí, eliminar" in ventana.text
    assert "<html" in pagina.text and "Sí, eliminar" in pagina.text
    assert Pedido.objects.filter(pk=pedido.pk).exists()


def test_la_ficha_tiene_eliminar_en_mas_acciones(sesion_duena, pedido):
    html = sesion_duena.get(url("detalle", pedido)).text

    menu = html[html.index("Más acciones") :]
    assert f'hx-get="{url("eliminar", pedido)}" hx-target="#ventana"' in menu
    assert "Eliminar el pedido</a>" in menu


def test_las_flechas_llevan_al_pedido_anterior_y_al_siguiente_de_la_lista(
    sesion_duena, taller
):
    primero = fabricas.crear_pedido(taller, fecha_entrega=hoy() + timedelta(days=1))
    medio = fabricas.crear_pedido(taller, fecha_entrega=hoy() + timedelta(days=2))
    ultimo = fabricas.crear_pedido(taller, fecha_entrega=hoy() + timedelta(days=3))

    html = sesion_duena.get(url("detalle", medio)).text
    assert f'href="{url("detalle", primero)}" aria-label="Pedido anterior"' in html
    assert f'href="{url("detalle", ultimo)}" aria-label="Pedido siguiente"' in html

    # En los extremos la flecha va apagada y sin enlace.
    html = sesion_duena.get(url("detalle", primero)).text
    assert 'aria-disabled="true" aria-label="Pedido anterior"' in html
    assert f'href="{url("detalle", medio)}" aria-label="Pedido siguiente"' in html
    html = sesion_duena.get(url("detalle", ultimo)).text
    assert 'aria-disabled="true" aria-label="Pedido siguiente"' in html


def test_las_flechas_no_llevan_a_pedidos_de_otro_taller(sesion_duena, pedido, ajeno):
    html = sesion_duena.get(url("detalle", pedido)).text

    assert url("detalle", ajeno) not in html


def test_el_boton_pasar_a_guarda_la_etapa_siguiente(sesion_duena, pedido):
    respuesta = sesion_duena.post(url("etapa", pedido), {"estado": "confeccion"}, headers=HTMX)

    pedido.refresh_from_db()
    assert pedido.estado == "confeccion"
    assert "Pasar a Listo" in respuesta.text


def test_entregado_no_tiene_pasar_a(sesion_duena, pedido):
    sesion_duena.post(url("etapa", pedido), {"estado": "entregado"}, headers=HTMX)

    html = sesion_duena.get(url("detalle", pedido)).text
    assert "Pasar a" not in html
    assert "Cambiar etapa" in html


def test_cambiar_la_fecha_sin_javascript_deja_el_campo_a_la_vista(sesion_duena, pedido):
    normal = sesion_duena.get(url("detalle", pedido)).text
    abierta = sesion_duena.get(url("detalle", pedido) + "?cambiar=fecha").text

    assert '<div id="entrega-fecha" hidden>' in normal
    assert '<div id="entrega-fecha">' in abierta


def test_eliminar_borra_el_pedido_con_todo_lo_suyo(sesion_duena, pedido, settings, tmp_path):
    settings.MEDIA_ROOT = tmp_path
    fabricas.crear_abono(pedido)
    fabricas.crear_talla(pedido)
    fabricas.crear_material(pedido)
    pedido.foto.save("prueba.jpg", ContentFile(b"no importa"), save=True)
    archivo = tmp_path / pedido.foto.name
    assert archivo.exists()

    respuesta = sesion_duena.post(url("eliminar", pedido), headers=HTMX)

    assert respuesta.headers["HX-Redirect"] == reverse("pedidos:lista")
    assert not Pedido.objects.filter(pk=pedido.pk).exists()
    assert not Abono.objects.filter(pedido=pedido.pk).exists()
    assert not Talla.objects.filter(pedido=pedido.pk).exists()
    assert not Material.objects.filter(pedido=pedido.pk).exists()
    assert not archivo.exists()
    # El cliente se queda: puede tener otros pedidos.
    pedido.cliente.refresh_from_db()


def test_sin_javascript_eliminar_vuelve_a_pedidos(sesion_duena, pedido):
    respuesta = sesion_duena.post(url("eliminar", pedido))

    assert respuesta.status_code == 302
    assert respuesta.url == reverse("pedidos:lista")
    assert not Pedido.objects.filter(pk=pedido.pk).exists()


def test_eliminar_un_pedido_de_otro_taller_responde_404_y_no_lo_borra(sesion_duena, ajeno):
    assert sesion_duena.get(url("eliminar", ajeno)).status_code == 404
    assert sesion_duena.post(url("eliminar", ajeno), headers=HTMX).status_code == 404
    assert Pedido.objects.filter(pk=ajeno.pk).exists()


def test_sin_sesion_las_acciones_llevan_a_entrar(client, pedido):
    for nombre in ("etapa", "entrega", "encargada", "whatsapp", "eliminar"):
        respuesta = client.post(url(nombre, pedido))
        assert respuesta.status_code == 302, nombre
        assert respuesta.url.startswith("/entrar/")
    pedido.refresh_from_db()
    assert pedido.estado == "corte"


# --- Aviso corto y pantalla fija (ajuste "pantalla fija y animaciones") ---------------------


def test_eliminar_avisa_pedido_eliminado_en_la_lista(sesion_duena, pedido):
    """Como la demo: el aviso sale en Pedidos, la página a la que se llega."""
    respuesta = sesion_duena.post(url("eliminar", pedido), headers=HTMX)

    assert "HX-Trigger" not in respuesta.headers
    lista = sesion_duena.get(respuesta.headers["HX-Redirect"]).text
    assert "<p data-aviso>Pedido eliminado.</p>" in lista


def test_sin_javascript_eliminar_avisa_en_la_lista(sesion_duena, pedido):
    respuesta = sesion_duena.post(url("eliminar", pedido), follow=True)

    assert "<p data-aviso>Pedido eliminado.</p>" in respuesta.text


def test_lo_que_se_ve_justo_donde_se_toca_no_avisa(sesion_duena, taller, pedido):
    """La etapa, la fecha, la encargada y el WhatsApp se guardan solos al tocarlos y el
    cambio se ve ahí mismo: no llevan aviso corto."""
    marta = fabricas.crear_usuaria(taller, rol=Usuario.Rol.COSTURERA, nombre_visible="Marta")
    respuestas = [
        sesion_duena.post(url("etapa", pedido), {"estado": "confeccion"}, headers=HTMX),
        sesion_duena.post(url("entrega", pedido),
                          {"fecha_entrega": (hoy() + timedelta(days=5)).isoformat()},
                          headers=HTMX),
        sesion_duena.post(url("encargada", pedido), {"encargada": marta.pk}, headers=HTMX),
        sesion_duena.post(url("whatsapp", pedido), {"whatsapp": "3001234567"}, headers=HTMX),
    ]

    for respuesta in respuestas:
        assert respuesta.status_code == 200
        assert "aviso" not in respuesta.headers.get("HX-Trigger", "")


def test_las_dos_columnas_miden_lo_que_mide_su_contenido(sesion_duena, pedido):
    """Ya no hay pantalla fija: la hoja se desplaza y cada columna es una pila de tarjetas."""
    html = sesion_duena.get(url("detalle", pedido)).text

    assert '<div class="columnas pedido-por-dentro">' in html
    assert "llenar" not in html and "desplazable" not in html
    izquierda, derecha = html.split('<div class="columnas pedido-por-dentro">')[1].split(
        '</div>\n<div class="columna">'
    )
    for tarjeta in ("pedido-etapa", 'id="pagos"', "tarjeta-tallas", "pedido-cronologia"):
        assert tarjeta in izquierda
    for tarjeta in ("pedido-cliente", "pedido-entrega", "pedido-foto", "pedido-materiales"):
        assert tarjeta in derecha
    assert "pedido-eliminar" not in html


def test_numero_guardado_lleva_id_para_aparecer_con_un_desvanecido(sesion_duena, pedido):
    respuesta = sesion_duena.post(url("whatsapp", pedido), {"whatsapp": "3001234567"},
                                  headers=HTMX)

    assert '<p class="nota" id="pedido-whatsapp-guardado" role="status">Número guardado.</p>' in (
        respuesta.text
    )
