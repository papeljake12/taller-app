"""Telas con muchas telas, en la pantalla fija (docs/08-diseno.md, "Pantalla fija").

Con los ejemplos (4 telas) Telas cabe completa: eso lo mira tests/test_pantalla_fija.py. Aquí
se prueba lo que pasa cuando el taller tiene muchas telas: la página y la hoja no se
desplazan, solo la tabla, por dentro de su tarjeta, con el encabezado fijo; las cifras de
arriba se quedan quietas y la tarjeta llega hasta abajo.

Abre un Chrome de verdad (sin ventana, con Playwright), como tests/test_pantalla_fija.py; si
no está, se salta.
"""

from decimal import Decimal

import pytest

from tests import fabricas
from tests.test_pantalla_fija import TAMANOS, _chrome, _sesion

TELAS = 30

MEDIR = """() => {
  const hoja = document.querySelector('.hoja__contenido');
  const lista = document.querySelector('#telas .desplazable');
  const medir = () => ({
    cifras: document.getElementById('telas-cifras').getBoundingClientRect().top,
    lista: lista.getBoundingClientRect().top,
    encabezado: lista.querySelector('th').getBoundingClientRect().top,
  });
  const antes = medir();
  lista.scrollTop = lista.scrollHeight;
  return {
    pagina: (document.scrollingElement || document.documentElement).scrollHeight,
    ventana: window.innerHeight,
    contenido: hoja.scrollHeight,
    cabe: hoja.clientHeight,
    hojaAbajo: hoja.getBoundingClientRect().bottom,
    tarjetaAbajo: document.getElementById('telas').getBoundingClientRect().bottom,
    listaAlto: lista.scrollHeight,
    listaCabe: lista.clientHeight,
    desplazada: lista.scrollTop,
    antes: antes,
    despues: medir(),
  };
}"""


@pytest.fixture
def sesion_con_muchas_telas():
    """Un taller con 30 telas y la sesión de su dueña (antes de abrir Chrome: Django no deja
    usar la base mientras Playwright corre)."""
    taller = fabricas.crear_taller()
    duena = fabricas.crear_usuaria(taller, rol="duena")
    for numero in range(1, TELAS + 1):
        fabricas.crear_tela(taller, nombre=f"Tela de prueba {numero:02d}",
                            metros=Decimal(numero), minimo=Decimal(5))
    return _sesion(duena)


def _medir(navegador, url, sesion, ancho, alto):
    contexto = navegador.new_context(viewport={"width": ancho, "height": alto})
    contexto.add_cookies([{"name": "sessionid", "value": sesion, "url": url}])
    pagina = contexto.new_page()
    pagina.goto(url, wait_until="load")
    pagina.evaluate("document.fonts.ready")
    medida = pagina.evaluate(MEDIR)
    medida["filas"] = pagina.locator("#telas tbody tr").count()
    contexto.close()
    return medida


def test_con_muchas_telas_solo_la_tabla_se_desplaza(live_server, sesion_con_muchas_telas):
    """Una sola prueba para los dos tamaños: abrir Chrome una vez por tamaño tarda mucho."""
    url = live_server.url + "/telas/"
    manejador, navegador = _chrome()
    try:
        medidas = {(ancho, alto): _medir(navegador, url, sesion_con_muchas_telas, ancho, alto)
                   for ancho, alto in TAMANOS}
    finally:
        navegador.close()
        manejador.stop()

    for tamano, medida in medidas.items():
        assert medida["filas"] == TELAS, tamano
        # Ni la página ni la hoja se desplazan: cabe completa.
        assert medida["pagina"] <= medida["ventana"], (tamano, medida)
        assert medida["contenido"] <= medida["cabe"] + 1, (tamano, medida)
        # La tarjeta llega hasta abajo (la hoja lleva 4 px de aire por dentro para el foco).
        assert abs(medida["tarjetaAbajo"] - (medida["hojaAbajo"] - 4)) <= 1, (tamano, medida)
        # La tabla no cabe y se desplaza por dentro de su tarjeta...
        assert medida["listaAlto"] > medida["listaCabe"], (tamano, medida)
        assert medida["desplazada"] > 0, (tamano, medida)
        # ...con el encabezado fijo arriba, y las cifras no se mueven.
        despues = medida["despues"]
        assert abs(despues["encabezado"] - despues["lista"]) <= 1, (tamano, medida)
        assert despues["cifras"] == medida["antes"]["cifras"], (tamano, medida)
