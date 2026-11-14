"""Desplazamiento (docs/08-diseno.md, "Desplazamiento"; reemplaza la "pantalla fija").

Abre cada pantalla en un Chrome de verdad (sin ventana, con Playwright), con los datos de
ejemplo, y comprueba:

1. en computador (1366 x 768 y 1920 x 1080), que la página misma no se desplaza nunca: mide
   lo mismo que la ventana. Lo que se desplaza es el contenido de la hoja, debajo de su
   encabezado, como en Shopify;
2. en ningún tamaño (tampoco en celular, 390 px) algo se sale de lo ancho de la pantalla;
3. en celular, la página se desliza normal.

Ya no se pide que cada pantalla quepa completa en 1366 x 768.

Es una sola prueba que recorre todas las pantallas: abrir Chrome y cargar los ejemplos una
vez por pantalla tomaría más de un minuto. Necesita Google Chrome instalado (como
herramientas/capturas.py); si no está, se salta.
"""

import pytest
from django.test import Client
from django.utils import timezone

from cuentas.models import Usuario
from pedidos import ejemplos
from pedidos.calculos import sumar_meses
from pedidos.models import Pedido

TAMANOS = [(1366, 768), (1920, 1080)]
CELULAR = {"viewport": {"width": 390, "height": 844}, "is_mobile": True, "has_touch": True}

# (nombre, dirección, rol, cookie del menú). {pedido} y {mes_anterior} se llenan con los
# datos de ejemplo; el pedido es el del diseño (Restaurante), que la costurera también tiene.
PANTALLAS = [
    ("hoy", "/", "duena", None),
    ("hoy-menu-contraido", "/", "duena", "contraido"),
    ("hoy-costurera", "/", "costurera", None),
    ("pedidos", "/pedidos/", "duena", None),
    ("pedidos-atrasados", "/pedidos/?filtro=atrasados", "duena", None),
    ("pedido", "/pedidos/{pedido}/", "duena", None),
    ("pedido-costurera", "/pedidos/{pedido}/", "costurera", None),
    ("nuevo-pedido", "/pedidos/nuevo/", "duena", None),
    ("calendario", "/calendario/", "duena", None),
    ("clientes", "/clientes/", "duena", None),
    ("cotizador", "/cotizador/", "duena", None),
    ("telas", "/telas/", "duena", None),
    ("resumen", "/resumen/", "duena", None),
    ("resumen-mes-anterior", "/resumen/?mes={mes_anterior}", "duena", None),
    ("mi-taller", "/mi-taller/", "duena", None),
    ("buscar", "/buscar/?q=esquina", "duena", None),
]

MEDIR = """() => {
  const pagina = document.scrollingElement || document.documentElement;
  return {
    pagina: pagina.scrollHeight,
    ventana: window.innerHeight,
    ancho: pagina.scrollWidth,
    ventana_ancho: window.innerWidth,
  };
}"""


def _chrome():
    """Abre Chrome con Playwright, o salta la prueba si no se puede."""
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        pytest.skip("Playwright no está instalado (uv sync con el grupo dev).")
    manejador = sync_playwright().start()
    try:
        return manejador, manejador.chromium.launch(channel="chrome")
    except Exception as error:  # noqa: BLE001 (sin Chrome no hay prueba)
        manejador.stop()
        pytest.skip(f"No se pudo abrir Chrome: {error}")


def _sesion(persona):
    cliente = Client()
    cliente.force_login(persona)
    return cliente.cookies["sessionid"].value


@pytest.fixture
def ejemplos_con_sesiones():
    """Carga los ejemplos y abre la sesión de la dueña y la de una costurera con pedidos.

    Se piden antes de abrir Chrome: Django no deja usar la base mientras Playwright corre.
    """
    taller = ejemplos.cargar(con_fotos=False)
    duena = Usuario.objects.get(taller=taller, rol=Usuario.Rol.DUENA)
    pedido = Pedido.objects.get(taller=taller, detalle__startswith="18 camisas")
    costurera = pedido.encargada
    anterior = sumar_meses(timezone.localdate(), -1)
    return {
        "sesiones": {"duena": _sesion(duena), "costurera": _sesion(costurera)},
        "datos": {"pedido": pedido.pk,
                  "mes_anterior": f"{anterior.year}-{anterior.month:02d}"},
    }


def _medir(navegador, url, sesion, menu=None, **formato):
    contexto = navegador.new_context(**formato)
    cookies = [{"name": "sessionid", "value": sesion, "url": url}]
    if menu:
        cookies.append({"name": "menu", "value": menu, "url": url})
    contexto.add_cookies(cookies)
    pagina = contexto.new_page()
    pagina.goto(url, wait_until="load")
    pagina.evaluate("document.fonts.ready")
    medida = pagina.evaluate(MEDIR)
    contexto.close()
    return medida


def test_la_pagina_no_se_mueve_y_nada_se_sale_de_lo_ancho(live_server, ejemplos_con_sesiones):
    sesiones, datos = ejemplos_con_sesiones["sesiones"], ejemplos_con_sesiones["datos"]
    se_desplazan, se_salen = [], []
    manejador, navegador = _chrome()
    try:
        for nombre, url, rol, menu in PANTALLAS:
            direccion = live_server.url + url.format(**datos)
            formatos = [(f"{a} x {b}", {"viewport": {"width": a, "height": b}}) for a, b in TAMANOS]
            if not menu:
                formatos.append(("celular", CELULAR))
            for tamano, formato in formatos:
                medida = _medir(navegador, direccion, sesiones[rol], menu, **formato)
                if tamano != "celular" and medida["pagina"] > medida["ventana"]:
                    se_desplazan.append(f"{nombre} en {tamano} ({medida['pagina']} px)")
                if medida["ancho"] > medida["ventana_ancho"]:
                    se_salen.append(f"{nombre} en {tamano} ({medida['ancho']} px)")
    finally:
        navegador.close()
        manejador.stop()
    assert not se_desplazan, "La página se desplaza en: " + "; ".join(se_desplazan)
    assert not se_salen, "Algo se sale de lo ancho en: " + "; ".join(se_salen)


def test_en_celular_la_pagina_se_sigue_deslizando(live_server, ejemplos_con_sesiones):
    sesion = ejemplos_con_sesiones["sesiones"]["duena"]
    manejador, navegador = _chrome()
    try:
        medida = _medir(navegador, live_server.url + "/", sesion, **CELULAR)
    finally:
        navegador.close()
        manejador.stop()
    assert medida["pagina"] > medida["ventana"], "En celular, Hoy es más alta que la pantalla"
