"""Las herramientas de plata del asistente (T28): quien_debe, cuentas_del_mes y gastos.

Las cifras del asistente deben ser las mismas de las pantallas: "Quién te debe" con Hoy (`/`)
y las cuentas del mes con Resumen (`/resumen/?mes=`). Por eso se comparan con
pedidos/calculos.py y con lo que dibujan esas pantallas, abiertas con la sesión de la dueña.
También: lo cotizado no cuenta, nada sale de otro taller, sin float y tarjetas con `pesos`.
"""

import json
from datetime import date, datetime, time, timedelta
from urllib.parse import urlencode

import pytest
from django.urls import reverse
from django.utils import timezone
from django.utils.html import escape

from asistente import herramientas
from asistente.contratos import ErrorDeHerramienta
from asistente.tests.test_herramientas_catalogo import consultar_todas, revisar_plantilla
from asistente.tests.test_herramientas_pedidos import (
    DIA_DEL_DISENO,
    contexto,
    pintar_las_dos,
    sin_float,
)
from pedidos import calculos, ejemplos
from pedidos.models import Cliente, Pedido
from tests import fabricas

pytestmark = pytest.mark.django_db


@pytest.fixture
def ejemplo(db):
    return ejemplos.cargar(hoy=DIA_DEL_DISENO, con_fotos=False)


def quien_debe(ctx):
    return herramientas.ejecutar("quien_debe", {}, ctx)


def cuentas(ctx, anio=None, mes=None):
    return herramientas.ejecutar("cuentas_del_mes", {"anio": anio, "mes": mes}, ctx)


def gastos(ctx, desde, hasta, categoria=None):
    return herramientas.ejecutar(
        "gastos", {"desde": desde, "hasta": hasta, "categoria": categoria}, ctx
    )


def a_las_diez(dia):
    return timezone.make_aware(datetime.combine(dia, time(10, 0)))


# --- quien_debe --------------------------------------------------------------------------------


def test_quien_debe_como_en_diseno_hoy(ejemplo):
    resultado = quien_debe(contexto(ejemplo))

    datos = resultado.datos
    assert datos["por_cobrar"] == 5_790_000
    assert datos["total"] == datos["mostrados"] == 4
    assert [(d["cliente"], d["saldo"], d["vencida"]) for d in datos["deudores"]] == [
        ("Colegio Nuevo Amanecer", 3_300_000, False),
        ("Restaurante El Fogón Costeño", 1_260_000, False),
        ("Grupo de danza Tambores del Río", 750_000, False),
        ("Ferretería La Esquina", 480_000, True),
    ]
    assert sum(d["saldo"] for d in datos["deudores"]) == calculos.por_cobrar(ejemplo)
    colegio = Cliente.objects.del_taller(ejemplo).get(nombre="Colegio Nuevo Amanecer")
    assert datos["deudores"][0]["cliente_id"] == colegio.pk
    assert resultado.revisado == "Revisé los saldos de tus pedidos confirmados"
    assert resultado.enlace.texto == "Ver los pedidos con saldo"
    assert resultado.enlace.url == reverse("pedidos:lista") + "?filtro=saldo"
    sin_float(datos)


def test_lo_cotizado_no_se_cobra(ejemplo):
    # Marcela P. tiene un pedido cotizado de 380.000 sin abonos: no le debe nada al taller.
    datos = quien_debe(contexto(ejemplo)).datos

    assert "Marcela P." not in [d["cliente"] for d in datos["deudores"]]
    marcela = Pedido.objects.get(taller=ejemplo, cliente__nombre="Marcela P.")
    assert calculos.saldo(marcela) == 380_000


def test_quien_debe_coincide_con_la_pantalla_hoy(sesion_duena, taller):
    hoy = timezone.localdate()
    ejemplos.cargar(taller=taller, hoy=hoy, con_fotos=False)

    datos = quien_debe(contexto(taller, hoy=hoy)).datos
    pantalla = sesion_duena.get(reverse("pedidos:hoy"))

    assert pantalla.status_code == 200
    filas = pantalla.context["deudores"]
    assert [(d["cliente"], d["saldo"], d["vencida"]) for d in datos["deudores"]] == [
        (f["deudor"].cliente.nombre, f["deudor"].saldo, f["deudor"].atrasado) for f in filas
    ]
    assert datos["por_cobrar"] == pantalla.context["total_por_cobrar"] == 5_790_000
    # La cifra "Por cobrar" de "Tu mes" también dice lo mismo.
    assert "$ 5.790.000" in pantalla.content.decode()


def test_quien_debe_no_ve_lo_de_otro_taller(ejemplo):
    otro = fabricas.crear_taller()
    deudor = fabricas.crear_cliente(otro, nombre="Deudor del otro taller")
    fabricas.crear_pedido(otro, deudor, estado="confirmado", total=700_000)

    del_ejemplo = quien_debe(contexto(ejemplo)).datos
    del_otro = quien_debe(contexto(otro)).datos

    assert "Deudor del otro taller" not in json.dumps(del_ejemplo, ensure_ascii=False)
    assert del_ejemplo["por_cobrar"] == 5_790_000
    assert del_otro["por_cobrar"] == 700_000
    assert [d["cliente"] for d in del_otro["deudores"]] == ["Deudor del otro taller"]


def test_nadie_debe(taller):
    resultado = quien_debe(contexto(taller))

    assert resultado.datos == {"por_cobrar": 0, "total": 0, "mostrados": 0, "deudores": []}
    assert resultado.tarjeta is None


def test_la_tarjeta_quien_te_debe_copia_la_del_diseno(ejemplo):
    resultado = quien_debe(contexto(ejemplo))

    html = pintar_las_dos(resultado.tarjeta)

    assert '<section class="tarjeta mensaje__tarjeta" aria-label="Quién te debe">' in html
    for nombre, cifra in (
        ("Colegio Nuevo Amanecer", "$ 3.300.000"),
        ("Restaurante El Fogón Costeño", "$ 1.260.000"),
        ("Grupo de danza Tambores del Río", "$ 750.000"),
        ("Ferretería La Esquina", "$ 480.000"),
    ):
        url = reverse("pedidos:lista") + "?" + urlencode({"filtro": "saldo", "q": nombre})
        assert f'<a class="fila-proporcion__nombre" href="{escape(url)}">{nombre}' in html
        assert f'<strong class="dinero">{cifra}</strong>' in html
    # Solo la Ferretería va en rojo, y sin circulito, como en la maqueta.
    assert html.count("etiqueta--rojo") == 1
    assert '<span class="etiqueta etiqueta--rojo">Vencida</span>' in html
    assert "y " not in html.split("$ 480.000")[-1]  # sin "y N más": caben todos


def test_con_muchos_deudores_la_tarjeta_muestra_6_y_cuantos_faltan(taller):
    for n in range(8):
        cliente = fabricas.crear_cliente(taller)
        fabricas.crear_pedido(taller, cliente, estado="confirmado", total=100_000 * (n + 1))

    resultado = quien_debe(contexto(taller))

    assert resultado.datos["total"] == resultado.datos["mostrados"] == 8
    assert len(resultado.tarjeta.datos["filas"]) == 6
    assert resultado.tarjeta.datos["mas"] == 2
    html = pintar_las_dos(resultado.tarjeta)
    assert "y 2 más" in html
    assert "$ 800.000" in html and "$ 200.000" not in html


def test_con_25_deudores_van_20_pero_el_total_es_de_todos(taller):
    for _ in range(25):
        fabricas.crear_pedido(taller, estado="confirmado", total=100_000)

    datos = quien_debe(contexto(taller)).datos

    assert datos["total"] == 25
    assert datos["mostrados"] == len(datos["deudores"]) == 20
    assert datos["por_cobrar"] == 2_500_000 == calculos.por_cobrar(taller)


# --- cuentas_del_mes ---------------------------------------------------------------------------


@pytest.fixture
def dos_meses(taller):
    """Pedidos, abonos y gastos en octubre y noviembre de 2026, y un cotizado que no cuenta."""
    octubre, noviembre = date(2026, 10, 20), date(2026, 11, 5)
    empresa = fabricas.crear_cliente(taller, tipo="empresa")
    colegio = fabricas.crear_cliente(taller, tipo="colegio")
    de_octubre = fabricas.crear_pedido(
        taller, empresa, estado="confeccion", total=1_500_000, creado=a_las_diez(octubre)
    )
    de_noviembre = fabricas.crear_pedido(
        taller, colegio, estado="confirmado", total=2_000_000, creado=a_las_diez(noviembre)
    )
    fabricas.crear_pedido(
        taller, colegio, estado="cotizado", total=900_000, creado=a_las_diez(noviembre)
    )
    fabricas.crear_abono(de_octubre, valor=500_000, fecha=octubre)
    fabricas.crear_abono(de_octubre, valor=300_000, fecha=noviembre)
    fabricas.crear_abono(de_noviembre, valor=1_000_000, fecha=noviembre)
    fabricas.crear_gasto(taller, valor=200_000, fecha=octubre, categoria="telas")
    fabricas.crear_gasto(taller, valor=120_000, fecha=noviembre, categoria="servicios")
    fabricas.crear_gasto(taller, valor=80_000, fecha=noviembre, categoria="telas")
    return taller


def test_cuentas_del_mes_de_dos_meses(dos_meses):
    ctx = contexto(dos_meses, hoy=date(2026, 11, 14))

    octubre = cuentas(ctx, 2026, 10).datos
    noviembre = cuentas(ctx, 2026, 11).datos

    assert octubre == {
        "anio": 2026, "mes": 10, "vendido": 1_500_000, "cobrado": 500_000, "gastado": 200_000,
        "te_quedo": 300_000, "ventas_por_tipo": [{"tipo": "Empresa", "total": 1_500_000}],
    }
    # El cotizado de 900.000 no cuenta como vendido.
    assert noviembre == {
        "anio": 2026, "mes": 11, "vendido": 2_000_000, "cobrado": 1_300_000, "gastado": 200_000,
        "te_quedo": 1_100_000, "ventas_por_tipo": [{"tipo": "Colegio", "total": 2_000_000}],
    }
    for mes, datos in ((10, octubre), (11, noviembre)):
        resumen = calculos.resumen_del_mes(dos_meses, 2026, mes)
        assert {k: datos[k] for k in resumen} == resumen
        sin_float(datos)


def test_cuentas_del_mes_coinciden_con_la_pantalla_resumen(sesion_duena, dos_meses):
    ctx = contexto(dos_meses, hoy=date(2026, 11, 14))

    for mes in ("2026-10", "2026-11"):
        anio, numero = (int(x) for x in mes.split("-"))
        datos = cuentas(ctx, anio, numero).datos
        pantalla = sesion_duena.get(reverse("finanzas:resumen") + f"?mes={mes}")
        assert pantalla.status_code == 200
        assert pantalla.context["cifras"] == {
            k: datos[k] for k in ("vendido", "cobrado", "gastado", "te_quedo")
        }
        assert [(b.nombre, b.valor) for b in pantalla.context["ventas"]] == [
            (v["tipo"], v["total"]) for v in datos["ventas_por_tipo"]
        ]


def test_sin_anio_ni_mes_es_el_mes_de_hoy_del_contexto(dos_meses):
    resultado = cuentas(contexto(dos_meses, hoy=date(2026, 10, 31)))

    assert (resultado.datos["anio"], resultado.datos["mes"]) == (2026, 10)
    assert resultado.datos["cobrado"] == 500_000
    assert resultado.revisado == "Revisé las cuentas de octubre de 2026"
    assert resultado.enlace.texto == "Ver el resumen de octubre"
    assert resultado.enlace.url == reverse("finanzas:resumen") + "?mes=2026-10"


def test_te_quedo_puede_ser_negativo_y_la_tarjeta_lo_muestra(taller):
    fabricas.crear_gasto(taller, valor=200_000, fecha=date(2026, 11, 3))

    resultado = cuentas(contexto(taller, hoy=date(2026, 11, 14)))

    assert resultado.datos["te_quedo"] == -200_000
    html = pintar_las_dos(resultado.tarjeta)
    assert "Noviembre de 2026" in html
    assert "-$ 200.000" in html
    assert "$ 0" in html


def test_cuentas_del_mes_no_ve_lo_de_otro_taller(dos_meses):
    otro = fabricas.crear_taller()
    ajeno = fabricas.crear_pedido(otro, estado="confirmado", total=9_000_000,
                                  creado=a_las_diez(date(2026, 11, 2)))
    fabricas.crear_abono(ajeno, valor=4_000_000, fecha=date(2026, 11, 2))
    fabricas.crear_gasto(otro, valor=3_000_000, fecha=date(2026, 11, 2))

    datos = cuentas(contexto(dos_meses), 2026, 11).datos

    assert (datos["vendido"], datos["cobrado"], datos["gastado"]) == (
        2_000_000, 1_300_000, 200_000
    )


def test_la_tarjeta_de_cuentas_usa_pesos(dos_meses):
    html = pintar_las_dos(cuentas(contexto(dos_meses), 2026, 11).tarjeta)

    for cifra in ("$ 2.000.000", "$ 1.300.000", "$ 200.000", "$ 1.100.000"):
        assert f'<span class="dinero">{cifra}</span>' in html
    assert "Te quedó" in html


# --- gastos ------------------------------------------------------------------------------------


def test_gastos_de_un_mes_dan_lo_mismo_que_gastado_en(ejemplo):
    resultado = gastos(contexto(ejemplo), "2026-11-01", "2026-11-30")

    datos = resultado.datos
    assert datos["total"] == calculos.gastado_en(ejemplo, 2026, 11) == 939_000
    assert datos["cantidad"] == datos["mostrados"] == 5
    assert datos["por_categoria"] == [
        {"categoria": "telas", "total": 684_000},
        {"categoria": "servicios", "total": 140_000},
        {"categoria": "insumos", "total": 85_000},
        {"categoria": "otros", "total": 30_000},
    ]
    # Del más nuevo al más viejo.
    assert [g["fecha"] for g in datos["gastos"]] == sorted(
        (g["fecha"] for g in datos["gastos"]), reverse=True
    )
    assert datos["gastos"][0] == {
        "fecha": "2026-11-09", "concepto": "Recibo de luz del taller", "categoria": "servicios",
        "valor": 140_000,
    }
    assert resultado.revisado == "Revisé tus gastos del 1 de nov al 30 de nov"
    assert resultado.enlace.texto == "Ver los gastos en Resumen"
    assert resultado.enlace.url == reverse("finanzas:resumen") + "?mes=2026-11#gastos"
    sin_float(datos)


def test_gastos_de_una_categoria(ejemplo):
    resultado = gastos(contexto(ejemplo), "2026-11-01", "2026-11-30", "telas")

    datos = resultado.datos
    assert datos["total"] == 684_000
    assert datos["por_categoria"] == [{"categoria": "telas", "total": 684_000}]
    assert [g["concepto"] for g in datos["gastos"]] == [
        "Tela piqué blanca, 22 m", "Dril para delantales, 16 m"
    ]
    assert resultado.revisado == "Revisé tus gastos de telas del 1 de nov al 30 de nov"


def test_gastos_de_dos_meses_suman_los_dos(dos_meses):
    datos = gastos(contexto(dos_meses), "2026-10-01", "2026-11-30").datos

    assert datos["total"] == calculos.gastado_en(dos_meses, 2026, 10) + calculos.gastado_en(
        dos_meses, 2026, 11
    ) == 400_000


def test_gastos_con_fechas_al_reves_da_error(ejemplo):
    with pytest.raises(ErrorDeHerramienta, match="desde .* es después de hasta"):
        gastos(contexto(ejemplo), "2026-11-30", "2026-11-01")


def test_con_35_gastos_van_30_y_el_total_es_de_todos(taller):
    for dia in range(1, 36):
        fabricas.crear_gasto(taller, valor=10_000, fecha=date(2026, 10, 1) + timedelta(days=dia))

    datos = gastos(contexto(taller), "2026-10-01", "2026-11-30").datos

    assert datos["cantidad"] == 35
    assert datos["mostrados"] == len(datos["gastos"]) == 30
    assert datos["total"] == 350_000
    assert datos["gastos"][0]["fecha"] == "2026-11-05"  # el más nuevo


def test_gastos_no_ve_los_de_otro_taller(ejemplo):
    otro = fabricas.crear_taller()
    fabricas.crear_gasto(otro, valor=5_000_000, fecha=DIA_DEL_DISENO, concepto="Gasto ajeno")

    del_ejemplo = gastos(contexto(ejemplo), "2026-11-01", "2026-11-30").datos
    del_otro = gastos(contexto(otro), "2026-11-01", "2026-11-30").datos

    assert del_ejemplo["total"] == 939_000
    assert "Gasto ajeno" not in json.dumps(del_ejemplo, ensure_ascii=False)
    assert del_otro["total"] == 5_000_000


def test_la_tarjeta_de_gastos(ejemplo):
    html = pintar_las_dos(gastos(contexto(ejemplo), "2026-11-01", "2026-11-30").tarjeta)

    assert '<span class="dinero">$ 684.000</span>' in html
    assert '<span class="dinero">$ 939.000</span>' in html
    assert "Telas" in html and "Servicios" in html


def test_la_tarjeta_sin_gastos(taller):
    html = pintar_las_dos(gastos(contexto(taller), "2026-11-01", "2026-11-30").tarjeta)

    assert "No hay gastos anotados en esas fechas." in html


# --- Reglas para todas -------------------------------------------------------------------------


@pytest.mark.parametrize("tipo", ["quien_debe", "cuentas", "gastos"])
def test_ninguna_tarjeta_de_plata_se_salta_el_escapado(tipo):
    revisar_plantilla(tipo)


def test_las_de_plata_no_escriben_en_la_base_ni_dan_float(ejemplo):
    consultas = [
        ("quien_debe", {}),
        ("cuentas_del_mes", {"anio": None, "mes": None}),
        ("cuentas_del_mes", {"anio": 2026, "mes": 10}),
        ("gastos", {"desde": "2026-11-01", "hasta": "2026-11-30", "categoria": None}),
        ("gastos", {"desde": "2026-01-01", "hasta": "2026-12-31", "categoria": "insumos"}),
    ]

    assert consultar_todas(contexto(ejemplo), consultas) == []


def test_lo_que_va_a_claude_no_lleva_telefono_ni_notas(taller):
    cliente = fabricas.crear_cliente(taller, nombre="Cliente Secreto", whatsapp="300 765 4321",
                                     notas="Nota privada 7788")
    pedido = fabricas.crear_pedido(taller, cliente, estado="confirmado", total=500_000)
    fabricas.crear_talla(pedido, talla="M", nombre="Persona Escondida")
    ctx = contexto(taller)

    for resultado in (quien_debe(ctx), cuentas(ctx), gastos(ctx, "2026-01-01", "2026-12-31")):
        texto = json.dumps(resultado.datos, ensure_ascii=False)
        for secreto in ("765", "Nota privada", "Persona Escondida", pedido.token_tallas):
            assert secreto not in texto
