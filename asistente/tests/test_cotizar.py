"""T32 (carril C): cotizar, la cotización del asistente con los precios de "Mis prendas".

Se llama como la llamaría Claude: por `herramientas.ejecutar(nombre, entrada, ctx)`. La cuenta
tiene que dar lo mismo que el Cotizador: la misma fórmula (calculos.cotizar), los mismos
valores por defecto (FormularioCotizacion) y la misma pantalla al abrir el enlace.
"""

import json
import re
from dataclasses import asdict
from datetime import date
from decimal import Decimal
from pathlib import Path

import pytest
from django.db import connection
from django.template.loader import render_to_string
from django.test.utils import CaptureQueriesContext
from django.urls import reverse

from asistente import herramientas
from asistente.contratos import Contexto, ErrorDeHerramienta
from asistente.herramientas.cotizar import nombre_para_titulo
from cotizador.formularios import FormularioCotizacion, datos_con_la_prenda
from cotizador.models import PrendaGuardada
from tests import fabricas

PLANTILLAS = Path(__file__).resolve().parent.parent / "templates" / "asistente" / "tarjetas"

# La camisa polo de docs/06-pruebas.md (datos de ejemplo).
POLO = {"metros": Decimal("1.20"), "precio_metro": 18_000, "insumos": 3_000,
        "mano_obra": 12_000, "extra": 5_000}

CLAVES = {"prenda", "cantidad", "costo", "precio_unidad", "total", "abono", "ganancia",
          "metros_totales"}


def contexto(taller):
    return Contexto(taller=taller, usuaria=fabricas._duena_de(taller), hoy=date(2026, 11, 14),
                    pedido_actual=None, url_base="http://testserver/")


def cotizar(ctx, prenda, cantidad, ganancia_pct=None, abono_pct=None):
    return herramientas.ejecutar("cotizar", {
        "prenda": prenda, "cantidad": cantidad, "ganancia_pct": ganancia_pct,
        "abono_pct": abono_pct,
    }, ctx)


def dibujar(tarjeta):
    return render_to_string("asistente/tarjetas/cotizacion.html", {"tarjeta": tarjeta})


@pytest.fixture
def polo(taller):
    return fabricas.crear_prenda(taller, nombre="Camisa polo bordada", **POLO)


# --- La cuenta ------------------------------------------------------------------------------


def test_la_camisa_polo_da_las_cifras_de_las_pruebas(taller, polo):
    resultado = cotizar(contexto(taller), "camisa polo bordada", 20)

    assert resultado.datos == {
        "prenda": "Camisa polo bordada",
        "cantidad": 20,
        "costo": 41_600,
        "precio_unidad": 54_500,
        "total": 1_090_000,
        "abono": 545_000,
        "ganancia": 258_000,
        "metros_totales": "24.00",
    }
    assert resultado.revisado == "Usé tu prenda guardada «Camisa polo bordada»"


def test_los_datos_son_enteros_y_texto_sin_float(taller, polo):
    datos = cotizar(contexto(taller), "Camisa polo bordada", 7, 45, 30).datos

    assert set(datos) == CLAVES
    for clave in CLAVES - {"prenda", "metros_totales"}:
        assert type(datos[clave]) is int
    assert isinstance(datos["metros_totales"], str)
    assert json.loads(json.dumps(datos)) == datos
    assert "." not in json.dumps({k: v for k, v in datos.items() if k != "metros_totales"})


@pytest.mark.parametrize(("cantidad", "ganancia", "abono"), [
    (20, None, None), (1, 0, 0), (2000, 300, 100), (15, 45, 30), (3, 100, None),
])
def test_da_lo_mismo_que_el_formulario_del_cotizador(taller, polo, cantidad, ganancia, abono):
    resultado = cotizar(contexto(taller), "Camisa polo bordada", cantidad, ganancia, abono)

    datos = {"cantidad": str(cantidad), "tipo": "empresa"}
    if ganancia is not None:
        datos["ganancia"] = str(ganancia)
    else:
        datos["ganancia"] = str(FormularioCotizacion.base_fields["ganancia"].initial)
    if abono is not None:
        datos["abono"] = str(abono)
    else:
        datos["abono"] = str(FormularioCotizacion.base_fields["abono"].initial)
    prendas = PrendaGuardada.objects.del_taller(taller)
    form = FormularioCotizacion(datos_con_la_prenda(datos, polo), prendas=prendas)
    esperado = form.cotizacion()

    assert resultado.datos["costo"] == esperado.costo
    assert resultado.datos["precio_unidad"] == esperado.precio_unidad
    assert resultado.datos["total"] == esperado.total
    assert resultado.datos["abono"] == esperado.abono
    assert resultado.datos["ganancia"] == esperado.ganancia
    assert resultado.datos["metros_totales"] == str(esperado.metros_totales)


def test_sin_ganancia_ni_abono_usa_los_valores_del_formulario(taller, polo, monkeypatch):
    # Por defecto, 30 % y 50 %: los del Cotizador.
    assert FormularioCotizacion.base_fields["ganancia"].initial == 30
    assert FormularioCotizacion.base_fields["abono"].initial == 50
    con_los_de_siempre = cotizar(contexto(taller), "Camisa polo bordada", 20).datos
    assert con_los_de_siempre == cotizar(contexto(taller), "Camisa polo bordada", 20, 30, 50).datos

    # Se leen del formulario, no están copiados: si el Cotizador cambia, el asistente también.
    monkeypatch.setattr(FormularioCotizacion.base_fields["ganancia"], "initial", 100)
    monkeypatch.setattr(FormularioCotizacion.base_fields["abono"], "initial", 0)
    otros = cotizar(contexto(taller), "Camisa polo bordada", 20).datos
    assert otros["precio_unidad"] == 83_500  # 41.600 × 2 = 83.200, hacia arriba a 500
    assert otros["abono"] == 0


# --- El enlace al Cotizador -----------------------------------------------------------------


@pytest.mark.parametrize(("ganancia", "abono"), [(None, None), (45, 30), (0, 100)])
def test_el_enlace_abre_el_cotizador_con_el_mismo_total(sesion_duena, duena, ganancia, abono):
    prenda = fabricas.crear_prenda(duena.taller, nombre="Camisa polo bordada", **POLO)
    resultado = cotizar(contexto(duena.taller), "polo", 20, ganancia, abono)
    url = resultado.tarjeta.datos["url_cotizador"]

    assert url.startswith(reverse("cotizador:calcular") + "?")
    assert f"guardada={prenda.pk}" in url and "tipo=empresa" in url

    respuesta = sesion_duena.get(url)

    assert respuesta.status_code == 200
    cotizacion = respuesta.context["cotizacion"]
    assert cotizacion.total == resultado.datos["total"]
    assert cotizacion.abono == resultado.datos["abono"]
    assert cotizacion.precio_unidad == resultado.datos["precio_unidad"]
    html = respuesta.content.decode()
    total = re.search(r'cotizacion__total dinero">([^<]*)<', html).group(1)
    assert total == dibujar(resultado.tarjeta).split('cotizacion__total dinero">')[1].split("<")[0]
    # La prenda queda elegida en la pantalla, con su nombre.
    assert 'value="Camisa polo bordada"' in html


# --- Buscar la prenda -----------------------------------------------------------------------


def test_busca_sin_tildes_ni_mayusculas(taller):
    fabricas.crear_prenda(taller, nombre="Pantalón de dril", **POLO)

    for escrito in ("PANTALON DE DRIL", "pantalón", "  dril  "):
        assert cotizar(contexto(taller), escrito, 2).datos["prenda"] == "Pantalón de dril"


def test_un_nombre_exacto_gana_aunque_haya_otros_parecidos(taller):
    fabricas.crear_prenda(taller, nombre="Polo", **POLO)
    fabricas.crear_prenda(taller, nombre="Polo bordado", **POLO)

    assert cotizar(contexto(taller), "polo", 5).datos["prenda"] == "Polo"


def test_varias_coincidencias_dan_las_opciones_sin_tarjeta(taller):
    fabricas.crear_prenda(taller, nombre="Polo bordado", **POLO)
    fabricas.crear_prenda(taller, nombre="Polo estampado", **POLO)
    fabricas.crear_prenda(taller, nombre="Overol", **POLO)

    resultado = cotizar(contexto(taller), "polo", 5)

    assert resultado.datos == {"opciones": ["Polo bordado", "Polo estampado"]}
    assert resultado.tarjeta is None


def test_sin_coincidencias_el_error_dice_cuales_hay(taller):
    fabricas.crear_prenda(taller, nombre="Overol", **POLO)
    fabricas.crear_prenda(taller, nombre="Vestido de comparsa", **POLO)

    with pytest.raises(ErrorDeHerramienta) as error:
        cotizar(contexto(taller), "chaqueta", 5)

    assert "Overol, Vestido de comparsa" in str(error.value)


def test_sin_prendas_guardadas_lo_dice(taller):
    with pytest.raises(ErrorDeHerramienta, match="No hay prendas guardadas"):
        cotizar(contexto(taller), "polo", 5)


def test_una_prenda_de_otro_taller_no_existe(taller):
    otro = fabricas.crear_taller()
    fabricas.crear_prenda(otro, nombre="Camisa polo bordada", **POLO)
    fabricas.crear_prenda(taller, nombre="Overol", **POLO)

    with pytest.raises(ErrorDeHerramienta) as error:
        cotizar(contexto(taller), "Camisa polo bordada", 20)

    assert "Camisa polo" not in str(error.value).split("Las guardadas son:")[1]
    assert "Overol" in str(error.value)


def test_una_prenda_sin_costos_da_error(taller):
    fabricas.crear_prenda(taller, nombre="Por llenar")

    with pytest.raises(ErrorDeHerramienta, match="no tiene costos"):
        cotizar(contexto(taller), "Por llenar", 5)


# --- Rangos (los revisa ejecutar) -----------------------------------------------------------


@pytest.mark.parametrize(("cantidad", "ganancia", "abono"), [
    (0, None, None), (2001, None, None), (-3, None, None), (10, 301, None), (10, -1, None),
    (10, None, 101), (10, None, -1),
])
def test_lo_que_se_sale_de_rango_da_error(taller, polo, cantidad, ganancia, abono):
    with pytest.raises(ErrorDeHerramienta, match="debe estar entre"):
        cotizar(contexto(taller), "Camisa polo bordada", cantidad, ganancia, abono)


def test_la_cantidad_tiene_que_ser_un_entero(taller, polo):
    with pytest.raises(ErrorDeHerramienta, match="no es válido"):
        cotizar(contexto(taller), "Camisa polo bordada", "20")


# --- La tarjeta -----------------------------------------------------------------------------


def test_la_tarjeta_copia_la_de_la_maqueta(taller):
    # El vestido de diseno/asistente.html (datos de ejemplo): 15 dan $ 2.730.000.
    fabricas.crear_prenda(taller, nombre="Vestido de comparsa", metros=Decimal("3.5"),
                          precio_metro=20_000, insumos=30_000, mano_obra=40_000)
    resultado = cotizar(contexto(taller), "vestido de comparsa", 15)
    html = dibujar(resultado.tarjeta)

    assert resultado.tarjeta.tipo == "cotizacion"
    assert resultado.tarjeta.titulo == "Total de 15 vestidos de comparsa"
    assert '<h3 class="texto-2">Total de 15 vestidos de comparsa</h3>' in html
    assert '<p class="cotizacion__total dinero">$ 2.730.000</p>' in html
    assert ('<span>Precio por unidad</span><span class="dinero fuerte">$ 182.000</span>'
            in html)
    assert '<span>Costo de hacer una</span><span class="dinero">$ 140.000</span>' in html
    assert '<span>Tu ganancia en el pedido</span><span class="dinero">$ 630.000</span>' in html
    assert '<span>Abono para empezar</span><span class="dinero">$ 1.365.000</span>' in html
    assert "Abrir en el Cotizador" in html and "#cotizador" in html
    assert resultado.tarjeta.datos["url_cotizador"].replace("&", "&amp;") in html


def test_la_tarjeta_se_guarda_en_la_sesion_y_se_dibuja_igual(taller, polo):
    tarjeta = cotizar(contexto(taller), "Camisa polo bordada", 20).tarjeta
    de_la_sesion = json.loads(json.dumps(asdict(tarjeta)))

    assert de_la_sesion["datos"] == tarjeta.datos
    assert set(tarjeta.datos) == CLAVES | {"url_cotizador"}
    assert dibujar(de_la_sesion) == dibujar(tarjeta)


def test_el_nombre_de_la_prenda_sale_escapado(taller):
    fabricas.crear_prenda(taller, nombre="<script>x</script>", **POLO)

    html = dibujar(cotizar(contexto(taller), "<script>x</script>", 2).tarjeta)

    assert "<script>" not in html and "&lt;script&gt;" in html


def test_la_tarjeta_no_usa_safe():
    plantilla = (PLANTILLAS / "cotizacion.html").read_text(encoding="utf-8")
    assert "|safe" not in plantilla and "autoescape" not in plantilla


@pytest.mark.parametrize(("nombre", "cantidad", "esperado"), [
    ("Vestido de comparsa", 15, "vestidos de comparsa"),
    ("Vestido de comparsa", 1, "vestido de comparsa"),
    ("Pantalón de dril", 3, "pantalones de dril"),
    ("Overol", 8, "overoles"),
    ("Camisa polo", 20, "camisas polo"),
    ("Jeans", 4, "jeans"),
    ("Disfraz de abeja", 2, "disfraces de abeja"),
    ("Suéter", 2, "suéteres"),
    ("JEAN", 2, "JEAN"),
])
def test_el_titulo_pone_la_prenda_en_plural(nombre, cantidad, esperado):
    assert nombre_para_titulo(nombre, cantidad) == esperado


# --- No cambia nada -------------------------------------------------------------------------


def test_no_escribe_en_la_base(taller, polo):
    ctx = contexto(taller)
    antes = PrendaGuardada.objects.count()
    with CaptureQueriesContext(connection) as consultas:
        cotizar(ctx, "Camisa polo bordada", 20)
        cotizar(ctx, "polo", 20, 50, 20)
    escrituras = [
        c["sql"] for c in consultas.captured_queries
        if c["sql"].lstrip().upper().startswith(("INSERT", "UPDATE", "DELETE"))
    ]
    assert escrituras == []
    assert PrendaGuardada.objects.count() == antes
