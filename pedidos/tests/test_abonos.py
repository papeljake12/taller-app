"""T08. Abonos: la tarjeta Pagos, registrar y quitar abonos, y el recordatorio del saldo."""

import json
import re
from datetime import date, timedelta

import pytest
from django.template.loader import render_to_string
from django.test import RequestFactory
from django.urls import reverse
from django.utils import timezone

from pedidos.formularios.abonos import FormularioAbono
from pedidos.formularios.comun import leer_pesos
from pedidos.models import Abono
from pedidos.vistas.abonos import contexto_pagos
from tests import fabricas

pytestmark = pytest.mark.django_db

HTMX = {"HX-Request": "true", "HX-Target": "pagos"}


def tarjeta(pedido, usuaria):
    """La tarjeta Pagos como la dibuja el pedido por dentro."""
    request = RequestFactory().get("/")
    request.user = usuaria
    request.taller = usuaria.taller
    return render_to_string("pedidos/_pagos.html", contexto_pagos(request, pedido), request)


def entrada(html, nombre):
    """La etiqueta <input> del campo `nombre` dentro del html."""
    return re.search(rf'<input[^>]*name="{nombre}"[^>]*>', html).group(0)


def url_nuevo(pedido):
    return reverse("pedidos:abono_nuevo", args=[pedido.pk])


def url_quitar(abono):
    return reverse("pedidos:abono_quitar", args=[abono.pedido_id, abono.pk])


@pytest.fixture
def pedido(taller):
    """El pedido del Restaurante del diseño: total 2.520.000 y un abono de 1.260.000."""
    pedido = fabricas.crear_pedido(
        taller, detalle="18 camisas polo bordadas y 18 delantales", total=2_520_000
    )
    fabricas.crear_abono(pedido, valor=1_260_000, fecha=date(2026, 11, 5))
    return pedido


# --- La tarjeta ---------------------------------------------------------------------------


def test_la_tarjeta_muestra_la_insignia_las_cuentas_y_cada_abono(pedido, duena):
    html = tarjeta(pedido, duena)

    assert 'id="pagos"' in html and 'aria-label="Pago"' in html
    assert '<span class="etiqueta etiqueta--naranja etiqueta--medio">Abonado 50 %</span>' in html
    assert '<span>Valor total</span><span class="dinero">$ 2.520.000</span>' in html
    assert "Falta por pagar</span><span class=\"dinero\">$ 1.260.000</span>" in html
    assert 'Abono del 5 de nov · <a href=' in html
    assert '<span class="dinero">− $ 1.260.000</span>' in html
    abono = pedido.abonos.get()
    assert f'href="{reverse("pedidos:recibo", args=[pedido.pk, abono.pk])}" download>Recibo</a>' in html
    assert f'hx-get="{url_quitar(abono)}"' in html
    assert ">Quitar</a>" in html
    assert 'href="#registrar-abono">Registrar abono</a>' in html
    assert "progressbar" not in html
    assert "Pagado" not in html


def test_el_formulario_trae_el_campo_al_que_lleva_el_boton_de_arriba_y_la_fecha_de_hoy(
    pedido, duena
):
    html = tarjeta(pedido, duena)

    assert 'id="registrar-abono"' in html
    assert 'for="registrar-abono"' in html
    assert "Valor del abono (pesos)" in html
    assert f'value="{timezone.localdate().isoformat()}"' in html
    assert f'hx-post="{url_nuevo(pedido)}"' in html
    assert 'hx-target="#pagos" hx-swap="outerHTML"' in html


def test_sin_abonos_solo_trae_el_total_y_lo_que_falta(taller, duena):
    pedido = fabricas.crear_pedido(taller, total=380_000)

    html = tarjeta(pedido, duena)

    assert "Sin abonos</span>" in html
    assert "Abono del" not in html
    assert "Falta por pagar</span><span class=\"dinero\">$ 380.000</span>" in html


def test_con_saldo_en_0_dice_pagado_en_gris_y_no_pide_recordar(pedido, duena):
    fabricas.crear_abono(pedido, valor=1_260_000)

    html = tarjeta(pedido, duena)

    assert '<span class="etiqueta etiqueta--gris etiqueta--lleno">Pagado</span>' in html
    assert '<span>Pagado</span><span class="dinero">$ 0</span>' in html
    assert "Falta por pagar" not in html
    assert "texto-verde" not in html
    assert "Recordar el saldo" not in html
    assert "Copiar recordatorio" not in html


def test_con_whatsapp_el_recordatorio_abre_whatsapp_con_el_texto(taller, duena):
    cliente = fabricas.crear_cliente(taller, whatsapp="300 000 0000")
    pedido = fabricas.crear_pedido(taller, cliente=cliente, total=900_000)

    html = tarjeta(pedido, duena)

    assert 'href="https://wa.me/573000000000?text=' in html
    assert "Recordar el saldo por WhatsApp" in html
    assert "saldo%20pendiente%20de%20%24%20900.000" in html
    assert "data-copiar" not in html


def test_sin_whatsapp_el_recordatorio_se_copia(pedido, duena):
    html = tarjeta(pedido, duena)

    assert "wa.me" not in html
    assert "Copiar recordatorio de saldo" in html
    assert "tiene un saldo pendiente de $ 1.260.000" in html  # dentro de data-copiar


def test_otro_taller_no_aparece_en_la_tarjeta(pedido, duena):
    otro = fabricas.crear_pedido(fabricas.crear_taller(), total=5_000_000)
    fabricas.crear_abono(otro, valor=777_000)

    html = tarjeta(pedido, duena)

    assert "777.000" not in html


# --- Registrar un abono -------------------------------------------------------------------


def test_registrar_un_abono_baja_el_saldo_y_devuelve_solo_la_tarjeta(sesion_duena, pedido, duena):
    respuesta = sesion_duena.post(
        url_nuevo(pedido), {"valor": "$ 380.000", "fecha": "2026-11-10"}, headers=HTMX
    )

    assert respuesta.status_code == 200
    html = respuesta.text
    assert "<html" not in html and 'id="pagos"' in html
    assert "$ 880.000" in html  # el saldo: 2.520.000 - 1.260.000 - 380.000
    assert '<span class="dinero">− $ 380.000</span>' in html
    assert "Abono del 10 de nov" in html
    # Lo que cambia con el saldo viaja aparte: el título con la insignia y la cronología.
    assert 'id="pedido-apoyo" hx-swap-oob="true"' in html
    assert 'id="pedido-cronologia" aria-labelledby="t-cronologia" hx-swap-oob="true"' in html
    assert "Se registró un abono de <span class=\"dinero\">$ 380.000</span>" in html
    nuevo = pedido.abonos.get(valor=380_000)
    assert nuevo.fecha == date(2026, 11, 10)
    assert nuevo.registrado_por == duena
    # El formulario vuelve vacío para el siguiente.
    assert 'name="valor" value=' not in html


@pytest.mark.parametrize(
    "escrito, pesos",
    [("380000", 380_000), ("380.000", 380_000), ("$ 1.260.000", 1_260_000),
     ("$380.000", 380_000), (" 1 260 000 ", 1_260_000)],
)
def test_el_valor_se_puede_escribir_con_puntos_y_signo_pesos(escrito, pesos):
    assert leer_pesos(escrito) == pesos


@pytest.mark.parametrize("escrito", ["", "abc", "1.5", "380,50", "-100", "1.2345", "12.000,00"])
def test_lo_que_no_es_un_valor_en_pesos_no_se_lee(escrito):
    assert leer_pesos(escrito) is None


def test_al_abrir_el_pedido_el_cursor_no_salta_al_formulario(pedido, duena):
    html = tarjeta(pedido, duena)

    assert "autofocus" not in html


def test_despues_de_registrar_el_cursor_queda_listo_para_el_siguiente_abono(
    sesion_duena, pedido
):
    respuesta = sesion_duena.post(url_nuevo(pedido), {"valor": "100.000"}, headers=HTMX)

    assert respuesta.status_code == 200
    assert "autofocus" in entrada(respuesta.text, "valor")


def test_con_un_error_el_cursor_vuelve_al_campo_que_hay_que_corregir(sesion_duena, pedido):
    mal_valor = sesion_duena.post(
        url_nuevo(pedido), {"valor": "cien", "fecha": "2026-11-10"}, headers=HTMX
    )
    mala_fecha = sesion_duena.post(
        url_nuevo(pedido), {"valor": "100.000", "fecha": "31/02/2026"}, headers=HTMX
    )

    assert mal_valor.status_code == mala_fecha.status_code == 422
    assert "autofocus" in entrada(mal_valor.text, "valor")
    assert "autofocus" not in entrada(mal_valor.text, "fecha")
    assert "autofocus" in entrada(mala_fecha.text, "fecha")
    assert "autofocus" not in entrada(mala_fecha.text, "valor")


def test_sin_fecha_el_abono_queda_con_la_de_hoy(sesion_duena, pedido):
    sesion_duena.post(url_nuevo(pedido), {"valor": "100.000", "fecha": ""}, headers=HTMX)

    assert pedido.abonos.get(valor=100_000).fecha == timezone.localdate()


@pytest.mark.parametrize(
    "valor, mensaje",
    [
        ("", "Escribe el valor del abono."),
        ("0", "El abono debe ser mayor que 0."),
        ("abc", "Escribe solo el valor en pesos, por ejemplo 380.000."),
        ("1.5", "Escribe solo el valor en pesos, por ejemplo 380.000."),
        ("2.000.000.000", "Revisa el valor: es demasiado grande."),
    ],
)
def test_un_valor_que_no_sirve_se_rechaza_con_un_mensaje_claro(
    sesion_duena, pedido, valor, mensaje
):
    respuesta = sesion_duena.post(
        url_nuevo(pedido), {"valor": valor, "fecha": "2026-11-10"}, headers=HTMX
    )

    assert respuesta.status_code == 422
    assert mensaje in respuesta.text
    assert 'id="pagos"' in respuesta.text  # la misma tarjeta, con el error en el campo
    assert pedido.abonos.count() == 1


def test_una_fecha_que_no_sirve_se_rechaza(sesion_duena, pedido):
    respuesta = sesion_duena.post(
        url_nuevo(pedido), {"valor": "100.000", "fecha": "31/02/2026"}, headers=HTMX
    )

    assert respuesta.status_code == 422
    assert "Escribe una fecha válida." in respuesta.text
    assert pedido.abonos.count() == 1


def test_un_abono_mayor_que_el_saldo_se_guarda_y_el_saldo_queda_en_0(sesion_duena, pedido):
    respuesta = sesion_duena.post(url_nuevo(pedido), {"valor": "2.000.000"}, headers=HTMX)

    assert respuesta.status_code == 200
    assert "Pagado</span>" in respuesta.text
    assert '<span>Pagado</span><span class="dinero">$ 0</span>' in respuesta.text
    assert '<span class="dinero">− $ 2.000.000</span>' in respuesta.text


def test_sin_javascript_registrar_vuelve_al_pedido(sesion_duena, pedido):
    respuesta = sesion_duena.post(url_nuevo(pedido), {"valor": "100000"})

    assert respuesta.status_code == 302
    assert respuesta.url == reverse("pedidos:detalle", args=[pedido.pk]) + "#pagos"
    assert pedido.abonos.filter(valor=100_000).exists()


def test_sin_javascript_los_errores_salen_en_una_pagina_con_el_formulario(sesion_duena, pedido):
    respuesta = sesion_duena.post(url_nuevo(pedido), {"valor": "cien"})

    assert respuesta.status_code == 422
    assert "<html" in respuesta.text
    assert "Escribe solo el valor en pesos" in respuesta.text
    assert f'action="{url_nuevo(pedido)}"' in respuesta.text


def test_desde_la_pagina_aparte_con_javascript_vuelve_al_pedido(sesion_duena, pedido):
    respuesta = sesion_duena.post(
        url_nuevo(pedido), {"valor": "100000"}, headers={"HX-Request": "true",
                                                         "HX-Target": "ventana"}
    )

    assert respuesta.headers["HX-Redirect"] == reverse(
        "pedidos:detalle", args=[pedido.pk]
    ) + "#pagos"
    assert pedido.abonos.filter(valor=100_000).exists()


def test_registrar_solo_acepta_post(sesion_duena, pedido):
    assert sesion_duena.get(url_nuevo(pedido)).status_code == 405


def test_el_formulario_no_deja_cambiar_el_pedido_ni_quien_registra(pedido):
    assert set(FormularioAbono().fields) == {"valor", "fecha"}


# --- Quitar un abono ----------------------------------------------------------------------


def test_quitar_primero_pregunta_y_no_borra(sesion_duena, pedido):
    abono = pedido.abonos.get()

    respuesta = sesion_duena.get(url_quitar(abono), headers=HTMX)

    assert respuesta.status_code == 200
    assert "¿Quitar el abono de <span class=\"dinero\">$ 1.260.000</span> del 5 de nov?" in (
        respuesta.text
    )
    assert "Sí, quitar el abono" in respuesta.text
    assert f'hx-post="{url_quitar(abono)}"' in respuesta.text
    assert Abono.objects.filter(pk=abono.pk).exists()


def test_cancelar_deja_la_tarjeta_como_estaba(sesion_duena, pedido):
    abono = pedido.abonos.get()

    respuesta = sesion_duena.get(url_quitar(abono) + "?cancelar=1", headers=HTMX)

    assert "¿Quitar el abono" not in respuesta.text
    assert "Abono del 5 de nov" in respuesta.text
    assert Abono.objects.filter(pk=abono.pk).exists()


def test_al_confirmar_se_quita_y_el_saldo_sube(sesion_duena, pedido):
    abono = pedido.abonos.get()

    respuesta = sesion_duena.post(url_quitar(abono), headers=HTMX)

    assert respuesta.status_code == 200
    assert not Abono.objects.filter(pk=abono.pk).exists()
    assert "$ 2.520.000" in respuesta.text
    assert "Abono del" not in respuesta.text
    assert "Sin abonos</span>" in respuesta.text


def test_sin_javascript_quitar_pregunta_en_una_pagina_y_vuelve_al_pedido(sesion_duena, pedido):
    abono = pedido.abonos.get()

    pregunta = sesion_duena.get(url_quitar(abono))
    respuesta = sesion_duena.post(url_quitar(abono))

    assert "<html" in pregunta.text and "Sí, quitar el abono" in pregunta.text
    assert f'action="{url_quitar(abono)}"' in pregunta.text
    assert respuesta.status_code == 302
    assert respuesta.url == reverse("pedidos:detalle", args=[pedido.pk]) + "#pagos"
    assert not Abono.objects.filter(pk=abono.pk).exists()


# --- Aislamiento: ids de otro taller o de otro pedido -------------------------------------


def test_no_se_registra_un_abono_en_un_pedido_de_otro_taller(sesion_duena):
    ajeno = fabricas.crear_pedido(fabricas.crear_taller())

    respuesta = sesion_duena.post(url_nuevo(ajeno), {"valor": "100000"}, headers=HTMX)

    assert respuesta.status_code == 404
    assert not ajeno.abonos.exists()


def test_no_se_quita_un_abono_de_otro_taller(sesion_duena, pedido):
    ajeno = fabricas.crear_abono(fabricas.crear_pedido(fabricas.crear_taller()))
    # Con el pedido del otro taller y con el pedido propio en la dirección.
    direcciones = [
        url_quitar(ajeno),
        reverse("pedidos:abono_quitar", args=[pedido.pk, ajeno.pk]),
    ]

    for url in direcciones:
        assert sesion_duena.get(url, headers=HTMX).status_code == 404
        assert sesion_duena.post(url, headers=HTMX).status_code == 404

    assert Abono.objects.filter(pk=ajeno.pk).exists()


def test_no_se_quita_un_abono_de_otro_pedido_del_mismo_taller(sesion_duena, taller, pedido):
    otro_pedido = fabricas.crear_pedido(taller)
    del_otro = fabricas.crear_abono(otro_pedido)

    url = reverse("pedidos:abono_quitar", args=[pedido.pk, del_otro.pk])

    assert sesion_duena.post(url, headers=HTMX).status_code == 404
    assert Abono.objects.filter(pk=del_otro.pk).exists()


def test_sin_sesion_no_se_registra_nada(client, pedido):
    respuesta = client.post(url_nuevo(pedido), {"valor": "100000"})

    assert respuesta.status_code == 302
    assert respuesta.url.startswith("/entrar/")
    assert pedido.abonos.count() == 1


def test_los_abonos_salen_en_orden_de_fecha(taller, duena):
    pedido = fabricas.crear_pedido(taller)
    hoy = timezone.localdate()
    fabricas.crear_abono(pedido, valor=200_000, fecha=hoy)
    fabricas.crear_abono(pedido, valor=100_000, fecha=hoy - timedelta(days=10))

    html = tarjeta(pedido, duena)

    assert html.index("$ 100.000") < html.index("$ 200.000")


# --- Aviso corto y animaciones (ajuste "pantalla fija y animaciones") ----------------------


def aviso(respuesta):
    """El aviso corto que lleva la respuesta de HTMX (config/avisos.py), o None."""
    return json.loads(respuesta.headers.get("HX-Trigger") or "{}").get("aviso")


def test_registrar_un_abono_avisa_abono_registrado(sesion_duena, pedido):
    respuesta = sesion_duena.post(url_nuevo(pedido), {"valor": "100000"}, headers=HTMX)

    assert aviso(respuesta) == "Abono registrado."


def test_un_abono_con_errores_no_avisa(sesion_duena, pedido):
    respuesta = sesion_duena.post(url_nuevo(pedido), {"valor": "cien"}, headers=HTMX)

    assert respuesta.status_code == 422
    assert aviso(respuesta) is None


def test_sin_javascript_el_aviso_sale_en_el_pedido(sesion_duena, pedido):
    respuesta = sesion_duena.post(url_nuevo(pedido), {"valor": "100000"}, follow=True)

    assert "<p data-aviso>Abono registrado.</p>" in respuesta.text


def test_desde_la_pagina_aparte_el_aviso_sale_en_el_pedido(sesion_duena, pedido):
    respuesta = sesion_duena.post(
        url_nuevo(pedido), {"valor": "100000"}, headers={"HX-Request": "true",
                                                         "HX-Target": "ventana"}
    )

    assert "HX-Trigger" not in respuesta.headers
    siguiente = sesion_duena.get(reverse("pedidos:detalle", args=[pedido.pk]))
    assert "<p data-aviso>Abono registrado.</p>" in siguiente.text


def test_quitar_un_abono_avisa_abono_quitado(sesion_duena, pedido):
    abono = pedido.abonos.get()

    respuesta = sesion_duena.post(url_quitar(abono), headers=HTMX)

    assert aviso(respuesta) == "Abono quitado."


def test_sin_javascript_quitar_avisa_en_el_pedido(sesion_duena, pedido):
    abono = pedido.abonos.get()

    respuesta = sesion_duena.post(url_quitar(abono), follow=True)

    assert "<p data-aviso>Abono quitado.</p>" in respuesta.text


def test_preguntar_y_cancelar_no_avisan(sesion_duena, pedido):
    abono = pedido.abonos.get()

    assert aviso(sesion_duena.get(url_quitar(abono), headers=HTMX)) is None
    assert aviso(sesion_duena.get(url_quitar(abono) + "?cancelar=1", headers=HTMX)) is None


def test_cada_abono_lleva_su_id_y_la_pregunta_conserva_el_mismo(sesion_duena, pedido):
    """Así la pregunta "¿Quitar?" toma el lugar de la fila sin que se cierre y se vuelva a
    abrir, y al quitarlo solo esa fila se cierra (static/js/app.js, sección 11)."""
    abono = pedido.abonos.get()

    pagina = sesion_duena.get(reverse("pedidos:detalle", args=[pedido.pk])).text
    pregunta = sesion_duena.get(url_quitar(abono), headers=HTMX).text

    assert f'<div class="cuentas__fila" id="abono-{abono.pk}">' in pagina
    assert f'<div class="pagos__confirmar" id="abono-{abono.pk}">' in pregunta
    assert pregunta.count(f'id="abono-{abono.pk}"') == 1
