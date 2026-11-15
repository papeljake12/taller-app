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
    assert texto(html.con_clase("menu__nombre")[0]) == taller.nombre
    assert fecha_larga(respuesta.context["hoy"]) in respuesta.text


def test_el_menu_tiene_las_secciones_en_orden_y_mi_taller_al_fondo(sesion_duena):
    html = Elementos(sesion_duena.get("/").text)

    nombres = [texto(e) for e in html.con_clase("menu__texto")]

    assert nombres == [
        "Hoy", "Pedidos", "Calendario", "Clientes", "Cotizador", "Telas", "Resumen",
        "Mi taller",
    ]
    # Al fondo, junto al nombre del taller, el botón para salir (docs/08-diseno.md)
    salir = html.con_clase("menu__salir")[0]
    assert salir["etiqueta"] == "button" and salir["atributos"]["aria-label"] == "Salir"


def test_dentro_de_pedidos_el_menu_muestra_atrasados_y_con_saldo(sesion_duena):
    en_hoy = Elementos(sesion_duena.get("/").text)
    en_pedidos = Elementos(sesion_duena.get("/pedidos/?filtro=atrasados").text)

    assert en_hoy.con_clase("menu__enlace--sub") == []
    subs = en_pedidos.con_clase("menu__enlace--sub")
    assert [texto(e) for e in subs] == ["Atrasados", "Con saldo"]
    assert [e["atributos"]["href"] for e in subs] == [
        "/pedidos/?filtro=atrasados", "/pedidos/?filtro=saldo",
    ]
    # La subsección del filtro que se ve queda marcada
    assert "es-actual" in subs[0]["clases"] and "es-actual" not in subs[1]["clases"]


def test_la_costurera_no_ve_la_subseccion_con_saldo(client, costurera):
    client.force_login(costurera)
    html = Elementos(client.get("/pedidos/").text)

    assert [texto(e) for e in html.con_clase("menu__enlace--sub")] == ["Atrasados"]


def test_el_taller_va_abajo_con_sus_iniciales_o_su_logo(sesion_duena, taller):
    from config.menu import iniciales

    assert iniciales("Taller de ejemplo") == "TE"
    assert iniciales("Confecciones la Costurera") == "CC"
    assert iniciales("Modas") == "M"
    assert iniciales("") == "T"
    html = Elementos(sesion_duena.get("/").text)
    assert texto(html.con_clase("menu__avatar")[0]) == iniciales(taller.nombre)


def test_el_titulo_lleva_el_icono_de_su_seccion(sesion_duena):
    html = sesion_duena.get("/calendario/").text

    assert re.search(r'<h1 class="encabezado__nombre"><svg class="icono"[^>]*>'
                     r'<use href="/static/iconos/iconos.svg#calendario">', html)


def test_ctrl_k_lleva_al_buscador(sesion_duena):
    html = sesion_duena.get("/").text

    assert "data-atajo-buscar" in html and '<kbd class="menu__atajo" aria-hidden="true">Ctrl K</kbd>' in html
    js = (ESTATICOS / "js/app.js").read_text("utf-8")
    assert 'evento.key.toLowerCase() === "k"' in js and "evento.metaKey" in js


def test_lo_que_se_muestra_con_un_boton_deja_el_cursor_en_un_campo_visible():
    # La fila del buscador de Pedidos empieza con un campo escondido (el filtro): el cursor va
    # al primer campo que se ve, no a ese (se encontró probando en Chrome).
    js = (ESTATICOS / "js/app.js").read_text("utf-8")
    assert 'parte.querySelector("input:not([type=hidden]), select, textarea")' in js


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


def test_mas_trae_buscar_cotizador_telas_resumen_mi_taller_y_salir(sesion_duena):
    # En celular el menú lateral (con su buscador) no se ve: "Buscar" va primero en "Más".
    html = Elementos(sesion_duena.get("/").text)

    panel = [e for e in html.elementos if e["atributos"].get("id") == "panel-mas"][0]
    entradas = [texto(e) for e in html.con_clase("panel-mas__enlace")]

    assert "hidden" in panel["atributos"]
    assert entradas == [
        "Buscar pedidos y clientes", "Cotizador", "Telas", "Resumen", "Mi taller", "Salir",
    ]


def test_el_buscador_del_menu_solo_muestra_lo_buscado_en_su_pagina(sesion_duena):
    en_pedidos = sesion_duena.get("/pedidos/?q=marta").text
    en_buscar = sesion_duena.get("/buscar/?q=marta").text

    assert 'id="menu-buscar" name="q" placeholder="Buscar" value=""' in en_pedidos
    assert 'id="menu-buscar" name="q" placeholder="Buscar" value="marta"' in en_buscar


def test_pedidos_va_resaltado_tambien_dentro_de_un_pedido(sesion_duena, taller):
    from tests import fabricas

    pedido = fabricas.crear_pedido(taller)
    html = Elementos(sesion_duena.get(f"/pedidos/{pedido.pk}/").text)

    actuales = [texto(e) for e in html.con_clase("menu__enlace") if "es-actual" in e["clases"]]
    assert actuales == ["Pedidos"]


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
    for titulo in ("Colores e insignias", "Tipografía", "Botones, chips y pestañas",
                   "Quién te debe", "Campos", "Cronología", "Materiales", "Tallas",
                   "Cobrado y gastado por mes", "Íconos", "Aquí vas a ver tus telas"):
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


def test_la_fuente_inter_variable_esta_guardada_en_el_proyecto():
    # Una sola letra, Inter, en su versión variable: los pesos de 400 a 700 (450, 550, 650...)
    archivo = ESTATICOS / "fuentes/inter-latin-wght-normal.woff2"
    assert archivo.read_bytes()[:4] == b"wOF2"
    css = (ESTATICOS / "css/app.css").read_text("utf-8")
    assert 'url("../fuentes/inter-latin-wght-normal.woff2")' in css
    assert "font-weight: 400 700;" in css
    assert (ESTATICOS / "fuentes/LICENCIA-Inter.txt").exists()


def test_htmx_2_esta_guardado_en_el_proyecto():
    contenido = (ESTATICOS / "js/htmx.min.js").read_text("utf-8")

    assert re.search(r'version:"2\.\d+\.\d+"', contenido)


@pytest.mark.parametrize("direccion", ["/", "/entrar/", "/piezas/"])
def test_ninguna_pagina_carga_nada_desde_internet(sesion_duena, settings, direccion):
    settings.DEBUG = True
    if direccion == "/entrar/":
        sesion_duena.logout()

    html = sesion_duena.get(direccion).text

    # Ni scripts, ni imágenes, ni hojas de estilo de afuera. Un enlace para abrir WhatsApp
    # (<a href="https://wa.me/...">) sí puede ir: no se descarga nada al cargar la página.
    assert not re.search(r'src="(?:https?:)?//', html)
    assert not re.search(r'<link[^>]+href="(?:https?:)?//', html)


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
        # Los circulitos de las insignias son dibujos dentro de la hoja (data:); llevan el
        # nombre del formato SVG, que no se descarga de ninguna parte.
        contenido = (ESTATICOS / archivo).read_text("utf-8").replace("http://www.w3.org/2000/svg", "")
        assert not re.search(r"https?://", contenido), archivo
        assert "@import" not in contenido


# --- Los colores coinciden con docs/08-diseno.md ------------------------------------------


def test_los_colores_de_la_hoja_de_estilos_son_los_del_documento_de_diseno():
    documento = (RAIZ / "docs/08-diseno.md").read_text("utf-8")
    css = (ESTATICOS / "css/app.css").read_text("utf-8")

    colores = re.findall(r"^\| `(--[a-z0-9-]+)` \| `(#[0-9A-F]{6})` \|", documento, re.MULTILINE)
    assert len(colores) == 17
    for variable, valor in colores:
        assert f"{variable}: {valor};" in css, variable

    tonos = re.findall(r"^\| `(gris|azul|verde|ambar|naranja|rojo)` \| `(#[0-9A-F]{6})` \| `(#[0-9A-F]{6})` \|",
                       documento, re.MULTILINE)
    assert len(tonos) == 6
    for tono, fondo, letra in tonos:
        assert f"--{tono}-fondo: {fondo};" in css, tono
        assert f"--{tono}-texto: {letra};" in css, tono
        assert f".etiqueta--{tono} {{ background: var(--{tono}-fondo); color: var(--{tono}-texto); }}" in css
    for circulo in ("vacio", "medio", "lleno", "alerta"):
        assert f".etiqueta--{circulo} {{ --circulo: var(--circulo-{circulo}); }}" in css


def test_la_hoja_de_estilos_de_la_aplicacion_copia_la_del_diseno():
    # Las secciones 1 a 6 de static/css/app.css son una copia de diseno/estilo.css.
    diseno = (RAIZ / "diseno/estilo.css").read_text("utf-8")
    css = (ESTATICOS / "css/app.css").read_text("utf-8")
    copia = diseno[diseno.index("/* 1. Colores, letra y medidas"):].strip()

    assert copia in css


def test_el_marco_es_negro_con_un_brillo_azul_abajo():
    css = (ESTATICOS / "css/app.css").read_text("utf-8")

    assert "--brillo: radial-gradient(closest-side, rgba(37, 99, 201, 0.7), rgba(37, 99, 201, 0));" in css
    marco = re.search(r"\n\.marco::before \{(.*?)\}", css, re.DOTALL).group(1)
    assert "background: var(--brillo);" in marco and "bottom: -150px;" in marco


def test_la_pagina_no_se_mueve_y_la_hoja_se_desplaza_por_dentro():
    # docs/08-diseno.md, "Desplazamiento": en computador el marco mide la ventana y lo que se
    # desplaza es el contenido de la hoja. Ya no hay "pantalla fija" (.llenar, .desplazable).
    css = (ESTATICOS / "css/app.css").read_text("utf-8")

    marco = re.search(r"\n\.marco \{(.*?)\}", css, re.DOTALL).group(1)
    assert "height: 100dvh;" in marco and "overflow: hidden;" in marco
    contenido = re.search(r"\n\.hoja__contenido \{(.*?)\}", css, re.DOTALL).group(1)
    assert "overflow-y: auto;" in contenido
    assert ".llenar" not in css and ".desplazable" not in css


def test_los_campos_usan_el_borde_de_campo_y_los_botones_el_de_control():
    css = (ESTATICOS / "css/app.css").read_text("utf-8")

    for selector in (".campo__control", ".buscador"):
        regla = re.search(r"\n" + re.escape(selector) + r" \{(.*?)\}", css, re.DOTALL).group(1)
        assert "border: 1px solid var(--borde-campo);" in regla, selector
    # Los botones y las tarjetas van con sombra suave, no con borde
    regla = re.search(r"^\.boton \{(.*?)\}", css, re.DOTALL | re.MULTILINE).group(1)
    assert "box-shadow: var(--sombra-boton);" in regla and "border: 0;" in regla
    regla = re.search(r"^\.tarjeta \{(.*?)\}", css, re.DOTALL | re.MULTILINE).group(1)
    assert "box-shadow: var(--sombra-tarjeta);" in regla and "border-radius: 12px;" in regla
    regla = re.search(r"^\.boton--principal \{(.*?)\}", css, re.DOTALL | re.MULTILINE).group(1)
    assert "background: var(--principal);" in regla


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


def test_en_celular_el_titulo_grande_va_debajo_de_los_botones_redondos():
    # Como la app de Shopify: una fila de botones redondos y, debajo, el título grande. Así un
    # título largo nunca empuja los botones fuera de la pantalla.
    celular = _reglas_de_celular()
    regla = re.search(r"\.encabezado \{(.*?)\}", celular, re.DOTALL).group(1)
    assert 'grid-template-areas: "izquierda . acciones" "titulo titulo titulo";' in regla
    assert re.search(r"\.encabezado__nombre \{\s*font-size: 28px;", celular)
    regla = re.search(r"\n  \.boton--redondo-celular \{(.*?)\}", celular, re.DOTALL).group(1)
    assert "width: 36px;" in regla and "border-radius: 50%;" in regla


def test_en_celular_la_letra_de_la_grafica_se_agranda():
    # La gráfica se dibuja a 600 de ancho y en celular se achica a unos 330 px. Con la
    # letra de 12 de computador quedaría en ~6 px; con 20 queda en ~11 px.
    regla = re.search(r"\.grafica text \{(.*?)\}", _reglas_de_celular(), re.DOTALL)
    assert regla and "font-size: 20px;" in regla.group(1)


def test_las_columnas_se_apilan_cuando_no_caben():
    css = (ESTATICOS / "css/app.css").read_text("utf-8")
    inicio = css.index("@media (max-width: 1023.98px) {")
    angosta = css[inicio:css.index("\n}\n", inicio)]
    assert re.search(r"\.columnas,\s*\.dos-columnas,\s*\.dos-columnas--iguales \{\s*"
                     r"grid-template-columns: minmax\(0, 1fr\);", angosta)



# --- Formatos de plata, fechas y metros (config/piezas.py) --------------------------------


@pytest.mark.parametrize(
    ("valor", "esperado"),
    [(1260000, "$ 1.260.000"), (0, "$ 0"), (500, "$ 500"), (-200000, "-$ 200.000"), (None, "")],
)
def test_la_plata_se_escribe_como_en_el_diseno(valor, esperado):
    from config.piezas import pesos

    assert pesos(valor) == esperado


def test_las_fechas_cortas_y_de_mes_como_en_el_diseno():
    from config.piezas import dia_y_mes, fecha_corta, mes_y_anio

    assert fecha_corta(date(2026, 11, 9)) == "9 de nov"
    assert fecha_corta(date(2027, 1, 12)) == "12 de ene"
    assert dia_y_mes(date(2026, 12, 20)) == "20 de diciembre"
    assert mes_y_anio(date(2026, 11, 1)) == "Noviembre de 2026"


@pytest.mark.parametrize(
    ("valor", "esperado"), [("60", "60 m"), ("6.50", "6,5 m"), ("0.25", "0,25 m"), (18, "18 m")]
)
def test_los_metros_se_escriben_con_coma(valor, esperado):
    from config.piezas import metros

    assert metros(valor) == esperado



# --- Gráfica de barras (config/piezas.py) -------------------------------------------------


def _meses_del_diseno():
    from pedidos.calculos import MesDeGrafica

    valores = [(2_100_000, 800_000), (2_900_000, 1_100_000), (3_600_000, 1_300_000),
               (1_900_000, 700_000), (2_660_000, 600_000), (4_460_000, 939_000)]
    return [MesDeGrafica(date(2026, m, 1), c, g) for m, (c, g) in zip(range(6, 12), valores)]


def test_la_grafica_dibuja_las_mismas_barras_que_el_diseno():
    from config.piezas import grafica_barras

    svg = grafica_barras(_meses_del_diseno())
    diseno = (RAIZ / "diseno/hoy.html").read_text("utf-8")

    rects = re.findall(r'<rect x="\d+" y="\d+" width="22" height="\d+" rx="4" fill="#[0-9A-F]+"></rect>', svg)
    assert len(rects) == 12
    # diseno/hoy.html dibuja octubre y noviembre con los valores de los ejemplos
    assert '<rect x="532" y="12" width="22" height="112" rx="4" fill="#2563C9"></rect>' in svg
    assert '<rect x="532" y="12" width="22" height="112" rx="4" fill="#2563C9"></rect>' in diseno
    assert 'fill="#B5B5B5"' in svg and 'fill="#A6A6A6"' not in svg
    assert '<text x="0" y="78" font-size="11" fill="#616161">2 M</text>' in svg
    assert '<text x="0" y="28" font-size="11" fill="#616161">4 M</text>' in svg
    assert 'font-weight="650" text-anchor="middle" fill="#1A1A1A">nov</text>' in svg
    assert 'viewBox="0 0 600 160"' in svg
    assert 'aria-label="Barras de cobrado y gastado de junio a noviembre. En noviembre: cobrado 4,46 millones y gastado 0,94 millones."' in svg


def test_la_grafica_sin_plata_no_dibuja_barras():
    from pedidos.calculos import MesDeGrafica

    from config.piezas import grafica_barras

    svg = grafica_barras([MesDeGrafica(date(2026, m, 1), 0, 0) for m in range(6, 12)])

    assert "<rect" not in svg and "<svg" in svg


def test_la_grafica_con_poca_plata_marca_miles():
    from pedidos.calculos import MesDeGrafica

    from config.piezas import grafica_barras

    svg = grafica_barras([MesDeGrafica(date(2026, 11, 1), 900_000, 100_000)])

    assert ">500 mil</text>" in svg



def test_en_celular_los_textos_cortos_y_el_cambio_de_mes_se_ven():
    celular = _reglas_de_celular()
    for regla in (r"\.solo-computador \{ display: none !important; \}",
                  r"\.texto-celular \{ display: inline; \}", r"\.texto-computador \{ display: none; \}"):
        assert re.search(regla, celular), regla
    # Lo que es solo del celular no se ve en computador
    assert re.search(r"@media \(min-width: 768px\) \{\s*\.solo-celular \{ display: none !important; \}",
                     _css())


# --- Agregado al unir la tanda 5 -------------------------------------------------------------


def test_la_cifra_explica_de_donde_sale_al_pasar_el_mouse():
    html = Template('{% include "piezas/_cifra.html" with nombre="Cobrado" valor=2 url="/resumen/" '
                    'explica="Los abonos del mes" %}').render(Context())

    assert html.strip() == ('<a class="cifra" href="/resumen/" title="Los abonos del mes">'
                    '<span class="cifra__nombre">Cobrado</span><span class="cifra__valor">2</span></a>')
    # Con su explicación, el nombre va con subrayado punteado
    assert re.search(r"\.cifra\[title\] \.cifra__nombre \{\s*text-decoration: underline dotted", _css())


def test_la_insignia_lleva_su_tono_y_su_circulito():
    from pedidos.calculos import Etiqueta

    html = Template('{% include "piezas/_etiqueta.html" with insignia=e %}').render(
        Context({"e": Etiqueta("Abonado 50 %", "naranja", "medio")}))
    assert html.strip() == '<span class="etiqueta etiqueta--naranja etiqueta--medio">Abonado 50 %</span>'
    html = Template('{% include "piezas/_etiqueta.html" with texto="1 atrasado" tono="rojo" %}').render(Context())
    assert html.strip() == '<span class="etiqueta etiqueta--rojo">1 atrasado</span>'


def test_el_nombre_del_taller_en_el_menu_tiene_id_para_cambiarlo_sin_recargar(sesion_duena, taller):
    assert (f'<span class="menu__nombre" id="menu-taller" title="{taller.nombre}">'
            f'{taller.nombre}</span>') in sesion_duena.get("/").text


def test_el_formulario_publico_lleva_en_la_pestana_el_taller_del_pedido(sesion_duena, taller):
    from tests import fabricas

    otro = fabricas.crear_taller(nombre="Confecciones del enlace")
    pedido = fabricas.crear_pedido(otro)

    html = sesion_duena.get(f"/tallas/{pedido.token_tallas}/").text

    assert "· Confecciones del enlace</title>" in html
    assert f"· {taller.nombre}</title>" not in html


def test_la_ventana_puede_cambiar_cancelar_por_cerrar():
    from django.template import engines

    plantilla = engines["django"].from_string(
        '{% extends "piezas/ventana.html" %}{% block cerrar %}Cerrar{% endblock %}'
    )
    html = plantilla.render({"accion": "/x/"})

    assert "data-cerrar-ventana>Cerrar</button>" in html



def test_en_celular_las_entregas_del_calendario_son_barritas_sin_partir_nombres():
    regla = re.search(r"\.calendario__entregas \.etiqueta \{(.*?)\}", _reglas_de_celular(), re.DOTALL)
    assert regla and "font-size: 0;" in regla.group(1) and "height: 6px;" in regla.group(1)


# --- Revisión final (T23) -------------------------------------------------------------------


def _css():
    return (ESTATICOS / "css/app.css").read_text("utf-8")


def _js():
    return (ESTATICOS / "js/app.js").read_text("utf-8")


def test_en_celular_los_campos_y_el_buscador_se_tocan_como_los_botones():
    celular = _reglas_de_celular()
    assert re.search(r"\n  \.boton \{\s*min-height: 40px;", celular)
    assert re.search(r"\n  \.campo__control \{\s*min-height: 44px;", celular)
    assert re.search(r"\n  \.buscador \{\s*min-height: 44px;", celular)
    assert re.search(r"\.ventana__cerrar \{\s*width: 40px;\s*height: 40px;", celular)


def test_en_celular_lo_de_abajo_no_queda_detras_de_la_barra():
    assert "scroll-padding-bottom: calc(var(--alto-barra)" in _reglas_de_celular()


def test_la_barra_de_abajo_va_despues_del_contenido(sesion_duena):
    # Con el teclado, primero el contenido y después la barra (que se ve fija abajo).
    html = sesion_duena.get("/").text
    assert html.index("</main>") < html.index('<nav class="navegacion-celular"')


def test_un_nombre_de_taller_largo_se_corta_y_se_lee_entero_al_pasar_el_mouse(sesion_duena, taller):
    regla = re.search(r"\.menu__nombre \{(.*?)\}", _css(), re.DOTALL).group(1)
    assert "text-overflow: ellipsis;" in regla
    assert f'title="{taller.nombre}"' in sesion_duena.get("/").text


def test_en_celular_una_cifra_sola_al_final_va_a_lo_ancho():
    assert re.search(r"\.cifras > :last-child:nth-child\(odd\) \{\s*grid-column: 1 / -1;",
                     _reglas_de_celular())


def test_las_barras_proporcionales_van_a_lo_ancho_debajo_del_nombre():
    # "Quién te debe" y "Ventas por tipo de cliente": todas las barras empiezan en el mismo
    # lugar, debajo del nombre y su valor.
    assert re.search(r"\.fila-proporcion > \.proporcion \{\s*grid-column: 1 / -1;", _css())


def test_un_dia_con_entregas_pone_su_numero_arriba_como_los_demas():
    regla = re.search(r"\n\.calendario__dia \{(.*?)\}", _css(), re.DOTALL).group(1)
    assert "flex-direction: column;" in regla and "align-items: flex-start;" in regla


def test_en_computador_un_nombre_largo_en_el_calendario_se_corta_con_puntos():
    regla = re.search(r"\n\.calendario__entregas \.etiqueta \{(.*?)\}", _css(), re.DOTALL).group(1)
    assert "max-width: 100%;" in regla
    regla = re.search(r"\n\.etiqueta__texto \{(.*?)\}", _css(), re.DOTALL).group(1)
    assert "text-overflow: ellipsis;" in regla


def test_la_leyenda_del_calendario_baja_de_linea_si_no_cabe():
    regla = re.search(r"\n\.calendario__leyenda \{(.*?)\}", _css(), re.DOTALL).group(1)
    assert "flex-wrap: wrap;" in regla


def test_la_ventana_pone_el_cursor_en_el_primer_campo_con_error():
    js = _js()
    assert js.index('".campo--error .campo__control"') < js.index('"[autofocus]"')
    # Y no en la ficha CSRF escondida, que es el primer <input> del formulario.
    assert 'input:not([type=hidden])' in js


def test_un_boton_que_desaparece_dice_a_donde_va_el_cursor():
    assert "dataset.focoDespues" in _js()


def test_ver_todo_el_mes_devuelve_el_cursor_al_dia_elegido(sesion_duena, taller):
    from tests import fabricas

    pedido = fabricas.crear_pedido(taller)
    dia = pedido.fecha_entrega
    url = f"/calendario/?mes={dia:%Y-%m}&dia={dia:%Y-%m-%d}"
    html = sesion_duena.get(url, headers={"HX-Request": "true"}).text

    assert f'data-foco-despues="dia-{dia:%Y-%m-%d}">Ver todo el mes</a>' in html
    assert f'id="dia-{dia:%Y-%m-%d}"' in html


def test_el_historial_de_una_tela_se_cierra_con_cerrar(sesion_duena, taller):
    from tests import fabricas

    tela = fabricas.crear_tela(taller)
    html = sesion_duena.get(f"/telas/{tela.pk}/movimiento/", headers={"HX-Request": "true"}).text

    assert "data-cerrar-ventana>Cerrar</button>" in html
    assert ">Cancelar</button>" not in html


def test_cancelar_en_gastos_devuelve_el_cursor_al_boton_de_donde_se_vino(sesion_duena, taller):
    from django.urls import reverse

    from tests import fabricas

    gasto = fabricas.crear_gasto(taller)
    mes = f"{gasto.fecha:%Y-%m}"
    htmx = {"HX-Request": "true", "HX-Target": "gastos"}
    pregunta = sesion_duena.get(reverse("finanzas:gasto_quitar", args=[gasto.pk]), headers=htmx).text
    formulario = sesion_duena.get(f'{reverse("finanzas:gasto_nuevo")}?mes={mes}', headers=htmx).text
    tarjeta = sesion_duena.get(f"/resumen/?mes={mes}").text

    assert f'data-foco-despues="gasto-{gasto.pk}-quitar">Cancelar</a>' in pregunta
    assert 'data-foco-despues="gastos-registrar">Cancelar</a>' in formulario
    assert f'id="gasto-{gasto.pk}-quitar"' in tarjeta and 'id="gastos-registrar"' in tarjeta


def test_un_enlace_a_un_campo_plegado_lo_abre_y_deja_aire_arriba():
    # "Cobrar el saldo" o "Registrar abono" llevan a #registrar-abono: el enlace abre la parte
    # plegada (static/js/app.js) y el campo no queda pegado arriba de la hoja.
    assert 'destino.closest("details")' in _js()
    assert re.search(r"\.campo__control \{\s*scroll-margin-top: 48px;", _css())


# --- Tanda 7: el botón y el panel del asistente -------------------------------------------


@pytest.fixture
def asistente_prendido(settings, taller):
    settings.ANTHROPIC_API_KEY = "clave-de-prueba"
    taller.asistente_limite_mes = 600
    taller.asistente_limite_dia = 40
    taller.save()
    return taller


def _boton_asistente(html):
    return [e for e in Elementos(html).elementos if "data-asistente-abrir" in e["atributos"]]


def _panel_asistente(html):
    return [e for e in Elementos(html).elementos if e["atributos"].get("id") == "asistente"]


def test_el_asistente_no_sale_sin_clave_aunque_el_taller_lo_tenga(sesion_duena, settings, taller):
    taller.asistente_limite_mes, taller.asistente_limite_dia = 600, 40
    taller.save()
    settings.ANTHROPIC_API_KEY = ""

    html = sesion_duena.get("/").text

    assert not _boton_asistente(html) and not _panel_asistente(html)


def test_el_asistente_no_sale_si_el_taller_lo_tiene_apagado(sesion_duena, settings):
    settings.ANTHROPIC_API_KEY = "clave-de-prueba"

    html = sesion_duena.get("/").text

    assert not _boton_asistente(html) and not _panel_asistente(html)


def test_el_asistente_no_le_sale_a_la_costurera(client, costurera, asistente_prendido):
    client.force_login(costurera)

    html = client.get("/").text

    assert not _boton_asistente(html) and not _panel_asistente(html)


# Mi taller con el asistente prendido muestra el cupo (asistente.uso.cupo): la prueba el
# carril D (T34) en asistente/tests/test_uso.py.
@pytest.mark.parametrize(
    "direccion", ["/", "/pedidos/", "/calendario/", "/clientes/", "/cotizador/", "/telas/",
                  "/resumen/"],
)
def test_la_duena_ve_el_boton_en_cada_pantalla_y_el_panel_cerrado(
    sesion_duena, asistente_prendido, direccion
):
    html = sesion_duena.get(direccion).text
    boton, = _boton_asistente(html)
    panel, = _panel_asistente(html)

    assert boton["atributos"]["href"] == "/asistente/"
    assert boton["atributos"]["aria-controls"] == "asistente"
    assert boton["atributos"]["aria-expanded"] == "false"
    assert "Asistente" in boton["texto"]
    assert "hidden" in panel["atributos"]
    assert panel["atributos"]["hx-get"] == "/asistente/"
    assert panel["atributos"]["hx-trigger"] == "asistente-abrir once"


def test_el_boton_del_asistente_va_a_la_izquierda_del_principal(sesion_duena, asistente_prendido):
    for direccion in ("/", "/pedidos/"):
        html = sesion_duena.get(direccion).text
        acciones = html[html.index('class="encabezado__acciones"'):html.index("</header>")]

        assert acciones.index("data-asistente-abrir") < acciones.index("boton--principal")
    # Hoy: la fecha y la lupa del celular siguen antes; Resumen: "Excel" antes.
    hoy = sesion_duena.get("/").text
    assert hoy.index("encabezado__apoyo") < hoy.index("data-asistente-abrir")
    resumen = sesion_duena.get("/resumen/").text
    assert resumen.index("Descargar para Excel") < resumen.index("data-asistente-abrir")


def test_con_la_cookie_el_panel_sale_abierto_y_se_llena_al_cargar(
    sesion_duena, asistente_prendido
):
    sesion_duena.cookies["asistente"] = "abierto"

    html = sesion_duena.get("/").text
    boton, = _boton_asistente(html)
    panel, = _panel_asistente(html)

    assert "hidden" not in panel["atributos"]
    assert panel["atributos"]["hx-trigger"] == "load"
    assert boton["atributos"]["aria-expanded"] == "true"
    assert "es-presionado" in boton["clases"]


def test_el_panel_va_al_lado_de_la_hoja_dentro_del_marco(sesion_duena, asistente_prendido):
    html = sesion_duena.get("/").text

    assert html.index('<main class="hoja') < html.index('id="asistente"') < html.index(
        "navegacion-celular"
    )


def test_el_javascript_del_asistente_tiene_su_atajo_y_sus_piezas():
    js = (ESTATICOS / "js/app.js").read_text("utf-8")
    seccion = js[js.index("/* 14. Asistente"):]

    assert 'evento.key.toLowerCase() === "j"' in seccion
    for pieza in ("[data-asistente-abrir]", "[data-asistente-cerrar]", "[data-asistente-form]",
                  "[data-asistente-sugerencia]", "#asistente-pendiente", "Revisando tus datos…",
                  "asistente=abierto"):
        assert pieza in seccion
    # La burbuja se escribe como texto, nunca como HTML.
    assert "innerHTML" not in seccion
    assert "texto.textContent = pregunta" in seccion


def test_el_panel_del_asistente_entra_y_sale_con_movimiento():
    # Pedido de David (2026-11-15): el panel salía "muy crudo".
    js = (ESTATICOS / "js/app.js").read_text("utf-8")
    seccion = js[js.index("/* 14. Asistente"):]
    css = (ESTATICOS / "css/app.css").read_text("utf-8")

    # Después: "se ve mal cuando la página se contrae". Desde 768 px el panel flota encima de
    # la hoja, que no cambia de ancho ni pasa sus columnas a una; el panel solo se desliza.
    assert "/* Computador y pantallas medianas: el panel flota encima de la hoja" in css
    assert "@media (min-width: 768px) {\n  .asistente {\n    position: absolute;" in css
    assert ".asistente:not([hidden])" not in css
    assert "startViewTransition" not in seccion and "view-transition-name: hoja" not in css
    assert ".asistente.entra {\n  animation: asistente-llega var(--duracion-larga) var(--curva);" in css
    assert ".asistente.se-cierra {\n  animation: asistente-se-va var(--duracion) var(--curva-salida) forwards;" in css
    assert "from { transform: translateX(calc(100% + 8px)); }" in css
    # Sin movimiento pedido, cambia de una vez; un movimiento viejo no deshace uno nuevo.
    assert "hayMovimiento()" in seccion and "numero !== movimientoAsistente" in seccion


def test_los_iconos_del_asistente_estan_guardados():
    iconos = (ESTATICOS / "iconos/iconos.svg").read_text("utf-8")

    assert '<symbol id="enviar"' in iconos


def test_con_el_asistente_la_caja_de_hoy_le_pregunta(sesion_duena, asistente_prendido):
    html = sesion_duena.get("/").text
    elementos = Elementos(html).elementos
    caja, = [e for e in elementos if "data-asistente-caja" in e["atributos"]]
    texto, = [e for e in elementos if e["atributos"].get("id") == "hoy-pregunta"]

    assert "caja-grande--asistente" in caja["clases"]
    assert caja["atributos"]["action"] == "/asistente/"
    assert texto["etiqueta"] == "textarea"
    assert texto["atributos"]["placeholder"] == "Pregúntale algo a tu asistente"
    assert texto["atributos"]["maxlength"] == "500"
    assert any("avatar-asistente" in e["clases"] for e in elementos)
    # Los atajos de siempre siguen, y el buscador de la caja ya no está.
    for atajo in ("Nuevo pedido", "Registrar abono", "Cotizar"):
        assert atajo in caja["texto"]
    assert 'placeholder="Busca un pedido o un cliente"' not in html


def test_sin_el_asistente_la_caja_de_hoy_sigue_buscando(sesion_duena):
    html = sesion_duena.get("/").text

    assert 'placeholder="Busca un pedido o un cliente"' in html
    assert "data-asistente-caja" not in html


def test_la_caja_de_hoy_abre_el_panel_y_pregunta_desde_alla():
    js = (ESTATICOS / "js/app.js").read_text("utf-8")
    seccion = js[js.index("/* 14. Asistente"):]

    assert "[data-asistente-caja]" in seccion
    assert "preguntaEnEspera" in seccion and "formulario.requestSubmit()" in seccion


def test_el_icono_del_asistente_es_la_esfera_de_lucy(sesion_duena, asistente_prendido):
    # Pedido de David (2026-11-15): la esfera azul de Lucy reemplaza al botón con carita.
    html = sesion_duena.get("/").text
    elementos = Elementos(html).elementos
    esferas = [e for e in elementos if "data-esfera" in e["atributos"]]
    boton = html[html.index("data-asistente-abrir"):]
    boton = boton[:boton.index("</a>")]

    # En el botón del encabezado (20 px en celular, 16 px en computador) y en la caja de Hoy.
    assert 'class="esfera esfera--boton"' in boton and 'class="esfera esfera--chica"' in boton
    assert all(e["atributos"]["aria-hidden"] == "true" for e in esferas)
    # La de la caja de Hoy se mueve (pedido de David); las del botón quedan quietas.
    vivas = [e for e in esferas if "data-esfera-viva" in e["atributos"]]
    assert len(vivas) == 1 and "avatar-asistente" in vivas[0]["clases"]
    assert 'data-esfera-viva' not in boton
    assert '<script src="/static/js/esfera.js" defer></script>' in html
    # El botón con carita ya no está en el juego de íconos.
    iconos = (ESTATICOS / "iconos/iconos.svg").read_text("utf-8")
    assert 'id="asistente"' not in iconos and 'id="asistente-cara"' not in iconos


def test_la_esfera_se_dibuja_aqui_sin_nada_de_afuera():
    js = (ESTATICOS / "js/esfera.js").read_text("utf-8")
    css = (ESTATICOS / "css/app.css").read_text("utf-8")

    assert "http" not in js and "fetch(" not in js
    # Se detiene si no se ve o si la persona pidió menos movimiento.
    assert "prefers-reduced-motion: reduce" in js and "document.hidden" in js
    # Late mientras app.js muestra los tres puntos (#asistente-pendiente).
    assert 'getElementById("asistente-pendiente")' in js and "esfera--atendiendo" in js
    esfera = re.search(r"\n\.esfera \{(.*?)\}", css, re.DOTALL).group(1)
    assert "background: #1463FF;" in esfera and "border-radius: 50%;" in esfera
