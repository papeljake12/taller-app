"""T18. Descarga para Excel: cuatro hojas con lo del taller, y nada de otro taller."""

from datetime import date, datetime
from decimal import Decimal
from io import BytesIO

import pytest
from django.urls import reverse
from django.utils import timezone
from openpyxl import load_workbook

from cuentas.models import Usuario
from finanzas.excel import libro_del_taller, nombre_del_archivo
from pedidos.models import Cliente, Pedido
from tests import fabricas

pytestmark = pytest.mark.django_db

ENCABEZADOS = {
    "Pedidos": ["Cliente", "Tipo", "Qué pidió", "Personas", "Entrega", "Etapa", "Encargada",
                "Total", "Abonado", "Saldo", "WhatsApp"],
    "Abonos": ["Fecha", "Cliente", "Pedido", "Valor"],
    "Gastos": ["Fecha", "Concepto", "Tipo", "Valor"],
    "Telas": ["Tela", "Metros", "Avisar cuando queden"],
}


def abrir(contenido):
    return load_workbook(BytesIO(contenido))


def filas(hoja):
    """Las filas de datos (sin la de títulos), como listas de valores."""
    return [list(fila) for fila in hoja.iter_rows(min_row=2, values_only=True)]


@pytest.fixture
def datos(taller):
    """Un pedido con abono, un gasto y una tela del taller; y lo mismo en otro taller."""
    marta = fabricas.crear_usuaria(taller, rol=Usuario.Rol.COSTURERA, nombre_visible="Marta")
    cliente = fabricas.crear_cliente(
        taller, nombre="Restaurante de prueba", tipo=Cliente.Tipo.EMPRESA, whatsapp="300 000 0000"
    )
    pedido = fabricas.crear_pedido(
        taller, cliente=cliente, detalle="18 camisas polo bordadas", cantidad=18,
        fecha_entrega=date(2026, 12, 4), total=2_520_000, estado=Pedido.Estado.CONFECCION,
        encargada=marta,
    )
    fabricas.crear_abono(pedido, valor=1_260_000, fecha=date(2026, 11, 5))
    fabricas.crear_gasto(taller, valor=140_000, concepto="Recibo de luz del taller",
                         categoria="servicios", fecha=date(2026, 11, 9))
    fabricas.crear_tela(taller, nombre="Dril azul", metros=Decimal("6.5"), minimo=10)

    otro = fabricas.crear_taller()
    ajeno = fabricas.crear_pedido(otro, detalle="Pedido ajeno", total=9_990_000)
    fabricas.crear_abono(ajeno, valor=777_000)
    fabricas.crear_gasto(otro, concepto="Gasto ajeno", valor=333_000)
    fabricas.crear_tela(otro, nombre="Tela ajena")
    return pedido


def test_el_libro_tiene_las_cuatro_hojas_con_sus_titulos(taller):
    libro = abrir(libro_del_taller(taller))

    assert libro.sheetnames == ["Pedidos", "Abonos", "Gastos", "Telas"]
    for nombre, titulos in ENCABEZADOS.items():
        hoja = libro[nombre]
        assert [c.value for c in hoja[1]] == titulos
        assert all(c.font.bold for c in hoja[1])
        assert hoja.freeze_panes == "A2"
        assert filas(hoja) == []  # un taller nuevo: solo los títulos


def test_una_fila_por_registro_con_plata_en_numeros_y_fechas_de_verdad(taller, datos):
    libro = abrir(libro_del_taller(taller))

    assert filas(libro["Pedidos"]) == [[
        "Restaurante de prueba", "Empresa", "18 camisas polo bordadas", 18,
        datetime(2026, 12, 4), "En confección", "Marta", 2_520_000, 1_260_000, 1_260_000,
        "300 000 0000",
    ]]
    assert filas(libro["Abonos"]) == [
        [datetime(2026, 11, 5), "Restaurante de prueba", "18 camisas polo bordadas", 1_260_000]
    ]
    assert filas(libro["Gastos"]) == [
        [datetime(2026, 11, 9), "Recibo de luz del taller", "Servicios", 140_000]
    ]
    assert filas(libro["Telas"]) == [["Dril azul", 6.5, 10]]


def test_la_plata_y_las_fechas_llevan_su_formato(taller, datos):
    libro = abrir(libro_del_taller(taller))

    pedido = libro["Pedidos"]
    assert pedido["E2"].is_date and pedido["E2"].number_format == "dd/mm/yyyy"
    for celda in ("H2", "I2", "J2"):
        assert isinstance(pedido[celda].value, int)
        assert pedido[celda].number_format == '"$ "#,##0'
    gasto = libro["Gastos"]
    assert gasto["A2"].is_date and isinstance(gasto["D2"].value, int)
    assert libro["Abonos"]["A2"].is_date


def test_las_columnas_tienen_un_ancho_que_se_lee(taller, datos):
    hoja = abrir(libro_del_taller(taller))["Pedidos"]

    assert hoja.column_dimensions["C"].width >= len("18 camisas polo bordadas")
    for letra in "ABCDEFGHIJK":
        assert 8 <= hoja.column_dimensions[letra].width <= 50


def test_nada_de_otro_taller_entra_en_el_archivo(taller, datos):
    libro = abrir(libro_del_taller(taller))

    for hoja in libro.worksheets:
        assert len(filas(hoja)) == 1
        for fila in filas(hoja):
            for valor in fila:
                assert valor not in ("Pedido ajeno", "Gasto ajeno", "Tela ajena", 9_990_000,
                                     777_000, 333_000)


def test_el_saldo_nunca_baja_de_cero_y_varios_abonos_suman(taller):
    pedido = fabricas.crear_pedido(taller, total=500_000)
    fabricas.crear_abono(pedido, valor=300_000, fecha=date(2026, 11, 1))
    fabricas.crear_abono(pedido, valor=300_000, fecha=date(2026, 11, 2))

    libro = abrir(libro_del_taller(taller))

    fila = filas(libro["Pedidos"])[0]
    assert fila[7:10] == [500_000, 600_000, 0]
    assert len(filas(libro["Abonos"])) == 2


def test_un_pedido_sin_encargada_y_sin_whatsapp_deja_las_celdas_vacias(taller):
    fabricas.crear_pedido(taller)

    fila = filas(abrir(libro_del_taller(taller))["Pedidos"])[0]

    assert fila[6] is None and fila[10] is None  # vacías, no "None"


def test_un_texto_que_parece_formula_queda_como_texto(taller):
    fabricas.crear_gasto(taller, concepto='=HYPERLINK("http://ejemplo.invalid","clic")')
    fabricas.crear_cliente(taller, nombre="Cliente\x0bcon un carácter raro")
    fabricas.crear_pedido(taller, cliente=taller.cliente_set.get())

    libro = abrir(libro_del_taller(taller))

    celda = libro["Gastos"]["B2"]
    assert celda.data_type == "s"
    assert celda.value.startswith("=HYPERLINK")
    assert libro["Pedidos"]["A2"].value == "Clientecon un carácter raro"


def test_el_nombre_del_archivo_lleva_el_taller_y_la_fecha():
    taller = fabricas.crear_taller(nombre="Confecciones Doña Ñusta")

    assert nombre_del_archivo(taller, date(2026, 11, 13)) == (
        "confecciones-dona-nusta-2026-11-13.xlsx"
    )


def test_un_nombre_sin_letras_usa_taller(db):
    taller = fabricas.crear_taller(nombre="!!!")

    assert nombre_del_archivo(taller, date(2026, 11, 13)) == "taller-2026-11-13.xlsx"


# --- La descarga --------------------------------------------------------------------------


def test_la_descarga_entrega_el_archivo_del_taller(sesion_duena, taller, datos):
    hoy = timezone.localdate()

    respuesta = sesion_duena.get(reverse("finanzas:excel"))

    assert respuesta.status_code == 200
    assert respuesta["Content-Type"] == (
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
    nombre = nombre_del_archivo(taller, hoy)
    assert nombre.endswith(f"-{hoy.isoformat()}.xlsx")
    assert respuesta["Content-Disposition"] == f'attachment; filename="{nombre}"'
    libro = abrir(respuesta.content)
    assert libro.sheetnames == ["Pedidos", "Abonos", "Gastos", "Telas"]
    assert filas(libro["Gastos"])[0][1] == "Recibo de luz del taller"
    assert "Gasto ajeno" not in [f[1] for f in filas(libro["Gastos"])]


def test_la_otra_duena_baja_solo_lo_suyo(client, datos):
    otro = Pedido.objects.get(detalle="Pedido ajeno").taller
    client.force_login(fabricas.crear_usuaria(otro))

    libro = abrir(client.get(reverse("finanzas:excel")).content)

    assert [f[2] for f in filas(libro["Pedidos"])] == ["Pedido ajeno"]
    assert [f[1] for f in filas(libro["Gastos"])] == ["Gasto ajeno"]


@pytest.mark.parametrize("nombre", ["pedidos:hoy", "pedidos:lista", "finanzas:resumen"])
def test_el_boton_esta_en_hoy_pedidos_y_resumen(sesion_duena, nombre):
    html = sesion_duena.get(reverse(nombre)).text

    assert f'href="{reverse("finanzas:excel")}"' in html
    assert ">Descargar para Excel</a>" in html


def test_sin_sesion_no_se_descarga(client, datos):
    respuesta = client.get(reverse("finanzas:excel"))

    assert respuesta.status_code == 302 and respuesta.url.startswith("/entrar/")


def test_solo_se_pide_con_get(sesion_duena):
    assert sesion_duena.post(reverse("finanzas:excel")).status_code == 405
