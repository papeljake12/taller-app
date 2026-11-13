"""Pantalla fija en computador (docs/08-diseno.md, "Pantalla fija").

Abre cada pantalla en un Chrome de verdad (sin ventana, con Playwright), con los datos de
ejemplo, en 1366 x 768 y en 1920 x 1080, y comprueba:

1. que la página no se desplaza nunca: mide lo mismo que la ventana;
2. qué pantallas caben completas: el contenido de la hoja no se desplaza por dentro. Lo que
   sí puede desplazarse por dentro son las listas largas (.desplazable), en su tarjeta. Las
   que no caben tienen que ser exactamente las de NO_CABEN, cada una con su razón.

Y en celular (390 px), que la página se sigue deslizando normal.

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

# Pantallas que no caben completas en algún tamaño, con su razón. Si una empieza a caber, o
# una nueva deja de caber, la prueba falla y dice cuál: se corrige la pantalla o esta lista.
NO_CABEN = {
    "hoy": "Todavía sin ajustar a la pantalla fija.",
    "hoy-menu-contraido": "Todavía sin ajustar a la pantalla fija.",
    "pedido": "Todavía sin ajustar a la pantalla fija.",
    "pedido-costurera": "Todavía sin ajustar a la pantalla fija.",
}

MEDIR = """() => {
  const pagina = document.scrollingElement || document.documentElement;
  const contenido = document.querySelector('.hoja__contenido');
  return {
    pagina: pagina.scrollHeight,
    ventana: window.innerHeight,
    contenido: contenido ? contenido.scrollHeight : 0,
    cabe: contenido ? contenido.clientHeight : 0,
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


def test_la_pagina_no_se_desplaza_y_las_pantallas_caben(live_server, ejemplos_con_sesiones):
    sesiones, datos = ejemplos_con_sesiones["sesiones"], ejemplos_con_sesiones["datos"]
    se_desplazan, no_caben = [], {}
    manejador, navegador = _chrome()
    try:
        for nombre, url, rol, menu in PANTALLAS:
            direccion = live_server.url + url.format(**datos)
            for ancho, alto in TAMANOS:
                medida = _medir(navegador, direccion, sesiones[rol], menu,
                                viewport={"width": ancho, "height": alto})
                tamano = f"{ancho} x {alto}"
                if medida["pagina"] > medida["ventana"]:
                    se_desplazan.append(f"{nombre} en {tamano} ({medida['pagina']} px)")
                if medida["contenido"] > medida["cabe"] + 1:
                    no_caben.setdefault(nombre, []).append(
                        f"{tamano}: {medida['contenido']} px en {medida['cabe']} px")
    finally:
        navegador.close()
        manejador.stop()
    assert not se_desplazan, "La página se desplaza en: " + "; ".join(se_desplazan)
    sobran = {n: m for n, m in no_caben.items() if n not in NO_CABEN}
    ya_caben = sorted(set(NO_CABEN) - set(no_caben))
    assert not sobran, f"No caben completas (y no están en NO_CABEN): {sobran}"
    assert not ya_caben, f"Ya caben completas: quítalas de NO_CABEN: {ya_caben}"


def test_en_celular_la_pagina_se_sigue_deslizando(live_server, ejemplos_con_sesiones):
    sesion = ejemplos_con_sesiones["sesiones"]["duena"]
    manejador, navegador = _chrome()
    try:
        medida = _medir(navegador, live_server.url + "/", sesion,
                        viewport={"width": 390, "height": 844}, is_mobile=True, has_touch=True)
    finally:
        navegador.close()
        manejador.stop()
    assert medida["pagina"] > medida["ventana"], "En celular, Hoy es más alta que la pantalla"
