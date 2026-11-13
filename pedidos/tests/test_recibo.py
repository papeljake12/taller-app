"""T09. Recibo de un abono en PDF."""

import re
from datetime import date

import pytest
from django.urls import reverse
from reportlab.pdfbase.pdfmetrics import stringWidth

from pedidos.recibo import datos_del_recibo, nombre_del_recibo, recibo_en_pdf
from tests import fabricas

pytestmark = pytest.mark.django_db


def textos_del_pdf(contenido):
    """Los textos que escribe el PDF, en orden.

    El PDF va sin comprimir: cada texto está entre paréntesis antes de "Tj". Las letras con
    tilde van como \\ más tres números (octal, en la codificación de Windows).
    """
    crudos = re.findall(rb"\(((?:\\.|[^\\)])*)\) Tj", contenido)

    def leer(crudo):
        bytes_ = bytearray()
        partes = re.finditer(rb"\\([0-7]{1,3})|\\(.)|(.)", crudo, re.DOTALL)
        for octal, escapado, letra in (p.groups() for p in partes):
            if octal:
                bytes_.append(int(octal, 8))
            else:
                bytes_ += escapado or letra
        return bytes_.decode("cp1252")

    return [leer(c) for c in crudos]


def url_recibo(abono):
    return reverse("pedidos:recibo", args=[abono.pedido_id, abono.pk])


@pytest.fixture
def pedido(taller):
    cliente = fabricas.crear_cliente(taller, nombre="Ferretería La Esquina")
    return fabricas.crear_pedido(
        taller, cliente=cliente, detalle="8 overoles con logo estampado", total=960_000
    )


def test_descarga_un_pdf_valido_con_cliente_valor_total_y_saldo(sesion_duena, taller, pedido):
    abono = fabricas.crear_abono(pedido, valor=480_000, fecha=date(2026, 10, 22))

    respuesta = sesion_duena.get(url_recibo(abono))

    assert respuesta.status_code == 200
    assert respuesta["Content-Type"] == "application/pdf"
    assert respuesta["Content-Disposition"] == (
        'attachment; filename="recibo-ferreteria-la-esquina-2026-10-22.pdf"'
    )
    assert respuesta.content.startswith(b"%PDF")
    assert respuesta.content.rstrip().endswith(b"%%EOF")
    textos = textos_del_pdf(respuesta.content)
    assert textos[:3] == [taller.nombre, "Recibo de abono", "Cliente"]
    for esperado in (
        "Ferretería La Esquina",
        "8 overoles con logo estampado",
        "Fecha del abono", "22 de octubre de 2026",
        "Valor de este abono", "$ 480.000",
        "Total del pedido", "$ 960.000",
        "Abonado hasta este recibo",
        "Saldo pendiente",
    ):
        assert esperado in textos, esperado
    # Abonado y saldo quedan en 480.000 cada uno.
    assert textos.count("$ 480.000") == 3
    assert textos[-1].startswith("Abono 1 de 1. Recibo generado el ")


def test_abonado_hasta_este_recibo_suma_en_orden_de_fecha_hasta_este_abono(pedido):
    # Se registran en desorden: cuenta la fecha, no el orden en que se anotaron.
    tercero = fabricas.crear_abono(pedido, valor=300_000, fecha=date(2026, 11, 9))
    primero = fabricas.crear_abono(pedido, valor=100_000, fecha=date(2026, 10, 1))
    segundo = fabricas.crear_abono(pedido, valor=200_000, fecha=date(2026, 10, 20))

    datos = datos_del_recibo(pedido, segundo, hoy=date(2026, 11, 12))

    assert datos["valor"] == "$ 200.000"
    assert datos["abonado"] == "$ 300.000"
    assert datos["saldo"] == "$ 660.000"
    assert datos["numero"] == "2 de 3"
    assert datos["hoy"] == "12 de noviembre de 2026"
    assert datos_del_recibo(pedido, primero)["numero"] == "1 de 3"
    assert datos_del_recibo(pedido, tercero)["abonado"] == "$ 600.000"


def test_el_saldo_del_recibo_nunca_es_negativo(pedido):
    abono = fabricas.crear_abono(pedido, valor=1_000_000)

    textos = textos_del_pdf(recibo_en_pdf(pedido, abono))

    assert "$ 0" in textos
    assert "$ 1.000.000" in textos


def test_sin_nombre_de_taller_dice_taller_de_confeccion(pedido):
    pedido.taller.nombre = ""
    abono = fabricas.crear_abono(pedido)

    assert textos_del_pdf(recibo_en_pdf(pedido, abono))[0] == "Taller de confección"


def test_un_detalle_largo_se_parte_en_lineas_sin_salirse(taller):
    detalle = "Vestidos de comparsa con lentejuelas, " * 6
    pedido = fabricas.crear_pedido(taller, detalle=detalle.strip()[:160])
    abono = fabricas.crear_abono(pedido)

    textos = textos_del_pdf(recibo_en_pdf(pedido, abono))

    lineas = [t for t in textos if t.startswith(("Vestidos", "lentejuelas", "con", "comparsa"))]
    assert 2 <= len(lineas) <= 3
    # Cada línea cabe entre los márgenes de la hoja (de 36 a 384 puntos).
    assert all(stringWidth(linea, "Helvetica", 12) <= 348 for linea in lineas)


def test_el_nombre_del_archivo_no_lleva_tildes_ni_espacios(taller):
    cliente = fabricas.crear_cliente(taller, nombre="Grupo de danza Tambores del Río / Ñ")
    pedido = fabricas.crear_pedido(taller, cliente=cliente)
    abono = fabricas.crear_abono(pedido, fecha=date(2026, 11, 3))

    nombre = nombre_del_recibo(pedido, abono)

    assert nombre == "recibo-grupo-de-danza-tambores-del-rio-n-2026-11-03.pdf"


def test_el_recibo_de_un_abono_de_otro_taller_responde_404(sesion_duena, pedido):
    ajeno = fabricas.crear_abono(fabricas.crear_pedido(fabricas.crear_taller()))

    assert sesion_duena.get(url_recibo(ajeno)).status_code == 404
    # Ni siquiera con el pedido propio en la dirección.
    url = reverse("pedidos:recibo", args=[pedido.pk, ajeno.pk])
    assert sesion_duena.get(url).status_code == 404


def test_el_recibo_de_un_abono_de_otro_pedido_responde_404(sesion_duena, taller, pedido):
    otro = fabricas.crear_abono(fabricas.crear_pedido(taller))

    url = reverse("pedidos:recibo", args=[pedido.pk, otro.pk])

    assert sesion_duena.get(url).status_code == 404


def test_sin_sesion_no_hay_recibo(client, pedido):
    abono = fabricas.crear_abono(pedido)

    respuesta = client.get(url_recibo(abono))

    assert respuesta.status_code == 302
    assert respuesta.url.startswith("/entrar/")
