"""Aislamiento entre talleres: lo más importante de la aplicación (docs/06-pruebas.md).

PLANTILLA PARA LAS TAREAS SIGUIENTES
------------------------------------
Cada modelo nuevo que guarda datos de un taller se agrega a MODELOS_DE_TALLER, con una
función que crea un registro en el taller que recibe. Las pruebas de abajo corren solas
para cada modelo de la lista. Por ejemplo, en la tanda 2:

    pytest.param(Cliente, lambda taller: fabricas.crear_cliente(taller), id="Cliente"),

Además, cada pantalla nueva que muestra o cambia datos debe tener en sus propias pruebas
los tres casos de docs/06-pruebas.md: la lista no muestra lo del otro taller, ver algo del
otro taller responde 404, y editar o borrar algo del otro taller responde 404 sin cambiar
nada. tests/urls_aislamiento.py muestra cómo se arma una pantalla así.
"""

import pytest
from django.http import Http404
from django.test import RequestFactory
from django.urls import URLPattern, URLResolver, get_resolver

from asistente.models import BorradorUsado, ResumenDelDia, UsoAsistente
from cuentas.aislamiento import del_taller, obtener_o_404
from cotizador.models import PrendaGuardada
from cuentas.models import Usuario
from finanzas.models import Gasto
from pedidos.models import Abono, Cliente, Material, Pedido, Talla
from telas.models import MovimientoTela, Tela, TelaPedido
from tests import fabricas

MODELOS_DE_TALLER = [
    pytest.param(Usuario, lambda taller: fabricas.crear_usuaria(taller), id="Usuario"),
    pytest.param(Cliente, lambda taller: fabricas.crear_cliente(taller), id="Cliente"),
    pytest.param(Pedido, lambda taller: fabricas.crear_pedido(taller), id="Pedido"),
    pytest.param(
        Abono, lambda taller: fabricas.crear_abono(fabricas.crear_pedido(taller)), id="Abono"
    ),
    pytest.param(
        Talla, lambda taller: fabricas.crear_talla(fabricas.crear_pedido(taller)), id="Talla"
    ),
    pytest.param(
        Material,
        lambda taller: fabricas.crear_material(fabricas.crear_pedido(taller)),
        id="Material",
    ),
    pytest.param(Tela, lambda taller: fabricas.crear_tela(taller), id="Tela"),
    pytest.param(
        MovimientoTela,
        lambda taller: fabricas.crear_movimiento(fabricas.crear_tela(taller)),
        id="MovimientoTela",
    ),
    pytest.param(Gasto, lambda taller: fabricas.crear_gasto(taller), id="Gasto"),
    pytest.param(PrendaGuardada, lambda taller: fabricas.crear_prenda(taller), id="PrendaGuardada"),
    pytest.param(UsoAsistente, lambda taller: fabricas.crear_uso(taller), id="UsoAsistente"),
    pytest.param(
        TelaPedido,
        lambda taller: fabricas.crear_tela_pedido(fabricas.crear_pedido(taller)),
        id="TelaPedido",
    ),
    pytest.param(ResumenDelDia, lambda taller: fabricas.crear_resumen(taller), id="ResumenDelDia"),
    pytest.param(
        BorradorUsado, lambda taller: fabricas.crear_borrador_usado(taller), id="BorradorUsado"
    ),
]


@pytest.fixture
def taller_a(db):
    return fabricas.crear_taller(nombre="Taller A")


@pytest.fixture
def taller_b(db):
    return fabricas.crear_taller(nombre="Taller B")


def solicitud_de(usuaria):
    """Una petición como la que llega cuando esa usuaria abre una pantalla."""
    request = RequestFactory().get("/")
    request.user = usuaria
    request.taller = usuaria.taller
    return request


def pks(consulta):
    return set(consulta.values_list("pk", flat=True))


# --- Para cada modelo de la lista ---------------------------------------------------------


@pytest.mark.parametrize(("modelo", "crear"), MODELOS_DE_TALLER)
def test_cada_taller_ve_solo_lo_suyo(modelo, crear, taller_a, taller_b):
    de_a = {crear(taller_a).pk, crear(taller_a).pk}
    de_b = {crear(taller_b).pk, crear(taller_b).pk}

    assert pks(modelo.objects.del_taller(taller_a)) == de_a
    assert pks(modelo.objects.del_taller(taller_b)) == de_b


@pytest.mark.parametrize(("modelo", "crear"), MODELOS_DE_TALLER)
def test_sin_taller_no_se_ve_nada(modelo, crear, taller_a):
    crear(taller_a)

    assert not modelo.objects.del_taller(None).exists()


@pytest.mark.parametrize(("modelo", "crear"), MODELOS_DE_TALLER)
def test_pedir_un_registro_de_otro_taller_responde_404(modelo, crear, taller_a, taller_b):
    request = solicitud_de(fabricas.crear_usuaria(taller_a))
    propio = crear(taller_a)
    ajeno = crear(taller_b)

    assert obtener_o_404(request, modelo, pk=propio.pk) == propio
    with pytest.raises(Http404):
        obtener_o_404(request, modelo, pk=ajeno.pk)


@pytest.mark.parametrize(("modelo", "crear"), MODELOS_DE_TALLER)
def test_filtrar_una_consulta_ya_armada_tambien_respeta_el_taller(
    modelo, crear, taller_a, taller_b
):
    request = solicitud_de(fabricas.crear_usuaria(taller_a))
    ajeno = crear(taller_b)

    assert not del_taller(request, modelo.objects.filter(pk=ajeno.pk)).exists()


# --- De punta a punta, con pantallas de prueba ----------------------------------------------


@pytest.mark.urls("tests.urls_aislamiento")
def test_la_lista_de_una_usuaria_no_muestra_lo_del_otro_taller(client, taller_a, taller_b):
    ana = fabricas.crear_usuaria(taller_a, username="ana")
    fabricas.crear_usuaria(taller_a, username="alba")
    fabricas.crear_usuaria(taller_b, username="berta")
    client.force_login(ana)

    respuesta = client.get("/usuarias/")

    assert respuesta.status_code == 200
    assert respuesta.text.splitlines() == ["alba", "ana"]


@pytest.mark.urls("tests.urls_aislamiento")
def test_abrir_por_la_direccion_algo_del_otro_taller_responde_404(client, taller_a, taller_b):
    ana = fabricas.crear_usuaria(taller_a, username="ana")
    berta = fabricas.crear_usuaria(taller_b, username="berta")
    client.force_login(ana)

    assert client.get(f"/usuarias/{ana.pk}/").status_code == 200
    assert client.get(f"/usuarias/{berta.pk}/").status_code == 404
    # Un número que no existe responde igual: así no se sabe si es de otro taller.
    assert client.get("/usuarias/999999/").status_code == 404


# --- request.taller y el administrador ------------------------------------------------------


def test_cada_peticion_sabe_el_taller_de_la_usuaria(sesion_duena, taller):
    respuesta = sesion_duena.get("/")

    assert respuesta.status_code == 200
    assert respuesta.wsgi_request.taller == taller


def test_el_administrador_sin_taller_va_al_panel(sesion_administrador):
    respuesta = sesion_administrador.get("/")

    assert respuesta.status_code == 302
    assert respuesta.url == "/admin/"
    assert sesion_administrador.get("/admin/").status_code == 200


def test_el_administrador_puede_salir(sesion_administrador):
    respuesta = sesion_administrador.post("/salir/")

    assert respuesta.status_code == 302
    assert respuesta.url == "/entrar/"
    assert "_auth_user_id" not in sesion_administrador.session


# --- Ninguna pantalla nueva queda abierta sin querer ---------------------------------------

# Las únicas pantallas que se abren sin sesión. Si una tarea agrega otra pública, se agrega
# aquí a propósito. El formulario de tallas (T11) es público: lo abre el cliente con su enlace.
PANTALLAS_PUBLICAS = {"cuentas:entrar", "admin:login", "pedidos:publico_tallas"}


def nombres_de_pantallas_publicas(resolver=None, prefijo=""):
    resolver = resolver or get_resolver()
    publicas = set()
    for patron in resolver.url_patterns:
        if isinstance(patron, URLResolver):
            espacio = f"{prefijo}{patron.namespace}:" if patron.namespace else prefijo
            publicas |= nombres_de_pantallas_publicas(patron, espacio)
        elif isinstance(patron, URLPattern):
            if getattr(patron.callback, "login_required", True) is False:
                publicas.add(f"{prefijo}{patron.name}")
    return publicas


def test_solo_estas_pantallas_se_abren_sin_sesion():
    assert nombres_de_pantallas_publicas() == PANTALLAS_PUBLICAS
