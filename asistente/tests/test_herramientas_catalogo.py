"""Las herramientas de telas y clientes del asistente (T27): telas y buscar_clientes.

Sobre los datos de ejemplo del día de las páginas de diseno/: las telas bajas son las mismas
del contador del menú y de la pantalla Telas, los clientes traen las cifras de la pantalla
Clientes, nada sale de otro taller y lo que va a Claude no lleva el WhatsApp ni las notas.
También se comprueba que ninguna herramienta de consulta escribe en la base y que ninguna
tarjeta usa `|safe`.
"""

import json
from datetime import timedelta
from pathlib import Path

import pytest
from django.db import connection
from django.test.utils import CaptureQueriesContext
from django.urls import reverse

from asistente import herramientas
from asistente.tests.test_herramientas_pedidos import (
    DIA_DEL_DISENO,
    contexto,
    pintar_las_dos,
    sin_float,
)
from pedidos import calculos, ejemplos
from pedidos.models import Pedido
from tests import fabricas

pytestmark = pytest.mark.django_db


@pytest.fixture
def ejemplo(db):
    return ejemplos.cargar(hoy=DIA_DEL_DISENO, con_fotos=False)


def telas(ctx, solo_bajas=False):
    return herramientas.ejecutar("telas", {"solo_bajas": solo_bajas}, ctx)


def clientes(ctx, texto=None, tipo=None):
    return herramientas.ejecutar("buscar_clientes", {"texto": texto, "tipo": tipo}, ctx)


# --- telas -------------------------------------------------------------------------------------


def test_telas_como_en_la_pantalla_telas(ejemplo):
    resultado = telas(contexto(ejemplo))

    assert resultado.datos == {
        "cantidad": 4,
        "metros": "60.00",
        "bajas": 2,
        # Primero las que se acaban, luego por nombre (calculos.telas_en_orden).
        "telas": [
            {"nombre": "Piqué blanco", "metros": "6.00", "minimo": "10.00", "baja": True},
            {"nombre": "Popelina blanca", "metros": "4.00", "minimo": "12.00", "baja": True},
            {"nombre": "Dril azul", "metros": "18.00", "minimo": "10.00", "baja": False},
            {"nombre": "Tela estampada para polleras", "metros": "32.00", "minimo": "8.00",
             "baja": False},
        ],
    }
    assert resultado.revisado == "Revisé tus telas"
    assert resultado.enlace.texto == "Ver las telas"
    assert resultado.enlace.url == reverse("telas:inicio")
    sin_float(resultado.datos)


def test_las_telas_bajas_son_las_del_contador_del_menu(ejemplo):
    resultado = telas(contexto(ejemplo), solo_bajas=True)

    bajas = [t["nombre"] for t in resultado.datos["telas"]]
    assert len(bajas) == calculos.contadores_del_menu(ejemplo, DIA_DEL_DISENO)["telas"] == 2
    assert sorted(bajas) == sorted(t.nombre for t in calculos.resumen_de_telas(ejemplo)["bajas"])
    assert resultado.revisado == "Revisé las telas que se están acabando"


def test_los_metros_van_como_texto_con_dos_decimales(taller):
    fabricas.crear_tela(taller, nombre="Lino", metros="6.5", minimo="0")

    datos = telas(contexto(taller)).datos

    assert datos["telas"] == [{"nombre": "Lino", "metros": "6.50", "minimo": "0.00",
                               "baja": False}]
    assert datos["metros"] == "6.50"
    sin_float(datos)


def test_telas_no_ve_las_de_otro_taller(ejemplo):
    otro = fabricas.crear_taller()
    fabricas.crear_tela(otro, nombre="Tela del otro taller", metros=1, minimo=5)

    del_ejemplo = telas(contexto(ejemplo)).datos
    del_otro = telas(contexto(otro)).datos

    assert "Tela del otro taller" not in json.dumps(del_ejemplo, ensure_ascii=False)
    assert del_ejemplo["cantidad"] == 4
    assert del_otro["cantidad"] == 1
    assert [t["nombre"] for t in del_otro["telas"]] == ["Tela del otro taller"]


def test_la_tarjeta_de_telas(ejemplo):
    resultado = telas(contexto(ejemplo))

    html = pintar_las_dos(resultado.tarjeta)

    assert "Piqué blanco" in html
    assert "6 m" in html and "32 m" in html  # el filtro `metros` de las pantallas
    assert "Se está acabando" in html and "etiqueta--ambar" in html
    assert "Suficiente" in html
    assert "etiqueta--rojo" not in html  # rojo solo para atrasos y deudas vencidas


def test_sin_telas_no_hay_tarjeta(taller):
    resultado = telas(contexto(taller))

    assert resultado.datos == {"cantidad": 0, "metros": "0.00", "bajas": 0, "telas": []}
    assert resultado.tarjeta is None


# --- buscar_clientes ---------------------------------------------------------------------------


def test_clientes_con_las_cifras_de_la_pantalla_clientes(ejemplo):
    resultado = clientes(contexto(ejemplo))

    datos = resultado.datos
    assert datos["total"] == datos["mostrados"] == 6
    cuentas = calculos.cuentas_de_clientes(ejemplo)
    assert [c["id"] for c in datos["clientes"]] == [c.cliente.pk for c in cuentas]
    por_nombre = {c["nombre"]: c for c in datos["clientes"]}
    colegio = por_nombre["Colegio Nuevo Amanecer"]
    assert colegio == {
        "id": colegio["id"],
        "nombre": "Colegio Nuevo Amanecer",
        "tipo": "colegio",
        "pedidos": 1,
        "ha_comprado": 4_800_000,
        "debe": 3_300_000,
        "deuda_vencida": False,
        "cotizacion_abierta": False,
        "tiene_whatsapp": False,
    }
    assert por_nombre["Ferretería La Esquina"]["deuda_vencida"] is True
    assert por_nombre["Marcela P."]["cotizacion_abierta"] is True
    assert por_nombre["Marcela P."]["debe"] == 0  # lo cotizado no se debe
    assert resultado.revisado == "Revisé tus clientes"
    assert resultado.enlace.url == reverse("pedidos:clientes")


def test_clientes_por_texto_y_por_tipo(ejemplo):
    ctx = contexto(ejemplo)

    assert [c["nombre"] for c in clientes(ctx, texto="ferreteria").datos["clientes"]] == [
        "Ferretería La Esquina"
    ]
    assert sorted(c["nombre"] for c in clientes(ctx, tipo="empresa").datos["clientes"]) == [
        "Ferretería La Esquina",
        "Restaurante El Fogón Costeño",
    ]
    assert clientes(ctx, texto="colegio", tipo="comparsa").datos["total"] == 0
    con_texto = clientes(ctx, texto="tambores")
    assert con_texto.revisado == "Busqué «tambores» en tus clientes"
    assert con_texto.enlace.url == reverse("pedidos:clientes") + "?q=tambores"


def test_el_whatsapp_no_se_busca_ni_se_manda(taller):
    fabricas.crear_cliente(taller, nombre="Comparsa Secreta", whatsapp="300 765 4321",
                           notas="Nota privada 7788")
    ctx = contexto(taller)

    todos = clientes(ctx)
    por_numero = clientes(ctx, texto="7654321")

    texto = json.dumps(todos.datos, ensure_ascii=False)
    assert "765" not in texto
    assert "Nota privada" not in texto
    assert todos.datos["clientes"][0]["tiene_whatsapp"] is True
    assert por_numero.datos["total"] == 0
    assert "765" not in json.dumps(todos.tarjeta.datos, ensure_ascii=False)
    sin_float(todos.datos)


def test_clientes_no_ve_los_de_otro_taller(ejemplo):
    otro = fabricas.crear_taller()
    fabricas.crear_cliente(otro, nombre="Colegio del otro taller")

    del_ejemplo = clientes(contexto(ejemplo), texto="colegio").datos
    del_otro = clientes(contexto(otro)).datos

    assert [c["nombre"] for c in del_ejemplo["clientes"]] == ["Colegio Nuevo Amanecer"]
    assert [c["nombre"] for c in del_otro["clientes"]] == ["Colegio del otro taller"]


def test_con_25_clientes_van_20(taller):
    for _ in range(25):
        fabricas.crear_cliente(taller)

    resultado = clientes(contexto(taller))

    assert resultado.datos["total"] == 25
    assert resultado.datos["mostrados"] == len(resultado.datos["clientes"]) == 20
    assert resultado.tarjeta.datos["mas"] == 19


def test_la_tarjeta_de_clientes(ejemplo):
    resultado = clientes(contexto(ejemplo))

    html = pintar_las_dos(resultado.tarjeta)

    assert "$ 3.300.000" in html
    assert 'href="/clientes/?q=Colegio+Nuevo+Amanecer"' in html
    assert "Vencida" in html and "etiqueta--rojo" in html  # Ferretería
    assert "Cotización abierta" in html  # Marcela P.
    assert "Al día" in html  # Brisa Caribe ya pagó


# --- Reglas para todas las herramientas de consulta ---------------------------------------------


CONSULTAS = [
    ("buscar_pedidos", {"texto": None, "filtro": None, "entrega_desde": None,
                        "entrega_hasta": None}),
    ("buscar_pedidos", {"texto": "colegio", "filtro": "saldo", "entrega_desde": "2026-11-01",
                        "entrega_hasta": "2027-03-01"}),
    ("ver_pedido", {"pedido_id": None}),
    ("entregas", {"desde": "2026-11-01", "hasta": "2026-12-31"}),
    ("telas", {"solo_bajas": False}),
    ("telas", {"solo_bajas": True}),
    ("buscar_clientes", {"texto": None, "tipo": None}),
    ("buscar_clientes", {"texto": "tambores", "tipo": "comparsa"}),
]


def consultar_todas(ctx, consultas):
    """Corre cada consulta y devuelve las sentencias que escribieron en la base."""
    with CaptureQueriesContext(connection) as sentencias:
        for nombre, entrada in consultas:
            resultado = herramientas.ejecutar(nombre, entrada, ctx)
            sin_float(resultado.datos)
            if resultado.tarjeta:
                sin_float(resultado.tarjeta.datos)
    return [
        q["sql"] for q in sentencias
        if q["sql"].lstrip().upper().startswith(("INSERT", "UPDATE", "DELETE"))
    ]


def test_ninguna_herramienta_de_consulta_escribe_en_la_base(ejemplo):
    ctx = contexto(ejemplo, pedido=Pedido.objects.del_taller(ejemplo).first())

    assert consultar_todas(ctx, CONSULTAS) == []


def test_los_enlaces_de_todas_salen_de_reverse(ejemplo):
    ctx = contexto(ejemplo, pedido=Pedido.objects.del_taller(ejemplo).first())
    raices = {reverse(n) for n in ("pedidos:lista", "pedidos:calendario", "pedidos:clientes",
                                   "telas:inicio", "finanzas:resumen")}

    for nombre, entrada in CONSULTAS:
        enlace = herramientas.ejecutar(nombre, entrada, ctx).enlace
        assert enlace.texto
        assert enlace.url.split("?")[0] in raices or enlace.url.startswith("/pedidos/")


PLANTILLAS = Path(__file__).resolve().parent.parent / "templates" / "asistente" / "tarjetas"
TARJETAS_DE_CONSULTA = ("pedidos", "pedido", "entregas", "telas", "clientes")


def revisar_plantilla(tipo):
    """La plantilla de la tarjeta no se salta el escapado y usa las piezas del diseño."""
    texto = (PLANTILLAS / f"{tipo}.html").read_text(encoding="utf-8")

    assert "|safe" not in texto
    assert "autoescape" not in texto
    assert "{% load piezas %}" in texto
    assert 'class="tarjeta mensaje__tarjeta"' in texto


@pytest.mark.parametrize("tipo", TARJETAS_DE_CONSULTA)
def test_ninguna_tarjeta_se_salta_el_escapado(tipo):
    revisar_plantilla(tipo)


def test_un_nombre_con_html_sale_escapado_en_la_tarjeta(taller):
    fabricas.crear_cliente(taller, nombre="<b>Cliente</b><script>x()</script>")

    html = pintar_las_dos(clientes(contexto(taller)).tarjeta)

    assert "<script>" not in html
    assert "&lt;script&gt;" in html


def test_una_fecha_relativa_usa_el_hoy_del_contexto(ejemplo):
    # Un día después del diseño, la Ferretería va 3 días atrasada.
    ctx = contexto(ejemplo, hoy=DIA_DEL_DISENO + timedelta(days=1))

    datos = herramientas.ejecutar(
        "buscar_pedidos",
        {"texto": "ferreteria", "filtro": "atrasados", "entrega_desde": None,
         "entrega_hasta": None},
        ctx,
    ).datos

    assert datos["pedidos"][0]["dias_para_entrega"] == -3
