"""El agente propone abonos y gastos (T40): proponer_abono y proponer_gasto.

Reglas: docs/13-plan-tanda-8.md, secciones 1.1, 1.2, 1.6 y "T40 (B)". Se comprueba que:

- se llaman como las llamaría Claude, por `herramientas.ejecutar(nombre, entrada, ctx)`, con
  0 y "" para decir "no hay";
- no guardan nada: sin tocar Guardar no cambia nada;
- escogen bien el pedido (el de la pantalla, el único con saldo del cliente) y preguntan
  cuál cuando hay dos;
- el "Falta" de la tarjeta sale de calculos.saldo y, después de guardar, es el saldo que
  muestra la tarjeta Pagos del pedido;
- revisan con los formularios de las pantallas y dan sus mismos mensajes;
- el gasto guardado suma en el Resumen del mes igual que uno de la pantalla;
- nunca tocan lo de otro taller, y lo que va a Claude no trae firma, WhatsApp ni float.
"""

import json
from datetime import date, timedelta

import pytest
from django.test import Client
from django.urls import reverse
from django.utils import timezone

from asistente import borradores, guardar, herramientas
from asistente.contratos import Contexto, ErrorDeHerramienta
from asistente.models import BorradorUsado
from asistente.tests.test_confirmar import HTMX, URL, sembrar
from asistente.tests.test_herramientas_pedidos import sin_float
from finanzas.models import Gasto
from pedidos import calculos
from pedidos.models import Abono, Pedido
from pedidos.vistas.abonos import contexto_pagos
from tests import fabricas

pytestmark = pytest.mark.django_db

WHATSAPP = "3001234567"


# --- Ayudas ------------------------------------------------------------------------------------


@pytest.fixture
def prendido(settings, taller):
    settings.ANTHROPIC_API_KEY = "clave-de-prueba"
    taller.asistente_limite_mes = 600
    taller.asistente_limite_dia = 40
    taller.save()
    return taller


def contexto(usuaria, pedido=None, hoy=None):
    return Contexto(taller=usuaria.taller, usuaria=usuaria, hoy=hoy or timezone.localdate(),
                    pedido_actual=pedido, url_base="http://testserver/")


@pytest.fixture
def tambores(taller):
    """El pedido de la maqueta (diseno/asistente-agente.html): debe $ 750.000."""
    cliente = fabricas.crear_cliente(taller, nombre="Grupo de danza Tambores del Río",
                                     tipo="comparsa", whatsapp=WHATSAPP)
    pedido = fabricas.crear_pedido(taller, cliente, detalle="15 polleras con blusa",
                                   cantidad=15, total=1_200_000)
    fabricas.crear_abono(pedido, 450_000)
    return pedido


def abono(ctx, pedido_id=0, cliente="", valor=300_000, fecha=""):
    entrada = {"pedido_id": pedido_id, "cliente": cliente, "valor": valor, "fecha": fecha}
    return herramientas.ejecutar("proponer_abono", entrada, ctx)


def gasto(ctx, concepto="Recibo de agua del taller", categoria="servicios", valor=65_000,
          fecha="", pedido_id=0):
    entrada = {"concepto": concepto, "categoria": categoria, "valor": valor, "fecha": fecha,
               "pedido_id": pedido_id}
    return herramientas.ejecutar("proponer_gasto", entrada, ctx)


def cuenta():
    return Pedido.objects.count(), Abono.objects.count(), Gasto.objects.count()


def guardar_borrador(ctx, resultado):
    """Lo que hace la vista confirmar: abrir la firma y guardar con los formularios."""
    clave, acciones = borradores.abrir(resultado.tarjeta.datos["firma"], ctx)
    return guardar.guardar(ctx, clave, acciones)


def lo_que_ve_claude(resultado):
    texto = json.dumps(resultado.datos, ensure_ascii=False)
    assert resultado.tarjeta.datos["firma"] not in texto
    assert "firma" not in resultado.datos
    assert resultado.tarjeta.datos["clave"] not in texto
    assert WHATSAPP not in texto
    sin_float(resultado.datos)
    return texto


# --- proponer_abono: qué pedido ---------------------------------------------------------------


def test_sin_pedido_id_usa_el_pedido_de_la_pantalla(duena, tambores):
    resultado = abono(contexto(duena, pedido=tambores))  # pedido_id 0, cliente ""

    assert resultado.tarjeta.tipo == "borrador"
    assert resultado.revisado == "Revisé el pedido de 15 polleras con blusa"
    fila = resultado.datos["filas"][0]
    assert fila == {
        "titulo": "Abono de hoy",
        "detalle": "Grupo de danza Tambores del Río · 15 polleras con blusa · Falta $ 450.000",
        "valor": 300_000,
        "aviso": "",
    }
    clave, acciones = borradores.abrir(resultado.tarjeta.datos["firma"], contexto(duena))
    assert acciones == [
        {"tipo": "abono", "datos": {"pedido": tambores.pk, "valor": 300_000, "fecha": None}}
    ]
    assert resultado.datos["borrador"] == "listo"
    lo_que_ve_claude(resultado)


def test_por_cliente_con_un_solo_pedido_con_saldo_lo_escoge(duena, taller, tambores):
    # Otro pedido del mismo cliente, ya pagado: no cuenta.
    pagado = fabricas.crear_pedido(taller, tambores.cliente, detalle="10 parejos", total=400_000)
    fabricas.crear_abono(pagado, 400_000)

    resultado = abono(contexto(duena), cliente="tambores del rio")  # sin tildes ni mayúsculas

    _, acciones = borradores.abrir(resultado.tarjeta.datos["firma"], contexto(duena))
    assert acciones[0]["datos"]["pedido"] == tambores.pk


def test_con_dos_pedidos_con_saldo_pregunta_cual(duena, taller):
    colegio = fabricas.crear_cliente(taller, nombre="Colegio Nuevo Amanecer")
    hoy = timezone.localdate()
    primero = fabricas.crear_pedido(taller, colegio, detalle="40 uniformes de diario",
                                    fecha_entrega=hoy + timedelta(days=10))
    segundo = fabricas.crear_pedido(taller, colegio, detalle="30 uniformes de diario",
                                    fecha_entrega=hoy + timedelta(days=20))
    antes = cuenta()

    resultado = abono(contexto(duena), cliente="Colegio", valor=200_000)

    assert resultado.datos == {
        "escoger": "pedido",
        "opciones": [{"id": primero.pk, "nombre": "40 uniformes de diario"},
                     {"id": segundo.pk, "nombre": "30 uniformes de diario"}],
    }
    assert resultado.tarjeta.tipo == "opciones"
    assert resultado.tarjeta.datos["opciones"] == ["40 uniformes de diario",
                                                   "30 uniformes de diario"]
    assert "firma" not in resultado.tarjeta.datos  # no hay borrador
    assert resultado.revisado == "Revisé los pedidos de Colegio Nuevo Amanecer"
    assert cuenta() == antes


def test_dos_clientes_parecidos_dicen_el_cliente_en_la_opcion(duena, taller):
    uno = fabricas.crear_pedido(taller, fabricas.crear_cliente(taller, nombre="Colegio Sol"),
                                detalle="20 sudaderas")
    otro = fabricas.crear_pedido(taller, fabricas.crear_cliente(taller, nombre="Colegio Luna"),
                                 detalle="20 sudaderas")

    resultado = abono(contexto(duena), cliente="colegio")

    nombres = {o["id"]: o["nombre"] for o in resultado.datos["opciones"]}
    assert nombres == {uno.pk: "Colegio Sol · 20 sudaderas",
                       otro.pk: "Colegio Luna · 20 sudaderas"}


def test_si_habla_de_otro_cliente_no_usa_el_de_la_pantalla(duena, taller, tambores):
    fogon = fabricas.crear_pedido(
        taller, fabricas.crear_cliente(taller, nombre="Restaurante El Fogón Costeño"),
        detalle="18 camisas", total=900_000)

    resultado = abono(contexto(duena, pedido=tambores), cliente="El Fogón", valor=100_000)

    _, acciones = borradores.abrir(resultado.tarjeta.datos["firma"], contexto(duena))
    assert acciones[0]["datos"]["pedido"] == fogon.pk


def test_sin_saldo_o_sin_nada_pide_lo_que_falta(duena, taller, tambores):
    with pytest.raises(ErrorDeHerramienta, match="No encontré un pedido con saldo de ese"):
        abono(contexto(duena), cliente="Nadie se llama así")
    with pytest.raises(ErrorDeHerramienta, match="de qué cliente es"):
        abono(contexto(duena))
    with pytest.raises(ErrorDeHerramienta, match="No encontré ese pedido."):
        abono(contexto(duena), pedido_id=tambores.pk + 1000)


# --- proponer_abono: las cifras ---------------------------------------------------------------


def test_el_falta_es_el_saldo_menos_el_abono_y_coincide_con_pagos_al_guardar(duena, tambores):
    ctx = contexto(duena)
    saldo = calculos.saldo(tambores)
    resultado = abono(ctx, pedido_id=tambores.pk, valor=300_000)
    assert resultado.datos["filas"][0]["detalle"].endswith("Falta $ 450.000")
    assert saldo - 300_000 == 450_000

    guardados = guardar_borrador(ctx, resultado)

    nuevo = Abono.objects.get(pk=guardados[0].objeto.pk)
    assert (nuevo.pedido, nuevo.valor, nuevo.por_asistente, nuevo.registrado_por) == (
        tambores, 300_000, True, duena)
    assert nuevo.fecha == timezone.localdate()
    pedido = Pedido.objects.get(pk=tambores.pk)
    pagos = contexto_pagos(None, pedido)["pagos"]  # la tarjeta Pagos del pedido
    assert pagos.saldo == calculos.saldo(pedido) == 450_000


def test_un_abono_que_paga_todo_dice_queda_pagado(duena, tambores):
    fila = abono(contexto(duena, pedido=tambores), valor=750_000).datos["filas"][0]

    assert fila["detalle"].endswith("· Queda pagado")
    assert fila["aviso"] == ""


def test_un_abono_de_mas_avisa_y_se_guarda_igual(duena, tambores):
    ctx = contexto(duena, pedido=tambores)
    resultado = abono(ctx, valor=1_000_000)

    fila = resultado.datos["filas"][0]
    assert fila["detalle"].endswith("· Queda pagado")
    assert fila["valor"] == 1_000_000
    assert fila["aviso"] == (
        "Es más de lo que debe ($ 750.000). Se guarda igual y el pedido queda pagado."
    )
    guardar_borrador(ctx, resultado)
    assert calculos.saldo(Pedido.objects.get(pk=tambores.pk)) == 0


def test_la_fecha_de_otro_dia_sale_en_el_titulo(duena, tambores):
    ctx = contexto(duena, pedido=tambores, hoy=date(2026, 11, 15))

    resultado = abono(ctx, fecha="2026-11-12")

    assert resultado.datos["filas"][0]["titulo"] == "Abono del 12 de noviembre"
    _, acciones = borradores.abrir(resultado.tarjeta.datos["firma"], ctx)
    assert acciones[0]["datos"]["fecha"] == "2026-11-12"
    guardar_borrador(ctx, resultado)
    assert Abono.objects.get(por_asistente=True).fecha == date(2026, 11, 12)


@pytest.mark.parametrize(("valor", "mensaje"), [
    (0, "El abono debe ser mayor que 0."),
    (-5_000, "Escribe solo el valor en pesos, por ejemplo 380.000."),
    (300_000.5, "Escribe solo el valor en pesos, por ejemplo 380.000."),
    (2_000_000_000, "Revisa el valor: es demasiado grande."),
])
def test_un_valor_que_la_pantalla_no_acepta_da_su_mensaje(duena, tambores, valor, mensaje):
    with pytest.raises(ErrorDeHerramienta) as error:
        herramientas.REGISTRO["proponer_abono"](
            contexto(duena, pedido=tambores), pedido_id=None, cliente=None, valor=valor,
            fecha=None)
    assert str(error.value) == mensaje
    # El mismo formulario de la tarjeta Pagos dice lo mismo.
    from pedidos.formularios.abonos import FormularioAbono
    form = FormularioAbono(data={"valor": str(valor), "fecha": ""})
    assert not form.is_valid() and form.errors["valor"] == [mensaje]


def test_por_ejecutar_los_valores_fuera_de_rango_no_llegan(duena, tambores):
    for valor in (0, -1, 300_000.5):
        with pytest.raises(ErrorDeHerramienta):
            abono(contexto(duena, pedido=tambores), valor=valor)
    assert not Abono.objects.filter(por_asistente=True).exists()


# --- proponer_gasto ---------------------------------------------------------------------------


def test_el_gasto_de_la_maqueta(duena):
    antes = cuenta()

    resultado = gasto(contexto(duena))  # fecha "" y pedido_id 0

    assert resultado.revisado == "Preparé el gasto"
    assert resultado.datos["filas"] == [{
        "titulo": "Gasto de hoy", "detalle": "Recibo de agua del taller · Servicios",
        "valor": 65_000, "aviso": "",
    }]
    _, acciones = borradores.abrir(resultado.tarjeta.datos["firma"], contexto(duena))
    assert acciones == [{"tipo": "gasto", "datos": {
        "concepto": "Recibo de agua del taller", "categoria": "servicios", "valor": 65_000,
        "fecha": None, "pedido": None}}]
    assert cuenta() == antes
    lo_que_ve_claude(resultado)


def test_el_gasto_de_un_pedido_y_de_otro_dia(duena, tambores):
    ctx = contexto(duena, hoy=date(2026, 11, 15))

    resultado = gasto(ctx, concepto="Botones dorados", categoria="insumos", valor=38_000,
                      fecha="2026-11-12", pedido_id=tambores.pk)

    fila = resultado.datos["filas"][0]
    assert fila["titulo"] == "Gasto del 12 de noviembre"
    assert fila["detalle"] == "Botones dorados · Insumos · Pedido: 15 polleras con blusa"
    guardar_borrador(ctx, resultado)
    guardado = Gasto.objects.get()
    assert (guardado.pedido, guardado.fecha, guardado.por_asistente) == (
        tambores, date(2026, 11, 12), True)


def test_el_gasto_guardado_suma_en_el_resumen_igual_que_el_de_la_pantalla(duena, prendido,
                                                                           sesion_duena):
    hoy = timezone.localdate()
    resultado = gasto(contexto(duena))
    sembrar(sesion_duena, resultado.tarjeta)
    respuesta = sesion_duena.post(URL, {"firma": resultado.tarjeta.datos["firma"]}, **HTMX)
    assert respuesta.status_code == 200 and "Listo" in respuesta.text

    # Otro taller anota lo mismo en la pantalla del Resumen del mes.
    otro = fabricas.crear_taller()
    navegador = Client()
    navegador.force_login(fabricas.crear_usuaria(otro))
    navegador.post(reverse("finanzas:gasto_nuevo"), {
        "concepto": "Recibo de agua del taller", "categoria": "servicios", "valor": "65.000",
        "fecha": "", "mes": f"{hoy:%Y-%m}"})

    del_agente = Gasto.objects.get(taller=prendido)
    de_la_pantalla = Gasto.objects.get(taller=otro)
    assert (del_agente.por_asistente, de_la_pantalla.por_asistente) == (True, False)
    campos = ("concepto", "categoria", "valor", "fecha", "pedido_id")
    assert [getattr(del_agente, c) for c in campos] == [getattr(de_la_pantalla, c) for c in campos]
    assert (calculos.resumen_del_mes(prendido, hoy.year, hoy.month)
            == calculos.resumen_del_mes(otro, hoy.year, hoy.month))
    assert calculos.gastado_en(prendido, hoy.year, hoy.month) == 65_000
    assert "$ 65.000" in sesion_duena.get(reverse("finanzas:resumen") + f"?mes={hoy:%Y-%m}").text


@pytest.mark.parametrize(("cambios", "mensaje"), [
    ({"valor": 0}, "El gasto debe ser mayor que 0."),
    ({"valor": -100}, "Escribe solo el valor en pesos, por ejemplo 380.000."),
    ({"valor": 65_000.5}, "Escribe solo el valor en pesos, por ejemplo 380.000."),
    ({"concepto": "x" * 81}, "Escribe máximo 80 letras."),
    ({"concepto": "   "}, "Escribe en qué gastaste."),
    ({"categoria": "comida"}, "Elige el tipo de gasto."),
    ({"fecha": date(1999, 1, 5)}, "Revisa la fecha del gasto."),
])
def test_un_gasto_que_la_pantalla_no_acepta_da_su_mensaje(duena, cambios, mensaje):
    entrada = {"concepto": "Recibo de agua del taller", "categoria": "servicios",
               "valor": 65_000, "fecha": None, "pedido_id": None, **cambios}
    with pytest.raises(ErrorDeHerramienta) as error:
        herramientas.REGISTRO["proponer_gasto"](contexto(duena), **entrada)
    assert str(error.value) == mensaje
    assert not Gasto.objects.exists()


# --- Nada se guarda sin Guardar, y cada taller con lo suyo ------------------------------------


def test_sin_tocar_guardar_no_cambia_nada(duena, tambores):
    antes = cuenta()
    saldo = calculos.saldo(tambores)

    abono(contexto(duena, pedido=tambores))
    gasto(contexto(duena), pedido_id=tambores.pk)

    assert cuenta() == antes
    assert calculos.saldo(Pedido.objects.get(pk=tambores.pk)) == saldo
    assert not BorradorUsado.objects.exists()


def test_guardar_por_la_vista_marca_el_abono_del_asistente(sesion_duena, prendido, duena,
                                                           tambores):
    resultado = abono(contexto(duena, pedido=tambores))
    sembrar(sesion_duena, resultado.tarjeta)

    html = sesion_duena.post(URL, {"firma": resultado.tarjeta.datos["firma"]}, **HTMX).text

    assert "Listo" in html and "Ver el pedido" in html
    nuevo = Abono.objects.get(por_asistente=True)
    assert (nuevo.pedido_id, nuevo.valor) == (tambores.pk, 300_000)
    # La tarjeta Pagos del pedido por dentro muestra el mismo "Falta" del borrador.
    pedido = Pedido.objects.get(pk=tambores.pk)
    assert contexto_pagos(None, pedido)["pagos"].saldo == 450_000
    detalle = sesion_duena.get(reverse("pedidos:detalle", args=[tambores.pk])).text
    assert "$ 450.000" in detalle and "Lo anotó el asistente" in detalle


def test_el_pedido_de_otro_taller_no_se_encuentra(duena):
    otro = fabricas.crear_taller()
    ajeno = fabricas.crear_pedido(otro, fabricas.crear_cliente(otro, nombre="Tambores del Río"))

    with pytest.raises(ErrorDeHerramienta, match="^No encontré ese pedido.$"):
        abono(contexto(duena), pedido_id=ajeno.pk)
    with pytest.raises(ErrorDeHerramienta, match="^No encontré ese pedido.$"):
        gasto(contexto(duena), pedido_id=ajeno.pk)
    # Por nombre tampoco: el cliente con el mismo nombre de otro taller no se ve.
    with pytest.raises(ErrorDeHerramienta, match="No encontré un pedido con saldo"):
        abono(contexto(duena), cliente="Tambores del Río")
    # Ni aunque llegue como el pedido "de la pantalla".
    with pytest.raises(ErrorDeHerramienta, match="^No encontré ese pedido.$"):
        abono(contexto(duena, pedido=ajeno))
    assert not Abono.objects.exists() and not Gasto.objects.exists()


def test_el_borrador_de_un_taller_no_sirve_en_otro(duena, tambores):
    resultado = abono(contexto(duena, pedido=tambores))
    otra = fabricas.crear_usuaria(fabricas.crear_taller())

    with pytest.raises(borradores.BorradorInvalido):
        borradores.abrir(resultado.tarjeta.datos["firma"], contexto(otra))


def test_lo_que_ve_claude_no_trae_firma_whatsapp_ni_float(duena, tambores):
    texto = lo_que_ve_claude(abono(contexto(duena, pedido=tambores)))
    assert "Nada se ha guardado todavía" in texto
    lo_que_ve_claude(gasto(contexto(duena), pedido_id=tambores.pk))
