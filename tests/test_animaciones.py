"""Animaciones y aviso corto de confirmación (docs/08-diseno.md, "Animaciones").

Las pruebas automáticas no ven el movimiento (eso se revisa a mano en /piezas/ con un
navegador). Aquí se comprueba lo que sí se puede leer: que las duraciones se definen una sola
vez y son cortas, que todo las usa, que "menos movimiento" las apaga, y que el servidor manda
bien el aviso corto.
"""

import json
import re
from datetime import date
from pathlib import Path

import pytest
from django.conf import settings
from django.contrib.messages import get_messages
from django.http import HttpResponse, HttpResponseRedirect
from django.template import Context, Template
from django.test import RequestFactory

from config.avisos import avisar
from config.ventanas import CERRAR_VENTANA

ESTATICOS = Path(settings.BASE_DIR) / "static"
CSS = (ESTATICOS / "css" / "app.css").read_text(encoding="utf-8")
JS = (ESTATICOS / "js" / "app.js").read_text(encoding="utf-8")

DURACIONES = ["--duracion-corta", "--duracion", "--duracion-larga"]


def _raiz(css):
    """El bloque :root del comienzo de app.css."""
    return css[css.index(":root {"):css.index("}", css.index(":root {"))]


def _sin_comentarios(css):
    return re.sub(r"/\*.*?\*/", "", css, flags=re.S)


# --- Duraciones: una sola vez, cortas, y todo las usa -------------------------------------


def test_las_duraciones_se_definen_una_sola_vez_y_son_cortas():
    raiz = _raiz(CSS)
    for variable in DURACIONES:
        valores = re.findall(rf"{variable}:\s*(\d+)ms;", raiz)
        assert len(valores) == 1, f"{variable} se define una vez en :root"
        assert 150 <= int(valores[0]) <= 250, f"{variable} está entre 150 y 250 ms"
        # Fuera de :root solo se redefine en "menos movimiento" (a 0).
        sin = _sin_comentarios(CSS)
        fuera = re.findall(rf"{variable}:\s*([^;]+);", sin.replace(_raiz(sin), ""))
        assert fuera == ["0ms"], f"{variable} solo se cambia a 0 con menos movimiento"


def test_las_transiciones_y_animaciones_usan_las_variables():
    """Ninguna duración escrita a mano, salvo la de las fotos que pasan (0.64 s, una regla del
    diseño anterior a esta) y el giro del indicador "cargando" (una variable, no una
    transición)."""
    css = _sin_comentarios(CSS)
    css = css.replace(_raiz(css), "")
    declaraciones = re.findall(r"(?:transition|animation)(?:-duration)?\s*:\s*([^;]+);", css)
    assert declaraciones, "hay transiciones y animaciones"
    for declaracion in declaraciones:
        if declaracion.strip() in ("none", "opacity 0.64s linear"):
            continue
        sin_variables = re.sub(r"var\(--[a-z-]+\)", "", declaracion)
        assert not re.search(r"\d+(\.\d+)?m?s\b", sin_variables), (
            f"duración escrita a mano en app.css: {declaracion!r}")


def test_menos_movimiento_apaga_las_animaciones():
    bloque = CSS[CSS.index("@media (prefers-reduced-motion: reduce)"):]
    for variable in DURACIONES:
        assert f"{variable}: 0ms;" in bloque
    assert "navigation: none;" in bloque  # sin desvanecido al cambiar de sección
    assert "transform: none !important;" in bloque  # los botones no suben ni se hunden
    # El JavaScript también pregunta antes de animar.
    assert 'matchMedia("(prefers-reduced-motion: reduce)")' in JS
    assert "function hayMovimiento()" in JS


def test_el_javascript_lee_las_duraciones_de_la_hoja_de_estilos():
    for variable in ["--duracion-corta", "--duracion", "--espera-cargando", "--tiempo-aviso"]:
        assert f'milisegundos("{variable}")' in JS
    # Sin duraciones de animación escritas a mano en el JavaScript.
    assert not re.search(r"duration:\s*\d", JS)
    assert "defaultSwapDelay = duracion" in JS


def test_el_cambio_de_seccion_usa_la_transicion_del_navegador():
    assert "@view-transition {\n  navigation: auto;\n}" in CSS
    assert "view-transition-name: menu;" in CSS


def test_la_pantalla_fija_solo_aplica_en_computador():
    inicio = CSS.index("/* 6. Pantalla fija")
    fin = CSS.index("/* 7. Animaciones")
    seccion = _sin_comentarios(CSS[inicio:fin])
    medias = re.findall(r"@media ([^{]+)\{", seccion)
    assert medias and all("min-width: 768px" in m for m in medias)
    # Fuera de un @media no hay reglas: en celular todo sigue como está.
    assert re.sub(r"@media[^{]+\{(?:[^{}]*\{[^{}]*\})*[^{}]*\}", "", seccion).strip() == ""


# --- Aviso corto de confirmación (config/avisos.py) ----------------------------------------


def _peticion(htmx=True):
    peticion = RequestFactory().post("/", HTTP_HX_REQUEST="true" if htmx else None)
    if not htmx:
        del peticion.META["HTTP_HX_REQUEST"]
    peticion.session = {}
    from django.contrib.messages.storage.fallback import FallbackStorage

    peticion._messages = FallbackStorage(peticion)
    return peticion


def test_avisar_en_htmx_va_en_la_cabecera():
    respuesta = avisar(_peticion(), HttpResponse("<p>x</p>"), "Abono registrado.")
    assert json.loads(respuesta["HX-Trigger"]) == {"aviso": "Abono registrado."}


def test_avisar_conserva_lo_que_ya_decia_la_cabecera():
    respuesta = avisar(_peticion(), HttpResponse(headers=CERRAR_VENTANA), "Tela agregada.")
    assert json.loads(respuesta["HX-Trigger"]) == {"cerrar-ventana": "", "aviso": "Tela agregada."}
    otra = HttpResponse(headers={"HX-Trigger": json.dumps({"algo": {"x": 1}})})
    otra = avisar(_peticion(), otra, "Listo.")
    assert json.loads(otra["HX-Trigger"]) == {"algo": {"x": 1}, "aviso": "Listo."}


def test_avisar_con_tildes_manda_la_cabecera_en_ascii():
    respuesta = avisar(_peticion(), HttpResponse(), "Piqué blanco: quedan 60 m.")
    respuesta["HX-Trigger"].encode("ascii")
    assert json.loads(respuesta["HX-Trigger"])["aviso"] == "Piqué blanco: quedan 60 m."


@pytest.mark.parametrize("respuesta", [
    HttpResponseRedirect("/pedidos/"),
    HttpResponse(headers={"HX-Redirect": "/pedidos/"}),
    HttpResponse(headers={"HX-Refresh": "true"}),
])
def test_si_se_va_a_otra_pagina_el_aviso_va_como_mensaje(respuesta):
    peticion = _peticion()
    respuesta = avisar(peticion, respuesta, "Pedido eliminado.")
    assert "HX-Trigger" not in respuesta
    assert [str(m) for m in get_messages(peticion)] == ["Pedido eliminado."]


def test_la_pagina_siguiente_muestra_el_mensaje(sesion_duena):
    from django.contrib.messages import constants

    respuesta = sesion_duena.get("/")
    assert 'id="avisos"' in respuesta.text
    assert "avisos-pendientes" not in respuesta.text
    # Un mensaje pendiente queda en la página siguiente, para que app.js lo muestre.
    almacen = respuesta.wsgi_request._messages
    almacen.add(constants.SUCCESS, "Pedido eliminado.")
    almacen.update(respuesta)
    sesion_duena.cookies.update(respuesta.cookies)
    siguiente = sesion_duena.get("/").text
    assert '<div id="avisos-pendientes" hidden><p data-aviso>Pedido eliminado.</p></div>' in siguiente


def test_la_caja_del_aviso_esta_en_todas_las_paginas(client):
    html = client.get("/entrar/").text
    assert '<div class="avisos" id="avisos" aria-hidden="true"></div>' in html


# --- Piezas que se animan ------------------------------------------------------------------


def test_cada_paso_tiene_su_id_y_su_visto_bueno():
    pasos = [{"nombre": "Cotizado", "valor": "cotizado", "estado": "hecho"},
             {"nombre": "En corte", "valor": "corte", "estado": "actual"},
             {"nombre": "Listo", "valor": "listo", "estado": "pendiente"}]
    html = Template('{% include "piezas/_pasos.html" %}').render(Context({"pasos": pasos}))
    assert 'id="paso-cotizado"' in html and 'id="paso-corte"' in html
    assert html.count("#visto") == 3  # siempre está; app.css lo muestra solo en los hechos
    otro = Template('{% include "piezas/_pasos.html" with id_pasos="p" %}').render(
        Context({"pasos": pasos}))
    assert 'id="p-listo"' in otro


def test_la_grafica_puede_venir_baja_para_el_computador():
    from config.piezas import grafica_barras
    from pedidos.calculos import MesDeGrafica

    meses = [MesDeGrafica(date(2026, m, 1), 1_000_000 * (m - 5), 500_000) for m in range(6, 12)]
    sola = grafica_barras(meses)
    assert sola.count("<svg") == 1 and 'class="grafica"' in sola
    dos = grafica_barras(meses, alto_computador=130)
    assert dos.count("<svg") == 2
    assert 'class="grafica grafica--computador" role="img"' in dos
    assert 'viewBox="0 0 600 130"' in dos and 'viewBox="0 0 600 200"' in dos
    # La del celular es igual a la de siempre.
    assert dos.split("</svg>")[1] + "</svg>" == sola.replace(
        'class="grafica"', 'class="grafica grafica--celular"')
    # En la baja, la base va en 100 y el espacio libre de arriba se achica en proporción
    # (36 * 130 / 200 = 23): la barra más alta mide 100 - 23 = 77.
    baja = dos.split("</svg>")[0]
    assert 'y="23" width="22" height="77"' in baja


# --- Ejemplos de /piezas/ ------------------------------------------------------------------


def test_piezas_muestra_las_animaciones(sesion_duena, settings):
    settings.DEBUG = True
    html = sesion_duena.get("/piezas/").text
    for parte in ['id="p-animaciones"', 'id="p-animaciones-filas"', 'id="p-animaciones-etapa"',
                  'id="p-animaciones-barras"', "Abrir una ventana"]:
        assert parte in html


def test_piezas_filas_de_ejemplo_entran_y_salen_con_aviso(sesion_duena, settings, monkeypatch):
    monkeypatch.setattr("config.vistas.DEMORA_EJEMPLO", 0)
    settings.DEBUG = True
    url = "/piezas/animaciones/filas/"
    agregar = sesion_duena.post(url, HTTP_HX_REQUEST="true")
    assert 'id="p-fila-4"' in agregar.text
    assert json.loads(agregar["HX-Trigger"]) == {"aviso": "Fila agregada (ejemplo)."}
    quitar = sesion_duena.post(url, {"quitar": "2"}, HTTP_HX_REQUEST="true")
    assert 'id="p-fila-2"' not in quitar.text and 'id="p-fila-4"' in quitar.text
    assert json.loads(quitar["HX-Trigger"]) == {"aviso": "Fila quitada (ejemplo)."}


def test_piezas_ventana_de_ejemplo_se_cierra_con_aviso(sesion_duena, settings, monkeypatch):
    monkeypatch.setattr("config.vistas.DEMORA_EJEMPLO", 0)
    settings.DEBUG = True
    url = "/piezas/animaciones/ventana/"
    assert "Ventana de ejemplo" in sesion_duena.get(url, HTTP_HX_REQUEST="true").text
    respuesta = sesion_duena.post(url, HTTP_HX_REQUEST="true")
    assert json.loads(respuesta["HX-Trigger"]) == {"cerrar-ventana": "",
                                                   "aviso": "Guardado (ejemplo)."}


def test_piezas_etapa_y_barras_de_ejemplo(sesion_duena, settings):
    settings.DEBUG = True
    etapa = sesion_duena.post("/piezas/animaciones/etapa/", {"estado": "4"},
                              HTTP_HX_REQUEST="true").text
    assert 'class="paso paso--actual" name="estado" value="4" aria-current="step" id="p-paso-4"' in etapa
    assert 'class="grafica grafica--computador"' in sesion_duena.get(
        "/piezas/animaciones/barras/", HTTP_HX_REQUEST="true").text


@pytest.mark.parametrize("direccion", ["/piezas/animaciones/filas/", "/piezas/animaciones/etapa/",
                                       "/piezas/animaciones/barras/",
                                       "/piezas/animaciones/ventana/"])
def test_los_ejemplos_de_piezas_solo_existen_en_desarrollo(sesion_duena, settings, direccion):
    settings.DEBUG = False
    assert sesion_duena.get(direccion).status_code == 404
