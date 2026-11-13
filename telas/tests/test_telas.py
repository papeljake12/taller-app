"""T16. Telas: la pantalla, "Entró" y "Usé" con su historial, agregar y quitar una tela."""

import re
from datetime import date, datetime
from decimal import Decimal
from zoneinfo import ZoneInfo

import pytest
from django.urls import reverse

from pedidos import ejemplos
from telas.formularios import MENSAJE_NOMBRE_REPETIDO, leer_metros
from telas.models import MovimientoTela, Tela
from telas.vistas import nombres_juntos
from tests import fabricas

pytestmark = pytest.mark.django_db

URL = "/telas/"
# Así llega una acción hecha desde la pantalla Telas, con JavaScript.
HTMX = {"HX-Request": "true", "HX-Target": "ventana", "HX-Current-URL": f"http://testserver{URL}"}
BOGOTA = ZoneInfo("America/Bogota")


def url_movimiento(tela, tipo=None):
    url = reverse("telas:movimiento", args=[tela.pk])
    return f"{url}?tipo={tipo}" if tipo else url


def url_quitar(tela):
    return reverse("telas:quitar", args=[tela.pk])


def filas(html):
    """Los nombres de las telas de la tabla, en orden."""
    return re.findall(r'ver el historial"><strong>([^<]+)</strong>', html)


def fila(html, nombre):
    """El html de la fila de una tela."""
    inicio = html.index(f"<strong>{nombre}</strong>")
    return html[inicio:html.index("</tr>", inicio)]


def entrada(html, nombre):
    return re.search(rf'<input[^>]*name="{nombre}"[^>]*>', html).group(0)


@pytest.fixture
def pique(taller):
    return fabricas.crear_tela(taller, nombre="Piqué blanco", metros=Decimal("6"),
                               minimo=Decimal("10"))


def mover(sesion, tela, tipo, metros, headers=HTMX):
    return sesion.post(url_movimiento(tela), {"tipo": tipo, "metros": metros}, headers=headers)


# --- La pantalla ---------------------------------------------------------------------------


def test_la_pantalla_sale_como_el_diseno(client):
    taller = ejemplos.cargar(hoy=date(2026, 11, 11), con_fotos=False)
    client.force_login(taller.usuarias.filter(rol="duena").first())

    respuesta = client.get(URL)

    assert respuesta.status_code == 200
    html = respuesta.text
    assert '<span class="encabezado__apoyo" id="telas-apoyo">4 telas, 60 m en total</span>' in html
    assert f'hx-get="{reverse("telas:nueva")}" hx-target="#ventana">Nueva tela</a>' in html
    inicio = html.index('id="telas-cifras"')
    cifras = html[inicio:html.index("</section>", inicio)]
    assert re.search(r"Telas</div>\s*<div class=\"cifra__valor\">4</div>\s*"
                     r"<div class=\"cifra__apoyo\">En inventario", cifras)
    assert re.search(r"Metros en total</div>\s*<div class=\"cifra__valor\">60 m</div>\s*"
                     r"<div class=\"cifra__apoyo\">Suma de todas", cifras)
    assert re.search(r'<div class="tarjeta cifra cifra--alerta">\s*<div class="cifra__nombre">'
                     r"Se están acabando</div>\s*<div class=\"cifra__valor\">2</div>\s*"
                     r'<div class="cifra__apoyo">Piqué blanco y popelina blanca</div>', cifras)
    for titulo in ("Tela", "Quedan", "Avisar cuando queden", "Estado", "Acción"):
        assert f">{titulo}</th>" in html
    # Primero las que se están acabando y después por nombre (calculos.telas_en_orden).
    assert filas(html) == ["Piqué blanco", "Popelina blanca", "Dril azul",
                           "Tela estampada para polleras"]
    pique = fila(html, "Piqué blanco")
    assert '<strong class="texto-rojo">6 m</strong>' in pique
    assert '<td class="num">10 m</td>' in pique
    assert '<span class="etiqueta etiqueta--ambar">Se está acabando</span>' in pique
    assert ">Entró</a>" in pique and ">Usé</a>" in pique
    dril = fila(html, "Dril azul")
    assert "<strong>18 m</strong>" in dril
    assert '<span class="etiqueta etiqueta--verde">Suficiente</span>' in dril


def test_cada_tela_abre_su_historial_y_sus_ventanas(sesion_duena, pique):
    html = sesion_duena.get(URL).text

    url = url_movimiento(pique)
    assert f'href="{url}" hx-get="{url}" hx-target="#ventana"' in html
    for tipo in ("entro", "uso"):
        assert f'hx-get="{url_movimiento(pique, tipo)}" hx-target="#ventana"' in html


def test_sin_telas_invita_a_anotar_la_primera(sesion_duena):
    html = sesion_duena.get(URL).text

    assert "0 telas, 0 m en total" in html
    assert "Todavía no has anotado ninguna tela" in html
    assert "<table" not in html
    assert "cifra--alerta" not in html
    assert "Ninguna por ahora" in html


def test_una_sola_tela_va_en_singular(sesion_duena, taller):
    fabricas.crear_tela(taller, nombre="Lino", metros=Decimal("6.5"))

    assert "1 tela, 6,5 m en total" in sesion_duena.get(URL).text


def test_sin_aviso_solo_hay_dos_estados(sesion_duena, taller):
    """docs/03-pantallas.md: "Se está acabando" o "Suficiente", nada más. Sin aviso, aunque
    no le queden metros, dice "Suficiente"."""
    fabricas.crear_tela(taller, nombre="Lino", metros=0, minimo=0)
    fabricas.crear_tela(taller, nombre="Seda", metros=3, minimo=0)

    html = sesion_duena.get(URL).text

    lino = fila(html, "Lino")
    assert '<span class="texto-2">Sin aviso</span>' in lino
    assert '<span class="etiqueta etiqueta--verde">Suficiente</span>' in lino
    assert '<span class="etiqueta etiqueta--verde">Suficiente</span>' in fila(html, "Seda")
    assert "Se acabó" not in html
    # Sin aviso, ninguna "se está acabando".
    assert "cifra--alerta" not in html


def test_no_muestra_las_telas_de_otro_taller(sesion_duena, pique):
    otro = fabricas.crear_taller()
    fabricas.crear_tela(otro, nombre="Tela ajena", metros=100, minimo=200)

    html = sesion_duena.get(URL).text

    assert "Tela ajena" not in html
    assert "1 tela, 6 m en total" in html
    assert re.search(r'cifra__valor">1</div>\s*<div class="cifra__apoyo">Piqué blanco</div>', html)


def test_los_nombres_que_se_acaban_van_juntos_como_en_el_diseno():
    def telas(*nombres):
        return [Tela(nombre=n) for n in nombres]

    assert nombres_juntos([]) == ""
    assert nombres_juntos(telas("Piqué blanco")) == "Piqué blanco"
    assert nombres_juntos(telas("Piqué blanco", "Popelina blanca")) == (
        "Piqué blanco y popelina blanca"
    )
    assert nombres_juntos(telas("Dril", "Lino", "Seda")) == "Dril, lino y seda"


# --- Leer los metros ------------------------------------------------------------------------


@pytest.mark.parametrize("texto, metros", [
    ("2,5", Decimal("2.5")), ("2.5", Decimal("2.5")), ("18", Decimal("18")),
    (" 6 m ", Decimal("6")), ("6m", Decimal("6")), ("0,25", Decimal("0.25")),
])
def test_lee_los_metros_con_coma_o_con_punto(texto, metros):
    assert leer_metros(texto) == metros


@pytest.mark.parametrize("texto", ["", "abc", "-2", "1.000", "2,555", "2,5,1", "١٢", "2 5"])
def test_no_lee_lo_que_no_son_metros(texto):
    assert leer_metros(texto) is None


# --- Entró y Usé ------------------------------------------------------------------------------


def test_entro_abre_la_ventana_que_pregunta_cuantos_metros(sesion_duena, pique):
    respuesta = sesion_duena.get(url_movimiento(pique, "entro"), headers=HTMX)

    assert respuesta.status_code == 200
    html = respuesta.text
    assert "<html" not in html
    assert "Entró: Piqué blanco" in html
    assert "¿Cuántos metros entraron?" in html
    assert '<input type="hidden" name="tipo" value="entro">' in html
    assert "Quedan <strong>6 m</strong>. Avisa cuando queden 10 m o menos." in html
    assert "autofocus" in entrada(html, "metros")
    assert 'inputmode="decimal"' in entrada(html, "metros")
    assert f'hx-post="{url_movimiento(pique)}"' in html
    assert ">Sumar metros</button>" in html


def test_use_abre_la_ventana_que_pregunta_cuantos_metros_se_usaron(sesion_duena, pique):
    html = sesion_duena.get(url_movimiento(pique, "uso"), headers=HTMX).text

    assert "Usé: Piqué blanco" in html
    assert "¿Cuántos metros usaste?" in html
    assert '<input type="hidden" name="tipo" value="uso">' in html
    assert ">Restar metros</button>" in html


def test_sin_javascript_entro_abre_una_pagina(sesion_duena, pique):
    respuesta = sesion_duena.get(url_movimiento(pique, "entro"))

    assert respuesta.status_code == 200
    assert "<html" in respuesta.text and "ventana--pagina" in respuesta.text
    assert f'action="{url_movimiento(pique)}"' in respuesta.text


def test_entro_suma_los_metros_y_lo_anota_en_el_historial(sesion_duena, duena, pique):
    respuesta = mover(sesion_duena, pique, "entro", "2,5")

    assert respuesta.status_code == 200
    pique.refresh_from_db()
    assert pique.metros == Decimal("8.5")
    movimiento = MovimientoTela.objects.get(tela=pique)
    assert movimiento.metros == Decimal("2.5")
    assert movimiento.usuario == duena


def test_use_resta_los_metros_y_lo_anota_en_negativo(sesion_duena, duena, pique):
    respuesta = mover(sesion_duena, pique, "uso", "2.5")

    assert respuesta.status_code == 200
    pique.refresh_from_db()
    assert pique.metros == Decimal("3.5")
    movimiento = MovimientoTela.objects.get(tela=pique)
    assert movimiento.metros == Decimal("-2.5")
    assert movimiento.usuario == duena


def test_se_puede_usar_todo_lo_que_queda(sesion_duena, pique):
    assert mover(sesion_duena, pique, "uso", "6").status_code == 200

    pique.refresh_from_db()
    assert pique.metros == 0


def test_usar_mas_de_lo_que_queda_lo_dice_y_no_guarda(sesion_duena, pique):
    respuesta = mover(sesion_duena, pique, "uso", "6,5")

    assert respuesta.status_code == 422
    assert "Solo quedan 6 m de esta tela: no puedes usar más de eso." in respuesta.text
    assert "Usé: Piqué blanco" in respuesta.text
    pique.refresh_from_db()
    assert pique.metros == Decimal("6")
    assert not MovimientoTela.objects.exists()


def test_al_guardar_cierra_la_ventana_y_trae_la_tabla_las_cifras_y_el_apoyo(sesion_duena, pique):
    respuesta = mover(sesion_duena, pique, "entro", "10")

    assert respuesta.headers["HX-Retarget"] == "#telas"
    assert respuesta.headers["HX-Reswap"] == "outerHTML"
    html = respuesta.text
    assert html.startswith('<section class="tarjeta tarjeta--lista" id="telas"')
    # Con 16 m ya no se está acabando.
    assert '<span class="etiqueta etiqueta--verde">Suficiente</span>' in fila(html, "Piqué blanco")
    cifras = re.search(r'<section class="cifras" id="telas-cifras"[^>]*>', html).group(0)
    assert 'hx-swap-oob="true"' in cifras
    assert ('<span class="encabezado__apoyo" id="telas-apoyo" hx-swap-oob="true">'
            "1 tela, 16 m en total</span>") in html
    assert "Ninguna por ahora" in html
    assert ('<dialog class="ventana" id="ventana" aria-label="Ventana" hx-swap-oob="true">'
            "</dialog>") in html


def menu_lateral(html):
    """El menú lateral que llega aparte (hx-swap-oob) después de una acción."""
    marca = '<div hx-swap-oob="innerHTML:.menu__lista">'
    assert html.count(marca) == 1
    inicio = html.index(marca)
    return html[inicio:html.index("</div>", inicio)]


def contador_de_telas(menu):
    entrada = re.search(r'<a class="menu__enlace[^"]*" href="/telas/".*?</a>', menu).group(0)
    contador = re.search(r'<span class="menu__contador">(\d+)</span>', entrada)
    return int(contador.group(1)) if contador else 0


def test_al_guardar_el_contador_del_menu_cambia_sin_recargar(sesion_duena, taller):
    dril = fabricas.crear_tela(taller, nombre="Dril azul", metros=18, minimo=10)
    assert contador_de_telas(sesion_duena.get(URL).text) == 0

    # Usé 9 m: quedan 9 y el aviso es en 10, así que ya se está acabando.
    menu = menu_lateral(mover(sesion_duena, dril, "uso", "9").text)

    assert contador_de_telas(menu) == 1
    # Telas sigue resaltada como la sección actual.
    assert re.search(r'class="menu__enlace es-actual" href="/telas/" data-nombre="Telas"', menu)
    assert menu.count('aria-current="page"') == 1

    # Entró 5 m: ya no se está acabando y el contador se va.
    assert contador_de_telas(menu_lateral(mover(sesion_duena, dril, "entro", "5").text)) == 0


def test_nueva_y_quitar_tambien_cambian_el_contador_del_menu(sesion_duena):
    html = sesion_duena.post(reverse("telas:nueva"),
                             {"nombre": "Lino", "metros": "2", "minimo": "8"}, headers=HTMX).text
    assert contador_de_telas(menu_lateral(html)) == 1

    lino = Tela.objects.get(nombre="Lino")
    html = sesion_duena.post(url_quitar(lino), headers=HTMX).text
    assert contador_de_telas(menu_lateral(html)) == 0


def test_al_guardar_el_cursor_vuelve_al_boton_que_se_uso(sesion_duena, taller, pique):
    fabricas.crear_tela(taller, nombre="Dril azul", metros=18, minimo=10)

    html = mover(sesion_duena, pique, "uso", "1").text

    assert html.count("autofocus") == 1
    assert 'aria-label="Usé Piqué blanco" autofocus>Usé</a>' in html
    # La pantalla completa no pone el cursor en ningún botón.
    assert "autofocus" not in sesion_duena.get(URL).text


def test_sin_javascript_al_guardar_vuelve_a_telas(sesion_duena, pique):
    respuesta = mover(sesion_duena, pique, "entro", "1", headers={})

    assert respuesta.status_code == 302
    assert respuesta.url == URL
    pique.refresh_from_db()
    assert pique.metros == Decimal("7")


def test_desde_otra_pagina_al_guardar_lleva_a_telas(sesion_duena, pique):
    """La ventana abierta como página aparte, con JavaScript: no hay tabla que cambiar."""
    headers = {**HTMX, "HX-Current-URL": f"http://testserver{url_movimiento(pique, 'uso')}"}

    respuesta = mover(sesion_duena, pique, "uso", "1", headers=headers)

    assert respuesta.status_code == 200
    assert respuesta.headers["HX-Redirect"] == URL
    pique.refresh_from_db()
    assert pique.metros == Decimal("5")


@pytest.mark.parametrize("tipo, metros, mensaje", [
    ("entro", "", "Escribe cuántos metros entraron."),
    ("uso", "", "Escribe cuántos metros usaste."),
    ("uso", "dos", "Escribe solo los metros, por ejemplo 2,5."),
    ("entro", "1.000", "Escribe solo los metros, por ejemplo 2,5."),
    ("entro", "-2", "Escribe solo los metros, por ejemplo 2,5."),
    ("uso", "0", "Los metros deben ser más que 0."),
    ("entro", "0,00", "Los metros deben ser más que 0."),
    ("entro", "20000", "Revisa los metros: son demasiados."),
])
def test_rechaza_metros_que_no_sirven(sesion_duena, pique, tipo, metros, mensaje):
    respuesta = mover(sesion_duena, pique, tipo, metros)

    assert respuesta.status_code == 422
    assert mensaje in respuesta.text
    pique.refresh_from_db()
    assert pique.metros == Decimal("6")
    assert not MovimientoTela.objects.exists()


def test_la_tela_no_pasa_de_lo_que_cabe(sesion_duena, taller):
    llena = fabricas.crear_tela(taller, nombre="Llena", metros=Decimal("995000"))

    respuesta = mover(sesion_duena, llena, "entro", "9000")

    assert respuesta.status_code == 422
    assert "Revisa los metros: son demasiados." in respuesta.text
    llena.refresh_from_db()
    assert llena.metros == Decimal("995000")


def test_sin_decir_si_entro_o_se_uso_no_cambia_nada(sesion_duena, pique):
    respuesta = mover(sesion_duena, pique, "regalo", "2")

    assert respuesta.status_code == 400
    pique.refresh_from_db()
    assert pique.metros == Decimal("6")
    assert not MovimientoTela.objects.exists()


def test_la_tela_de_otro_taller_no_se_toca(sesion_duena):
    ajena = fabricas.crear_tela(fabricas.crear_taller(), metros=Decimal("10"))

    for tipo in ("entro", "uso"):
        assert sesion_duena.get(url_movimiento(ajena, tipo), headers=HTMX).status_code == 404
        assert mover(sesion_duena, ajena, tipo, "2").status_code == 404
    assert sesion_duena.get(url_movimiento(ajena), headers=HTMX).status_code == 404
    ajena.refresh_from_db()
    assert ajena.metros == Decimal("10")
    assert not MovimientoTela.objects.exists()


# --- Historial ------------------------------------------------------------------------------


def test_el_historial_muestra_cada_movimiento_del_mas_nuevo_al_mas_viejo(
    sesion_duena, taller, pique
):
    costurera = fabricas.crear_usuaria(taller, rol="costurera", nombre_visible="Luz")
    fabricas.crear_movimiento(pique, metros=Decimal("10"),
                              fecha=datetime(2026, 11, 2, 9, 0, tzinfo=BOGOTA))
    fabricas.crear_movimiento(pique, metros=Decimal("-4"), usuario=costurera,
                              fecha=datetime(2026, 11, 9, 15, 30, tzinfo=BOGOTA))

    respuesta = sesion_duena.get(url_movimiento(pique), headers=HTMX)

    assert respuesta.status_code == 200
    html = respuesta.text
    assert "<h2 id=\"ventana-titulo\">Piqué blanco</h2>" in html
    assert "Quedan <strong>6 m</strong>. Avisa cuando queden 10 m o menos." in html
    assert "9 de nov, 3:30 p.m., Luz" in html
    assert "<strong>-4 m</strong>" in html
    assert "2 de nov, 9:00 a.m." in html and "<strong>+10 m</strong>" in html
    assert html.index("9 de nov") < html.index("2 de nov")
    assert html.index("Usé<br>") < html.index("Entró<br>")
    assert f'hx-get="{url_quitar(pique)}" hx-target="#ventana">Quitar tela</a>' in html


def test_el_historial_vacio_lo_dice(sesion_duena, taller):
    lino = fabricas.crear_tela(taller, nombre="Lino", metros=0, minimo=0)

    html = sesion_duena.get(url_movimiento(lino), headers=HTMX).text

    assert "Todavía no hay movimientos de esta tela." in html
    assert "Sin aviso." in html


def test_el_historial_solo_muestra_los_ultimos_30(sesion_duena, pique):
    for _ in range(31):
        fabricas.crear_movimiento(pique, metros=1)

    html = sesion_duena.get(url_movimiento(pique), headers=HTMX).text

    assert html.count('<div class="renglon">') == 30
    assert "Se ven los últimos 30 movimientos." in html


def test_cada_movimiento_queda_en_el_historial(sesion_duena, pique):
    mover(sesion_duena, pique, "entro", "4")
    mover(sesion_duena, pique, "uso", "1,5")

    html = sesion_duena.get(url_movimiento(pique), headers=HTMX).text

    assert "<strong>+4 m</strong>" in html and "<strong>-1,5 m</strong>" in html
    assert "Quedan <strong>8,5 m</strong>" in html


# --- Nueva tela -----------------------------------------------------------------------------


def test_nueva_tela_abre_la_ventana_con_sus_campos(sesion_duena):
    respuesta = sesion_duena.get(reverse("telas:nueva"), headers=HTMX)

    assert respuesta.status_code == 200
    html = respuesta.text
    assert "<html" not in html and "Nueva tela" in html
    assert ">Tela</label>" in html and 'placeholder="Ej.: Dril azul"' in html
    assert ">Metros que tienes</label>" in html
    assert ">Avisarme cuando queden (metros)</label>" in html
    assert "autofocus" in entrada(html, "nombre")
    assert ">Agregar tela</button>" in html


def test_agregar_una_tela_la_guarda_con_su_primer_movimiento(sesion_duena, taller, duena):
    respuesta = sesion_duena.post(
        reverse("telas:nueva"),
        {"nombre": "  Lino   crudo ", "metros": "7,5", "minimo": "8"},
        headers=HTMX,
    )

    assert respuesta.status_code == 200
    tela = Tela.objects.get()
    assert tela.taller == taller
    assert tela.nombre == "Lino crudo"
    assert tela.metros == Decimal("7.5")
    assert tela.minimo == Decimal("8")
    movimiento = MovimientoTela.objects.get()
    assert movimiento.tela == tela and movimiento.metros == Decimal("7.5")
    assert movimiento.usuario == duena
    # La ventana se cierra y la tela aparece en la tabla, que dice que se está acabando.
    assert respuesta.headers["HX-Retarget"] == "#telas"
    assert "Se está acabando" in fila(respuesta.text, "Lino crudo")
    assert "1 tela, 7,5 m en total" in respuesta.text


def test_una_tela_sin_metros_no_anota_movimiento(sesion_duena):
    respuesta = sesion_duena.post(
        reverse("telas:nueva"), {"nombre": "Seda", "metros": "", "minimo": ""}, headers=HTMX
    )

    assert respuesta.status_code == 200
    tela = Tela.objects.get()
    assert tela.metros == 0 and tela.minimo == 0
    assert not MovimientoTela.objects.exists()


def test_sin_javascript_agregar_vuelve_a_telas(sesion_duena):
    respuesta = sesion_duena.post(reverse("telas:nueva"), {"nombre": "Seda", "metros": "3"})

    assert respuesta.status_code == 302
    assert respuesta.url == URL
    assert Tela.objects.filter(nombre="Seda").exists()


def test_el_taller_de_la_tela_nunca_llega_del_formulario(sesion_duena, taller):
    otro = fabricas.crear_taller()

    sesion_duena.post(reverse("telas:nueva"), {"nombre": "Seda", "taller": otro.pk},
                      headers=HTMX)

    assert Tela.objects.get().taller == taller


METROS_QUE_NO_SIRVEN = "Escribe solo los metros que tienes, por ejemplo 18 o 6,5."


@pytest.mark.parametrize("datos, mensaje", [
    ({"nombre": ""}, "Escribe el nombre de la tela."),
    ({"nombre": "   "}, "Escribe el nombre de la tela."),
    ({"nombre": "x" * 61}, "Escribe máximo 60 letras en el nombre."),
    ({"nombre": "Seda", "metros": "mucho"}, METROS_QUE_NO_SIRVEN),
    ({"nombre": "Seda", "metros": "-3"}, METROS_QUE_NO_SIRVEN),
    ({"nombre": "Seda", "minimo": "diez"}, "Escribe solo los metros, por ejemplo 10."),
    ({"nombre": "Seda", "metros": "50000"}, "Revisa los metros: son demasiados."),
])
def test_nueva_tela_rechaza_lo_que_no_sirve(sesion_duena, datos, mensaje):
    respuesta = sesion_duena.post(reverse("telas:nueva"), datos, headers=HTMX)

    assert respuesta.status_code == 422
    assert mensaje in respuesta.text
    assert not Tela.objects.exists()


def test_no_se_repite_el_nombre_de_una_tela(sesion_duena, pique):
    respuesta = sesion_duena.post(reverse("telas:nueva"), {"nombre": "pique BLANCO"},
                                  headers=HTMX)

    assert respuesta.status_code == 422
    assert MENSAJE_NOMBRE_REPETIDO in respuesta.text
    assert "autofocus" in entrada(respuesta.text, "nombre")
    assert Tela.objects.count() == 1


def test_el_mismo_nombre_en_otro_taller_si_se_puede(sesion_duena, taller):
    fabricas.crear_tela(fabricas.crear_taller(), nombre="Seda")

    respuesta = sesion_duena.post(reverse("telas:nueva"), {"nombre": "Seda"}, headers=HTMX)

    assert respuesta.status_code == 200
    assert Tela.objects.filter(taller=taller, nombre="Seda").exists()


# --- Quitar ---------------------------------------------------------------------------------


def test_quitar_pregunta_primero(sesion_duena, pique):
    fabricas.crear_movimiento(pique, metros=6)

    respuesta = sesion_duena.get(url_quitar(pique), headers=HTMX)

    assert respuesta.status_code == 200
    html = respuesta.text
    assert "Quitar tela" in html
    assert ("¿Quitar la tela «Piqué blanco»? Quedan 6 m. También se borra su historial "
            "(1 movimiento).") in html
    assert f'hx-post="{url_quitar(pique)}"' in html
    assert ">Sí, quitar la tela</button>" in html
    assert Tela.objects.filter(pk=pique.pk).exists()


def test_quitar_borra_la_tela_y_su_historial(sesion_duena, taller, pique):
    fabricas.crear_movimiento(pique, metros=6)
    dril = fabricas.crear_tela(taller, nombre="Dril azul", metros=18)
    fabricas.crear_movimiento(dril, metros=18)

    respuesta = sesion_duena.post(url_quitar(pique), headers=HTMX)

    assert respuesta.status_code == 200
    assert not Tela.objects.filter(pk=pique.pk).exists()
    assert list(MovimientoTela.objects.values_list("tela", flat=True)) == [dril.pk]
    assert respuesta.headers["HX-Retarget"] == "#telas"
    assert "Piqué blanco" not in respuesta.text
    assert "1 tela, 18 m en total" in respuesta.text


def test_sin_javascript_quitar_vuelve_a_telas(sesion_duena, pique):
    pagina = sesion_duena.get(url_quitar(pique))
    assert "<html" in pagina.text and "Sí, quitar la tela" in pagina.text

    respuesta = sesion_duena.post(url_quitar(pique))

    assert respuesta.status_code == 302
    assert respuesta.url == URL
    assert not Tela.objects.exists()


def test_no_se_puede_quitar_la_tela_de_otro_taller(sesion_duena):
    ajena = fabricas.crear_tela(fabricas.crear_taller())
    fabricas.crear_movimiento(ajena)

    assert sesion_duena.get(url_quitar(ajena), headers=HTMX).status_code == 404
    assert sesion_duena.post(url_quitar(ajena), headers=HTMX).status_code == 404
    assert Tela.objects.filter(pk=ajena.pk).exists()
    assert MovimientoTela.objects.filter(tela=ajena).exists()
