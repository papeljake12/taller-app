"""Recibo de un abono en PDF (T09), hecho con ReportLab.

Tiene el mismo contenido y la misma forma que el recibo de la demo (demo/index.html:
datosRecibo y pdfRecibo): una hoja de 420 por 595 puntos (A5) con el nombre del taller,
"Recibo de abono", el cliente, el pedido, la fecha y el valor del abono, y abajo el total,
lo abonado hasta ese recibo y el saldo que quedó.

Solo usa las fuentes que trae ReportLab (Helvetica y Times), así que no descarga nada.
El PDF va sin comprimir: pesa poco y así las pruebas pueden leer su texto.
"""

from io import BytesIO

from django.utils import timezone
from django.utils.text import slugify
from reportlab.lib.utils import simpleSplit
from reportlab.pdfbase.pdfmetrics import stringWidth
from reportlab.pdfgen.canvas import Canvas

from config.piezas import dia_y_mes, pesos

# La hoja y sus márgenes, como en la demo.
ANCHO, ALTO = 420, 595
IZQUIERDA, DERECHA = 36, 384
COLUMNA_VALORES = 250
GRIS = 0.42  # los nombres de cada dato van en gris

NORMAL = "Helvetica"
NEGRITA = "Helvetica-Bold"
TITULO = "Times-Bold"

SIN_NOMBRE = "Taller de confección"


def fecha_del_recibo(fecha):
    """'5 de noviembre de 2026'."""
    return f"{dia_y_mes(fecha)} de {fecha.year}"


def datos_del_recibo(pedido, abono, hoy=None):
    """Lo que dice el recibo de `abono`, que es uno de los abonos de `pedido`.

    "Abonado hasta este recibo" suma los abonos del pedido en orden de fecha, desde el
    primero hasta este (incluido). El saldo es lo que faltaba después de este abono, y
    nunca baja de 0 (como en calculos.saldo).
    """
    abonos = list(pedido.abonos.all())  # en orden de fecha (Meta.ordering)
    posicion = next(i for i, a in enumerate(abonos) if a.pk == abono.pk)
    hasta = sum(a.valor for a in abonos[: posicion + 1])
    nombre = (getattr(pedido.taller, "nombre", "") or "").strip()
    return {
        "taller": nombre or SIN_NOMBRE,
        "cliente": pedido.cliente.nombre,
        "detalle": pedido.detalle,
        "fecha": fecha_del_recibo(abono.fecha),
        "valor": pesos(abono.valor),
        "total": pesos(pedido.total),
        "abonado": pesos(hasta),
        "saldo": pesos(max(0, pedido.total - hasta)),
        "numero": f"{posicion + 1} de {len(abonos)}",
        "hoy": fecha_del_recibo(hoy or timezone.localdate()),
    }


def nombre_del_recibo(pedido, abono):
    """'recibo-ferreteria-la-esquina-2026-11-05.pdf': sin tildes ni espacios."""
    cliente = slugify(pedido.cliente.nombre)[:40].strip("-") or "cliente"
    return f"recibo-{cliente}-{abono.fecha.isoformat()}.pdf"


def _tamano_que_cabe(texto, fuente, tamano, minimo=8):
    """El tamaño de letra más grande (hasta `tamano`) con el que el texto cabe en la hoja."""
    ancho = DERECHA - IZQUIERDA
    while tamano > minimo and stringWidth(texto, fuente, tamano) > ancho:
        tamano -= 1
    return tamano


def _lineas(texto, fuente, tamano, maximo):
    """El texto partido en líneas que caben en el ancho de la hoja, máximo `maximo`."""
    lineas = simpleSplit(texto, fuente, tamano, DERECHA - IZQUIERDA) or [""]
    if len(lineas) > maximo:
        lineas = lineas[:maximo]
        lineas[-1] = lineas[-1].rstrip(" .,") + "…"
    return lineas


def recibo_en_pdf(pedido, abono, hoy=None):
    """Los bytes del PDF del recibo."""
    datos = datos_del_recibo(pedido, abono, hoy)
    archivo = BytesIO()
    hoja = Canvas(archivo, pagesize=(ANCHO, ALTO), pageCompression=0)
    hoja.setTitle(f"Recibo de abono · {datos['cliente']}")
    hoja.setAuthor(datos["taller"])
    hoja.setSubject(datos["detalle"])

    def escribir(fuente, tamano, x, y, texto, gris=False):
        hoja.setFillGray(GRIS if gris else 0)
        hoja.setFont(fuente, tamano)
        hoja.drawString(x, y, texto)

    def linea(y, punteada=False):
        hoja.setLineWidth(0.9)
        hoja.setStrokeGray(0)
        if punteada:
            hoja.setDash(5, 4)
        else:
            hoja.setDash()
        hoja.line(IZQUIERDA, y, DERECHA, y)

    # Encabezado: el taller y el título.
    escribir(TITULO, _tamano_que_cabe(datos["taller"], TITULO, 14), IZQUIERDA, 545,
             datos["taller"])
    escribir(TITULO, 30, IZQUIERDA, 505, "Recibo de abono")
    linea(486, punteada=True)

    # Cliente (hasta 2 líneas) y pedido (hasta 3 líneas).
    escribir(NORMAL, 10, IZQUIERDA, 462, "Cliente", gris=True)
    y = 445
    for texto in _lineas(datos["cliente"], NEGRITA, 13, 2):
        escribir(NEGRITA, 13, IZQUIERDA, y, texto)
        y -= 17
    y -= 10
    escribir(NORMAL, 10, IZQUIERDA, y, "Pedido", gris=True)
    y -= 16
    for texto in _lineas(datos["detalle"], NORMAL, 12, 3):
        escribir(NORMAL, 12, IZQUIERDA, y, texto)
        y -= 16

    # Fecha y valor de este abono.
    y -= 10
    escribir(NORMAL, 10, IZQUIERDA, y, "Fecha del abono", gris=True)
    escribir(NORMAL, 12, IZQUIERDA, y - 16, datos["fecha"])
    y -= 46
    escribir(NORMAL, 10, IZQUIERDA, y, "Valor de este abono", gris=True)
    escribir(TITULO, _tamano_que_cabe(datos["valor"], TITULO, 30), IZQUIERDA, y - 32,
             datos["valor"])

    # Las cuentas del pedido hasta este recibo.
    y -= 54
    linea(y, punteada=True)
    y -= 26
    escribir(NORMAL, 11, IZQUIERDA, y, "Total del pedido")
    escribir(NORMAL, 11, COLUMNA_VALORES, y, datos["total"])
    y -= 20
    escribir(NORMAL, 11, IZQUIERDA, y, "Abonado hasta este recibo")
    escribir(NORMAL, 11, COLUMNA_VALORES, y, datos["abonado"])
    y -= 20
    escribir(NEGRITA, 11, IZQUIERDA, y, "Saldo pendiente")
    escribir(NEGRITA, 11, COLUMNA_VALORES, y, datos["saldo"])
    y -= 16
    linea(y)

    escribir(NORMAL, 9, IZQUIERDA, 40,
             f"Abono {datos['numero']}. Recibo generado el {datos['hoy']}.", gris=True)

    hoja.showPage()
    hoja.save()
    return archivo.getvalue()
