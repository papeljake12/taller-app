"""Modelos de la tanda 2: las reglas de docs/02-modelo-de-datos.md que vive en la base."""

from decimal import Decimal

import pytest
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.db.models import ProtectedError

from finanzas.models import Gasto
from pedidos.models import Abono, Cliente, Material, Pedido, Talla
from telas.models import MovimientoTela
from tests import fabricas

pytestmark = pytest.mark.django_db


def falla_en_la_base(funcion):
    with pytest.raises(IntegrityError), transaction.atomic():
        funcion()


# --- Cliente --------------------------------------------------------------------------------


def test_el_nombre_del_cliente_no_se_repite_en_el_taller_sin_importar_mayusculas(taller):
    fabricas.crear_cliente(taller, nombre="Colegio Nuevo Amanecer")

    falla_en_la_base(lambda: fabricas.crear_cliente(taller, nombre="colegio nuevo amanecer"))


def test_dos_talleres_pueden_tener_un_cliente_con_el_mismo_nombre(taller):
    otro = fabricas.crear_taller()
    fabricas.crear_cliente(taller, nombre="Marcela P.")

    assert fabricas.crear_cliente(otro, nombre="Marcela P.").pk


def test_un_cliente_con_pedidos_no_se_puede_borrar(taller):
    pedido = fabricas.crear_pedido(taller)

    with pytest.raises(ProtectedError):
        pedido.cliente.delete()


def test_el_whatsapp_se_deja_solo_en_digitos(taller):
    cliente = fabricas.crear_cliente(taller, whatsapp="+57 300 123-4567")

    assert cliente.whatsapp_digitos == "573001234567"


# --- Pedido ---------------------------------------------------------------------------------


def test_un_pedido_nace_cotizado_con_el_enlace_de_tallas_abierto(taller):
    pedido = fabricas.crear_pedido(taller)

    assert pedido.estado == Pedido.Estado.COTIZADO
    assert pedido.tallas_abiertas is True
    assert len(pedido.token_tallas) == 32


def test_cada_pedido_tiene_su_propio_token(taller):
    tokens = {fabricas.crear_pedido(taller).token_tallas for _ in range(5)}

    assert len(tokens) == 5


def test_los_estados_van_en_el_orden_del_documento():
    assert Pedido.Estado.values == [
        "cotizado", "confirmado", "corte", "confeccion", "listo", "entregado",
    ]


@pytest.mark.parametrize("cantidad", [0, 2001])
def test_la_cantidad_va_de_1_a_2000(taller, cantidad):
    falla_en_la_base(lambda: fabricas.crear_pedido(taller, cantidad=cantidad))


def test_las_tallas_dependen_del_tallaje(taller):
    adulto = fabricas.crear_pedido(taller, tallaje=Pedido.Tallaje.ADULTO)
    nino = fabricas.crear_pedido(taller, tallaje=Pedido.Tallaje.NINO)

    assert adulto.opciones_de_talla == ("XS", "S", "M", "L", "XL", "XXL", "medida")
    assert nino.opciones_de_talla == ("4", "6", "8", "10", "12", "14", "16", "medida")


def test_el_cliente_y_la_encargada_deben_ser_del_mismo_taller(taller):
    otro = fabricas.crear_taller()
    pedido = fabricas.crear_pedido(taller)
    pedido.cliente = fabricas.crear_cliente(otro)
    pedido.encargada = fabricas.crear_usuaria(otro)

    with pytest.raises(ValidationError) as error:
        pedido.full_clean()

    assert set(error.value.message_dict) >= {"cliente", "encargada"}


def test_borrar_un_pedido_borra_sus_abonos_tallas_y_materiales(taller):
    pedido = fabricas.crear_pedido(taller)
    fabricas.crear_abono(pedido)
    fabricas.crear_talla(pedido)
    fabricas.crear_material(pedido)

    pedido.delete()

    assert not Abono.objects.exists()
    assert not Talla.objects.exists()
    assert not Material.objects.exists()


def test_borrar_un_pedido_deja_sus_gastos_sin_pedido(taller):
    pedido = fabricas.crear_pedido(taller)
    gasto = fabricas.crear_gasto(taller, pedido=pedido)

    pedido.delete()
    gasto.refresh_from_db()

    assert gasto.pedido is None


def test_si_se_borra_la_encargada_el_pedido_queda_sin_asignar(taller):
    costurera = fabricas.crear_usuaria(taller, rol="costurera")
    pedido = fabricas.crear_pedido(taller, encargada=costurera)

    costurera.delete()
    pedido.refresh_from_db()

    assert pedido.encargada is None


# --- Abono ----------------------------------------------------------------------------------


def test_un_abono_debe_ser_mayor_que_0(taller):
    pedido = fabricas.crear_pedido(taller)

    falla_en_la_base(lambda: fabricas.crear_abono(pedido, valor=0))


# --- Talla ----------------------------------------------------------------------------------


def test_a_la_medida_exige_pecho_cintura_y_cadera_en_la_base(taller):
    pedido = fabricas.crear_pedido(taller)

    falla_en_la_base(lambda: fabricas.crear_talla(pedido, talla="medida", pecho=90))


def test_a_la_medida_con_sus_medidas_se_guarda(taller):
    pedido = fabricas.crear_pedido(taller)

    talla = fabricas.crear_talla(
        pedido, talla="medida", pecho=Decimal("92.5"), cintura=78, cadera=100
    )

    assert talla.pk


def test_a_la_medida_sin_medidas_explica_cual_falta(taller):
    pedido = fabricas.crear_pedido(taller)
    talla = Talla(pedido=pedido, nombre="Laura", talla="medida", pecho=90)

    with pytest.raises(ValidationError) as error:
        talla.full_clean()

    assert set(error.value.message_dict) == {"cintura", "cadera"}


def test_la_talla_debe_ser_del_tallaje_del_pedido(taller):
    pedido = fabricas.crear_pedido(taller, tallaje=Pedido.Tallaje.NINO)
    talla = Talla(pedido=pedido, nombre="Laura", talla="XL")

    with pytest.raises(ValidationError) as error:
        talla.full_clean()

    assert "talla" in error.value.message_dict


# --- Telas y gastos -------------------------------------------------------------------------


def test_los_metros_de_una_tela_no_bajan_de_0(taller):
    falla_en_la_base(lambda: fabricas.crear_tela(taller, metros=-1))


def test_un_movimiento_de_tela_no_puede_ser_de_0_metros(taller):
    tela = fabricas.crear_tela(taller)

    falla_en_la_base(lambda: fabricas.crear_movimiento(tela, metros=0))


def test_borrar_una_tela_borra_su_historial(taller):
    tela = fabricas.crear_tela(taller)
    fabricas.crear_movimiento(tela, metros=5)
    fabricas.crear_movimiento(tela, metros=-2)

    tela.delete()

    assert not MovimientoTela.objects.exists()


def test_un_gasto_debe_ser_mayor_que_0(taller):
    falla_en_la_base(lambda: fabricas.crear_gasto(taller, valor=0))


def test_el_pedido_de_un_gasto_debe_ser_del_mismo_taller(taller):
    otro = fabricas.crear_taller()
    gasto = Gasto(
        taller=taller, concepto="Hilos", valor=1000, pedido=fabricas.crear_pedido(otro)
    )

    with pytest.raises(ValidationError) as error:
        gasto.full_clean()

    assert "pedido" in error.value.message_dict


# --- Cotizador ------------------------------------------------------------------------------


def test_una_prenda_guardada_no_se_repite_en_el_taller(taller):
    fabricas.crear_prenda(taller, nombre="Camisa polo bordada")

    falla_en_la_base(lambda: fabricas.crear_prenda(taller, nombre="Camisa polo bordada"))


# --- La plata va en enteros -----------------------------------------------------------------


@pytest.mark.parametrize(
    ("modelo", "campos"),
    [
        (Pedido, ["total"]),
        (Abono, ["valor"]),
        (Gasto, ["valor"]),
        ("cotizador.PrendaGuardada", ["precio_metro", "insumos", "mano_obra", "extra"]),
    ],
)
def test_la_plata_se_guarda_en_enteros(modelo, campos):
    from django.apps import apps
    from django.db import models

    if isinstance(modelo, str):
        modelo = apps.get_model(modelo)
    for campo in campos:
        assert isinstance(modelo._meta.get_field(campo), models.PositiveIntegerField), campo


def test_ningun_modelo_guarda_el_saldo():
    nombres = {f.name for f in Pedido._meta.get_fields()}

    assert not nombres & {"saldo", "abonado"}


def test_el_cliente_se_ordena_por_nombre(taller):
    fabricas.crear_cliente(taller, nombre="Zapatería")
    fabricas.crear_cliente(taller, nombre="Almacén")

    assert list(Cliente.objects.values_list("nombre", flat=True)) == ["Almacén", "Zapatería"]
