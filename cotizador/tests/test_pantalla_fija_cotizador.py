"""Cotizador en la pantalla fija, usándolo en un Chrome de verdad (ajuste "pantalla fija y
animaciones", docs/08-diseno.md).

tests/test_pantalla_fija.py mide el cotizador recién abierto. Aquí se mide como queda al
usarlo, con los datos de ejemplo: con una de "Mis prendas guardadas" elegida (aparece "Quitar
de mi lista") y el resultado lleno. En 1366 x 768 y en 1920 x 1080:

1. cabe completo y la página no se desplaza;
2. las dos columnas terminan juntas, justo al final de la hoja (sin hueco abajo);
3. el resultado, que cambia mientras se escribe, no se anima (no parpadea).

Necesita Google Chrome (como tests/test_pantalla_fija.py); si no está, se salta.
"""

import pytest

from cotizador.models import PrendaGuardada
from cuentas.models import Usuario
from pedidos import ejemplos
from tests.test_pantalla_fija import TAMANOS, _chrome, _sesion

MEDIR = """() => {
  const pagina = document.scrollingElement || document.documentElement;
  const contenido = document.querySelector('.hoja__contenido');
  const abajo = e => Math.round(e.getBoundingClientRect().bottom);
  return {
    pagina: pagina.scrollHeight,
    ventana: window.innerHeight,
    contenido: contenido.scrollHeight,
    cabe: contenido.clientHeight,
    hoja: abajo(contenido) - parseFloat(getComputedStyle(contenido).paddingBottom),
    izquierda: abajo(document.querySelector('#cotizador .columna-ancha')),
    derecha: abajo(document.getElementById('resultado')),
  };
}"""

# Anota cada animación de static/js/app.js que empieza dentro del resultado.
ESPIAR_ANIMACIONES = """() => {
  window.animadasEnElResultado = [];
  const animar = Element.prototype.animate;
  Element.prototype.animate = function (...argumentos) {
    if (this.closest('#resultado')) window.animadasEnElResultado.push(this.tagName);
    return animar.apply(this, argumentos);
  };
}"""


@pytest.fixture
def duena_con_prendas():
    """Los datos de ejemplo (traen la camisa polo del diseño) y la sesión de la dueña.

    Se piden antes de abrir Chrome: Django no deja usar la base mientras Playwright corre.
    """
    taller = ejemplos.cargar(con_fotos=False)
    duena = Usuario.objects.get(taller=taller, rol=Usuario.Rol.DUENA)
    camisa = PrendaGuardada.objects.get(taller=taller, nombre="Camisa polo bordada")
    return _sesion(duena), str(camisa.pk)


def test_con_una_prenda_elegida_y_el_resultado_lleno_cabe(live_server, duena_con_prendas):
    sesion, camisa = duena_con_prendas
    direccion = live_server.url + "/cotizador/"
    medidas = {}
    manejador, navegador = _chrome()
    try:
        for ancho, alto in TAMANOS:
            contexto = navegador.new_context(viewport={"width": ancho, "height": alto})
            contexto.add_cookies([{"name": "sessionid", "value": sesion, "url": direccion}])
            pagina = contexto.new_page()
            pagina.goto(direccion, wait_until="networkidle")
            pagina.select_option("#cot-guardada", camisa)
            pagina.wait_for_selector("#quitar-de-mi-lista")
            pagina.evaluate(ESPIAR_ANIMACIONES)
            pagina.fill("#cot-cliente", "Cliente de ejemplo")
            pagina.fill("#cot-cantidad", "20")
            pagina.wait_for_function(
                "document.querySelector('.cotizacion__total').textContent.trim()"
                " === '$ 1.090.000'"
            )
            pagina.wait_for_timeout(400)  # lo que entra termina de aparecer
            medidas[f"{ancho} x {alto}"] = {
                **pagina.evaluate(MEDIR),
                "animadas": pagina.evaluate("window.animadasEnElResultado"),
            }
            contexto.close()
    finally:
        navegador.close()
        manejador.stop()
    for tamano, medida in medidas.items():
        assert medida["pagina"] <= medida["ventana"], f"La página se desplaza en {tamano}"
        assert medida["contenido"] <= medida["cabe"] + 1, f"No cabe en {tamano}: {medida}"
        assert abs(medida["izquierda"] - medida["derecha"]) <= 1, f"Columnas disparejas: {medida}"
        assert abs(medida["izquierda"] - medida["hoja"]) <= 1, f"Hueco abajo en {tamano}: {medida}"
        assert medida["animadas"] == [], f"El resultado se animó al escribir: {medida}"
