"""Calendario (T14): el mes con las entregas marcadas, la lista de entregas (con el filtro
por día) y la semana más cargada. Al final, la pantalla fija en computador y lo que necesitan
las animaciones (ajuste "pantalla fija y animaciones")."""

import re
from datetime import date, timedelta

import pytest
from django.test import Client
from django.urls import reverse
from django.utils import timezone

from pedidos import ejemplos
from pedidos.models import Pedido
from pedidos.vistas import calendario as vista
from tests import fabricas

pytestmark = pytest.mark.django_db

HOY = date(2026, 11, 11)  # el miércoles de diseno/calendario.html
PAGINA = reverse("pedidos:calendario")
HTMX = {"HX-Request": "true"}
Estado = Pedido.Estado


@pytest.fixture(autouse=True)
def dia_fijo(monkeypatch):
    """Hoy es siempre HOY, para que las pruebas no dependan del día en que se corren."""
    original = timezone.localdate

    def localdate(value=None, timezone=None):
        return HOY if value is None else original(value, timezone)

    monkeypatch.setattr("django.utils.timezone.localdate", localdate)


@pytest.fixture
def ejemplo(taller, duena):
    """Los pedidos de diseno/calendario.html, contados desde HOY."""
    return ejemplos.cargar(taller=taller, hoy=HOY, con_fotos=False)


def pedido_de(taller, cliente=None, **campos):
    """Un pedido del taller con su cliente (si no se dice, uno nuevo). Por defecto, en
    confección."""
    campos.setdefault("estado", Estado.CONFECCION)
    cliente = fabricas.crear_cliente(taller, nombre=cliente)
    return fabricas.crear_pedido(taller, cliente=cliente, **campos)


def url(mes=None, dia=None):
    parametros = [f"mes={mes}"] if mes is not None else []
    if dia is not None:
        parametros.append(f"dia={dia}")
    return f"{PAGINA}?{'&'.join(parametros)}" if parametros else PAGINA


def tarjeta(html, id_titulo):
    """La tarjeta cuyo título tiene ese id, hasta su </section>."""
    return re.search(rf'<section[^>]*aria-labelledby="{id_titulo}".*?</section>', html, re.S).group(0)


def cuadricula(html):
    return re.search(r'<div class="calendario" id="calendario-dias".*?\n</div>', html, re.S).group(0)


def celda(html, dia):
    """La celda del día (de un número) dentro del mes: su botón o su <div>."""
    for encontrado in re.finditer(r'<(button|div) [^>]*class="calendario__dia[^"]*"[^>]*>.*?</\1>',
                                  cuadricula(html), re.S):
        trozo = encontrado.group(0)
        if f'<span class="calendario__numero">{dia}</span>' in trozo and "--fuera" not in trozo:
            return trozo
    raise AssertionError(f"No está el día {dia}")


def filas_de_la_lista(html):
    """(fecha, cliente, etiqueta) de cada entrega de la lista, en orden."""
    return re.findall(
        r'<strong>([^<]+)</strong><br><span class="texto-2">([^<]+)</span></a>'
        r'<span class="etiqueta etiqueta--\w+">([^<]+)</span>',
        tarjeta(html, "t-entregas"),
    )


# --- La página con los datos del diseño -------------------------------------------------------


def test_el_encabezado_dice_el_mes_y_lleva_a_los_vecinos(sesion_duena, ejemplo):
    html = sesion_duena.get(PAGINA).text

    assert "<h1>Calendario</h1>" in html
    assert '<span class="encabezado__apoyo">Noviembre de 2026</span>' in html
    # En el encabezado y, para el celular, al comienzo del contenido.
    assert html.count('href="?mes=2026-10">Mes anterior</a>') == 2
    assert html.count('href="?mes=2026-12">Mes siguiente</a>') == 2
    assert '<nav class="navegacion-mes" aria-label="Cambiar de mes">' in html
    assert ">Nuevo pedido</a>" in html


def test_la_cuadricula_va_de_lunes_a_domingo_con_los_dias_vecinos(sesion_duena, ejemplo):
    html = cuadricula(sesion_duena.get(PAGINA).text)

    assert re.findall(r'<div class="calendario__semana">(\w+)</div>', html) == [
        "Lun", "Mar", "Mié", "Jue", "Vie", "Sáb", "Dom"
    ]
    numeros = re.findall(r'<span class="calendario__numero">(\d+)</span>', html)
    # Noviembre de 2026 empieza en domingo: la primera semana trae del 26 al 31 de octubre,
    # y la última, del 1 al 6 de diciembre.
    assert numeros[:7] == ["26", "27", "28", "29", "30", "31", "1"]
    assert numeros[-7:] == ["30", "1", "2", "3", "4", "5", "6"]
    assert len(numeros) == 42
    assert html.count("calendario__dia--fuera") == 12


def test_hoy_va_con_el_circulo_negro(sesion_duena, ejemplo):
    html = sesion_duena.get(PAGINA).text

    assert "calendario__dia--hoy" in celda(html, 11)
    assert cuadricula(html).count("calendario__dia--hoy") == 1


def test_cada_entrega_va_en_su_dia_con_su_color(sesion_duena, ejemplo):
    html = sesion_duena.get(PAGINA).text

    for dia, tono, cliente in (
        (6, "verde", "Comparsa Brisa Caribe"),
        (9, "rojo", "Ferretería La Esquina"),
        (14, "ambar", "Grupo de danza Tambores del Río"),
    ):
        assert (
            f'<span class="etiqueta etiqueta--{tono} etiqueta--bloque">{cliente}</span>'
            in celda(html, dia)
        )
    assert "etiqueta" not in celda(html, 10)


def test_las_entregas_de_los_meses_vecinos_no_se_ven(sesion_duena, ejemplo):
    # Marcela P. (cotizado) se entrega el 1 de diciembre, que se ve en la última semana.
    html = cuadricula(sesion_duena.get(PAGINA).text)

    assert "Marcela" not in html
    assert '<div class="calendario__dia calendario__dia--fuera"><span class="calendario__numero">1</span></div>' in html


def test_la_leyenda_va_debajo(sesion_duena, ejemplo):
    html = tarjeta(sesion_duena.get(PAGINA).text, "t-mes")

    leyenda = html[html.index('<div class="calendario__leyenda">'):]
    # Cada cuadrito va junto a su palabra, para que en el celular no queden en líneas distintas.
    assert re.findall(
        r'<span class="calendario__clave"><span class="etiqueta etiqueta--(\w+)" aria-hidden="true">&nbsp;</span>'
        r' ?([\w ]+?)</span>', leyenda
    ) == [("ambar", "Por entregar"), ("rojo", "Atrasado"), ("verde", "Entregado")]


def test_las_columnas_reparten_el_ancho_como_el_diseno(sesion_duena, ejemplo):
    # El diseño le da al mes un poco más de ancho que en las demás pantallas de dos columnas.
    html = sesion_duena.get(PAGINA).text

    assert 'class="tarjeta tarjeta--lista columna-ancha columna-ancha--calendario"' in html
    assert '<div class="columna-angosta columna-angosta--calendario columna">' in html


def test_la_lista_trae_las_entregas_del_mes(sesion_duena, ejemplo):
    html = sesion_duena.get(PAGINA).text

    assert '<h2 id="t-entregas">Entregas de noviembre</h2>' in html
    assert filas_de_la_lista(html) == [
        ("6 de nov", "Comparsa Brisa Caribe", "Entregado"),
        ("9 de nov", "Ferretería La Esquina", "Atrasado 2 días"),
        ("14 de nov", "Grupo de danza Tambores del Río", "Faltan 3 días"),
    ]
    assert "Ver todo el mes" not in html


def test_cada_entrega_de_la_lista_abre_su_pedido(sesion_duena, ejemplo):
    ferreteria = Pedido.objects.get(taller=ejemplo, cliente__nombre="Ferretería La Esquina")

    html = tarjeta(sesion_duena.get(PAGINA).text, "t-entregas")

    enlace = reverse("pedidos:detalle", args=[ferreteria.pk])
    assert f'<a class="tabla__enlace" href="{enlace}"><strong>9 de nov</strong>' in html


def test_la_semana_mas_cargada_dice_que_no_se_juntan(sesion_duena, ejemplo):
    html = tarjeta(sesion_duena.get(PAGINA).text, "t-semana")

    assert (
        "No se te juntan entregas: ninguna semana tiene más de una pendiente. "
        "La próxima es el 14 de nov."
    ) in html


# --- Otros meses y otros casos ------------------------------------------------------------------


def test_otro_mes_por_la_direccion(sesion_duena, ejemplo):
    html = sesion_duena.get(url("2026-12")).text

    assert '<span class="encabezado__apoyo">Diciembre de 2026</span>' in html
    assert 'href="?mes=2026-11">Mes anterior</a>' in html
    assert 'href="?mes=2027-01">Mes siguiente</a>' in html
    assert '<h2 id="t-entregas">Entregas de diciembre</h2>' in html
    assert [fila[1] for fila in filas_de_la_lista(html)] == [
        "Marcela P.", "Restaurante El Fogón Costeño"
    ]
    # Hoy (11 de noviembre) no está en la cuadrícula de diciembre.
    assert "calendario__dia--hoy" not in cuadricula(html)


def test_de_diciembre_a_enero_cambia_el_anio(sesion_duena):
    html = sesion_duena.get(url("2026-12")).text

    assert 'href="?mes=2027-01">Mes siguiente</a>' in html
    assert 'href="?mes=2026-11">Mes anterior</a>' in html


@pytest.mark.parametrize("mes", ["", "noviembre", "2026-13", "2026-00", "0001-01", "2026-1", "٢٠٢٦-١١"])
def test_un_mes_que_no_sirve_es_el_de_hoy(sesion_duena, mes):
    respuesta = sesion_duena.get(url(mes))

    assert respuesta.status_code == 200
    assert '<span class="encabezado__apoyo">Noviembre de 2026</span>' in respuesta.text


def test_un_cotizado_cuenta_como_entrega_por_confirmar(sesion_duena, taller):
    pedido_de(taller, "Cliente cotizado", estado=Estado.COTIZADO, fecha_entrega=date(2026, 11, 25))

    html = sesion_duena.get(PAGINA).text

    assert '<span class="etiqueta etiqueta--ambar etiqueta--bloque">Cliente cotizado</span>' in celda(html, 25)
    assert filas_de_la_lista(html) == [("25 de nov", "Cliente cotizado", "Por confirmar")]


def test_una_entrega_lejana_dice_cuantos_dias_faltan(sesion_duena, taller):
    pedido_de(taller, "Cliente sin afán", fecha_entrega=date(2026, 11, 30))

    html = sesion_duena.get(PAGINA).text

    assert filas_de_la_lista(html) == [("30 de nov", "Cliente sin afán", "Faltan 19 días")]
    assert 'etiqueta--gris">Faltan 19 días</span>' in html
    assert "etiqueta--ambar etiqueta--bloque\">Cliente sin afán" in celda(html, 30)


def test_dos_entregas_el_mismo_dia(sesion_duena, taller):
    pedido_de(taller, "Primera", fecha_entrega=date(2026, 11, 20))
    pedido_de(taller, "Segunda", fecha_entrega=date(2026, 11, 20))

    dia = celda(sesion_duena.get(PAGINA).text, 20)

    assert dia.index(">Primera<") < dia.index(">Segunda<")
    assert 'aria-label="20 de nov, 2 entregas"' in dia


def test_un_mes_sin_entregas(sesion_duena):
    html = sesion_duena.get(PAGINA).text

    assert "No hay entregas en este mes." in tarjeta(html, "t-entregas")
    assert "No hay entregas pendientes en las próximas semanas." in tarjeta(html, "t-semana")
    assert "<button" not in cuadricula(html)


def test_la_semana_mas_cargada_con_varias_entregas(sesion_duena, taller):
    # Semana del 16 al 22: dos entregas para 25 personas. Del 23 al 29: una sola.
    pedido_de(taller, fecha_entrega=date(2026, 11, 16), cantidad=10)
    pedido_de(taller, fecha_entrega=date(2026, 11, 22), cantidad=15)
    pedido_de(taller, fecha_entrega=date(2026, 11, 24), cantidad=40)
    # Ni los entregados ni los atrasados cuentan.
    pedido_de(taller, estado=Estado.ENTREGADO, fecha_entrega=date(2026, 11, 24))
    pedido_de(taller, fecha_entrega=date(2026, 11, 10))

    html = tarjeta(sesion_duena.get(PAGINA).text, "t-semana")

    assert "La semana más cargada que viene es la del 16 al 22 de noviembre: 2 entregas para 25 personas." in html


def test_una_semana_que_cambia_de_mes():
    assert vista.rango_de_la_semana(date(2026, 11, 30)) == "30 de noviembre al 6 de diciembre"
    assert vista.rango_de_la_semana(date(2026, 11, 9)) == "9 al 15 de noviembre"


# --- Tocar un día -------------------------------------------------------------------------------


def test_un_dia_con_entregas_es_un_boton(sesion_duena, ejemplo):
    html = sesion_duena.get(PAGINA).text
    dia = celda(html, 9)

    assert dia.startswith('<button type="submit" class="calendario__dia" id="dia-2026-11-09"')
    assert 'form="calendario-elegir-dia" name="dia" value="2026-11-09"' in dia
    assert 'aria-pressed="false"' in dia
    assert 'aria-label="9 de nov, 1 entrega"' in dia
    # HTMX pide solo la dirección del botón, sin repetir el día que envía el formulario.
    assert (
        f'hx-get="{PAGINA}?mes=2026-11&amp;dia=2026-11-09" hx-params="none" '
        'hx-target="#calendario-entregas"'
    ) in dia
    # El formulario que envía el botón sin JavaScript lleva el mes.
    assert (
        f'<form id="calendario-elegir-dia" action="{PAGINA}" method="get">'
        '<input type="hidden" name="mes" value="2026-11"></form>'
    ) in html
    # Un día sin entregas no es un botón.
    assert celda(html, 10).startswith('<div class="calendario__dia">')


def test_un_dia_elegido_filtra_la_lista(sesion_duena, ejemplo):
    html = sesion_duena.get(url("2026-11", "2026-11-09")).text

    assert '<h2 id="t-entregas">Entregas del 9 de nov</h2>' in html
    assert filas_de_la_lista(html) == [("9 de nov", "Ferretería La Esquina", "Atrasado 2 días")]
    assert f'<a class="boton" id="calendario-ver-mes" href="{PAGINA}?mes=2026-11"' in html
    assert ">Ver todo el mes</a>" in html
    # El día queda marcado y tocarlo otra vez vuelve al mes entero.
    dia = celda(html, 9)
    assert 'aria-pressed="true"' in dia
    assert 'name="dia" value=""' in dia
    assert f'hx-get="{PAGINA}?mes=2026-11"' in dia
    assert 'aria-pressed="false"' in celda(html, 6)


def test_con_htmx_responde_solo_la_lista_y_la_cuadricula(sesion_duena, ejemplo):
    respuesta = sesion_duena.get(url("2026-11", "2026-11-14"), headers=HTMX)
    html = respuesta.text

    assert respuesta.status_code == 200
    assert html.lstrip().startswith(
        '<section class="tarjeta tarjeta--lista calendario-lista" id="calendario-entregas"'
    )
    assert filas_de_la_lista(html) == [("14 de nov", "Grupo de danza Tambores del Río", "Faltan 3 días")]
    assert '<div class="calendario" id="calendario-dias" hx-swap-oob="true">' in html
    assert 'aria-pressed="true"' in celda(html, 14)
    assert "<html" not in html
    assert "Semana más cargada" not in html
    assert "HX-Request" in respuesta["Vary"]


def test_ver_todo_el_mes_con_htmx(sesion_duena, ejemplo):
    html = sesion_duena.get(url("2026-11"), headers=HTMX).text

    assert '<h2 id="t-entregas">Entregas de noviembre</h2>' in html
    assert len(filas_de_la_lista(html)) == 3
    assert 'aria-pressed="true"' not in html


def test_al_volver_atras_htmx_recibe_la_pagina_entera(sesion_duena, ejemplo):
    html = sesion_duena.get(
        url("2026-11", "2026-11-09"), headers={**HTMX, "HX-History-Restore-Request": "true"}
    ).text

    assert "<h1>Calendario</h1>" in html
    assert "Entregas del 9 de nov" in html


def test_un_dia_sin_entregas_lo_dice(sesion_duena, ejemplo):
    html = sesion_duena.get(url("2026-11", "2026-11-10")).text

    assert '<h2 id="t-entregas">Entregas del 10 de nov</h2>' in html
    assert "No hay entregas ese día." in html


@pytest.mark.parametrize("dia", ["", "ayer", "2026-11-31", "2026-12-01", "2026-11-9", "2026-11-09x"])
def test_un_dia_que_no_sirve_o_de_otro_mes_muestra_el_mes_entero(sesion_duena, ejemplo, dia):
    respuesta = sesion_duena.get(url("2026-11", dia))

    assert respuesta.status_code == 200
    assert '<h2 id="t-entregas">Entregas de noviembre</h2>' in respuesta.text
    assert len(filas_de_la_lista(respuesta.text)) == 3


def test_solo_responde_a_get(sesion_duena):
    assert sesion_duena.post(PAGINA).status_code == 405


# --- Otro taller ------------------------------------------------------------------------------


def test_no_muestra_las_entregas_de_otro_taller(sesion_duena, taller):
    otro = fabricas.crear_taller()
    pedido_de(otro, "Cliente de otro taller", fecha_entrega=date(2026, 11, 12))
    pedido_de(otro, "Otro más", fecha_entrega=date(2026, 11, 13))
    pedido_de(taller, "Cliente propio", fecha_entrega=date(2026, 11, 20))

    html = sesion_duena.get(PAGINA).text

    assert "Cliente de otro taller" not in html
    assert "Otro más" not in html
    assert "Cliente propio" in html
    assert filas_de_la_lista(sesion_duena.get(url("2026-11", "2026-11-12")).text) == []
    # La semana más cargada tampoco cuenta las de otro taller.
    assert "No se te juntan entregas" in tarjeta(html, "t-semana")
    assert "La próxima es el 20 de nov." in html


def test_sin_sesion_lleva_a_entrar(client):
    respuesta = client.get(url("2026-11", "2026-11-09"))

    assert respuesta.status_code == 302
    assert respuesta.url.startswith("/entrar/")


# --- Partes de la vista -----------------------------------------------------------------------


def test_dia_elegido():
    noviembre = date(2026, 11, 1)

    assert vista.dia_elegido("2026-11-09", noviembre) == date(2026, 11, 9)
    assert vista.dia_elegido(" 2026-11-30 ", noviembre) == date(2026, 11, 30)
    assert vista.dia_elegido("2026-12-01", noviembre) is None
    assert vista.dia_elegido("2026-02-30", date(2026, 2, 1)) is None
    assert vista.dia_elegido(None, noviembre) is None


def test_el_tono_de_cada_entrega_en_su_dia(taller):
    entregado = pedido_de(taller, estado=Estado.ENTREGADO, fecha_entrega=HOY - timedelta(days=3))
    atrasado = pedido_de(taller, fecha_entrega=HOY - timedelta(days=1))
    cotizado_vencido = pedido_de(taller, estado=Estado.COTIZADO, fecha_entrega=HOY - timedelta(days=1))
    por_entregar = pedido_de(taller, estado=Estado.LISTO, fecha_entrega=HOY + timedelta(days=40))

    assert vista.tono_en_el_dia(entregado, HOY) == "verde"
    assert vista.tono_en_el_dia(atrasado, HOY) == "rojo"
    assert vista.tono_en_el_dia(cotizado_vencido, HOY) == "ambar"
    assert vista.tono_en_el_dia(por_entregar, HOY) == "ambar"


# --- Pantalla fija y animaciones (ajuste "pantalla fija y animaciones") ----------------------


def test_en_computador_las_columnas_llenan_la_hoja(sesion_duena, ejemplo):
    html = sesion_duena.get(PAGINA).text

    # Las dos columnas toman el alto que queda (static/css/app.css, sección 6 y apartado
    # "Calendario"); la lista de entregas es la que se encoge si no cabe.
    assert '<div class="dos-columnas dos-columnas--calendario llenar">' in html
    assert (
        '<section class="tarjeta tarjeta--lista calendario-lista" id="calendario-entregas"'
    ) in html


def test_las_entregas_van_en_una_lista_que_se_desplaza_por_dentro(sesion_duena, ejemplo):
    lista = tarjeta(sesion_duena.get(PAGINA).text, "t-entregas")

    # El título queda afuera, quieto; las filas, dentro de la parte que se desplaza.
    cabeza, filas = lista.split('<div class="desplazable">')
    assert 'id="t-entregas"' in cabeza
    assert filas.count('class="fila fila--compacta tabla__fila"') == 3


def test_un_mes_sin_entregas_no_lleva_lista_que_se_desplace(sesion_duena):
    lista = tarjeta(sesion_duena.get(PAGINA).text, "t-entregas")

    assert "desplazable" not in lista
    assert "No hay entregas en este mes." in lista


def test_cada_entrega_lleva_el_id_de_su_pedido(sesion_duena, ejemplo):
    lista = tarjeta(sesion_duena.get(PAGINA).text, "t-entregas")

    pedidos = Pedido.objects.filter(taller=ejemplo, fecha_entrega__month=11).order_by(
        "fecha_entrega", "pk"
    )
    assert re.findall(r'class="fila fila--compacta tabla__fila" id="([\w-]+)"', lista) == [
        f"entrega-{pedido.pk}" for pedido in pedidos
    ]


def test_al_tocar_un_dia_la_entrega_conserva_su_id(sesion_duena, ejemplo):
    # Así solo se cierran las entregas que se van; la que sigue no se mueve
    # (static/js/app.js, sección 11).
    tambores = Pedido.objects.get(taller=ejemplo, cliente__nombre="Grupo de danza Tambores del Río")
    fila = f'<div class="fila fila--compacta tabla__fila" id="entrega-{tambores.pk}">'

    pagina = sesion_duena.get(PAGINA).text
    dia = sesion_duena.get(url("2026-11", "2026-11-14"), headers=HTMX).text
    mes = sesion_duena.get(url("2026-11"), headers=HTMX).text

    assert fila in pagina and fila in dia and fila in mes
    assert dia.count('class="fila fila--compacta tabla__fila"') == 1


def test_ver_todo_el_mes_lleva_su_id(sesion_duena, ejemplo):
    # Así aparece y se va con un desvanecido, y no cambia si se toca otro día.
    html = sesion_duena.get(url("2026-11", "2026-11-09"), headers=HTMX).text

    assert '<a class="boton" id="calendario-ver-mes" href="' in html
    assert 'id="calendario-ver-mes"' not in sesion_duena.get(url("2026-11"), headers=HTMX).text


def test_la_cuadricula_que_llega_aparte_conserva_los_ids(sesion_duena, ejemplo):
    # Los mismos días con los mismos ids: la cuadrícula se cambia sin parpadear.
    def ids(html):
        return re.findall(r'id="(dia-[\d-]+)"', cuadricula(html))

    pagina = sesion_duena.get(PAGINA).text
    dia = sesion_duena.get(url("2026-11", "2026-11-14"), headers=HTMX).text

    assert ids(pagina) == ids(dia) == ["dia-2026-11-06", "dia-2026-11-09", "dia-2026-11-14"]


def test_el_calendario_no_manda_aviso(sesion_duena, ejemplo):
    # No guarda nada: tocar un día solo filtra (la demo tampoco tiene aviso aquí).
    respuesta = sesion_duena.get(url("2026-11", "2026-11-14"), headers=HTMX)

    assert "HX-Trigger" not in respuesta


# Medidas de la pantalla en Chrome: la página, la hoja, las dos columnas, la cuadrícula del mes,
# la lista de entregas y el día con más entregas de las que caben en su cuadro.
MEDIR = """() => {
  const caja = s => document.querySelector(s).getBoundingClientRect();
  const hoja = document.querySelector('.hoja__contenido');
  const lista = document.querySelector('#calendario-entregas .desplazable');
  const dias = Array.from(document.querySelectorAll('#calendario-dias > .calendario__dia'));
  const lleno = document.querySelector('#dia-2026-11-20 .calendario__entregas');
  return {
    pagina: document.scrollingElement.scrollHeight,
    ventana: window.innerHeight,
    contenido: hoja.scrollHeight,
    cabe: hoja.clientHeight,
    fondo_hoja: caja('.hoja__contenido').bottom,
    fondo_mes: caja('.columna-ancha--calendario').bottom,
    fondo_derecha: caja('.columna-angosta--calendario').bottom,
    fondo_cuadricula: caja('#calendario-dias').bottom,
    arriba_leyenda: caja('.calendario__leyenda').top,
    fondo_leyenda: caja('.calendario__leyenda').bottom,
    lista: [lista.clientHeight, lista.scrollHeight],
    altos_de_los_dias: dias.map(d => d.getBoundingClientRect().height),
    dia_lleno: [lleno.clientHeight, lleno.scrollHeight],
    // Una parte que se desplaza dentro del botón del día sería una parada más del tabulador.
    dia_lleno_se_desplaza: /auto|scroll/.test(getComputedStyle(lleno).overflowY),
  };
}"""


def _abrir_chrome():
    """Chrome sin ventana con Playwright (como tests/test_pantalla_fija.py), o salta."""
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


@pytest.fixture
def mes_lleno(taller, duena):
    """Noviembre de 2026 (seis semanas) con 36 entregas, cinco el mismo día (el 20) con
    nombres largos. Devuelve la sesión de la dueña, abierta antes de Chrome (Django no deja
    usar la base mientras Playwright corre)."""
    for numero in range(1, 6):
        pedido_de(taller, f"Cliente con un nombre bastante largo {numero}",
                  fecha_entrega=date(2026, 11, 20))
    for numero in range(31):
        pedido_de(taller, fecha_entrega=date(2026, 11, 1 + numero % 30))
    cliente = Client()
    cliente.force_login(duena)
    return cliente.cookies["sessionid"].value


def test_en_computador_un_mes_lleno_cabe_sin_desplazar_la_pagina(live_server, mes_lleno):
    direccion = live_server.url + url("2026-11")
    medidas = {}
    manejador, navegador = _abrir_chrome()
    try:
        for ancho, alto in ((1366, 768), (1920, 1080)):
            contexto = navegador.new_context(viewport={"width": ancho, "height": alto})
            contexto.add_cookies([{"name": "sessionid", "value": mes_lleno, "url": direccion}])
            pagina = contexto.new_page()
            pagina.goto(direccion, wait_until="load")
            pagina.evaluate("document.fonts.ready")
            medidas[f"{ancho} x {alto}"] = pagina.evaluate(MEDIR)
            contexto.close()
    finally:
        navegador.close()
        manejador.stop()

    for tamano, medida in medidas.items():
        # Ni la página ni la hoja se desplazan: solo la lista de entregas, por dentro.
        assert medida["pagina"] <= medida["ventana"], tamano
        assert medida["contenido"] <= medida["cabe"] + 1, tamano
        assert medida["lista"][1] > medida["lista"][0], tamano
        # Las dos columnas terminan parejas y llegan hasta abajo (sin hueco).
        assert abs(medida["fondo_mes"] - medida["fondo_derecha"]) <= 1, tamano
        assert medida["fondo_hoja"] - medida["fondo_mes"] <= 6, tamano
        # El mes se ve completo: sus seis semanas, del mismo alto, y la leyenda debajo.
        altos = medida["altos_de_los_dias"]
        assert len(altos) == 42 and max(altos) - min(altos) <= 1, tamano
        assert medida["fondo_cuadricula"] <= medida["arriba_leyenda"] + 1, tamano
        assert medida["fondo_leyenda"] <= medida["fondo_mes"], tamano
        # Las cinco entregas del 20 no caben en su cuadro: se ven las primeras, sin estirar su
        # semana (las cinco están en la lista y al tocar el día).
        assert medida["dia_lleno"][1] > medida["dia_lleno"][0], tamano
        assert medida["dia_lleno_se_desplaza"] is False, tamano
