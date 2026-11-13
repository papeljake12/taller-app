"""Descarga para Excel (T18): un archivo .xlsx con todo lo del taller, en cuatro hojas.

Las hojas y sus columnas son las de la demo (hojas() en demo/index.html):

- Pedidos: Cliente, Tipo, Qué pidió, Personas, Entrega, Etapa, Encargada, Total, Abonado,
  Saldo y WhatsApp.
- Abonos: Fecha, Cliente, Pedido y Valor.
- Gastos: Fecha, Concepto, Tipo y Valor.
- Telas: Tela, Metros y "Avisar cuando queden" (en la demo, "Avisar por debajo de"; aquí
  con el nombre que tiene en el modelo y en la pantalla Telas).

Para que Excel pueda sumar y ordenar, la plata va como número entero de pesos (con formato
"$ 1.260.000"), las fechas como fechas (dd/mm/aaaa) y los metros como números. El saldo y
lo abonado salen de pedidos/calculos.py, como en el resto de la aplicación.

Solo entra lo del taller que se pasa: cada consulta se filtra con .del_taller(taller).
"""

from dataclasses import dataclass
from io import BytesIO

from django.utils.text import slugify
from openpyxl import Workbook
from openpyxl.cell.cell import ILLEGAL_CHARACTERS_RE
from openpyxl.styles import Font
from openpyxl.utils import get_column_letter

from finanzas.models import Gasto
from pedidos import calculos
from pedidos.models import Abono, Pedido
from telas.models import Tela

TIPO_DE_ARCHIVO = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"

# Formatos de las celdas. Excel en español muestra "$ 1.260.000" y "13/11/2026".
FORMATO_PESOS = '"$ "#,##0'
FORMATO_FECHA = "dd/mm/yyyy"
# Los metros con el formato "General" de Excel: 60 se ve "60" y 6,5 se ve "6,5".
FORMATO_METROS = "General"

# Anchos de columna, en caracteres: lo que ocupa el texto más largo, entre estos límites.
ANCHO_MINIMO, ANCHO_MAXIMO = 8, 50


@dataclass(frozen=True)
class Columna:
    titulo: str
    formato: str | None = None  # None: texto o número sin formato especial


def _hoja_pedidos(taller):
    columnas = [
        Columna("Cliente"), Columna("Tipo"), Columna("Qué pidió"), Columna("Personas"),
        Columna("Entrega", FORMATO_FECHA), Columna("Etapa"), Columna("Encargada"),
        Columna("Total", FORMATO_PESOS), Columna("Abonado", FORMATO_PESOS),
        Columna("Saldo", FORMATO_PESOS), Columna("WhatsApp"),
    ]
    pedidos = calculos.con_cuentas(
        Pedido.objects.del_taller(taller).select_related("cliente", "encargada")
    )
    filas = [
        [
            pedido.cliente.nombre,
            pedido.cliente.get_tipo_display(),
            pedido.detalle,
            pedido.cantidad,
            pedido.fecha_entrega,
            pedido.get_estado_display(),
            pedido.encargada.nombre if pedido.encargada else "",
            pedido.total,
            calculos.abonado(pedido),
            calculos.saldo(pedido),
            pedido.cliente.whatsapp,
        ]
        for pedido in pedidos
    ]
    return "Pedidos", columnas, filas


def _hoja_abonos(taller):
    columnas = [Columna("Fecha", FORMATO_FECHA), Columna("Cliente"), Columna("Pedido"),
                Columna("Valor", FORMATO_PESOS)]
    abonos = Abono.objects.del_taller(taller).select_related("pedido__cliente")
    filas = [[a.fecha, a.pedido.cliente.nombre, a.pedido.detalle, a.valor] for a in abonos]
    return "Abonos", columnas, filas


def _hoja_gastos(taller):
    columnas = [Columna("Fecha", FORMATO_FECHA), Columna("Concepto"), Columna("Tipo"),
                Columna("Valor", FORMATO_PESOS)]
    # Del más viejo al más nuevo, como los abonos: así se lee como un cuaderno de cuentas.
    gastos = Gasto.objects.del_taller(taller).order_by("fecha", "pk")
    filas = [[g.fecha, g.concepto, g.get_categoria_display(), g.valor] for g in gastos]
    return "Gastos", columnas, filas


def _hoja_telas(taller):
    columnas = [Columna("Tela"), Columna("Metros", FORMATO_METROS),
                Columna("Avisar cuando queden", FORMATO_METROS)]
    telas = Tela.objects.del_taller(taller)
    filas = [[t.nombre, t.metros, t.minimo] for t in telas]
    return "Telas", columnas, filas


def _texto_seguro(valor):
    """Quita los caracteres de control que no caben en un archivo de Excel. Un texto vacío
    (un pedido sin encargada, un cliente sin WhatsApp) deja la celda vacía."""
    if not isinstance(valor, str):
        return valor
    return ILLEGAL_CHARACTERS_RE.sub("", valor) or None


def _escribir_hoja(hoja, columnas, filas):
    hoja.append([c.titulo for c in columnas])
    for celda in hoja[1]:
        celda.font = Font(bold=True)
    for fila in filas:
        hoja.append([_texto_seguro(valor) for valor in fila])
    for numero, columna in enumerate(columnas, start=1):
        celdas = hoja.iter_rows(min_row=2, min_col=numero, max_col=numero)
        largo = len(columna.titulo)
        for (celda,) in celdas:
            if isinstance(celda.value, str) and celda.data_type == "f":
                # Un texto que empieza con "=" se queda como texto: nunca como fórmula.
                celda.data_type = "s"
            if columna.formato:
                celda.number_format = columna.formato
                largo = max(largo, 12)
            elif celda.value is not None:
                largo = max(largo, len(str(celda.value)))
        ancho = min(max(largo + 2, ANCHO_MINIMO), ANCHO_MAXIMO)
        hoja.column_dimensions[get_column_letter(numero)].width = ancho
    # Los títulos quedan quietos al bajar por la hoja.
    hoja.freeze_panes = "A2"


def libro_del_taller(taller):
    """El archivo .xlsx, en bytes, con las cuatro hojas del taller."""
    libro = Workbook()
    libro.remove(libro.active)
    for armar in (_hoja_pedidos, _hoja_abonos, _hoja_gastos, _hoja_telas):
        nombre, columnas, filas = armar(taller)
        _escribir_hoja(libro.create_sheet(nombre), columnas, filas)
    salida = BytesIO()
    libro.save(salida)
    return salida.getvalue()


def nombre_del_archivo(taller, hoy):
    """'taller-de-ejemplo-2026-11-13.xlsx': el nombre del taller sin tildes y la fecha."""
    return f"{slugify(taller.nombre) or 'taller'}-{hoy.isoformat()}.xlsx"
