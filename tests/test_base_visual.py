"""Base visual (T02): marco, menú, barra de celular, piezas y archivos guardados en el proyecto.

Las pruebas automáticas no ven el diseño; eso se revisa a mano con las capturas en 1280 y
390 px. Aquí se comprueba lo que sí se puede leer en el HTML y en los archivos.
"""

import re
from datetime import date
from html.parser import HTMLParser
from pathlib import Path

import pytest
from django.conf import settings
from django.template import Context, Template

from config.menu import MI_TALLER, SECCIONES
from config.piezas import fecha_larga

RAIZ = Path(settings.BASE_DIR)
ESTATICOS = RAIZ / "static"


class Elementos(HTMLParser):
    """Recorre el HTML y guarda cada elemento con su clase, atributos y texto."""

    def __init__(self, html):
        super().__init__()
        self.elementos = []
        self._abiertos = []
        self.feed(html)

    def handle_starttag(self, etiqueta, atributos):
        elemento = {"etiqueta": etiqueta, "atributos": dict(atributos), "texto": ""}
        elemento["clases"] = (elemento["atributos"].get("class") or "").split()
        self.elementos.append(elemento)
        if etiqueta not in ("input", "img", "meta", "link", "br", "use"):
            self._abiertos.append(elemento)

    def handle_endtag(self, etiqueta):
        for i in range(len(self._abiertos) - 1, -1, -1):
            if self._abiertos[i]["etiqueta"] == etiqueta:
                del self._abiertos[i:]
                break

    def handle_data(self, datos):
        for elemento in self._abiertos:
            elemento["texto"] += datos

    def con_clase(self, clase):
        return [e for e in self.elementos if clase in e["clases"]]


def texto(elemento):
    return " ".join(elemento["texto"].split())


# --- El marco y el menú ------------------------------------------------------------------


def test_hoy_tiene_el_marco_el_menu_y_la_fecha(sesion_duena, taller):
    respuesta = sesion_duena.get("/")
    html = Elementos(respuesta.text)

    assert html.con_clase("marco")
    assert html.con_clase("hoja")
    assert texto(html.con_clase("menu__taller")[0]) == taller.nombre
    assert "<h1>Hoy</h1>" in respuesta.text
    assert fecha_larga(respuesta.context["hoy"]) in respuesta.text


def test_el_menu_tiene_las_secciones_en_orden_y_mi_taller_al_fondo(sesion_duena):
    html = Elementos(sesion_duena.get("/").text)

    nombres = [texto(e) for e in html.con_clase("menu__texto")]

    assert nombres == [
        "Hoy", "Pedidos", "Calendario", "Clientes", "Cotizador", "Telas", "Resumen",
        "Mi taller", "Salir",
    ]


def test_el_menu_resalta_la_seccion_actual(sesion_duena):
    html = Elementos(sesion_duena.get("/").text)

    actuales = [e for e in html.con_clase("menu__enlace") if "es-actual" in e["clases"]]

    assert len(actuales) == 1
    assert texto(actuales[0]) == "Hoy"
    assert actuales[0]["atributos"]["aria-current"] == "page"


def test_cada_entrada_lleva_a_una_pantalla_o_queda_quieta(sesion_duena):
    # Las secciones que todavía no existen se ven, pero no llevan a ninguna parte.
    html = Elementos(sesion_duena.get("/").text)

    for entrada in html.con_clase("menu__enlace"):
        if entrada["etiqueta"] != "a":
            continue
        direccion = entrada["atributos"].get("href")
        if direccion:
            assert sesion_duena.get(direccion).status_code == 200, direccion
        else:
            assert entrada["atributos"].get("aria-disabled") == "true", texto(entrada)


def test_el_menu_se_contrae_y_se_abre_con_botones(sesion_duena):
    html = Elementos(sesion_duena.get("/").text)

    contraer = html.con_clase("menu__contraer")[0]
    abrir = html.con_clase("menu__abrir")[0]

    assert contraer["etiqueta"] == "button"
    assert contraer["atributos"]["aria-label"] == "Contraer el menú"
    assert abrir["etiqueta"] == "button"
    assert abrir["atributos"]["aria-label"] == "Abrir el menú"


def test_la_eleccion_de_menu_contraido_se_recuerda(sesion_duena):
    sin_cookie = Elementos(sesion_duena.get("/").text)
    assert "marco--contraido" not in sin_cookie.con_clase("marco")[0]["clases"]

    sesion_duena.cookies["menu"] = "contraido"
    con_cookie = Elementos(sesion_duena.get("/").text)

    assert "marco--contraido" in con_cookie.con_clase("marco")[0]["clases"]
    # Contraído, cada ícono muestra su nombre al pasar el mouse.
    titulos = [e["atributos"].get("title") for e in con_cookie.con_clase("menu__enlace")]
    assert titulos[:3] == ["Hoy", "Pedidos", "Calendario"]


def test_salir_es_un_boton_que_envia_un_formulario(sesion_duena):
    respuesta = sesion_duena.get("/")

    assert respuesta.text.count('action="/salir/"') == 2  # menú lateral y panel "Más"
    assert re.search(r'<form method="post" action="/salir/"><input type="hidden" '
                     r'name="csrfmiddlewaretoken"', respuesta.text)


# --- Contadores ---------------------------------------------------------------------------


def test_sin_pendientes_no_se_muestra_ningun_contador(sesion_duena):
    html = Elementos(sesion_duena.get("/").text)

    assert html.con_clase("menu__contador") == []


def test_los_contadores_cuentan_pedidos_atrasados_y_telas_que_se_acaban(sesion_duena, taller):
    from datetime import timedelta

    from django.utils import timezone

    from tests import fabricas

    ayer = timezone.localdate() - timedelta(days=1)
    fabricas.crear_pedido(taller, estado="confeccion", fecha_entrega=ayer)
    fabricas.crear_pedido(taller, estado="entregado", fecha_entrega=ayer)  # no cuenta
    fabricas.crear_tela(taller, metros=2, minimo=5)
    fabricas.crear_tela(taller, metros=3, minimo=5)
    fabricas.crear_tela(taller, metros=9, minimo=5)  # suficiente
    otro = fabricas.crear_taller()
    fabricas.crear_pedido(otro, estado="corte", fecha_entrega=ayer)  # de otro taller

    html = Elementos(sesion_duena.get("/").text)

    assert [texto(e) for e in html.con_clase("menu__contador")] == ["1", "2"]


def test_con_pendientes_se_muestran_los_contadores(sesion_duena, settings):
    settings.DEBUG = True  # la página Piezas trae contadores de ejemplo
    html = Elementos(sesion_duena.get("/piezas/").text)

    contadores = [texto(e) for e in html.con_clase("menu__contador")]

    assert contadores == ["1", "2"]


# --- Celular: barra de abajo y "Más" ------------------------------------------------------


def test_en_celular_la_barra_tiene_hoy_pedidos_calendario_clientes_y_mas(sesion_duena):
    html = Elementos(sesion_duena.get("/").text)

    entradas = [texto(e) for e in html.con_clase("navegacion-celular__enlace")]

    assert entradas == ["Hoy", "Pedidos", "Calendario", "Clientes", "Más"]
    mas = html.con_clase("navegacion-celular__enlace")[-1]
    assert mas["etiqueta"] == "button"
    assert mas["atributos"]["aria-expanded"] == "false"
    assert mas["atributos"]["aria-controls"] == "panel-mas"


def test_mas_trae_cotizador_telas_resumen_mi_taller_y_salir(sesion_duena):
    html = Elementos(sesion_duena.get("/").text)

    panel = [e for e in html.elementos if e["atributos"].get("id") == "panel-mas"][0]
    entradas = [texto(e) for e in html.con_clase("panel-mas__enlace")]

    assert "hidden" in panel["atributos"]
    assert entradas == ["Cotizador", "Telas", "Resumen", "Mi taller", "Salir"]


def test_las_secciones_del_menu_coinciden_con_el_diseno():
    assert [s.nombre for s in SECCIONES] == [
        "Hoy", "Pedidos", "Calendario", "Clientes", "Cotizador", "Telas", "Resumen",
    ]
    assert [s.nombre for s in SECCIONES if s.en_barra] == [
        "Hoy", "Pedidos", "Calendario", "Clientes",
    ]
    assert MI_TALLER.nombre == "Mi taller"


# --- Página de entrada --------------------------------------------------------------------


@pytest.mark.django_db
def test_la_pagina_de_entrada_es_una_tarjeta_sobre_el_marco_sin_menu(client):
    html = Elementos(client.get("/entrar/").text)

    assert html.con_clase("marco-acceso")
    assert html.con_clase("tarjeta")
    assert html.con_clase("boton--principal")
    assert html.con_clase("menu") == []
    assert html.con_clase("navegacion-celular") == []


# --- Página "Piezas" ----------------------------------------------------------------------


def test_piezas_solo_existe_en_desarrollo(sesion_duena, settings):
    settings.DEBUG = False
    assert sesion_duena.get("/piezas/").status_code == 404

    settings.DEBUG = True
    respuesta = sesion_duena.get("/piezas/")
    assert respuesta.status_code == 200
    for titulo in ("Colores", "Tipografía", "Botones y filtros", "Qué hacer hoy",
                   "Quién te debe", "Trabajos del taller", "Campos", "Pasos de etapa",
                   "Materiales", "Barras de progreso", "Cobrado y gastado por mes", "Íconos"):
        assert titulo in respuesta.text, titulo


@pytest.mark.django_db
def test_piezas_pide_sesion(client, settings):
    settings.DEBUG = True

    assert client.get("/piezas/").status_code == 302


def test_un_campo_con_error_avisa_a_los_lectores_de_pantalla(sesion_duena, settings):
    settings.DEBUG = True
    html = Elementos(sesion_duena.get("/piezas/").text)

    cantidad = [e for e in html.elementos if e["atributos"].get("id") == "id_errores-cantidad"][0]
    error = [e for e in html.elementos if e["atributos"].get("id") == "id_errores-cantidad_error"]

    assert "campo__control" in cantidad["clases"]
    assert cantidad["atributos"]["aria-invalid"] == "true"
    assert "id_errores-cantidad_error" in cantidad["atributos"]["aria-describedby"]
    assert error and "campo__error" in error[0]["clases"]


# --- Piezas de plantilla ------------------------------------------------------------------


@pytest.mark.parametrize(
    ("fecha", "esperado"),
    [
        (date(2026, 11, 11), "Miércoles, 11 de noviembre"),
        (date(2027, 1, 1), "Viernes, 1 de enero"),
        (date(2026, 8, 31), "Lunes, 31 de agosto"),
    ],
)
def test_la_fecha_larga_queda_como_en_el_diseno(fecha, esperado):
    assert fecha_larga(fecha) == esperado


def test_el_icono_sale_del_archivo_de_iconos_del_proyecto():
    html = Template('{% load piezas %}{% icono "hoy" %}').render(Context())

    assert 'aria-hidden="true"' in html
    assert 'width="18"' in html
    assert 'stroke-width="1.75"' in html
    assert '<use href="/static/iconos/iconos.svg#hoy">' in html


def test_todos_los_iconos_que_se_usan_existen():
    simbolos = set(re.findall(r'<symbol id="([^"]+)"', (ESTATICOS / "iconos/iconos.svg").read_text("utf-8")))
    usados = set()
    plantillas = [*RAIZ.glob("templates/**/*.html"), *RAIZ.glob("*/templates/**/*.html")]
    assert len(plantillas) > 10
    for plantilla in plantillas:
        usados |= set(re.findall(r'{% icono "([^"]+)"', plantilla.read_text("utf-8")))
    usados |= {s.icono for s in SECCIONES} | {MI_TALLER.icono}

    assert usados <= simbolos, usados - simbolos


# --- Todo guardado en el proyecto, nada desde internet ------------------------------------


def test_la_fuente_inter_esta_guardada_en_sus_cuatro_pesos():
    for peso in (400, 500, 600, 700):
        archivo = ESTATICOS / f"fuentes/inter-latin-{peso}-normal.woff2"
        assert archivo.read_bytes()[:4] == b"wOF2", archivo.name
        assert f"inter-latin-{peso}-normal.woff2" in (ESTATICOS / "css/app.css").read_text("utf-8")


def test_htmx_2_esta_guardado_en_el_proyecto():
    contenido = (ESTATICOS / "js/htmx.min.js").read_text("utf-8")

    assert re.search(r'version:"2\.\d+\.\d+"', contenido)


@pytest.mark.parametrize("direccion", ["/", "/entrar/", "/piezas/"])
def test_ninguna_pagina_carga_nada_desde_internet(sesion_duena, settings, direccion):
    settings.DEBUG = True
    if direccion == "/entrar/":
        sesion_duena.logout()

    html = sesion_duena.get(direccion).text

    assert not re.search(r'(?:src|href)="(?:https?:)?//', html)


@pytest.mark.parametrize("direccion", ["/", "/entrar/"])
def test_cada_pagina_trae_el_icono_de_la_pestana(sesion_duena, direccion):
    # Sin él, el navegador pide /favicon.ico y recibe "no existe".
    if direccion == "/entrar/":
        sesion_duena.logout()
    html = sesion_duena.get(direccion).text

    assert '<link rel="icon" href="/static/iconos/favicon.svg"' in html
    assert (ESTATICOS / "iconos/favicon.svg").exists()


def test_los_estilos_y_el_javascript_no_cargan_nada_desde_internet():
    for archivo in ("css/app.css", "js/app.js"):
        contenido = (ESTATICOS / archivo).read_text("utf-8")
        assert not re.search(r"https?://", contenido), archivo
        assert "@import" not in contenido


# --- Los colores coinciden con docs/08-diseno.md ------------------------------------------


def test_los_colores_de_la_hoja_de_estilos_son_los_del_documento_de_diseno():
    documento = (RAIZ / "docs/08-diseno.md").read_text("utf-8")
    css = (ESTATICOS / "css/app.css").read_text("utf-8")

    colores = re.findall(r"^\| `(--[a-z0-9-]+)` \| `(#[0-9A-F]{6})` \|", documento, re.MULTILINE)
    assert len(colores) == 14
    for variable, valor in colores:
        assert f"{variable}: {valor};" in css, variable

    tonos = re.findall(r"^\| (Rojo|Verde|Ámbar|Azul|Gris) \| `(#[0-9A-F]{6})` \| `(#[0-9A-F]{6})` \|",
                       documento, re.MULTILINE)
    assert len(tonos) == 5
    nombres = {"Rojo": "rojo", "Verde": "verde", "Ámbar": "ambar", "Azul": "azul", "Gris": "gris"}
    for tono, fondo, letra in tonos:
        assert f"--{nombres[tono]}-fondo: {fondo};" in css, tono
        assert f"--{nombres[tono]}-texto: {letra};" in css, tono


def test_el_marco_y_la_franja_usan_los_degradados_del_documento():
    css = (ESTATICOS / "css/app.css").read_text("utf-8")

    assert "linear-gradient(180deg, #000000 0%, #000000 70%, #2563C9 100%)" in css
    assert "linear-gradient(90deg, #000000 0%, #000000 55%, #2563C9 100%)" in css


def test_los_campos_usan_el_borde_de_campo_y_los_botones_el_de_control():
    css = (ESTATICOS / "css/app.css").read_text("utf-8")

    for selector in (".campo__control", ".buscador"):
        regla = re.search(re.escape(selector) + r" \{(.*?)\}", css, re.DOTALL).group(1)
        assert "border: 1px solid var(--borde-campo);" in regla, selector
    regla = re.search(r"^\.boton \{(.*?)\}", css, re.DOTALL | re.MULTILINE).group(1)
    assert "var(--borde-control)" in regla


def test_piezas_muestra_todos_los_colores_del_documento(sesion_duena, settings):
    settings.DEBUG = True
    documento = (RAIZ / "docs/08-diseno.md").read_text("utf-8")
    pagina = sesion_duena.get("/piezas/").text

    for variable, valor in re.findall(r"^\| `(--[a-z0-9-]+)` \| `(#[0-9A-F]{6})` \|",
                                      documento, re.MULTILINE):
        assert variable in pagina and valor in pagina, variable


# --- Celular: nada se sale de los 390 px ---------------------------------------------------


def _reglas_de_celular():
    css = (ESTATICOS / "css/app.css").read_text("utf-8")
    inicio = css.index("@media (max-width: 767.98px) {")
    return css[inicio:css.index("\n}\n", inicio)]


def test_en_celular_los_botones_del_encabezado_no_se_encogen():
    # Si la caja de botones se encoge, "Nuevo pedido" (que no se parte) se sale de la
    # pantalla cuando el título es largo. El que cede espacio debe ser el título.
    regla = re.search(r"\.encabezado__acciones \{(.*?)\}", _reglas_de_celular(), re.DOTALL)
    assert regla and "flex: none;" in regla.group(1)


def test_en_celular_la_letra_de_la_grafica_se_agranda():
    # La gráfica se dibuja a 600 de ancho y en celular se achica a unos 330 px. Con la
    # letra de 12 de computador quedaría en ~6 px; con 20 queda en ~11 px.
    regla = re.search(r"\.grafica text \{(.*?)\}", _reglas_de_celular(), re.DOTALL)
    assert regla and "font-size: 20px;" in regla.group(1)
