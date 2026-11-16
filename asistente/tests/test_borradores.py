"""El borrador firmado (tanda 8, T38): lo arma una herramienta, lo abre `confirmar`.

Reglas: docs/13-plan-tanda-8.md, sección 1.1. La firma lleva el taller, la usuaria, una clave
al azar y las acciones; vence a las dos horas, sirve una sola vez y nunca va a Claude.
"""

import json

import pytest
from django.core import signing
from django.utils import timezone

from asistente import borradores
from asistente.contratos import Contexto, Fila
from asistente.conversacion import contexto
from tests import fabricas

pytestmark = pytest.mark.django_db

ACCIONES = [
    {"tipo": "gasto", "datos": {"concepto": "Recibo de agua", "categoria": "servicios",
                                "valor": 65_000, "fecha": None, "pedido": None}},
]
FILAS = [Fila("Gasto de hoy", "Recibo de agua · Servicios", 65_000)]


def contexto_de(usuaria):
    return Contexto(taller=usuaria.taller, usuaria=usuaria, hoy=timezone.localdate(),
                    pedido_actual=None, url_base="http://testserver/")


@pytest.fixture
def ctx(duena):
    return contexto_de(duena)


def test_la_tarjeta_nace_pendiente_con_sus_filas_y_su_firma(ctx):
    tarjeta = borradores.armar(ctx, ACCIONES, FILAS)

    assert tarjeta.tipo == "borrador" and tarjeta.titulo == "Para guardar"
    assert tarjeta.datos["estado"] == "pendiente"
    assert len(tarjeta.datos["clave"]) == 32
    assert tarjeta.datos["filas"] == [
        {"titulo": "Gasto de hoy", "detalle": "Recibo de agua · Servicios", "valor": 65_000,
         "aviso": ""},
    ]
    # Cabe en la sesión tal cual.
    json.dumps(tarjeta.datos)


def test_claude_ve_las_filas_pero_nunca_la_firma_ni_la_clave(ctx):
    resultado = borradores.resultado(ctx, ACCIONES, FILAS, "Preparé el gasto")
    para_claude = json.dumps(resultado.datos, ensure_ascii=False)

    assert resultado.datos["borrador"] == "listo"
    assert "Recibo de agua" in para_claude
    assert resultado.tarjeta.datos["firma"] not in para_claude
    assert resultado.tarjeta.datos["clave"] not in para_claude
    assert "No digas que quedó guardado" in para_claude


def test_abrir_devuelve_lo_mismo_que_se_firmo(ctx):
    tarjeta = borradores.armar(ctx, ACCIONES, FILAS)

    clave, acciones = borradores.abrir(tarjeta.datos["firma"], ctx)

    assert clave == tarjeta.datos["clave"]
    assert acciones == ACCIONES


def test_un_borrador_de_otra_usuaria_o_de_otro_taller_no_sirve(ctx, taller):
    firma = borradores.armar(ctx, ACCIONES, FILAS).datos["firma"]
    otra_del_mismo_taller = contexto_de(fabricas.crear_usuaria(taller))
    de_otro_taller = contexto_de(fabricas.crear_usuaria(fabricas.crear_taller()))

    for ajeno in (otra_del_mismo_taller, de_otro_taller):
        with pytest.raises(borradores.BorradorInvalido) as error:
            borradores.abrir(firma, ajeno)
        assert error.value.motivo == "ajeno"


def test_una_firma_cambiada_en_el_navegador_no_sirve(ctx):
    firma = borradores.armar(ctx, ACCIONES, FILAS).datos["firma"]
    datos = signing.loads(firma, salt=borradores.SAL)
    datos["a"][0]["datos"]["valor"] = 1
    falsa = signing.dumps(datos, salt="otra-sal", compress=True)

    for mala in (falsa, firma[:-3] + "abc", "", "cualquier cosa"):
        with pytest.raises(borradores.BorradorInvalido) as error:
            borradores.abrir(mala, ctx)
        assert error.value.motivo == "danado"


def test_un_borrador_vencido_no_sirve(ctx, monkeypatch):
    firma = borradores.armar(ctx, ACCIONES, FILAS).datos["firma"]
    monkeypatch.setattr(borradores, "VIGENCIA_SEGUNDOS", -1)

    with pytest.raises(borradores.BorradorInvalido) as error:
        borradores.abrir(firma, ctx)
    assert error.value.motivo == "vencido"
    assert str(error.value) == "Este borrador venció. Pídemelo otra vez."


def test_vence_a_las_dos_horas():
    assert borradores.VIGENCIA_SEGUNDOS == 2 * 60 * 60


def test_un_borrador_ya_guardado_no_sirve_otra_vez(ctx, taller):
    tarjeta = borradores.armar(ctx, ACCIONES, FILAS)
    fabricas.crear_borrador_usado(taller, clave=tarjeta.datos["clave"])

    with pytest.raises(borradores.BorradorInvalido) as error:
        borradores.abrir(tarjeta.datos["firma"], ctx)
    assert error.value.motivo == "usado"


@pytest.mark.parametrize("acciones", [
    [],
    [{"tipo": "borrar", "datos": {}}],
    [{"tipo": "abono", "datos": {"pedido": "@0", "valor": 1}}],  # apunta a sí misma
    [{"tipo": "abono", "datos": {"pedido": "@1", "valor": 1}},
     {"tipo": "pedido", "datos": {}}],  # apunta a una que viene después
])
def test_no_se_arma_un_borrador_raro(ctx, acciones):
    with pytest.raises(ValueError):
        borradores.armar(ctx, acciones, FILAS)


def test_no_existe_una_accion_para_borrar():
    assert not any(p in tipo for tipo in borradores.TIPOS for p in ("borrar", "quitar", "elimin"))


def test_varios_parecidos_dan_opciones_sin_borrador():
    resultado = borradores.opciones(
        "pedido", [(4, "40 uniformes de diario"), (9, "30 uniformes de diario")],
        "Revisé los pedidos de Colegio Nuevo Amanecer",
    )

    assert resultado.datos == {
        "escoger": "pedido",
        "opciones": [{"id": 4, "nombre": "40 uniformes de diario"},
                     {"id": 9, "nombre": "30 uniformes de diario"}],
    }
    assert resultado.tarjeta.tipo == "opciones"
    assert resultado.tarjeta.datos == {"opciones": ["40 uniformes de diario",
                                                    "30 uniformes de diario"]}


def test_lo_guardado_se_le_cuenta_a_claude_en_el_mensaje_del_sistema(ctx):
    sin_nota = contexto(ctx, "La dueña está en Hoy.")
    con_nota = contexto(ctx, "La dueña está en Hoy.", "abono de $ 300.000 al pedido 7")

    assert "Guardar" not in sin_nota
    assert con_nota.startswith(sin_nota)
    assert con_nota.endswith(
        "Desde tu última respuesta, la dueña tocó Guardar y quedó guardado: "
        "abono de $ 300.000 al pedido 7."
    )
