"""T17. Gastos: abrir el formulario, registrar y quitar un gasto desde el Resumen.

Con HTMX, cada acción devuelve lo de adentro de la lista de gastos (id="gastos-lista") y,
aparte (hx-swap-oob), la cabeza de la tarjeta y, si el gasto cambió algo, las cifras y la
gráfica. Al registrar o quitar, un aviso corto lo confirma (ajuste "pantalla fija y
animaciones").
"""

import json
import re
from datetime import date

import pytest
from django.urls import reverse
from django.utils import timezone

from finanzas.models import Gasto
from tests import fabricas

pytestmark = pytest.mark.django_db

HTMX = {"HX-Request": "true", "HX-Target": "gastos-lista"}
NUEVO = "finanzas:gasto_nuevo"
CABEZA_OOB = 'id="gastos-cabeza" hx-swap-oob="true"'
A_LA_LISTA = 'hx-target="#gastos-lista" hx-swap="innerHTML"'


def url_nuevo(mes=None, cancelar=False):
    url = reverse(NUEVO)
    partes = ([f"mes={mes}"] if mes else []) + (["cancelar=1"] if cancelar else [])
    return url + ("?" + "&".join(partes) if partes else "")


def url_quitar(gasto):
    return reverse("finanzas:gasto_quitar", args=[gasto.pk])


def entrada(html, nombre):
    """La etiqueta <input> (o <select>) del campo `nombre` dentro del html."""
    return re.search(rf'<(?:input|select)[^>]*name="{nombre}"[^>]*>', html).group(0)


def aviso(respuesta):
    """El aviso corto que lleva la respuesta de HTMX (cabecera HX-Trigger), o None."""
    disparos = respuesta.headers.get("HX-Trigger")
    return json.loads(disparos).get("aviso") if disparos else None


def avisos_de_la_pagina(cliente, url):
    """Los avisos que esperan en la página siguiente (base.html, #avisos-pendientes)."""
    return re.findall(r"<p data-aviso>(.*?)</p>", cliente.get(url).text)


def datos(**cambios):
    """Un gasto bien escrito, de noviembre de 2026, que se puede cambiar campo por campo."""
    return {"concepto": "Recibo de luz del taller", "categoria": "servicios",
            "valor": "140.000", "fecha": "2026-11-09", "mes": "2026-11", **cambios}


@pytest.fixture
def gasto(taller):
    return fabricas.crear_gasto(
        taller, valor=85_000, concepto="Hilos y botones", categoria="insumos",
        fecha=date(2026, 11, 6),
    )


# --- Abrir y cerrar el formulario ---------------------------------------------------------


def test_registrar_gasto_abre_el_formulario_en_la_tarjeta(sesion_duena, gasto):
    respuesta = sesion_duena.get(url_nuevo("2026-11"), headers=HTMX)

    assert respuesta.status_code == 200
    html = respuesta.text
    assert "<html" not in html and CABEZA_OOB in html
    assert "Gastos de noviembre" in html and "Hilos y botones" in html
    assert f'id="gastos-formulario" method="post" action="{reverse(NUEVO)}"' in html
    assert f'hx-post="{reverse(NUEVO)}" {A_LA_LISTA}' in html
    # Abierto, el botón de la cabeza lleva al primer campo y conserva su id.
    assert '<a class="boton tarjeta__aparte" id="gastos-registrar" href="#registrar-gasto">' in html
    assert '<input type="hidden" name="mes" value="2026-11">' in html
    assert "¿En qué gastaste?" in html and 'for="registrar-gasto"' in html
    assert "Tipo de gasto" in html and "Valor (pesos)" in html and ">Fecha</label>" in html
    for valor, nombre in (("telas", "Telas"), ("insumos", "Insumos"),
                          ("servicios", "Servicios"), ("otros", "Otros")):
        assert f'value="{valor}"' in html and f">{nombre}</option>" in html
    assert '<option value="telas" selected>' in html  # como en la demo
    assert f'value="{timezone.localdate().isoformat()}"' in entrada(html, "fecha")
    assert "autofocus" in entrada(html, "concepto")
    # Las cifras y la gráfica no cambian: no vienen.
    assert "resumen-cifras" not in html and "resumen-grafica" not in html


def test_cancelar_cierra_el_formulario(sesion_duena, gasto):
    respuesta = sesion_duena.get(url_nuevo("2026-11", cancelar=True), headers=HTMX)

    assert respuesta.status_code == 200
    assert CABEZA_OOB in respuesta.text and "<form" not in respuesta.text
    assert "Hilos y botones" in respuesta.text
    assert aviso(respuesta) is None  # cerrar el formulario no guarda nada


def test_sin_javascript_registrar_gasto_abre_una_pagina_con_el_formulario(sesion_duena):
    respuesta = sesion_duena.get(url_nuevo("2026-11"))

    assert respuesta.status_code == 200
    html = respuesta.text
    assert "<html" in html and "ventana--pagina" in html
    assert f'action="{reverse(NUEVO)}"' in html
    assert '<input type="hidden" name="mes" value="2026-11">' in html
    assert "¿En qué gastaste?" in html


def test_sin_javascript_cancelar_vuelve_al_resumen(sesion_duena):
    respuesta = sesion_duena.get(url_nuevo("2026-10", cancelar=True))

    assert respuesta.status_code == 302
    assert respuesta.url == reverse("finanzas:resumen") + "?mes=2026-10#gastos"


# --- Registrar ----------------------------------------------------------------------------


def test_registrar_un_gasto_lo_guarda_y_devuelve_la_tarjeta_las_cifras_y_la_grafica(
    sesion_duena, taller, gasto
):
    respuesta = sesion_duena.post(reverse(NUEVO), datos(), headers=HTMX)

    assert respuesta.status_code == 200
    nuevo = Gasto.objects.get(concepto="Recibo de luz del taller")
    assert nuevo.taller == taller
    assert nuevo.valor == 140_000
    assert nuevo.categoria == "servicios"
    assert nuevo.fecha == date(2026, 11, 9)
    html = respuesta.text
    assert "<html" not in html
    assert "9 de nov · servicios" in html and "$ 140.000" in html
    # El nuevo (9 de nov) va antes que el viejo (6 de nov).
    assert html.index("Recibo de luz") < html.index("Hilos y botones")
    cifras = re.search(r'<section class="cifras" id="resumen-cifras"[^>]*>', html).group(0)
    assert 'hx-swap-oob="true"' in cifras
    assert "$ 225.000" in html  # gastado: 85.000 + 140.000
    assert "-$ 225.000" in html  # te quedó: no hay abonos
    grafica = re.search(r'<section[^>]*id="resumen-grafica"[^>]*>', html).group(0)
    assert 'hx-swap-oob="true"' in grafica
    assert "gastado 0,23 millones" in html
    # El formulario queda abierto, vacío y con el cursor para el siguiente gasto.
    assert "autofocus" in entrada(html, "concepto")
    assert "value=" not in entrada(html, "concepto")
    # El gasto nuevo llega con su id (aparece suave) y el viejo conserva el suyo.
    assert f'<div class="fila fila--compacta" id="gasto-{nuevo.pk}">' in html
    assert f'<div class="fila fila--compacta" id="gasto-{gasto.pk}">' in html
    assert 'id="gastos-formulario"' in html and CABEZA_OOB in html
    assert aviso(respuesta) == "Gasto registrado."  # el texto de la demo


@pytest.mark.parametrize(
    "escrito, pesos", [("140000", 140_000), ("140.000", 140_000), ("$ 1.260.000", 1_260_000)]
)
def test_el_valor_se_escribe_con_o_sin_puntos(sesion_duena, escrito, pesos):
    respuesta = sesion_duena.post(reverse(NUEVO), datos(valor=escrito), headers=HTMX)

    assert respuesta.status_code == 200
    assert Gasto.objects.get().valor == pesos


def test_sin_fecha_el_gasto_queda_con_la_de_hoy(sesion_duena):
    hoy = timezone.localdate()

    respuesta = sesion_duena.post(
        reverse(NUEVO), datos(fecha="", mes=f"{hoy:%Y-%m}"), headers=HTMX
    )

    assert respuesta.status_code == 200
    assert Gasto.objects.get().fecha == hoy


def test_un_gasto_de_otro_mes_abre_ese_mes_para_verlo(sesion_duena):
    respuesta = sesion_duena.post(reverse(NUEVO), datos(fecha="2026-10-28"), headers=HTMX)

    assert respuesta.status_code == 200
    assert respuesta["HX-Redirect"] == reverse("finanzas:resumen") + "?mes=2026-10#gastos"
    assert Gasto.objects.get().fecha == date(2026, 10, 28)
    # La página se va al otro mes: el aviso la espera allá.
    assert aviso(respuesta) is None
    assert avisos_de_la_pagina(sesion_duena, respuesta["HX-Redirect"]) == ["Gasto registrado."]


def test_sin_javascript_registrar_vuelve_al_mes_del_gasto(sesion_duena):
    respuesta = sesion_duena.post(reverse(NUEVO), datos())

    assert respuesta.status_code == 302
    assert respuesta.url == reverse("finanzas:resumen") + "?mes=2026-11#gastos"
    assert Gasto.objects.count() == 1
    assert avisos_de_la_pagina(sesion_duena, respuesta.url) == ["Gasto registrado."]


def test_el_taller_no_llega_del_formulario(sesion_duena, taller):
    otro = fabricas.crear_taller()

    sesion_duena.post(reverse(NUEVO), datos(taller=otro.pk), headers=HTMX)

    assert Gasto.objects.get().taller == taller


# --- Errores ------------------------------------------------------------------------------


@pytest.mark.parametrize(
    "cambio, mensaje",
    [
        ({"concepto": ""}, "Escribe en qué gastaste."),
        ({"concepto": "   "}, "Escribe en qué gastaste."),
        ({"concepto": "x" * 81}, "Escribe máximo 80 letras."),
        ({"valor": ""}, "Escribe el valor del gasto en pesos."),
        ({"valor": "abc"}, "Escribe solo el valor en pesos, por ejemplo 380.000."),
        ({"valor": "140,50"}, "Escribe solo el valor en pesos, por ejemplo 380.000."),
        ({"valor": "-5000"}, "Escribe solo el valor en pesos, por ejemplo 380.000."),
        ({"valor": "0"}, "El gasto debe ser mayor que 0."),
        ({"valor": "99.000.000.000"}, "Revisa el valor: es demasiado grande."),
        ({"categoria": "comida"}, "Elige el tipo de gasto."),
        ({"fecha": "31/02/2026"}, "Escribe una fecha válida."),
        # Un año mal escrito: la fecha existe, pero el gasto no se vería en ningún mes.
        ({"fecha": "0202-11-09"}, "Revisa la fecha del gasto."),
        ({"fecha": "1999-12-31"}, "Revisa la fecha del gasto."),
    ],
)
def test_lo_mal_escrito_se_rechaza_con_un_mensaje_claro(sesion_duena, cambio, mensaje):
    respuesta = sesion_duena.post(reverse(NUEVO), datos(**cambio), headers=HTMX)

    assert respuesta.status_code == 422
    assert mensaje in respuesta.text
    assert 'id="gastos-formulario"' in respuesta.text and CABEZA_OOB in respuesta.text
    assert "resumen-cifras" not in respuesta.text
    assert aviso(respuesta) is None  # no se guardó nada: no hay aviso
    assert not Gasto.objects.exists()


def test_la_fecha_va_desde_el_2000_hasta_el_fin_del_otro_anio(sesion_duena):
    hoy = timezone.localdate()
    lejos = sesion_duena.post(reverse(NUEVO), datos(fecha=f"{hoy.year + 2}-01-01"), headers=HTMX)

    assert lejos.status_code == 422
    assert "Revisa la fecha del gasto." in lejos.text
    assert not Gasto.objects.exists()

    for fecha in (date(2000, 1, 1), date(hoy.year + 1, 12, 31)):
        sesion_duena.post(reverse(NUEVO), datos(fecha=fecha.isoformat()), headers=HTMX)
    assert sorted(Gasto.objects.values_list("fecha", flat=True)) == [
        date(2000, 1, 1), date(hoy.year + 1, 12, 31)]


def test_con_un_error_el_cursor_vuelve_al_campo_que_hay_que_corregir(sesion_duena):
    respuesta = sesion_duena.post(reverse(NUEVO), datos(valor="cien"), headers=HTMX)

    assert "autofocus" in entrada(respuesta.text, "valor")
    assert "autofocus" not in entrada(respuesta.text, "concepto")
    # Lo bien escrito no se pierde.
    assert 'value="Recibo de luz del taller"' in entrada(respuesta.text, "concepto")


def test_sin_javascript_un_error_muestra_la_pagina_con_el_mensaje(sesion_duena):
    respuesta = sesion_duena.post(reverse(NUEVO), datos(concepto=""))

    assert respuesta.status_code == 422
    assert "<html" in respuesta.text and "Escribe en qué gastaste." in respuesta.text
    assert not Gasto.objects.exists()


# --- Quitar -------------------------------------------------------------------------------


def test_quitar_primero_pregunta_en_la_tarjeta(sesion_duena, gasto):
    respuesta = sesion_duena.get(url_quitar(gasto), headers=HTMX)

    assert respuesta.status_code == 200
    html = respuesta.text
    assert "¿Quitar el gasto «Hilos y botones» de <span class=\"dinero\">$ 85.000</span> del 6 de nov?" in html
    assert f'hx-post="{url_quitar(gasto)}" {A_LA_LISTA}' in html
    assert "Sí, quitar el gasto" in html and ">Cancelar</a>" in html
    assert Gasto.objects.filter(pk=gasto.pk).exists()
    assert aviso(respuesta) is None  # preguntar no guarda nada


def test_la_pregunta_va_en_el_lugar_del_gasto_y_conserva_su_id(sesion_duena, gasto):
    """Así la fila no se cierra y se vuelve a abrir al cambiar por su pregunta (app.js)."""
    fila = f'<div class="fila fila--compacta" id="gasto-{gasto.pk}">'
    pregunta = f'<div class="tarjeta__cuerpo" id="gasto-{gasto.pk}">'
    otro = fabricas.crear_gasto(gasto.taller, concepto="Transporte", fecha=date(2026, 11, 8))

    respuesta = sesion_duena.get(url_quitar(gasto), headers=HTMX)

    assert pregunta in respuesta.text and fila not in respuesta.text
    assert f'<div class="fila fila--compacta" id="gasto-{otro.pk}">' in respuesta.text
    cancelar = sesion_duena.get(url_quitar(gasto) + "?cancelar=1", headers=HTMX)
    assert fila in cancelar.text and pregunta not in cancelar.text
    # "Cancelar" devuelve el cursor a la X del gasto, que tiene su propio id.
    assert f'data-foco-despues="gasto-{gasto.pk}-quitar"' in respuesta.text
    assert f'id="gasto-{gasto.pk}-quitar"' in cancelar.text


def test_cancelar_deja_el_gasto_como_estaba(sesion_duena, gasto):
    respuesta = sesion_duena.get(url_quitar(gasto) + "?cancelar=1", headers=HTMX)

    assert respuesta.status_code == 200
    assert "¿Quitar" not in respuesta.text and "Hilos y botones" in respuesta.text
    assert Gasto.objects.filter(pk=gasto.pk).exists()
    assert aviso(respuesta) is None


def test_si_quitar_lo_borra_y_devuelve_la_tarjeta_las_cifras_y_la_grafica(sesion_duena, gasto):
    respuesta = sesion_duena.post(url_quitar(gasto), headers=HTMX)

    assert respuesta.status_code == 200
    assert not Gasto.objects.filter(pk=gasto.pk).exists()
    html = respuesta.text
    assert "Hilos y botones" not in html
    assert f'id="gasto-{gasto.pk}"' not in html  # su fila se cierra suave
    assert '<p class="tarjeta__nota" id="gastos-vacio">No hay gastos anotados en este mes.</p>' in html
    assert CABEZA_OOB in html
    assert 'id="resumen-cifras" aria-label="Resumen" hx-swap-oob="true"' in html
    assert 'id="resumen-grafica"' in html
    assert aviso(respuesta) == "Gasto quitado."


def test_sin_javascript_quitar_pregunta_en_una_pagina_y_despues_vuelve_al_mes(
    sesion_duena, gasto
):
    pregunta = sesion_duena.get(url_quitar(gasto))
    assert pregunta.status_code == 200
    assert "<html" in pregunta.text and "Sí, quitar el gasto" in pregunta.text
    assert f'action="{url_quitar(gasto)}"' in pregunta.text

    respuesta = sesion_duena.post(url_quitar(gasto))

    assert respuesta.status_code == 302
    assert respuesta.url == reverse("finanzas:resumen") + "?mes=2026-11#gastos"
    assert not Gasto.objects.exists()
    assert avisos_de_la_pagina(sesion_duena, respuesta.url) == ["Gasto quitado."]


# --- Otro taller --------------------------------------------------------------------------


def test_el_gasto_de_otro_taller_responde_404_y_no_se_toca(sesion_duena):
    ajeno = fabricas.crear_gasto(fabricas.crear_taller(), valor=333_000)

    for respuesta in (
        sesion_duena.get(url_quitar(ajeno), headers=HTMX),
        sesion_duena.get(url_quitar(ajeno)),
        sesion_duena.post(url_quitar(ajeno), headers=HTMX),
        sesion_duena.post(url_quitar(ajeno)),
    ):
        assert respuesta.status_code == 404
    assert Gasto.objects.filter(pk=ajeno.pk, valor=333_000).exists()


def test_la_tarjeta_que_vuelve_no_trae_gastos_de_otro_taller(sesion_duena, gasto):
    fabricas.crear_gasto(fabricas.crear_taller(), concepto="Gasto ajeno", fecha=date(2026, 11, 6))

    respuesta = sesion_duena.post(reverse(NUEVO), datos(), headers=HTMX)

    assert "Gasto ajeno" not in respuesta.text
    assert "$ 225.000" in respuesta.text  # solo los dos gastos de este taller


def test_sin_sesion_no_se_registra_ni_se_quita(client, gasto):
    nuevo = client.post(reverse(NUEVO), datos())
    quitar = client.post(url_quitar(gasto))

    assert nuevo.status_code == quitar.status_code == 302
    assert Gasto.objects.count() == 1
