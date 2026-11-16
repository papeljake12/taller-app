"""T39 (carril A): proponer_pedido, el borrador del pedido nuevo con su cliente, abono y tela.

Reglas: docs/13-plan-tanda-8.md, secciones 1.2, 1.6 y "T39 (A)". La herramienta no escribe en
la base: arma un borrador. Las cifras salen de la aplicación (Cotizador, calculos.falta_tela),
las reglas de las pantallas (NuevoPedidoForm, FormularioAbono) y lo de otro taller no se toca.
"""

import json
from dataclasses import asdict
from datetime import date, timedelta
from decimal import Decimal

import pytest
from django.urls import reverse
from django.utils import timezone

from asistente import borradores, guardar, herramientas, vistas
from asistente.contratos import Contexto, ErrorDeHerramienta, Resultado
from asistente.guardar import NoSeGuardo
from asistente.herramientas.pedido_nuevo import proponer_pedido
from asistente.models import BorradorUsado
from cotizador.formularios import FormularioCotizacion, datos_con_la_prenda
from cotizador.models import PrendaGuardada
from finanzas.models import Gasto
from pedidos.models import Abono, Cliente, Pedido
from telas.models import TelaPedido
from tests import fabricas

pytestmark = pytest.mark.django_db

HTMX = {"HTTP_HX_REQUEST": "true"}
HOY = date(2026, 11, 15)
ENTREGA = date(2026, 12, 15)

# El pedido de las 10:30 de diseno/asistente-agente.html (datos de ejemplo).
UNIFORME = {"metros": Decimal("2.20"), "precio_metro": 16_000, "insumos": 4_000,
            "mano_obra": 20_000, "extra": 0}


def contexto(usuaria, hoy=HOY):
    return Contexto(taller=usuaria.taller, usuaria=usuaria, hoy=hoy, pedido_actual=None,
                    url_base="http://testserver/")


def entrada(**cambios):
    """Lo que manda Claude: con 0 y "" donde no hay nada (docs/13, sección 1.6)."""
    return {
        "cliente": "Colegio Nuevo Amanecer", "cliente_id": 0, "tipo_cliente": "colegio",
        "detalle": "30 uniformes de diario", "cantidad": 30, "tallaje": "nino",
        "fecha_entrega": ENTREGA.isoformat(), "prenda": "Uniforme de diario", "total": 0,
        "abono": 500_000, "tela": "Dril azul", "metros": "", **cambios,
    }


def proponer(ctx, **cambios):
    return herramientas.ejecutar("proponer_pedido", entrada(**cambios), ctx)


def directo(ctx, **cambios):
    """La función sin pasar por el esquema (para entradas que el esquema ya no deja pasar)."""
    datos = {"cliente": "Colegio Nuevo Amanecer", "cliente_id": None, "tipo_cliente": "colegio",
             "detalle": "30 uniformes de diario", "cantidad": 30, "tallaje": "nino",
             "fecha_entrega": ENTREGA, "prenda": None, "total": 2_310_000, "abono": None,
             "tela": None, "metros": None, **cambios}
    return proponer_pedido(ctx, **datos)


def cuenta():
    return (Pedido.objects.count(), Abono.objects.count(), TelaPedido.objects.count(),
            Cliente.objects.count(), Gasto.objects.count(), BorradorUsado.objects.count())


def filas(resultado):
    return {f["titulo"]: f for f in resultado.datos["filas"]}


def acciones_de(resultado, ctx):
    _, acciones = borradores.abrir(resultado.tarjeta.datos["firma"], ctx)
    return acciones


def flotantes(valor):
    if isinstance(valor, float):
        return True
    if isinstance(valor, dict):
        return any(flotantes(v) for v in valor.values())
    if isinstance(valor, list | tuple):
        return any(flotantes(v) for v in valor)
    return False


@pytest.fixture
def ctx(duena):
    return contexto(duena)


@pytest.fixture
def uniforme(taller):
    return fabricas.crear_prenda(taller, nombre="Uniforme de diario", **UNIFORME)


@pytest.fixture
def dril(taller):
    return fabricas.crear_tela(taller, nombre="Dril azul", metros=18)


@pytest.fixture
def colegio(taller):
    return fabricas.crear_cliente(taller, nombre="Colegio Nuevo Amanecer", tipo="colegio",
                                  whatsapp="300 123 4567", notas="Notas privadas del colegio")


# --- El ejemplo de la maqueta -----------------------------------------------------------------


def test_el_pedido_de_la_maqueta(ctx, uniforme, dril, colegio):
    resultado = proponer(ctx)

    assert resultado.datos["borrador"] == "listo"
    assert resultado.revisado == (
        "Revisé tus clientes, tu prenda «Uniforme de diario» y tus telas")
    assert [f["titulo"] for f in resultado.datos["filas"]] == [
        "Pedido nuevo", "Abono de hoy", "Tela", "Tallas"]
    fila = filas(resultado)
    assert fila["Pedido nuevo"] == {
        "titulo": "Pedido nuevo",
        "detalle": "Colegio Nuevo Amanecer · 30 uniformes de diario · Niño (4 a 16) · "
                   "Se entrega el 15 de diciembre · Confirmado, porque dejó abono",
        "valor": 2_310_000, "aviso": ""}
    assert fila["Abono de hoy"] == {
        "titulo": "Abono de hoy", "detalle": "Después del abono falta $ 1.810.000",
        "valor": 500_000, "aviso": ""}
    assert fila["Tela"] == {
        "titulo": "Tela",
        "detalle": "66 m de dril azul (2,2 m por uniforme). Tienes 18 m.",
        "valor": None, "aviso": "Te faltan 48 m de dril azul."}
    assert fila["Tallas"]["detalle"] == "El enlace para pedir las tallas queda listo al guardar."
    assert resultado.tarjeta.tipo == "borrador"
    assert resultado.tarjeta.datos["estado"] == "pendiente"


def test_las_acciones_llevan_los_datos_de_la_base(ctx, uniforme, dril, colegio):
    resultado = proponer(ctx)

    assert acciones_de(resultado, ctx) == [
        {"tipo": "pedido", "datos": {
            "cliente": "Colegio Nuevo Amanecer", "cliente_id": colegio.pk, "tipo": "colegio",
            "detalle": "30 uniformes de diario", "cantidad": 30, "tallaje": "nino",
            "fecha_entrega": "2026-12-15", "total": 2_310_000}},
        {"tipo": "etapa", "datos": {"pedido": "@0", "estado": "confirmado"}},
        {"tipo": "abono", "datos": {"pedido": "@0", "valor": 500_000, "fecha": None}},
        {"tipo": "tela_pedido", "datos": {"pedido": "@0", "tela": dril.pk, "metros": "66.00"}},
    ]


def test_sin_tela_ni_abono_solo_el_pedido_y_las_tallas(ctx, uniforme, colegio):
    resultado = proponer(ctx, abono=0, tela="")

    assert [f["titulo"] for f in resultado.datos["filas"]] == ["Pedido nuevo", "Tallas"]
    assert "Confirmado" not in filas(resultado)["Pedido nuevo"]["detalle"]
    assert [a["tipo"] for a in acciones_de(resultado, ctx)] == ["pedido"]
    assert resultado.revisado == "Revisé tus clientes y tu prenda «Uniforme de diario»"


def test_con_otro_anio_la_fecha_lo_dice(ctx, uniforme, colegio):
    resultado = proponer(ctx, fecha_entrega="2027-01-20", abono=0, tela="")

    assert "Se entrega el 20 de enero de 2027" in filas(resultado)["Pedido nuevo"]["detalle"]


# --- El cliente -------------------------------------------------------------------------------


def test_el_cliente_que_ya_existe_con_otras_mayusculas_no_se_repite(ctx, sesion_duena, prendido,
                                                                     uniforme, colegio):
    resultado = proponer(ctx, cliente="  colegio   NUEVO amanecer ", tipo_cliente="",
                         abono=0, tela="")

    pedido = acciones_de(resultado, ctx)[0]["datos"]
    assert (pedido["cliente_id"], pedido["cliente"], pedido["tipo"]) == (
        colegio.pk, "Colegio Nuevo Amanecer", "colegio")
    assert "Cliente nuevo" not in filas(resultado)["Pedido nuevo"]["detalle"]

    confirmar(sesion_duena, resultado)
    assert Cliente.objects.count() == 1
    assert Pedido.objects.get().cliente == colegio


def test_el_cliente_sin_tildes_es_el_mismo(ctx, taller, uniforme):
    ferreteria = fabricas.crear_cliente(taller, nombre="Ferretería La Esquina", tipo="empresa")

    resultado = proponer(ctx, cliente="ferreteria la esquina", tipo_cliente="", abono=0, tela="")

    assert acciones_de(resultado, ctx)[0]["datos"]["cliente_id"] == ferreteria.pk


def test_el_unico_parecido_es_ese(ctx, uniforme, colegio):
    resultado = proponer(ctx, cliente="nuevo amanecer", tipo_cliente="", abono=0, tela="")

    assert acciones_de(resultado, ctx)[0]["datos"]["cliente_id"] == colegio.pk


def test_con_el_id_usa_ese_cliente(ctx, uniforme, colegio):
    resultado = proponer(ctx, cliente="el colegio", cliente_id=colegio.pk, tipo_cliente="",
                         abono=0, tela="")

    datos = acciones_de(resultado, ctx)[0]["datos"]
    assert (datos["cliente_id"], datos["cliente"]) == (colegio.pk, "Colegio Nuevo Amanecer")


def test_cliente_nuevo_sin_tipo_pide_el_tipo(ctx, uniforme):
    antes = cuenta()

    with pytest.raises(ErrorDeHerramienta) as error:
        proponer(ctx, tipo_cliente="")

    assert str(error.value) == (
        "«Colegio Nuevo Amanecer» es un cliente nuevo: pregúntale qué tipo de cliente es "
        "(comparsa, empresa, colegio o particular).")
    assert cuenta() == antes


def test_cliente_nuevo_con_tipo(ctx, uniforme):
    resultado = proponer(ctx, abono=0, tela="")

    datos = acciones_de(resultado, ctx)[0]["datos"]
    assert (datos["cliente_id"], datos["tipo"]) == (None, "colegio")
    assert filas(resultado)["Pedido nuevo"]["detalle"].endswith(" · Cliente nuevo")


def test_dos_clientes_parecidos_dan_opciones_sin_borrador(ctx, taller, uniforme):
    uno = fabricas.crear_cliente(taller, nombre="Colegio Nuevo Amanecer", tipo="colegio")
    otro = fabricas.crear_cliente(taller, nombre="Colegio San José", tipo="colegio")

    resultado = proponer(ctx, cliente="colegio", tipo_cliente="")

    assert resultado.datos == {"escoger": "cliente", "opciones": [
        {"id": uno.pk, "nombre": "Colegio Nuevo Amanecer"},
        {"id": otro.pk, "nombre": "Colegio San José"}]}
    assert resultado.tarjeta.tipo == "opciones"
    assert "firma" not in resultado.tarjeta.datos


def test_el_cliente_de_otro_taller_no_se_toca(ctx, sesion_duena, prendido, uniforme):
    otro_taller = fabricas.crear_taller()
    ajeno = fabricas.crear_cliente(otro_taller, nombre="Colegio Nuevo Amanecer", tipo="empresa",
                                   whatsapp="311 000 0000")

    # Por id: no existe para ella.
    with pytest.raises(ErrorDeHerramienta, match="No encontré ese cliente."):
        proponer(ctx, cliente_id=ajeno.pk)

    # Por nombre: es un cliente nuevo de su taller.
    resultado = proponer(ctx, tela="")
    assert acciones_de(resultado, ctx)[0]["datos"]["cliente_id"] is None
    confirmar(sesion_duena, resultado)

    pedido = Pedido.objects.get()
    assert pedido.cliente != ajeno and pedido.cliente.taller == prendido
    ajeno.refresh_from_db()
    assert (ajeno.tipo, ajeno.whatsapp, ajeno.pedidos.count()) == ("empresa", "311 000 0000", 0)


# --- La prenda y el total ---------------------------------------------------------------------


def test_sin_total_es_el_del_cotizador(ctx, taller, uniforme, colegio):
    resultado = proponer(ctx, cantidad=17, abono=0, tela="")

    datos = {"cantidad": "17", "tipo": "empresa",
             "ganancia": str(FormularioCotizacion.base_fields["ganancia"].initial),
             "abono": str(FormularioCotizacion.base_fields["abono"].initial)}
    form = FormularioCotizacion(datos_con_la_prenda(datos, uniforme),
                                prendas=PrendaGuardada.objects.del_taller(taller))
    assert FormularioCotizacion.base_fields["ganancia"].initial == 30
    assert filas(resultado)["Pedido nuevo"]["valor"] == form.cotizacion().total
    assert acciones_de(resultado, ctx)[0]["datos"]["total"] == form.cotizacion().total


def test_sin_total_es_el_que_muestra_el_cotizador(ctx, sesion_duena, uniforme, colegio):
    resultado = proponer(ctx, abono=0, tela="")

    respuesta = sesion_duena.get(reverse("cotizador:calcular"), {
        "guardada": uniforme.pk, "cantidad": 30, "ganancia": 30, "abono": 50, "tipo": "empresa",
    })
    assert respuesta.status_code == 200
    assert respuesta.context["cotizacion"].total == 2_310_000
    assert filas(resultado)["Pedido nuevo"]["valor"] == 2_310_000


def test_con_total_manda_el_de_ella(ctx, uniforme, dril, colegio):
    resultado = proponer(ctx, total=2_000_000)

    assert filas(resultado)["Pedido nuevo"]["valor"] == 2_000_000
    assert filas(resultado)["Abono de hoy"]["detalle"] == "Después del abono falta $ 1.500.000"
    assert acciones_de(resultado, ctx)[0]["datos"]["total"] == 2_000_000


def test_sin_total_ni_prenda_pide_el_total(ctx, colegio):
    with pytest.raises(ErrorDeHerramienta) as error:
        proponer(ctx, prenda="", tela="")

    assert str(error.value) == (
        "Falta el total: pregúntale cuánto cobra o qué prenda guardada usar.")


def test_dos_prendas_parecidas_dan_opciones(ctx, taller, colegio):
    diario = fabricas.crear_prenda(taller, nombre="Uniforme de diario", **UNIFORME)
    gala = fabricas.crear_prenda(taller, nombre="Uniforme de gala", **UNIFORME)

    resultado = proponer(ctx, prenda="uniforme")

    assert resultado.datos == {"escoger": "prenda", "opciones": [
        {"id": diario.pk, "nombre": "Uniforme de diario"},
        {"id": gala.pk, "nombre": "Uniforme de gala"}]}
    assert resultado.tarjeta.tipo == "opciones"


def test_la_prenda_que_no_existe_da_error(ctx, uniforme, colegio):
    with pytest.raises(ErrorDeHerramienta, match="No hay una prenda guardada que se llame"):
        proponer(ctx, prenda="Overol")


def test_la_prenda_de_otro_taller_no_sirve(ctx, colegio):
    fabricas.crear_prenda(fabricas.crear_taller(), nombre="Uniforme de diario", **UNIFORME)

    with pytest.raises(ErrorDeHerramienta, match="No hay prendas guardadas"):
        proponer(ctx)


# --- Las reglas de la pantalla ----------------------------------------------------------------


@pytest.mark.parametrize(("cambios", "mensaje"), [
    ({"cantidad": 5000}, "Escribe un número entre 1 y 2000."),
    ({"cantidad": 0}, "Escribe un número entre 1 y 2000."),
    ({"fecha_entrega": None}, "Elige la fecha de entrega."),
    ({"detalle": "   "}, "Escribe qué pidió el cliente."),
    ({"total": 2_000_000_000}, "Ese valor es demasiado alto. Revisa los ceros."),
])
def test_lo_que_la_pantalla_no_acepta_da_su_mismo_mensaje(ctx, colegio, cambios, mensaje):
    with pytest.raises(ErrorDeHerramienta) as error:
        directo(ctx, **cambios)
    assert str(error.value) == mensaje

    # Es el mismo mensaje de Pedidos > Nuevo pedido.
    from pedidos.formularios.lista import NuevoPedidoForm

    datos = {"cliente": "Colegio Nuevo Amanecer", "tipo": "colegio",
             "detalle": "30 uniformes de diario", "cantidad": "30", "tallaje": "nino",
             "fecha_entrega": ENTREGA.isoformat(), "total": "2310000", "whatsapp": ""}
    clave = next(iter(cambios))
    valor = cambios[clave]
    datos[clave] = "" if valor is None else str(valor)
    form = NuevoPedidoForm(data=datos)
    assert not form.is_valid() and mensaje in form.errors[clave]


def test_el_abono_que_la_pantalla_no_acepta(ctx, colegio):
    with pytest.raises(ErrorDeHerramienta, match="Revisa el valor: es demasiado grande."):
        directo(ctx, abono=2_000_000_000)


def test_el_abono_mayor_que_el_total_no_deja_falta_negativa(ctx, colegio):
    resultado = directo(ctx, total=300_000, abono=500_000)

    assert filas(resultado)["Abono de hoy"]["detalle"] == "Después del abono falta $ 0"


# --- La tela ----------------------------------------------------------------------------------


def test_la_tela_que_no_alcanza_usa_falta_tela(ctx, taller, uniforme, dril, colegio):
    # Otro pedido Confirmado ya apartó 10 m de dril: faltan 66 + 10 - 18 = 58.
    otro = fabricas.crear_pedido(taller, estado="confirmado")
    fabricas.crear_tela_pedido(otro, dril, 10)

    fila = filas(proponer(ctx))["Tela"]

    assert fila["aviso"] == "Te faltan 58 m de dril azul."
    assert fila["detalle"] == ("66 m de dril azul (2,2 m por uniforme). Tienes 18 m, y 10 m ya "
                               "están apartados para otros pedidos.")


def test_la_tela_que_alcanza_no_avisa(ctx, taller, uniforme, colegio):
    fabricas.crear_tela(taller, nombre="Dril azul", metros=100)

    assert filas(proponer(ctx))["Tela"]["aviso"] == ""


def test_con_metros_usa_los_de_ella(ctx, uniforme, dril, colegio):
    resultado = proponer(ctx, metros="12,5")

    fila = filas(resultado)["Tela"]
    assert fila["detalle"] == "12,5 m de dril azul. Tienes 18 m."
    assert fila["aviso"] == ""
    assert acciones_de(resultado, ctx)[-1]["datos"]["metros"] == "12.50"


@pytest.mark.parametrize("metros", ["0", "-3", "abc", "1.234", "nan"])
def test_metros_que_no_sirven_dan_error(ctx, uniforme, dril, colegio, metros):
    with pytest.raises(ErrorDeHerramienta):
        proponer(ctx, metros=metros)


def test_sin_metros_ni_prenda_pide_los_metros(ctx, dril, colegio):
    with pytest.raises(ErrorDeHerramienta) as error:
        proponer(ctx, prenda="", total=2_000_000)

    assert str(error.value) == (
        "Faltan los metros de dril azul: pregúntale cuántos metros lleva todo el pedido.")


def test_dos_telas_parecidas_dan_opciones(ctx, taller, uniforme, colegio):
    azul = fabricas.crear_tela(taller, nombre="Dril azul")
    gris = fabricas.crear_tela(taller, nombre="Dril gris")

    resultado = proponer(ctx, tela="dril")

    assert resultado.datos == {"escoger": "tela", "opciones": [
        {"id": azul.pk, "nombre": "Dril azul"}, {"id": gris.pk, "nombre": "Dril gris"}]}
    assert resultado.tarjeta.tipo == "opciones"


def test_la_tela_de_otro_taller_no_se_toca(ctx, uniforme, colegio):
    fabricas.crear_tela(fabricas.crear_taller(), nombre="Dril azul", metros=500)

    with pytest.raises(ErrorDeHerramienta) as error:
        proponer(ctx)

    assert str(error.value) == "No encontré esa tela en Telas."


# --- Guardar ----------------------------------------------------------------------------------


@pytest.fixture
def prendido(settings, taller):
    settings.ANTHROPIC_API_KEY = "clave-de-prueba"
    taller.asistente_limite_mes = 600
    taller.asistente_limite_dia = 40
    taller.save()
    return taller


def confirmar(client, resultado):
    """Muestra la tarjeta en la conversación (como lo hace el panel) y toca Guardar."""
    sesion = client.session
    sesion[vistas.CLAVE_SESION] = {
        "huella": vistas.huella(),
        "mensajes": [],
        "turnos": [{"pregunta": "…", "estado": "ok", "texto": "Revísalo y toca Guardar:",
                    "revisado": [resultado.revisado], "tarjetas": [asdict(resultado.tarjeta)],
                    "enlaces": []}],
        "notas": [],
    }
    sesion.save()
    respuesta = client.post(reverse("asistente:confirmar"),
                            {"firma": resultado.tarjeta.datos["firma"]}, **HTMX)
    assert respuesta.status_code == 200
    return respuesta


def test_sin_tocar_guardar_no_se_crea_nada(ctx, uniforme, dril, colegio):
    antes = cuenta()

    proponer(ctx)
    proponer(ctx, cliente="Comparsa Nueva", tipo_cliente="comparsa")

    assert cuenta() == antes


def test_al_guardar_se_crea_todo_junto(sesion_duena, prendido, duena, uniforme, dril):
    ctx = contexto(duena, hoy=timezone.localdate())
    entrega = (timezone.localdate() + timedelta(days=30)).isoformat()
    resultado = proponer(ctx, fecha_entrega=entrega)

    html = confirmar(sesion_duena, resultado).text

    pedido = Pedido.objects.get()
    assert (pedido.taller, pedido.creado_por, pedido.por_asistente) == (prendido, duena, True)
    assert (pedido.estado, pedido.total, pedido.cantidad, pedido.tallaje) == (
        "confirmado", 2_310_000, 30, "nino")
    assert (pedido.cliente.nombre, pedido.cliente.tipo) == ("Colegio Nuevo Amanecer", "colegio")
    abono = Abono.objects.get()
    assert (abono.pedido, abono.valor, abono.por_asistente, abono.fecha) == (
        pedido, 500_000, True, timezone.localdate())
    tela = TelaPedido.objects.get()
    assert (tela.pedido, tela.tela, tela.metros) == (pedido, dril, Decimal("66.00"))
    assert "Listo" in html and "Ver el pedido" in html

    # La cronología del pedido dice que lo anotó el asistente.
    detalle = sesion_duena.get(reverse("pedidos:detalle", args=[pedido.pk])).content.decode()
    assert "Lo anotó el asistente" in detalle


def test_con_guardar_directo_tambien(ctx, duena, uniforme, dril, colegio):
    resultado = proponer(ctx)
    clave, acciones = borradores.abrir(resultado.tarjeta.datos["firma"], ctx)

    guardar.guardar(ctx, clave, acciones)

    pedido = Pedido.objects.get()
    assert pedido.cliente == colegio and pedido.por_asistente and pedido.estado == "confirmado"
    assert Abono.objects.get().pedido == pedido
    assert TelaPedido.objects.get().pedido == pedido


def test_si_el_abono_falla_no_queda_ni_el_pedido(ctx, uniforme, dril, monkeypatch):
    resultado = proponer(ctx)
    clave, acciones = borradores.abrir(resultado.tarjeta.datos["firma"], ctx)
    antes = cuenta()

    def falla(*_):
        raise NoSeGuardo("El abono debe ser mayor que 0.")

    monkeypatch.setitem(guardar.GUARDADORES, "abono", falla)
    with pytest.raises(NoSeGuardo):
        guardar.guardar(ctx, clave, acciones)

    assert cuenta() == antes  # ni el cliente nuevo, ni el pedido, ni la tela


# --- Lo que ve Claude -------------------------------------------------------------------------


def test_corre_por_ejecutar_con_ceros_y_vacios(ctx, colegio):
    resultado = herramientas.ejecutar("proponer_pedido", {
        "cliente": "Colegio Nuevo Amanecer", "cliente_id": 0, "tipo_cliente": "",
        "detalle": "30 uniformes de diario", "cantidad": 30, "tallaje": "adulto",
        "fecha_entrega": "2026-12-15", "prenda": "", "total": 1_500_000, "abono": 0,
        "tela": "", "metros": "",
    }, ctx)

    assert isinstance(resultado, Resultado)
    assert [f["titulo"] for f in resultado.datos["filas"]] == ["Pedido nuevo", "Tallas"]
    assert "Adulto (XS a XXL)" in filas(resultado)["Pedido nuevo"]["detalle"]


def test_lo_que_va_a_claude_no_trae_secretos_ni_float(ctx, uniforme, dril, colegio):
    resultado = proponer(ctx)
    texto = json.dumps(resultado.datos, ensure_ascii=False)

    assert resultado.tarjeta.datos["firma"] not in texto
    assert resultado.tarjeta.datos["clave"] not in texto
    assert "firma" not in resultado.datos
    assert "300 123 4567" not in texto and "3001234567" not in texto
    assert "Notas privadas" not in texto
    assert "token" not in texto
    assert not flotantes(resultado.datos)
    assert not flotantes(acciones_de(resultado, ctx))
    assert "Nada se ha guardado todavía" in resultado.datos["nota"]


def test_las_opciones_no_traen_secretos(ctx, taller, uniforme):
    fabricas.crear_cliente(taller, nombre="Colegio A", whatsapp="300 999 8888", notas="Secreto")
    fabricas.crear_cliente(taller, nombre="Colegio B")

    texto = json.dumps(proponer(ctx, cliente="colegio").datos, ensure_ascii=False)

    assert "300 999 8888" not in texto and "Secreto" not in texto


def test_sin_abono_la_tela_faltara_cuando_lo_confirme(ctx, uniforme, dril, colegio):
    # Ajuste del revisor: sin abono el pedido nace Cotizado y todavía no aparta tela.
    resultado = proponer(ctx, abono=0)

    assert filas(resultado)["Tela"]["aviso"] == (
        "Cuando lo confirmes, te faltarán 48 m de dril azul.")
