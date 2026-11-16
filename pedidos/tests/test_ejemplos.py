"""El comando cargar_ejemplos (T22)."""

from datetime import date

import pytest
from django.core.management import CommandError, call_command

from cotizador.models import PrendaGuardada
from cuentas.models import Taller, Usuario
from finanzas.models import Gasto
from pedidos import ejemplos
from pedidos.models import Abono, Cliente, Material, Pedido, Talla
from telas.models import Tela, TelaPedido
from tests import fabricas

pytestmark = pytest.mark.django_db


@pytest.fixture(autouse=True)
def en_desarrollo(settings, tmp_path):
    settings.DEBUG = True
    settings.MEDIA_ROOT = tmp_path


def contar():
    return {
        modelo.__name__: modelo.objects.count()
        for modelo in (
            Cliente, Pedido, Abono, Talla, Material, Gasto, Tela, PrendaGuardada, TelaPedido,
        )
    }


def test_carga_los_ejemplos_en_el_taller_de_ejemplo():
    call_command("cargar_ejemplos", fecha=date(2026, 11, 11))

    taller = Taller.objects.get(nombre="Taller de ejemplo")
    assert contar() == {
        "Cliente": 6, "Pedido": 6, "Abono": 7, "Talla": 58, "Material": 10, "Gasto": 5,
        "Tela": 4, "PrendaGuardada": 4, "TelaPedido": 2,
    }
    assert set(Pedido.objects.values_list("taller", flat=True)) == {taller.pk}
    assert Pedido.objects.exclude(foto="").count() == 3


def test_cada_cliente_va_marcado_como_ejemplo():
    call_command("cargar_ejemplos")

    assert set(Cliente.objects.values_list("notas", flat=True)) == {"Dato de ejemplo."}
    assert not Cliente.objects.exclude(whatsapp="").exists()


def test_cargar_dos_veces_no_duplica_nada():
    call_command("cargar_ejemplos")
    primera = contar()

    call_command("cargar_ejemplos")

    assert contar() == primera
    assert Usuario.objects.filter(username__startswith="ejemplo.").count() == 4


def test_usa_la_duena_que_ya_tiene_el_taller():
    taller = fabricas.crear_taller(nombre="Taller de ejemplo")
    duena = fabricas.crear_usuaria(taller, username="dueña-real")

    call_command("cargar_ejemplos")

    assert set(Pedido.objects.values_list("creado_por", flat=True)) == {duena.pk}
    assert not Usuario.objects.filter(username="ejemplo.duena").exists()


def test_las_costureras_de_ejemplo_no_pueden_entrar_sin_contrasena():
    call_command("cargar_ejemplos")

    for nombre in ("Marta", "Yolima", "Carmen"):
        costurera = Usuario.objects.get(nombre_visible=nombre)
        assert costurera.rol == Usuario.Rol.COSTURERA
        assert not costurera.has_usable_password()


def test_no_toca_los_datos_de_otro_taller():
    otro = fabricas.crear_taller()
    fabricas.crear_pedido(otro)

    call_command("cargar_ejemplos")
    call_command("cargar_ejemplos")

    assert Pedido.objects.filter(taller=otro).count() == 1


def test_se_puede_cargar_en_otro_taller_por_su_nombre():
    call_command("cargar_ejemplos", taller="Taller de pruebas de David")

    assert Pedido.objects.filter(taller__nombre="Taller de pruebas de David").count() == 6


def test_avisa_si_una_costurera_de_ejemplo_es_de_otro_taller():
    call_command("cargar_ejemplos")

    with pytest.raises(CommandError, match="ya existe en otro taller"):
        call_command("cargar_ejemplos", taller="Otro taller")
    # Si falla, no deja creado el taller a medias.
    assert not Taller.objects.filter(nombre="Otro taller").exists()


def test_fuera_de_desarrollo_no_corre_sin_forzar(settings):
    settings.DEBUG = False

    with pytest.raises(CommandError, match="--forzar"):
        call_command("cargar_ejemplos")
    assert not Pedido.objects.exists()

    call_command("cargar_ejemplos", forzar=True)
    assert Pedido.objects.count() == 6


def test_al_recargar_borra_las_fotos_viejas(tmp_path):
    call_command("cargar_ejemplos")
    call_command("cargar_ejemplos")

    fotos = list((tmp_path / "pedidos" / "fotos").iterdir())
    assert len(fotos) == 3


def test_los_ejemplos_son_los_de_la_demo():
    # Los seis pedidos de demo/index.html, con los nombres de diseno/.
    assert [p.cliente for p in ejemplos.PEDIDOS] == [
        "Comparsa Brisa Caribe",
        "Restaurante El Fogón Costeño",
        "Colegio Nuevo Amanecer",
        "Ferretería La Esquina",
        "Grupo de danza Tambores del Río",
        "Marcela P.",
    ]
