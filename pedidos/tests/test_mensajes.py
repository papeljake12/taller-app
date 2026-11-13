"""Textos de los mensajes y enlace de WhatsApp (pedidos/mensajes.py)."""

from datetime import date
from urllib.parse import unquote

import pytest

from pedidos import calculos, ejemplos, mensajes
from pedidos.models import Pedido

pytestmark = pytest.mark.django_db

DIA = date(2026, 11, 11)


@pytest.fixture
def ejemplo(db):
    return ejemplos.cargar(hoy=DIA, con_fotos=False)


def pedido_de(taller, cliente):
    return Pedido.objects.get(taller=taller, cliente__nombre=cliente)


@pytest.mark.parametrize(
    ("numero", "esperado"),
    [
        ("300 123 4567", "https://wa.me/573001234567?text=Hola"),
        ("+57 300-123-4567", "https://wa.me/573001234567?text=Hola"),
        ("1 555 123 4567", "https://wa.me/15551234567?text=Hola"),
        ("12345", ""),
        ("", ""),
    ],
)
def test_enlace_de_whatsapp(numero, esperado):
    assert mensajes.enlace_whatsapp(numero, "Hola") == esperado


def test_el_enlace_lleva_el_texto_escrito():
    enlace = mensajes.enlace_whatsapp("3001234567", "Su pedido ya está listo. ¡Gracias!")

    assert unquote(enlace.split("text=")[1]) == "Su pedido ya está listo. ¡Gracias!"


def test_aviso_de_pedido_listo_con_saldo(ejemplo):
    tambores = pedido_de(ejemplo, "Grupo de danza Tambores del Río")

    assert mensajes.texto_listo(tambores) == (
        "Hola, le escribimos de Taller de ejemplo. Su pedido (15 polleras con blusa) ya está "
        "listo para entregar. Saldo pendiente: $ 750.000."
    )


def test_aviso_de_pedido_listo_sin_saldo(ejemplo):
    comparsa = pedido_de(ejemplo, "Comparsa Brisa Caribe")

    assert mensajes.texto_listo(comparsa).endswith("ya está listo para entregar.")


def test_recordatorio_del_saldo(ejemplo):
    restaurante = pedido_de(ejemplo, "Restaurante El Fogón Costeño")

    assert mensajes.texto_cobro(restaurante) == (
        "Hola, le escribimos de Taller de ejemplo. Su pedido (18 camisas polo bordadas y 18 "
        "delantales) tiene un saldo pendiente de $ 1.260.000. La entrega está programada "
        "para el 14 de dic. ¡Gracias!"
    )


def test_resumen_de_tallas(ejemplo):
    restaurante = pedido_de(ejemplo, "Restaurante El Fogón Costeño")

    assert mensajes.texto_tallas(restaurante) == (
        "Tallas: Restaurante El Fogón Costeño\n18 camisas polo bordadas y 18 delantales\n\n"
        "S: 3\nM: 6\nL: 3\nXL: 2\n\nRecibidas: 14 de 18 (faltan 4)"
    )


def test_dotacion_y_oferta(ejemplo):
    assert mensajes.texto_dotacion(ejemplo, DIA) == (
        "Hola, le escribimos de Taller de ejemplo. Se acerca la entrega de dotación del 20 de "
        "diciembre. ¿Le cotizamos los uniformes para su equipo?"
    )
    assert mensajes.texto_oferta(ejemplo).startswith("Hola, le escribimos de Taller de ejemplo.")


def test_un_taller_sin_nombre_firma_del_taller():
    class SinNombre:
        nombre = ""

    assert mensajes.firma(SinNombre()) == "del taller"


def test_cotizacion_para_copiar(ejemplo):
    cotizacion = calculos.cotizar("1,2", 18_000, 3_000, 12_000, 5_000, 30, 20, 50)

    texto = mensajes.texto_cotizacion(
        ejemplo, cotizacion, "Camisa polo bordada", cliente="Restaurante", entrega=date(2026, 12, 14)
    )

    assert texto == (
        "Cotización de Taller de ejemplo\nCliente: Restaurante\n20 × Camisa polo bordada\n"
        "Precio por unidad: $ 54.500\nTotal: $ 1.090.000\nAbono para empezar: $ 545.000\n"
        "Entrega estimada: 14 de dic"
    )


def test_preguntar_si_confirma(ejemplo):
    marcela = pedido_de(ejemplo, "Marcela P.")

    assert mensajes.texto_confirmar(marcela) == (
        "Hola, le escribimos de Taller de ejemplo. ¿Le confirmamos su pedido (Vestido de "
        "grado a la medida) por $ 380.000? Apenas nos confirme, empezamos."
    )


def test_aviso_de_atraso(ejemplo):
    ferreteria = pedido_de(ejemplo, "Ferretería La Esquina")

    assert mensajes.texto_atraso(ferreteria) == (
        "Hola, le escribimos de Taller de ejemplo. Su pedido (8 overoles con logo estampado) "
        "se nos demoró un poco. Le avisamos apenas esté listo. ¡Gracias por la paciencia!"
    )
