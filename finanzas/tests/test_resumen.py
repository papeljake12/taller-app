"""T17. Resumen del mes: el mes elegido, las cuatro cifras, la gráfica, los gastos del mes,
las ventas por tipo de cliente y quién tiene qué."""

import re
from datetime import date, datetime

import pytest
from django.urls import reverse
from django.utils import timezone

from cuentas.models import Usuario
from finanzas.vistas import mes_elegido
from pedidos.models import Cliente, Pedido
from tests import fabricas

pytestmark = pytest.mark.django_db

NOVIEMBRE = date(2026, 11, 1)


def url(mes=None):
    base = reverse("finanzas:resumen")
    return f"{base}?mes={mes}" if mes is not None else base


def creado_el(dia):
    """Un momento de ese día en Bogotá, para el campo `creado` de un pedido."""
    return timezone.make_aware(datetime(dia.year, dia.month, dia.day, 10))


def cifra(html, nombre):
    """El bloque de la cifra `nombre` (de su <div class="tarjeta cifra"> a su cierre)."""
    return re.search(
        rf'<div class="tarjeta cifra[^"]*">\s*<div class="cifra__nombre">{nombre}</div>.*?</div>\s*</div>',
        html,
        re.S,
    ).group(0)


def tarjeta(html, id_titulo):
    """La tarjeta cuyo título tiene ese id, hasta su </section>."""
    return re.search(rf'<section[^>]*aria-labelledby="{id_titulo}".*?</section>', html, re.S).group(0)


@pytest.fixture
def dos_meses(taller):
    """Ventas, abonos y gastos en octubre y noviembre de 2026, como para el diseño."""
    colegio = fabricas.crear_cliente(taller, nombre="Colegio de prueba", tipo=Cliente.Tipo.COLEGIO)
    empresa = fabricas.crear_cliente(taller, nombre="Empresa de prueba", tipo=Cliente.Tipo.EMPRESA)
    confirmado = Pedido.Estado.CONFIRMADO
    uniformes = fabricas.crear_pedido(
        taller, cliente=colegio, total=4_800_000, estado=confirmado,
        creado=creado_el(date(2026, 11, 2)),
    )
    polos = fabricas.crear_pedido(
        taller, cliente=empresa, total=2_520_000, estado=confirmado,
        creado=creado_el(date(2026, 11, 3)),
    )
    # Cotizado: no cuenta como vendido.
    fabricas.crear_pedido(taller, cliente=empresa, total=9_000_000, creado=creado_el(date(2026, 11, 4)))
    # De octubre.
    viejo = fabricas.crear_pedido(
        taller, cliente=colegio, total=1_000_000, estado=confirmado,
        creado=creado_el(date(2026, 10, 15)),
    )
    fabricas.crear_abono(uniformes, valor=3_200_000, fecha=date(2026, 11, 5))
    fabricas.crear_abono(polos, valor=1_260_000, fecha=date(2026, 11, 6))
    fabricas.crear_abono(viejo, valor=500_000, fecha=date(2026, 10, 20))
    fabricas.crear_gasto(taller, valor=140_000, concepto="Recibo de luz del taller",
                         categoria="servicios", fecha=date(2026, 11, 9))
    fabricas.crear_gasto(taller, valor=396_000, concepto="Tela piqué blanca, 22 m",
                         categoria="telas", fecha=date(2026, 11, 4))
    fabricas.crear_gasto(taller, valor=85_000, concepto="Hilos y botones",
                         categoria="insumos", fecha=date(2026, 11, 6))
    fabricas.crear_gasto(taller, valor=70_000, concepto="Gasto de octubre",
                         categoria="otros", fecha=date(2026, 10, 30))


# --- El mes elegido -----------------------------------------------------------------------


@pytest.mark.parametrize(
    "texto, mes",
    [("2026-11", date(2026, 11, 1)), ("2025-01", date(2025, 1, 1)), (" 2026-12 ", date(2026, 12, 1))],
)
def test_el_mes_se_lee_de_la_direccion(texto, mes):
    assert mes_elegido(texto, hoy=date(2026, 11, 13)) == mes


@pytest.mark.parametrize(
    "texto", [None, "", "2026-13", "2026-00", "2026-1", "noviembre", "0001-01", "9999-12",
              "2026-11-01", "２０２６-０５"]
)
def test_sin_mes_o_con_uno_que_no_sirve_es_el_mes_de_hoy(texto):
    assert mes_elegido(texto, hoy=date(2026, 11, 13)) == date(2026, 11, 1)


def test_sin_mes_la_pantalla_muestra_el_mes_de_hoy(sesion_duena):
    hoy = timezone.localdate()

    html = sesion_duena.get(url()).text

    nombre = ["Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio", "Julio", "Agosto",
              "Septiembre", "Octubre", "Noviembre", "Diciembre"][hoy.month - 1]
    assert f'<span class="encabezado__apoyo">{nombre} de {hoy.year}</span>' in html
    assert f'name="mes" value="{hoy:%Y-%m}"' not in html  # el formulario empieza cerrado
    assert f"?mes={hoy:%Y-%m}" in html  # "Registrar gasto" lleva el mes


def test_con_un_mes_que_no_sirve_no_falla(sesion_duena):
    assert sesion_duena.get(url("2026-99")).status_code == 200
    assert sesion_duena.get(url("<script>")).status_code == 200


def test_el_encabezado_trae_el_mes_y_los_botones_del_diseno(sesion_duena):
    html = sesion_duena.get(url("2026-11")).text

    assert "<h1>Resumen</h1>" in html
    assert '<span class="encabezado__apoyo">Noviembre de 2026</span>' in html
    assert '<a class="boton" href="?mes=2026-10">Mes anterior</a>' in html
    assert '<a class="boton" href="?mes=2026-12">Mes siguiente</a>' in html
    assert (
        f'<a class="boton boton--principal" href="{reverse("finanzas:excel")}">'
        "Descargar para Excel</a>"
    ) in html


def test_el_mes_anterior_y_el_siguiente_cruzan_el_anio(sesion_duena):
    enero = sesion_duena.get(url("2027-01")).text
    diciembre = sesion_duena.get(url("2026-12")).text

    assert 'href="?mes=2026-12">Mes anterior' in enero
    assert 'href="?mes=2027-01">Mes siguiente' in diciembre


# --- Las cuatro cifras --------------------------------------------------------------------


def test_las_cifras_son_las_del_mes_elegido(sesion_duena, dos_meses):
    html = sesion_duena.get(url("2026-11")).text

    vendido = cifra(html, "Vendido")
    assert "$ 7.320.000" in vendido and "Pedidos confirmados en el mes" in vendido
    cobrado = cifra(html, "Cobrado")
    assert "$ 4.460.000" in cobrado and "Abonos recibidos en el mes" in cobrado
    gastado = cifra(html, "Gastado")
    assert "$ 621.000" in gastado and "Telas, insumos y demás" in gastado
    quedo = cifra(html, "Te quedó")
    assert "$ 3.839.000" in quedo and "Cobrado menos gastado" in quedo
    assert "cifra--buena" in quedo  # en verde


def test_otro_mes_tiene_sus_propias_cifras(sesion_duena, dos_meses):
    html = sesion_duena.get(url("2026-10")).text

    assert "$ 1.000.000" in cifra(html, "Vendido")
    assert "$ 500.000" in cifra(html, "Cobrado")
    assert "$ 70.000" in cifra(html, "Gastado")
    assert "$ 430.000" in cifra(html, "Te quedó")


def test_si_te_quedo_es_negativo_no_va_en_verde_ni_en_rojo_y_lo_dice(sesion_duena, taller):
    fabricas.crear_gasto(taller, valor=200_000, fecha=date(2026, 11, 3))

    quedo = cifra(sesion_duena.get(url("2026-11")).text, "Te quedó")

    assert "-$ 200.000" in quedo
    assert "Gastaste más de lo que cobraste" in quedo
    assert "cifra--buena" not in quedo and "cifra--alerta" not in quedo


def test_un_mes_sin_nada_muestra_ceros(sesion_duena):
    html = sesion_duena.get(url("2026-11")).text

    for nombre in ("Vendido", "Cobrado", "Gastado", "Te quedó"):
        assert "$ 0" in cifra(html, nombre)


def test_lo_de_otro_taller_no_entra_en_las_cuentas(sesion_duena, dos_meses):
    otro = fabricas.crear_taller()
    ajeno = fabricas.crear_pedido(
        otro, total=5_555_000, estado=Pedido.Estado.CONFIRMADO,
        creado=creado_el(date(2026, 11, 2)),
    )
    fabricas.crear_abono(ajeno, valor=777_000, fecha=date(2026, 11, 5))
    fabricas.crear_gasto(otro, valor=333_000, concepto="Gasto ajeno", fecha=date(2026, 11, 5))

    html = sesion_duena.get(url("2026-11")).text

    assert "$ 7.320.000" in cifra(html, "Vendido")
    assert "$ 4.460.000" in cifra(html, "Cobrado")
    assert "$ 621.000" in cifra(html, "Gastado")
    assert "Gasto ajeno" not in html
    assert "333.000" not in html and "777.000" not in html and "5.555.000" not in html


# --- La gráfica ---------------------------------------------------------------------------


def test_la_grafica_muestra_los_seis_meses_que_terminan_en_el_mes_elegido(sesion_duena, dos_meses):
    grafica = tarjeta(sesion_duena.get(url("2026-11")).text, "t-grafica")

    assert "Cobrado y gastado por mes" in grafica
    assert "leyenda__color--cobrado" in grafica and "leyenda__color--gastado" in grafica
    assert 'aria-label="Barras de cobrado y gastado de junio a noviembre.' in grafica
    assert "En noviembre: cobrado 4,46 millones y gastado 0,62 millones." in grafica
    assert ">nov</text>" in grafica and ">jun</text>" in grafica
    assert "De junio a noviembre, en millones de pesos (M)." in grafica


def test_la_grafica_de_un_mes_pasado_termina_en_ese_mes(sesion_duena, dos_meses):
    grafica = tarjeta(sesion_duena.get(url("2026-10")).text, "t-grafica")

    assert "de mayo a octubre." in grafica
    assert ">nov</text>" not in grafica
    assert "En octubre: cobrado 0,5 millones y gastado 0,07 millones." in grafica
    assert "De mayo a octubre, en miles de pesos." in grafica


# --- Gastos del mes -----------------------------------------------------------------------


def test_los_gastos_del_mes_van_del_mas_nuevo_al_mas_viejo_como_en_el_diseno(
    sesion_duena, dos_meses
):
    gastos = tarjeta(sesion_duena.get(url("2026-11")).text, "t-gastos")

    assert "Gastos de noviembre" in gastos
    assert "Recibo de luz del taller<br><span class=\"texto-2\">9 de nov, servicios</span>" in gastos
    assert '<strong class="dinero">$ 140.000</strong>' in gastos
    assert "6 de nov, insumos" in gastos and "4 de nov, telas" in gastos
    posiciones = [gastos.index(c) for c in ("Recibo de luz", "Hilos y botones", "Tela piqué")]
    assert posiciones == sorted(posiciones)
    assert "Gasto de octubre" not in gastos


def test_cada_gasto_se_puede_quitar_y_el_boton_de_registrar_abre_el_formulario(
    sesion_duena, dos_meses, taller
):
    gastos = tarjeta(sesion_duena.get(url("2026-11")).text, "t-gastos")

    for gasto in taller.gasto_set.filter(fecha__month=11):
        quitar = reverse("finanzas:gasto_quitar", args=[gasto.pk])
        assert f'hx-get="{quitar}"' in gastos
    nuevo = reverse("finanzas:gasto_nuevo")
    assert f'href="{nuevo}?mes=2026-11" hx-get="{nuevo}?mes=2026-11"' in gastos
    assert ">Registrar gasto</a>" in gastos
    assert "<form" not in gastos  # el formulario empieza cerrado, como en el diseño


def test_un_mes_sin_gastos_lo_dice(sesion_duena, dos_meses):
    gastos = tarjeta(sesion_duena.get(url("2026-09")).text, "t-gastos")

    assert "Gastos de septiembre" in gastos
    assert "No hay gastos anotados en este mes." in gastos


# --- Ventas por tipo y quién tiene qué ----------------------------------------------------


def test_ventas_por_tipo_de_cliente_con_barras_contra_la_mas_grande(sesion_duena, dos_meses):
    ventas = tarjeta(sesion_duena.get(url("2026-11")).text, "t-ventas")

    assert "Ventas por tipo de cliente" in ventas
    assert ventas.index("Colegio") < ventas.index("Empresa")
    assert 'aria-label="Colegio"><span class="progreso__relleno" style="width: 100%">' in ventas
    assert 'aria-label="Empresa"><span class="progreso__relleno" style="width: 53%">' in ventas
    assert "$ 4.800.000" in ventas and "$ 2.520.000" in ventas


def test_un_mes_sin_ventas_lo_dice(sesion_duena, dos_meses):
    ventas = tarjeta(sesion_duena.get(url("2026-09")).text, "t-ventas")

    assert "No hay ventas confirmadas en este mes." in ventas


def test_quien_tiene_que_cuenta_los_pedidos_en_produccion_por_persona(sesion_duena, taller):
    marta = fabricas.crear_usuaria(taller, rol=Usuario.Rol.COSTURERA, nombre_visible="Marta")
    carmen = fabricas.crear_usuaria(taller, rol=Usuario.Rol.COSTURERA, nombre_visible="Carmen")
    for encargada, estado in ((marta, "corte"), (marta, "confeccion"), (carmen, "confeccion"),
                              (carmen, "entregado")):
        fabricas.crear_pedido(taller, encargada=encargada, estado=estado)
    ajena = fabricas.crear_usuaria(fabricas.crear_taller(), rol=Usuario.Rol.COSTURERA,
                                   nombre_visible="Ajena")
    fabricas.crear_pedido(ajena.taller, encargada=ajena, estado="corte")

    personas = tarjeta(sesion_duena.get(url()).text, "t-personas")

    assert "Pedidos en producción hoy, por persona." in personas
    assert personas.index("Marta") < personas.index("Carmen")
    assert 'aria-label="Marta"><span class="progreso__relleno" style="width: 100%">' in personas
    assert 'aria-label="Carmen"><span class="progreso__relleno" style="width: 50%">' in personas
    assert "<strong class=\"dinero\">2</strong>" in personas
    assert "Ajena" not in personas


def test_sin_pedidos_en_produccion_lo_dice(sesion_duena):
    personas = tarjeta(sesion_duena.get(url()).text, "t-personas")

    assert "No hay pedidos en producción." in personas
    assert "por persona" not in personas


def test_sin_sesion_lleva_a_entrar(client):
    respuesta = client.get(url("2026-11"))

    assert respuesta.status_code == 302 and respuesta.url.startswith("/entrar/")
