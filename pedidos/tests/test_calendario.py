"""Calendario (T14): el mes con las entregas marcadas, la lista de entregas (con el filtro
por día) y la semana más cargada. Al final, la pantalla fija en computador y lo que necesitan
las animaciones. Diseño nuevo (rediseño estilo Shopify): diseno/calendario.html."""

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
        r'<strong>([^<]+)</strong></a><div class="texto-2">([^<]+)</div></div>'
        r'<span class="etiqueta etiqueta--\w+(?: etiqueta--\w+)?">([^<]+)</span>',
        tarjeta(html, "t-entregas"),
    )


# --- La página con los datos del diseño -------------------------------------------------------


def test_el_encabezado_solo_trae_el_boton_de_nuevo_pedido(sesion_duena, ejemplo):
    html = sesion_duena.get(PAGINA).text

    assert re.search(r"<h1[^>]*>(?:<svg.*?</svg>)?Calendario</h1>", html, re.S)
    assert ">Nuevo pedido</" in html
    # Los botones de mes ya no están en el encabezado: viven en la tarjeta del mes.
    assert "Mes anterior</a>" not in html and "navegacion-mes" not in html
    assert "encabezado__apoyo" not in html


def test_la_tarjeta_del_mes_trae_hoy_y_las_flechas(sesion_duena, ejemplo):
    html = tarjeta(sesion_duena.get(PAGINA).text, "t-mes")

    assert '<h2 id="t-mes">Noviembre de 2026</h2>' in html
    assert f'<a class="boton" href="{PAGINA}">Hoy</a>' in html
    assert '<span class="grupo-botones">' in html
    assert 'href="?mes=2026-10" aria-label="Mes anterior" title="Mes anterior"' in html
    assert 'href="?mes=2026-12" aria-label="Mes siguiente" title="Mes siguiente"' in html


def test_la_cuadricula_va_de_lunes_a_domingo_con_los_dias_vecinos(sesion_duena, ejemplo):
    html = cuadricula(sesion_duena.get(PAGINA).text)

    assert re.findall(r'<span class="calendario__semana">(\w+)</span>', html) == [
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

    for dia, tono, circulo, cliente in (
        (6, "gris", "lleno", "Comparsa Brisa Caribe"),
        (9, "rojo", "alerta", "Ferretería La Esquina"),
        (14, "ambar", "vacio", "Grupo de danza Tambores del Río"),
    ):
        assert (
            f'<span class="etiqueta etiqueta--{tono} etiqueta--{circulo}" title="{cliente}">'
            f'<span class="etiqueta__texto">{cliente}</span></span>'
        ) in celda(html, dia)
    assert "etiqueta" not in celda(html, 10)


def test_las_entregas_de_los_meses_vecinos_no_se_ven(sesion_duena, ejemplo):
    # Marcela P. (cotizado) se entrega el 1 de diciembre, que se ve en la última semana.
    html = cuadricula(sesion_duena.get(PAGINA).text)

    assert "Marcela" not in html
    assert '<div class="calendario__dia calendario__dia--fuera"><span class="calendario__numero">1</span></div>' in html


def test_la_leyenda_va_debajo(sesion_duena, ejemplo):
    html = tarjeta(sesion_duena.get(PAGINA).text, "t-mes")

    leyenda = html[html.index('<div class="calendario__leyenda">'):]
    assert re.findall(r'<span class="etiqueta etiqueta--(\w+) etiqueta--(\w+)">([\w ]+)</span>', leyenda) == [
        ("ambar", "vacio", "Por entregar"),
        ("rojo", "alerta", "Atrasado"),
        ("gris", "lleno", "Entregado"),
    ]


def test_las_columnas_son_las_del_diseno(sesion_duena, ejemplo):
    html = sesion_duena.get(PAGINA).text.split("<main", 1)[1].split("</main>")[0]  # sin lo compartido

    assert '<div class="columnas">' in html
    assert '<section class="tarjeta tarjeta--recortada" aria-labelledby="t-mes">' in html
    assert '<div class="columna">' in html
    for vieja in ("llenar", "desplazable", "dos-columnas", "columna-ancha", "columna-angosta", "tarjeta--lista"):
        assert vieja not in html


def test_la_lista_trae_las_entregas_del_mes(sesion_duena, ejemplo):
    html = sesion_duena.get(PAGINA).text

    assert '<h2 id="t-entregas">Entregas de noviembre</h2><span class="tarjeta__aparte">3</span>' in html
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
    assert f'<a class="tabla__enlace" href="{enlace}"><strong>9 de nov</strong></a>' in html


def test_la_semana_mas_cargada_dice_que_no_se_juntan(sesion_duena, ejemplo):
    html = tarjeta(sesion_duena.get(PAGINA).text, "t-semana")

    assert (
        "No se te juntan entregas: ninguna semana tiene más de una pendiente. "
        "La próxima es el 14 de nov."
    ) in html


# --- Otros meses y otros casos ------------------------------------------------------------------


def test_otro_mes_por_la_direccion(sesion_duena, ejemplo):
    html = sesion_duena.get(url("2026-12")).text

    assert '<h2 id="t-mes">Diciembre de 2026</h2>' in html
    assert 'href="?mes=2026-11" aria-label="Mes anterior"' in html
    assert 'href="?mes=2027-01" aria-label="Mes siguiente"' in html
    assert '<h2 id="t-entregas">Entregas de diciembre</h2>' in html
    assert [fila[1] for fila in filas_de_la_lista(html)] == [
        "Marcela P.", "Restaurante El Fogón Costeño"
    ]
    # Hoy (11 de noviembre) no está en la cuadrícula de diciembre.
    assert "calendario__dia--hoy" not in cuadricula(html)


def test_de_diciembre_a_enero_cambia_el_anio(sesion_duena):
    html = sesion_duena.get(url("2026-12")).text

    assert 'href="?mes=2027-01" aria-label="Mes siguiente"' in html
    assert 'href="?mes=2026-11" aria-label="Mes anterior"' in html


@pytest.mark.parametrize("mes", ["", "noviembre", "2026-13", "2026-00", "0001-01", "2026-1", "٢٠٢٦-١١"])
def test_un_mes_que_no_sirve_es_el_de_hoy(sesion_duena, mes):
    respuesta = sesion_duena.get(url(mes))

    assert respuesta.status_code == 200
    assert '<h2 id="t-mes">Noviembre de 2026</h2>' in respuesta.text


def test_un_cotizado_cuenta_como_entrega_por_confirmar(sesion_duena, taller):
    pedido_de(taller, "Cliente cotizado", estado=Estado.COTIZADO, fecha_entrega=date(2026, 11, 25))

    html = sesion_duena.get(PAGINA).text

    assert 'etiqueta--ambar etiqueta--vacio" title="Cliente cotizado"' in celda(html, 25)
    assert filas_de_la_lista(html) == [("25 de nov", "Cliente cotizado", "Por confirmar")]


def test_una_entrega_lejana_dice_cuantos_dias_faltan(sesion_duena, taller):
    pedido_de(taller, "Cliente sin afán", fecha_entrega=date(2026, 11, 30))

    html = sesion_duena.get(PAGINA).text

    assert filas_de_la_lista(html) == [("30 de nov", "Cliente sin afán", "Faltan 19 días")]
    assert 'etiqueta--gris">Faltan 19 días</span>' in html
    assert 'etiqueta--ambar etiqueta--vacio" title="Cliente sin afán"' in celda(html, 30)


def test_dos_entregas_el_mismo_dia(sesion_duena, taller):
    pedido_de(taller, "Primera", fecha_entrega=date(2026, 11, 20))
    pedido_de(taller, "Segunda", fecha_entrega=date(2026, 11, 20))

    dia = celda(sesion_duena.get(PAGINA).text, 20)

    assert dia.index(">Primera<") < dia.index(">Segunda<")
    assert dia.count('class="etiqueta etiqueta--ambar etiqueta--vacio"') == 2
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
        '<section class="tarjeta calendario-lista" id="calendario-entregas"'
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

    assert re.search(r"<h1[^>]*>(?:<svg.*?</svg>)?Calendario</h1>", html, re.S)
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

    assert vista.tono_en_el_dia(entregado, HOY) == "gris"
    assert vista.tono_en_el_dia(atrasado, HOY) == "rojo"
    assert vista.tono_en_el_dia(cotizado_vencido, HOY) == "ambar"
    assert vista.tono_en_el_dia(por_entregar, HOY) == "ambar"


# --- Lo que necesitan las animaciones y el foco --------------------------------------------------


def test_sin_entregas_la_cuenta_es_cero(sesion_duena):
    lista = tarjeta(sesion_duena.get(PAGINA).text, "t-entregas")

    assert '<span class="tarjeta__aparte">0</span>' in lista
    assert "No hay entregas en este mes." in lista


def test_la_lista_trae_las_filas_compactas_con_su_insignia(sesion_duena, ejemplo):
    lista = tarjeta(sesion_duena.get(PAGINA).text, "t-entregas")

    assert lista.count('class="fila fila--compacta tabla__fila"') == 3
    assert '<span class="etiqueta etiqueta--gris etiqueta--lleno">Entregado</span>' in lista
    assert '<span class="etiqueta etiqueta--rojo etiqueta--alerta">Atrasado 2 días</span>' in lista
    assert '<span class="etiqueta etiqueta--ambar etiqueta--vacio">Faltan 3 días</span>' in lista


def test_un_dia_elegido_no_muestra_la_cuenta_sino_ver_todo_el_mes(sesion_duena, ejemplo):
    lista = tarjeta(sesion_duena.get(url("2026-11", "2026-11-09")).text, "t-entregas")

    assert "tarjeta__aparte" not in lista
    assert 'data-foco-despues="dia-2026-11-09"' in lista


def test_la_costurera_ve_el_calendario_sin_nuevo_pedido(client, taller):
    from cuentas.models import Usuario  # noqa: PLC0415

    costurera = fabricas.crear_usuaria(taller, rol=Usuario.Rol.COSTURERA)
    client.force_login(costurera)
    pedido_de(taller, "Cliente propio", fecha_entrega=date(2026, 11, 20))

    respuesta = client.get(PAGINA)

    assert respuesta.status_code == 200
    assert "Cliente propio" in respuesta.text
    assert ">Nuevo pedido</" not in respuesta.text


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
