"""Los cálculos de pedidos/calculos.py.

Dos clases de pruebas:

1. Con los datos de ejemplo cargados el miércoles 11 de noviembre de 2026 (el día de las
   páginas de diseno/), cada cálculo da la cifra que muestra el diseño.
2. Los casos de docs/06-pruebas.md: saldo, fechas, resumen, dotación y cotizador.
"""

from datetime import date, datetime, timedelta
from decimal import Decimal

import pytest
from django.utils import timezone

from pedidos import calculos, ejemplos
from pedidos.models import Pedido
from tests import fabricas

pytestmark = pytest.mark.django_db

DIA_DEL_DISENO = date(2026, 11, 11)


@pytest.fixture
def ejemplo(db):
    return ejemplos.cargar(hoy=DIA_DEL_DISENO, con_fotos=False)


def pedido_de(taller, cliente):
    return Pedido.objects.get(taller=taller, cliente__nombre=cliente)


# --- 1. Las cifras de diseno/ ----------------------------------------------------------------


def test_cifras_de_hoy_como_en_el_diseno(ejemplo):
    assert calculos.cifras_de_hoy(ejemplo, DIA_DEL_DISENO) == {
        "en_produccion": 4,
        "por_confirmar": 1,
        "entregas_7_dias": 1,
        "dias_mas_cercana": 3,
        "atrasados": 1,
        "por_cobrar": 5_790_000,
        "pedidos_con_saldo": 4,
    }


def test_que_hacer_hoy_como_en_el_diseno(ejemplo):
    pendientes = calculos.que_hacer_hoy(ejemplo, DIA_DEL_DISENO)

    assert [(p.pedido.cliente.nombre, p.motivo) for p in pendientes] == [
        ("Ferretería La Esquina", "atrasado"),
        ("Grupo de danza Tambores del Río", "listo"),
        ("Marcela P.", "cotizado"),
    ]
    assert [calculos.saldo(p.pedido) for p in pendientes] == [480_000, 750_000, 380_000]


def test_quien_te_debe_como_en_el_diseno(ejemplo):
    deudores = calculos.quien_te_debe(ejemplo, DIA_DEL_DISENO)

    assert [(d.cliente.nombre, d.saldo, d.atrasado) for d in deudores] == [
        ("Colegio Nuevo Amanecer", 3_300_000, False),
        ("Restaurante El Fogón Costeño", 1_260_000, False),
        ("Grupo de danza Tambores del Río", 750_000, False),
        ("Ferretería La Esquina", 480_000, True),
    ]
    # Redondeado como las barras de diseno/hoy.html (100 %, 38 %, 23 % y 15 %).
    assert [d.porcentaje for d in deudores] == [100, 38, 23, 15]


def test_pedidos_por_etapa_como_en_el_diseno(ejemplo):
    etapas = calculos.pedidos_por_etapa(ejemplo, DIA_DEL_DISENO)

    assert [(e.nombre, e.cantidad, e.atrasados) for e in etapas] == [
        ("Cotizado", 1, 0),
        ("Confirmado", 1, 0),
        ("En corte", 1, 0),
        ("En confección", 1, 1),
        ("Listo", 1, 0),
        ("Entregado", 1, 0),
    ]
    entregado = etapas[-1]
    assert entregado.con_saldo == 0  # "Pagado"
    assert etapas[0].con_saldo == 0  # los cotizados no cuentan como "con saldo"


def test_la_grafica_termina_en_noviembre_como_en_el_diseno(ejemplo):
    grafica = calculos.grafica_cobrado_y_gastado(ejemplo, DIA_DEL_DISENO)

    assert [m.mes for m in grafica] == [date(2026, m, 1) for m in range(6, 12)]
    assert (grafica[-1].cobrado, grafica[-1].gastado) == (4_460_000, 939_000)
    # Octubre: 1.200.000 + 480.000 + 1.000.000 de abonos, como la barra del diseño.
    assert grafica[-2].cobrado == 2_680_000


def test_gastos_del_mes_en_el_orden_del_diseno(ejemplo):
    from finanzas.models import Gasto

    gastos = Gasto.objects.del_taller(ejemplo)

    assert [g.concepto for g in gastos] == [
        "Recibo de luz del taller",
        "Hilos y botones",
        "Transporte de telas",
        "Tela piqué blanca, 22 m",
        "Dril para delantales, 16 m",
    ]


def test_resumen_de_noviembre_como_en_el_diseno(ejemplo):
    assert calculos.resumen_del_mes(ejemplo, 2026, 11) == {
        "vendido": 7_320_000,
        "cobrado": 4_460_000,
        "gastado": 939_000,
        "te_quedo": 3_521_000,
    }
    assert calculos.ventas_por_tipo(ejemplo, 2026, 11) == [
        ("Colegio", 4_800_000),
        ("Empresa", 2_520_000),
    ]
    assert calculos.en_produccion_por_persona(ejemplo) == [
        ("Marta", 2), ("Carmen", 1), ("Yolima", 1),
    ]


def test_filtros_y_orden_de_pedidos_como_en_el_diseno(ejemplo):
    pedidos = Pedido.objects.del_taller(ejemplo)

    assert calculos.conteo_de_filtros(pedidos, DIA_DEL_DISENO) == [
        ("todos", "Todos", 6),
        ("produccion", "En producción", 4),
        ("semana", "Esta semana", 1),
        ("atrasados", "Atrasados", 1),
        ("saldo", "Con saldo", 4),
        ("entregados", "Entregados", 1),
    ]
    ordenados = calculos.ordenar_pedidos(calculos.con_cuentas(pedidos).select_related("cliente"))
    assert [p.cliente.nombre for p in ordenados] == [
        "Ferretería La Esquina",
        "Grupo de danza Tambores del Río",
        "Marcela P.",
        "Restaurante El Fogón Costeño",
        "Colegio Nuevo Amanecer",
        "Comparsa Brisa Caribe",
    ]
    assert [(p.num_tallas, p.cantidad) for p in ordenados] == [
        (8, 8), (15, 15), (0, 1), (14, 18), (9, 40), (12, 12),
    ]


def test_etiquetas_como_en_el_diseno(ejemplo):
    ferreteria = pedido_de(ejemplo, "Ferretería La Esquina")
    tambores = pedido_de(ejemplo, "Grupo de danza Tambores del Río")
    restaurante = pedido_de(ejemplo, "Restaurante El Fogón Costeño")

    assert calculos.etiqueta_urgencia(ferreteria, DIA_DEL_DISENO) == calculos.Etiqueta(
        "Atrasado 2 días", "rojo", "alerta"
    )
    assert calculos.etiqueta_urgencia(tambores, DIA_DEL_DISENO) == calculos.Etiqueta(
        "Faltan 3 días", "ambar", "vacio"
    )
    assert calculos.etiqueta_urgencia(restaurante, DIA_DEL_DISENO) is None
    # Rediseño (docs/08-diseno.md, "Insignias"): lo que está bien en gris, verde solo "Listo"
    assert calculos.etiqueta_etapa(ferreteria) == calculos.Etiqueta("En confección", "azul", "medio")
    assert calculos.etiqueta_etapa(tambores) == calculos.Etiqueta("Listo", "verde", "lleno")
    assert calculos.etiqueta_etapa(restaurante) == calculos.Etiqueta("En corte", "azul", "medio")
    assert calculos.etiqueta_etapa(pedido_de(ejemplo, "Colegio Nuevo Amanecer")) == (
        calculos.Etiqueta("Confirmado", "ambar", "vacio")
    )
    assert calculos.etiqueta_etapa(pedido_de(ejemplo, "Marcela P.")) == (
        calculos.Etiqueta("Cotizado", "gris", "vacio")
    )
    assert calculos.etiqueta_etapa(pedido_de(ejemplo, "Comparsa Brisa Caribe")) == (
        calculos.Etiqueta("Entregado", "gris", "lleno")
    )


def test_la_insignia_del_pago_como_en_el_diseno(ejemplo):
    def pago(cliente):
        return calculos.etiqueta_pago(pedido_de(ejemplo, cliente), DIA_DEL_DISENO)

    # Los mismos de diseno/pedidos.html
    assert pago("Ferretería La Esquina") == calculos.Etiqueta("Vencido", "rojo", "alerta")
    assert pago("Grupo de danza Tambores del Río") == calculos.Etiqueta("Abonado 67 %", "naranja", "medio")
    assert pago("Marcela P.") == calculos.Etiqueta("Sin abonos", "gris", "vacio")
    assert pago("Restaurante El Fogón Costeño") == calculos.Etiqueta("Abonado 50 %", "naranja", "medio")
    assert pago("Colegio Nuevo Amanecer") == calculos.Etiqueta("Abonado 31 %", "naranja", "medio")
    assert pago("Comparsa Brisa Caribe") == calculos.Etiqueta("Pagado", "gris", "lleno")


def test_la_insignia_del_pago_sin_abonos_y_casi_pagado(taller):
    confirmado = pedido_con(taller, "confirmado", 30)
    assert calculos.etiqueta_pago(confirmado, HOY) == calculos.Etiqueta("Sin abonos", "naranja", "vacio")
    # Con casi todo pagado no dice "100 %" mientras falte algo, ni "0 %" con un abono chiquito.
    confirmado.total = 1_000
    fabricas.crear_abono(confirmado, valor=999)
    assert calculos.etiqueta_pago(confirmado, HOY).texto == "Abonado 99 %"
    otro = pedido_con(taller, "confirmado", 30)
    otro.total = 1_000_000
    fabricas.crear_abono(otro, valor=100)
    assert calculos.etiqueta_pago(otro, HOY).texto == "Abonado 1 %"


def test_pedido_por_dentro_como_en_el_diseno(ejemplo):
    restaurante = pedido_de(ejemplo, "Restaurante El Fogón Costeño")

    assert calculos.tallas_recibidas(restaurante) == (14, 18)
    assert calculos.tallas_por_talla(restaurante) == [("S", 3), ("M", 6), ("L", 3), ("XL", 2)]
    assert calculos.materiales_comprados(restaurante) == (2, 4)
    assert calculos.abonado(restaurante) == 1_260_000
    assert calculos.saldo(restaurante) == 1_260_000
    assert calculos.porcentaje_pagado(restaurante) == 50
    assert calculos.dias_para_entrega(restaurante, DIA_DEL_DISENO) == 33


def test_clientes_como_en_el_diseno(ejemplo):
    filas = calculos.cuentas_de_clientes(ejemplo)

    assert [(f.cliente.nombre, f.pedidos, f.ha_comprado, f.debe) for f in filas] == [
        ("Colegio Nuevo Amanecer", 1, 4_800_000, 3_300_000),
        ("Restaurante El Fogón Costeño", 1, 2_520_000, 1_260_000),
        ("Comparsa Brisa Caribe", 1, 2_400_000, 0),
        ("Grupo de danza Tambores del Río", 1, 2_250_000, 750_000),
        ("Ferretería La Esquina", 1, 960_000, 480_000),
        ("Marcela P.", 1, 0, 0),
    ]
    assert filas[-1].cotizacion_abierta
    assert sum(1 for f in filas if f.debe > 0) == 4  # "6 clientes, 4 te deben"
    dotacion = calculos.proxima_dotacion(DIA_DEL_DISENO)
    assert (dotacion, (dotacion - DIA_DEL_DISENO).days) == (date(2026, 12, 20), 39)


def test_telas_y_contadores_del_menu_como_en_el_diseno(ejemplo):
    resumen = calculos.resumen_de_telas(ejemplo)

    # diseno/telas.html: primero las que se acaban.
    assert [t.nombre for t in calculos.telas_en_orden(ejemplo)] == [
        "Piqué blanco", "Popelina blanca", "Dril azul", "Tela estampada para polleras",
    ]
    assert calculos.clientes_empresa(ejemplo).count() == 2  # "Tienes 2 clientes empresa"

    assert resumen["cantidad"] == 4
    assert resumen["metros"] == Decimal("60")
    assert [t.nombre for t in resumen["bajas"]] == ["Piqué blanco", "Popelina blanca"]
    assert calculos.contadores_del_menu(ejemplo, DIA_DEL_DISENO) == {"pedidos": 1, "telas": 2}


def test_calendario_como_en_el_diseno(ejemplo):
    entregas = calculos.entregas_del_mes(ejemplo, 2026, 11)

    assert [(p.fecha_entrega.day, p.cliente.nombre) for p in entregas] == [
        (6, "Comparsa Brisa Caribe"),
        (9, "Ferretería La Esquina"),
        (14, "Grupo de danza Tambores del Río"),
    ]
    # "No se te juntan entregas: ninguna semana tiene más de una pendiente. La próxima es
    # el 14 de nov."
    assert calculos.semana_mas_cargada(ejemplo, DIA_DEL_DISENO).entregas == 1
    assert calculos.proxima_entrega(ejemplo, DIA_DEL_DISENO).fecha_entrega == date(2026, 11, 14)
    semanas = calculos.semanas_del_mes(2026, 11)
    assert (semanas[0][0], semanas[-1][-1]) == (date(2026, 10, 26), date(2026, 12, 6))


def test_cotizador_como_en_el_diseno():
    # Camisa polo de ejemplo: 1,2 m a 18.000, insumos 3.000, mano de obra 12.000, extra
    # 5.000, ganancia 30 %, 20 unidades, abono 50 %.
    resultado = calculos.cotizar("1,2", 18_000, 3_000, 12_000, 5_000, 30, 20, 50)

    assert resultado == calculos.Cotizacion(
        tela=21_600, costo=41_600, precio_unidad=54_500, total=1_090_000, abono=545_000,
        ganancia=258_000, metros_totales=Decimal("24.00"),
    )


def test_trabajos_del_taller_son_los_pedidos_con_foto_del_mas_reciente(db, settings, tmp_path):
    settings.MEDIA_ROOT = tmp_path
    taller = ejemplos.cargar(hoy=DIA_DEL_DISENO)

    trabajos = calculos.trabajos_del_taller(taller)

    assert [p.detalle for p in trabajos] == [
        "Vestido de grado a la medida", "15 polleras con blusa", "12 vestidos de fantasía",
    ]


# --- 2. Casos de docs/06-pruebas.md: plata ---------------------------------------------------


def test_saldo_es_total_menos_abonos(taller):
    pedido = fabricas.crear_pedido(taller, total=2_520_000)
    fabricas.crear_abono(pedido, valor=1_260_000)

    assert calculos.saldo(pedido) == 1_260_000


def test_abonos_de_mas_dejan_el_saldo_en_0_nunca_negativo(taller):
    pedido = fabricas.crear_pedido(taller, total=500_000)
    fabricas.crear_abono(pedido, valor=400_000)
    fabricas.crear_abono(pedido, valor=300_000)

    assert calculos.saldo(pedido) == 0
    assert calculos.con_cuentas(Pedido.objects.all()).get().saldo == 0
    assert calculos.porcentaje_pagado(pedido) == 100


def test_las_cuentas_en_lista_dan_lo_mismo_que_una_por_una(taller):
    for total, abonos in ((900_000, [300_000]), (100_000, []), (50_000, [20_000, 40_000])):
        pedido = fabricas.crear_pedido(taller, total=total)
        for valor in abonos:
            fabricas.crear_abono(pedido, valor=valor)
        fabricas.crear_talla(pedido)

    for anotado in calculos.con_cuentas(Pedido.objects.all()):
        suelto = Pedido.objects.get(pk=anotado.pk)
        assert (anotado.abonado, anotado.saldo) == (calculos.abonado(suelto), calculos.saldo(suelto))
        assert anotado.num_tallas == 1


def test_por_cobrar_no_incluye_los_cotizados(taller):
    fabricas.crear_pedido(taller, total=380_000, estado="cotizado")
    fabricas.crear_pedido(taller, total=960_000, estado="confeccion")

    assert calculos.por_cobrar(taller) == 960_000


def test_resumen_del_mes_con_abonos_y_gastos_de_dos_meses(taller):
    octubre = fabricas.crear_pedido(
        taller, total=1_000_000, estado="confirmado",
        creado=timezone.make_aware(datetime(2026, 10, 15, 12)),
    )
    noviembre = fabricas.crear_pedido(
        taller, total=2_000_000, estado="corte",
        creado=timezone.make_aware(datetime(2026, 11, 3, 12)),
    )
    fabricas.crear_pedido(  # cotizado: no cuenta como vendido
        taller, total=9_000_000, creado=timezone.make_aware(datetime(2026, 11, 4, 12))
    )
    fabricas.crear_abono(octubre, valor=400_000, fecha=date(2026, 10, 20))
    fabricas.crear_abono(octubre, valor=100_000, fecha=date(2026, 11, 1))
    fabricas.crear_abono(noviembre, valor=700_000, fecha=date(2026, 11, 10))
    fabricas.crear_gasto(taller, valor=250_000, fecha=date(2026, 10, 31))
    fabricas.crear_gasto(taller, valor=1_000_000, fecha=date(2026, 11, 2))

    assert calculos.resumen_del_mes(taller, 2026, 10) == {
        "vendido": 1_000_000, "cobrado": 400_000, "gastado": 250_000, "te_quedo": 150_000,
    }
    assert calculos.resumen_del_mes(taller, 2026, 11) == {
        "vendido": 2_000_000, "cobrado": 800_000, "gastado": 1_000_000, "te_quedo": -200_000,
    }


def test_vendido_cuenta_el_dia_en_la_hora_de_bogota(taller):
    # 30 de noviembre a las 11:30 p. m. en Bogotá ya es 1 de diciembre en hora mundial.
    fabricas.crear_pedido(
        taller, total=100_000, estado="confirmado",
        creado=timezone.make_aware(datetime(2026, 11, 30, 23, 30)),
    )

    assert calculos.vendido_en(taller, 2026, 11) == 100_000
    assert calculos.vendido_en(taller, 2026, 12) == 0


def test_las_cuentas_de_un_taller_no_mezclan_las_de_otro(taller):
    otro = fabricas.crear_taller()
    for donde in (taller, otro):
        pedido = fabricas.crear_pedido(donde, total=1_000_000, estado="corte")
        fabricas.crear_abono(pedido, valor=300_000, fecha=date(2026, 11, 5))
        fabricas.crear_gasto(donde, valor=50_000, fecha=date(2026, 11, 5))
        fabricas.crear_tela(donde, metros=1, minimo=5)

    assert calculos.por_cobrar(taller) == 700_000
    assert calculos.cobrado_en(taller, 2026, 11) == 300_000
    assert calculos.gastado_en(taller, 2026, 11) == 50_000
    assert calculos.contadores_del_menu(taller)["telas"] == 1
    assert len(calculos.quien_te_debe(taller)) == 1
    assert len(calculos.cuentas_de_clientes(taller)) == 1


# --- 2. Casos de docs/06-pruebas.md: fechas --------------------------------------------------

HOY = date(2026, 11, 11)


def pedido_con(taller, estado, dias):
    return fabricas.crear_pedido(taller, estado=estado, fecha_entrega=HOY + timedelta(days=dias))


def test_en_produccion_con_entrega_ayer_esta_atrasado(taller):
    assert calculos.esta_atrasado(pedido_con(taller, "corte", -1), HOY)


@pytest.mark.parametrize("estado", ["cotizado", "entregado"])
def test_cotizado_o_entregado_nunca_esta_atrasado(taller, estado):
    pedido = pedido_con(taller, estado, -30)

    assert not calculos.esta_atrasado(pedido, HOY)
    assert not calculos.pedidos_atrasados(Pedido.objects.all(), HOY).exists()


@pytest.mark.parametrize(("dias", "pronto"), [(-1, False), (0, True), (7, True), (8, False)])
def test_pronto_es_de_hoy_a_7_dias(taller, dias, pronto):
    pedido = pedido_con(taller, "confeccion", dias)

    assert calculos.esta_pronto(pedido, HOY) is pronto
    assert calculos.pedidos_prontos(Pedido.objects.all(), HOY).exists() is pronto


@pytest.mark.parametrize(
    ("dias", "texto"),
    [(-1, "Atrasado 1 día"), (0, "Se entrega hoy"), (1, "Se entrega mañana"), (5, "Faltan 5 días")],
)
def test_textos_de_urgencia(taller, dias, texto):
    assert calculos.etiqueta_urgencia(pedido_con(taller, "corte", dias), HOY).texto == texto


@pytest.mark.parametrize(
    ("hoy", "proxima"),
    [
        (date(2026, 1, 1), date(2026, 4, 30)),
        (date(2026, 4, 30), date(2026, 4, 30)),
        (date(2026, 5, 1), date(2026, 8, 31)),
        (date(2026, 8, 31), date(2026, 8, 31)),
        (date(2026, 9, 1), date(2026, 12, 20)),
        (date(2026, 12, 20), date(2026, 12, 20)),
        (date(2026, 12, 21), date(2027, 4, 30)),
        (date(2026, 12, 31), date(2027, 4, 30)),
    ],
)
def test_proxima_fecha_de_dotacion(hoy, proxima):
    assert calculos.proxima_dotacion(hoy) == proxima


def test_que_hacer_hoy_muestra_cada_pedido_una_sola_vez(taller):
    # Listo y atrasado a la vez: va solo en "atrasado", que es el primer grupo.
    pedido_con(taller, "listo", -3)
    pedido_con(taller, "listo", 2)  # listo y pronto: va en "listo"
    pedido_con(taller, "corte", 5)  # pronto
    pedido_con(taller, "corte", 30)  # nada que hacer

    motivos = [p.motivo for p in calculos.que_hacer_hoy(taller, HOY)]

    assert motivos == ["atrasado", "listo", "pronto"]


def test_semana_mas_cargada_junta_las_entregas_de_lunes_a_domingo(taller):
    lunes = date(2026, 11, 16)
    fabricas.crear_pedido(taller, estado="corte", fecha_entrega=lunes, cantidad=10)
    fabricas.crear_pedido(taller, estado="corte", fecha_entrega=lunes + timedelta(days=6), cantidad=5)
    fabricas.crear_pedido(taller, estado="corte", fecha_entrega=lunes + timedelta(days=7), cantidad=99)

    semana = calculos.semana_mas_cargada(taller, HOY)

    assert semana == calculos.SemanaCargada(lunes, 2, 15)


def test_sin_entregas_pendientes_no_hay_semana_cargada(taller):
    pedido_con(taller, "entregado", 3)

    assert calculos.semana_mas_cargada(taller, HOY) is None


def test_sumar_meses_cruza_el_ano():
    assert calculos.sumar_meses(date(2026, 11, 30), 2) == date(2027, 1, 1)
    assert calculos.sumar_meses(date(2026, 1, 15), -1) == date(2025, 12, 1)


# --- 2. Casos de docs/06-pruebas.md: cotizador y búsqueda ------------------------------------


def test_un_precio_que_ya_es_multiplo_de_500_no_sube():
    assert calculos.cotizar(0, 0, 10_000, 0, 0, 0, 1, 0).precio_unidad == 10_000


def test_el_abono_no_pasa_del_100_por_ciento_y_lo_invalido_cuenta_como_0():
    resultado = calculos.cotizar("abc", None, 10_000, "", -5, 0, 3, 150)

    assert resultado.costo == 10_000
    assert resultado.abono == resultado.total == 30_000


def test_el_cotizador_redondea_a_500_el_costo_exacto_como_la_demo():
    # 0,01 m a 40 pesos = 0,40 de tela. Costo exacto 1.000,40: sube a 1.500, como en la demo.
    resultado = calculos.cotizar("0.01", 40, 1_000, 0, 0, 0, 1, 0)

    assert (resultado.tela, resultado.costo, resultado.precio_unidad) == (0, 1_000, 1_500)


@pytest.mark.parametrize("raro", ["nan", "inf", "-inf", "1e30", "NaN"])
def test_el_cotizador_no_se_rompe_con_numeros_raros(raro):
    resultado = calculos.cotizar(raro, 18_000, 3_000, raro, 0, raro, raro, raro)

    assert resultado.costo == 3_000
    assert resultado.total == 0


def test_etiqueta_de_entrega_como_en_hoy_y_el_calendario(taller):
    assert calculos.etiqueta_entrega(pedido_con(taller, "cotizado", 20), HOY) == calculos.Etiqueta(
        "Por confirmar", "gris", "vacio"
    )
    assert calculos.etiqueta_entrega(pedido_con(taller, "entregado", -5), HOY) == calculos.Etiqueta(
        "Entregado", "gris", "lleno"
    )
    assert calculos.etiqueta_entrega(pedido_con(taller, "corte", -2), HOY).texto == "Atrasado 2 días"
    assert calculos.etiqueta_entrega(pedido_con(taller, "corte", 30), HOY) is None


def test_porcentaje_redondea_al_entero_mas_cercano():
    assert calculos.porcentaje(480_000, 3_300_000) == 15
    assert calculos.porcentaje(1, 3) == 33
    assert calculos.porcentaje(5, 0) == 0


def test_buscar_sin_tildes_ni_mayusculas():
    assert calculos.sin_tildes("Ferretería LA ESQUINA") == "ferreteria la esquina"
    assert calculos.coincide("fogon", "Restaurante El Fogón Costeño")
    assert calculos.coincide("MARTA", "8 overoles", "Marta")
    assert not calculos.coincide("colegio", "Ferretería")
    assert calculos.coincide("  ", "lo que sea")
