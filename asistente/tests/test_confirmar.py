"""Guardar un borrador: la vista `confirmar` y los guardadores (tanda 8, T38).

Reglas: docs/13-plan-tanda-8.md, sección 1.3. Sin tocar Guardar no cambia nada; lo que se
guarda pasa por los formularios de las pantallas; o todo o nada; un solo uso; no llama a
Claude ni gasta preguntas; lo guardado se le cuenta a Claude en la siguiente pregunta.
"""

from dataclasses import asdict
from datetime import timedelta
from decimal import Decimal

import pytest
from django.urls import reverse
from django.utils import timezone

from asistente import borradores, falso, vistas
from asistente.contratos import Contexto, Fila, Resultado, Uso
from asistente.conversacion import Respuesta
from asistente.models import BorradorUsado, UsoAsistente
from cuentas.models import Usuario
from finanzas.models import Gasto
from pedidos.models import Abono, Cliente, Pedido
from telas.models import TelaPedido
from tests import fabricas

pytestmark = pytest.mark.django_db

HTMX = {"HTTP_HX_REQUEST": "true"}
URL = "/asistente/confirmar/"


@pytest.fixture
def prendido(settings, taller):
    settings.ANTHROPIC_API_KEY = "clave-de-prueba"
    taller.asistente_limite_mes = 600
    taller.asistente_limite_dia = 40
    taller.save()
    return taller


def contexto_de(usuaria):
    return Contexto(taller=usuaria.taller, usuaria=usuaria, hoy=timezone.localdate(),
                    pedido_actual=None, url_base="http://testserver/")


def sembrar(client, *tarjetas, notas=()):
    """Deja en la sesión una conversación con un turno por tarjeta."""
    sesion = client.session
    sesion[vistas.CLAVE_SESION] = {
        "huella": vistas.huella(),
        "mensajes": [],
        "turnos": [
            {"pregunta": "…", "estado": "ok", "texto": "Revísalo y toca Guardar:",
             "revisado": [], "tarjetas": [asdict(t) if not isinstance(t, dict) else t],
             "enlaces": []}
            for t in tarjetas
        ],
        "notas": list(notas),
    }
    sesion.save()


def tarjeta_en_sesion(client, clave):
    for turno in client.session[vistas.CLAVE_SESION]["turnos"]:
        for tarjeta in turno["tarjetas"]:
            if tarjeta["datos"].get("clave") == clave:
                return tarjeta
    raise AssertionError("no está")


def borrador_del_pedido(duena, dril, abono=500_000, **cambios):
    """El pedido de las 10:30 (docs/12-agente.md): pedido, abono, tela y pasa a Confirmado."""
    entrega = (timezone.localdate() + timedelta(days=30)).isoformat()
    pedido = {"cliente": "Colegio Nuevo Amanecer", "cliente_id": None, "tipo": "colegio",
              "detalle": "30 uniformes de diario", "cantidad": 30, "tallaje": "nino",
              "fecha_entrega": entrega, "total": 2_310_000, **cambios}
    acciones = [
        {"tipo": "pedido", "datos": pedido},
        {"tipo": "etapa", "datos": {"pedido": "@0", "estado": "confirmado"}},
        {"tipo": "abono", "datos": {"pedido": "@0", "valor": abono, "fecha": None}},
        {"tipo": "tela_pedido", "datos": {"pedido": "@0", "tela": dril.pk, "metros": "66.00"}},
    ]
    filas = [Fila("Pedido nuevo", "Colegio Nuevo Amanecer · 30 uniformes de diario", 2_310_000),
             Fila("Abono de hoy", "Después del abono falta $ 1.810.000", abono),
             Fila("Tela", "66 m de dril azul. Tienes 18 m.", None, "Te faltan 48 m de dril azul.")]
    return borradores.armar(contexto_de(duena), acciones, filas)


def borrador_del_gasto(duena, **cambios):
    datos = {"concepto": "Recibo de agua del taller", "categoria": "servicios",
             "valor": 65_000, "fecha": None, "pedido": None, **cambios}
    return borradores.armar(contexto_de(duena), [{"tipo": "gasto", "datos": datos}],
                            [Fila("Gasto de hoy", "Recibo de agua del taller · Servicios", 65_000)])


def cuenta():
    return (Pedido.objects.count(), Abono.objects.count(), Gasto.objects.count(),
            TelaPedido.objects.count(), Cliente.objects.count())


@pytest.fixture
def dril(taller):
    return fabricas.crear_tela(taller, nombre="Dril azul", metros=18)


# --- Guardar ----------------------------------------------------------------------------------


def test_sin_tocar_guardar_no_cambia_nada(sesion_duena, prendido, duena, dril):
    antes = cuenta()
    sembrar(sesion_duena, borrador_del_pedido(duena, dril))

    html = sesion_duena.get("/asistente/", **HTMX).text

    assert "Para guardar" in html and "Sin guardar" in html
    assert cuenta() == antes
    assert not BorradorUsado.objects.exists()


def test_guardar_crea_todo_junto_con_las_reglas_de_las_pantallas(sesion_duena, prendido, duena,
                                                                  dril):
    tarjeta = borrador_del_pedido(duena, dril)
    sembrar(sesion_duena, tarjeta)

    respuesta = sesion_duena.post(URL, {"firma": tarjeta.datos["firma"]}, **HTMX)

    assert respuesta.status_code == 200
    pedido = Pedido.objects.get()
    assert (pedido.taller, pedido.creado_por, pedido.por_asistente) == (prendido, duena, True)
    assert pedido.cliente.nombre == "Colegio Nuevo Amanecer" and pedido.cliente.tipo == "colegio"
    assert pedido.estado == "confirmado"  # dejó abono (decisión 4 de David)
    abono = Abono.objects.get()
    assert (abono.pedido, abono.valor, abono.por_asistente, abono.registrado_por) == (
        pedido, 500_000, True, duena)
    assert abono.fecha == timezone.localdate()
    tela = TelaPedido.objects.get()
    assert (tela.pedido, tela.tela, tela.metros) == (pedido, dril, Decimal("66.00"))
    # La tarjeta cambia a "Listo" con el enlace al pedido, y sale el aviso corto.
    html = respuesta.text
    assert "Listo" in html and "Sin guardar" not in html
    assert reverse("pedidos:detalle", args=[pedido.pk]) in html and "Ver el pedido" in html
    assert "Guardado a las" in html
    assert "Guardado." in respuesta["HX-Trigger"]
    assert BorradorUsado.objects.filter(taller=prendido, clave=tarjeta.datos["clave"]).exists()
    # Al recargar el panel se ve igual: el estado quedó en la sesión.
    assert tarjeta_en_sesion(sesion_duena, tarjeta.datos["clave"])["datos"]["estado"] == "guardado"
    assert "Listo" in sesion_duena.get("/asistente/", **HTMX).text


def test_el_cliente_que_ya_existe_no_se_repite(sesion_duena, prendido, duena, dril):
    colegio = fabricas.crear_cliente(prendido, nombre="Colegio Nuevo Amanecer", tipo="colegio")
    tarjeta = borrador_del_pedido(duena, dril, cliente="colegio nuevo amanecer",
                                  cliente_id=colegio.pk)
    sembrar(sesion_duena, tarjeta)

    sesion_duena.post(URL, {"firma": tarjeta.datos["firma"]}, **HTMX)

    assert Cliente.objects.count() == 1
    assert Pedido.objects.get().cliente == colegio


def test_o_todo_o_nada(sesion_duena, prendido, duena, dril):
    antes = cuenta()
    tarjeta = borrador_del_pedido(duena, dril, abono=0)  # la pantalla no deja un abono de 0
    sembrar(sesion_duena, tarjeta)

    respuesta = sesion_duena.post(URL, {"firma": tarjeta.datos["firma"]}, **HTMX)

    assert cuenta() == antes  # ni el pedido, ni el cliente, ni la tela
    assert not BorradorUsado.objects.exists()
    html = respuesta.text
    assert "No se guardó nada: El abono debe ser mayor que 0." in html
    assert "Guardar" in html  # se puede volver a intentar
    assert "HX-Trigger" not in respuesta


def test_el_mismo_mensaje_que_la_pantalla_cuando_algo_no_cumple(sesion_duena, prendido, duena,
                                                                 dril):
    tarjeta = borrador_del_pedido(duena, dril, cantidad=5000)
    sembrar(sesion_duena, tarjeta)

    html = sesion_duena.post(URL, {"firma": tarjeta.datos["firma"]}, **HTMX).text

    assert "No se guardó nada: Escribe un número entre 1 y 2000." in html
    assert not Pedido.objects.exists()


def test_el_gasto_se_guarda_como_en_la_pantalla(sesion_duena, prendido, duena):
    tarjeta = borrador_del_gasto(duena)
    sembrar(sesion_duena, tarjeta)

    html = sesion_duena.post(URL, {"firma": tarjeta.datos["firma"]}, **HTMX).text

    gasto = Gasto.objects.get()
    assert (gasto.taller, gasto.valor, gasto.categoria, gasto.por_asistente) == (
        prendido, 65_000, "servicios", True)
    assert gasto.fecha == timezone.localdate()
    assert "Ver el resumen del mes" in html


def test_un_pedido_de_otro_taller_no_se_toca(sesion_duena, prendido, duena):
    ajeno = fabricas.crear_pedido(fabricas.crear_taller())
    tarjeta = borradores.armar(
        contexto_de(duena),
        [{"tipo": "abono", "datos": {"pedido": ajeno.pk, "valor": 100_000, "fecha": None}}],
        [Fila("Abono de hoy", "", 100_000)],
    )
    sembrar(sesion_duena, tarjeta)

    html = sesion_duena.post(URL, {"firma": tarjeta.datos["firma"]}, **HTMX).text

    assert "No se guardó nada: Ese pedido ya no existe." in html
    assert not Abono.objects.exists()


# --- Cuándo un borrador ya no sirve -----------------------------------------------------------


def test_un_borrador_sirve_una_sola_vez(sesion_duena, prendido, duena):
    tarjeta = borrador_del_gasto(duena)
    sembrar(sesion_duena, tarjeta)
    sesion_duena.post(URL, {"firma": tarjeta.datos["firma"]}, **HTMX)
    # Otra pestaña con la misma tarjeta todavía pendiente.
    sembrar(sesion_duena, tarjeta)

    html = sesion_duena.post(URL, {"firma": tarjeta.datos["firma"]}, **HTMX).text

    assert Gasto.objects.count() == 1
    assert "Este borrador ya se guardó." in html


def test_dos_toques_seguidos_guardan_una_vez(sesion_duena, prendido, duena):
    tarjeta = borrador_del_gasto(duena)
    sembrar(sesion_duena, tarjeta)

    for _ in range(2):
        sesion_duena.post(URL, {"firma": tarjeta.datos["firma"]}, **HTMX)

    assert Gasto.objects.count() == 1


def test_un_borrador_vencido_no_guarda(sesion_duena, prendido, duena, monkeypatch):
    tarjeta = borrador_del_gasto(duena)
    sembrar(sesion_duena, tarjeta)
    monkeypatch.setattr(borradores, "VIGENCIA_SEGUNDOS", -1)

    html = sesion_duena.post(URL, {"firma": tarjeta.datos["firma"]}, **HTMX).text

    assert "Este borrador venció. Pídemelo otra vez." in html
    assert not Gasto.objects.exists()
    assert 'name="firma"' not in html  # sin Guardar: hay que pedirlo otra vez


def test_un_borrador_reemplazado_no_guarda(sesion_duena, prendido, duena):
    tarjeta = borrador_del_gasto(duena)
    datos = asdict(tarjeta)
    datos["datos"]["estado"] = "reemplazado"
    sembrar(sesion_duena, datos)

    html = sesion_duena.post(URL, {"firma": tarjeta.datos["firma"]}, **HTMX).text

    assert "Reemplazado" in html
    assert not Gasto.objects.exists()


def test_una_firma_que_no_esta_en_la_conversacion_no_guarda(sesion_duena, prendido, duena):
    sembrar(sesion_duena, borrador_del_gasto(duena))
    otra = borrador_del_gasto(duena, valor=999_000)  # firmada, pero no se le mostró

    html = sesion_duena.post(URL, {"firma": otra.datos["firma"]}, **HTMX).text

    assert "Este borrador ya no sirve." in html
    assert not Gasto.objects.exists()


def test_el_borrador_de_otra_duena_no_guarda(sesion_duena, prendido, duena):
    otra = fabricas.crear_usuaria(fabricas.crear_taller())
    tarjeta = borrador_del_gasto(otra)
    sembrar(sesion_duena, tarjeta)

    html = sesion_duena.post(URL, {"firma": tarjeta.datos["firma"]}, **HTMX).text

    assert "Este borrador ya no sirve." in html
    assert not Gasto.objects.exists()


# --- Quién y cuánto ---------------------------------------------------------------------------


def test_la_costurera_no_puede(client, prendido):
    client.force_login(fabricas.crear_usuaria(prendido, rol=Usuario.Rol.COSTURERA))

    assert client.post(URL, {"firma": "x"}, **HTMX).status_code == 403


def test_con_el_asistente_apagado_no_existe(sesion_duena, settings, duena):
    settings.ANTHROPIC_API_KEY = ""

    assert sesion_duena.post(URL, {"firma": "x"}, **HTMX).status_code == 404


def test_solo_por_post(sesion_duena, prendido):
    assert sesion_duena.get(URL).status_code == 405


def test_guardar_no_llama_a_claude_ni_gasta_preguntas(sesion_duena, prendido, duena,
                                                      monkeypatch, settings):
    llamado = falso.instalar(monkeypatch, settings, [])
    tarjeta = borrador_del_gasto(duena)
    sembrar(sesion_duena, tarjeta)

    sesion_duena.post(URL, {"firma": tarjeta.datos["firma"]}, **HTMX)

    assert llamado.llamadas == []
    assert not UsoAsistente.objects.filter(preguntas__gt=0).exists()


def test_sin_javascript_vuelve_al_panel(sesion_duena, prendido, duena):
    tarjeta = borrador_del_gasto(duena)
    sembrar(sesion_duena, tarjeta)

    respuesta = sesion_duena.post(URL, {"firma": tarjeta.datos["firma"]})

    assert respuesta.status_code == 302 and respuesta.url == reverse("asistente:panel")
    assert Gasto.objects.count() == 1


# --- Lo que sigue en la conversación ----------------------------------------------------------


def test_lo_guardado_se_le_cuenta_a_claude_en_la_siguiente_pregunta(sesion_duena, prendido,
                                                                    duena, monkeypatch, settings):
    tarjeta = borrador_del_gasto(duena)
    sembrar(sesion_duena, tarjeta)
    sesion_duena.post(URL, {"firma": tarjeta.datos["firma"]}, **HTMX)
    claude = falso.instalar(monkeypatch, settings, [falso.texto("Listo."), falso.texto("Bien.")])

    sesion_duena.post("/asistente/preguntar/", {"pregunta": "¿Y ahora?"}, **HTMX)
    sistema_de_la_pregunta = claude.llamadas[0]["mensajes"][-1]

    assert sistema_de_la_pregunta["role"] == "system"
    assert "quedó guardado: gasto de $ 65.000 (Recibo de agua del taller)" in (
        sistema_de_la_pregunta["content"])
    # Se cuenta una sola vez.
    sesion_duena.post("/asistente/preguntar/", {"pregunta": "¿Y después?"}, **HTMX)
    assert "quedó guardado" not in claude.llamadas[1]["mensajes"][-1]["content"]


def test_corregir_deja_reemplazado_el_borrador_viejo_y_no_otros(sesion_duena, prendido, duena,
                                                               monkeypatch):
    viejo = borrador_del_gasto(duena)
    otro = borrador_del_gasto(duena, concepto="Hilos", categoria="insumos")
    sembrar(sesion_duena, viejo, otro)
    nuevo = borrador_del_gasto(duena, valor=70_000)

    def preguntar(**_):
        return Respuesta(estado="ok", texto="Revísalo y toca Guardar:",
                         resultados=[Resultado({}, "Preparé el gasto", tarjeta=nuevo)],
                         uso=Uso(entrada=10), mensajes=[{"role": "user", "content": "x"}],
                         cobrada=True)

    monkeypatch.setattr("asistente.conversacion.preguntar", preguntar)
    sesion_duena.post("/asistente/preguntar/",
                      {"pregunta": "No, eran 70 mil", "corrige": viejo.datos["clave"]}, **HTMX)

    assert tarjeta_en_sesion(sesion_duena, viejo.datos["clave"])["datos"]["estado"] == "reemplazado"
    assert tarjeta_en_sesion(sesion_duena, otro.datos["clave"])["datos"]["estado"] == "pendiente"
    assert tarjeta_en_sesion(sesion_duena, nuevo.datos["clave"])["datos"]["estado"] == "pendiente"
    html = sesion_duena.post(URL, {"firma": viejo.datos["firma"]}, **HTMX).text
    assert "Reemplazado" in html and not Gasto.objects.exists()


def test_la_tarjeta_pendiente_trae_corregir_y_guardar(sesion_duena, prendido, duena, dril):
    tarjeta = borrador_del_pedido(duena, dril)
    sembrar(sesion_duena, tarjeta)

    html = sesion_duena.get("/asistente/", **HTMX).text

    assert f'data-asistente-corregir="{tarjeta.datos["clave"]}"' in html
    assert 'hx-post="/asistente/confirmar/"' in html and 'hx-target="closest .borrador"' in html
    assert "$ 2.310.000" in html and "Te faltan 48 m de dril azul." in html
    assert 'class="aviso borrador__aviso"' in html
