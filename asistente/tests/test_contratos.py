"""La base del asistente (T26): esquemas, registro, la puerta `ejecutar`, el cliente falso,
el corte de internet de las pruebas y quién tiene el asistente disponible."""

import json
from datetime import date

import anthropic
import pytest
from django.test import RequestFactory

from asistente import cliente, esquemas, falso, herramientas
from asistente.contratos import Contexto, ErrorDeHerramienta, Resultado, Uso
from asistente.disponibilidad import disponible
from cuentas.models import Usuario
from tests import fabricas

# --- Esquemas y registro --------------------------------------------------------------------


def test_los_esquemas_y_el_registro_tienen_las_mismas_trece_herramientas():
    # Diez de consulta (tanda 7) y tres que proponen borradores (tanda 8).
    assert len(esquemas.ESQUEMAS) == 13
    assert set(esquemas.NOMBRES) == set(herramientas.REGISTRO)
    assert herramientas.DE_PLATA <= set(herramientas.REGISTRO)
    assert {"proponer_pedido", "proponer_abono", "proponer_gasto"} <= herramientas.DE_PLATA


def _con_uniones(propiedad):
    tipos = propiedad.get("type")
    return "anyOf" in propiedad or isinstance(tipos, list)


def test_no_pasan_del_limite_de_parametros_anulables_de_la_api():
    # Con strict, la API acepta como mucho 16 parámetros con varios tipos (null incluido),
    # sumando todas las herramientas: con más responde 400 (prueba corta de la tanda 8).
    uniones = sum(
        _con_uniones(p) for h in esquemas.ESQUEMAS for p in h["input_schema"]["properties"].values()
    )
    assert uniones <= 16


def test_los_vacios_de_los_borradores_llegan_como_none(taller):
    entrada = {"pedido_id": 0, "cliente": "", "valor": 300_000, "fecha": ""}
    assert herramientas.validar("proponer_abono", entrada) == {
        "pedido_id": None, "cliente": None, "valor": 300_000, "fecha": None,
    }
    entrada = {"pedido_id": 7, "cliente": "Tambores", "valor": 300_000, "fecha": "2026-11-15"}
    assert herramientas.validar("proponer_abono", entrada)["fecha"].isoformat() == "2026-11-15"
    with pytest.raises(ErrorDeHerramienta, match="AAAA-MM-DD"):
        herramientas.validar("proponer_gasto", {
            "concepto": "Luz", "categoria": "servicios", "valor": 1, "fecha": "ayer",
            "pedido_id": 0,
        })


def test_ninguna_herramienta_borra():
    # Regla fija del agente (docs/12-agente.md): no existe herramienta para borrar.
    for nombre in esquemas.NOMBRES:
        assert not any(p in nombre for p in ("borrar", "quitar", "eliminar"))
    for esquema in esquemas.ESQUEMAS:
        descripcion = esquema["description"].lower()
        assert not any(p in descripcion for p in ("borrar", "borra ", "quita ", "elimina"))


def test_los_esquemas_van_ordenados_por_nombre_y_siempre_iguales():
    assert list(esquemas.NOMBRES) == sorted(esquemas.NOMBRES)
    # Byte a byte iguales cada vez: así Claude los guarda en caché.
    assert json.dumps(esquemas.ESQUEMAS, sort_keys=True) == json.dumps(
        sorted(esquemas.ESQUEMAS, key=lambda h: h["name"]), sort_keys=True
    )


@pytest.mark.parametrize("herramienta", esquemas.ESQUEMAS, ids=lambda h: h["name"])
def test_cada_esquema_es_estricto_y_pide_todas_sus_propiedades(herramienta):
    esquema = herramienta["input_schema"]

    assert herramienta["strict"] is True
    assert herramienta["description"]
    assert esquema["type"] == "object"
    assert esquema["additionalProperties"] is False
    assert esquema["required"] == list(esquema["properties"])
    assert set(herramienta) == {"name", "description", "strict", "input_schema"}


def test_los_rangos_hablan_de_campos_que_existen():
    for nombre, campo in herramientas.RANGOS:
        assert campo in esquemas.POR_NOMBRE[nombre]["input_schema"]["properties"]


# --- validar y ejecutar ---------------------------------------------------------------------


def contexto(taller):
    duena = fabricas.crear_usuaria(taller)
    return Contexto(taller=taller, usuaria=duena, hoy=date(2026, 11, 14), pedido_actual=None,
                    url_base="http://testserver/")


@pytest.mark.parametrize(
    ("nombre", "entrada"),
    [
        ("cotizar", {"prenda": "Polo", "cantidad": 10, "ganancia_pct": None}),  # falta
        ("telas", {"solo_bajas": True, "taller_id": 2}),  # sobra
        ("telas", {"solo_bajas": "si"}),  # tipo
        ("cotizar", {"prenda": "Polo", "cantidad": True, "ganancia_pct": None, "abono_pct": None}),
        ("buscar_pedidos", {"texto": None, "filtro": "todo", "entrega_desde": None,
                            "entrega_hasta": None}),  # opción que no existe
        ("entregas", {"desde": "14/11/2026", "hasta": "2026-11-20"}),  # fecha mal escrita
        ("cotizar", {"prenda": "Polo", "cantidad": 0, "ganancia_pct": None, "abono_pct": None}),
        ("cotizar", {"prenda": "Polo", "cantidad": 2001, "ganancia_pct": None, "abono_pct": None}),
        ("cuentas_del_mes", {"anio": 2026, "mes": 13}),
        ("preparar_mensaje", {"pedido_id": 1, "cliente_id": None, "motivo": "cobro",
                              "texto": "x" * 701}),
        ("ver_pedido", {"pedido_id": 0}),
        ("no_existe", {}),
        ("telas", ["solo_bajas"]),
    ],
)
def test_ejecutar_rechaza_lo_que_no_cumple_el_esquema(taller, nombre, entrada):
    with pytest.raises(ErrorDeHerramienta):
        herramientas.ejecutar(nombre, entrada, contexto(taller))


def test_validar_convierte_las_fechas_y_deja_lo_demas_igual():
    entrada = {"texto": "colegio", "filtro": None, "entrega_desde": "2026-11-01",
               "entrega_hasta": None}

    assert herramientas.validar("buscar_pedidos", entrada) == {
        "texto": "colegio", "filtro": None, "entrega_desde": date(2026, 11, 1),
        "entrega_hasta": None,
    }


def test_ejecutar_corre_la_herramienta_con_el_contexto(taller, monkeypatch):
    vistos = []

    def telas(ctx, *, solo_bajas):
        vistos.append((ctx.taller, solo_bajas))
        return Resultado(datos={"cantidad": 0}, revisado="Revisé tus telas")

    monkeypatch.setitem(herramientas.REGISTRO, "telas", telas)

    resultado = herramientas.ejecutar("telas", {"solo_bajas": True}, contexto(taller))

    assert resultado.datos == {"cantidad": 0}
    assert vistos == [(taller, True)]


@pytest.mark.parametrize(
    ("falla", "texto"),
    [
        (NotImplementedError("sin hacer"), "Esa consulta todavía no está lista."),
        (ZeroDivisionError("un error del código"), "No pude hacer esa consulta."),
        (ErrorDeHerramienta("No encontré ese pedido."), "No encontré ese pedido."),
    ],
)
def test_lo_que_sale_mal_le_llega_a_claude_como_error_de_herramienta(
    taller, monkeypatch, falla, texto
):
    def telas(ctx, *, solo_bajas):
        raise falla

    monkeypatch.setitem(herramientas.REGISTRO, "telas", telas)

    with pytest.raises(ErrorDeHerramienta, match=texto):
        herramientas.ejecutar("telas", {"solo_bajas": False}, contexto(taller))


# --- Contratos ------------------------------------------------------------------------------


def test_los_usos_se_suman():
    total = Uso(10, 2, 3, 4) + Uso(1, 1, 1, 1)

    assert total == Uso(11, 3, 4, 5)
    assert total.total == 23


# --- Cliente falso y corte de internet ------------------------------------------------------


def test_el_cliente_falso_sigue_su_guion_y_guarda_copia_de_cada_llamada(monkeypatch, settings):
    claude = falso.instalar(monkeypatch, settings, [
        falso.usa(("quien_debe", {}, "toolu_1")),
        anthropic.APIConnectionError(request=None),
        falso.texto("Listo."),
    ])
    mensajes = [{"role": "user", "content": "¿Quién me debe?"}]

    primera = cliente.obtener_cliente().enviar(mensajes=mensajes, esfuerzo="high")
    mensajes.append({"role": "assistant", "content": primera.contenido})
    with pytest.raises(anthropic.APIConnectionError):
        cliente.obtener_cliente().enviar(mensajes=mensajes, esfuerzo="high")
    ultima = cliente.obtener_cliente().enviar(mensajes=mensajes, esfuerzo="high")

    assert primera.stop_reason == "tool_use"
    assert [b["type"] for b in primera.contenido] == ["thinking", "tool_use"]
    assert ultima.contenido[0]["text"] == "Listo."
    assert len(claude.llamadas) == 3
    assert len(claude.llamadas[0]["mensajes"]) == 1  # una copia: no cambió después


def test_sin_clave_no_hay_cliente(settings):
    settings.ANTHROPIC_API_KEY = ""

    assert cliente.obtener_cliente() is None


def test_en_las_pruebas_el_cliente_de_los_ajustes_falla_si_lo_usan(settings):
    settings.ANTHROPIC_API_KEY = "clave-de-prueba"

    with pytest.raises(AssertionError, match="no llaman a Claude"):
        cliente.obtener_cliente().enviar(mensajes=[], esfuerzo="medium")


def test_la_libreria_de_anthropic_no_llega_a_internet_en_las_pruebas():
    llamada = anthropic.Anthropic(api_key="clave-de-prueba", max_retries=0)

    with pytest.raises(AssertionError, match="no llaman a la API de Claude"):
        llamada.messages.create(
            model="claude-opus-5-5", max_tokens=10, messages=[{"role": "user", "content": "Hola"}]
        )


# --- Quién lo tiene disponible --------------------------------------------------------------


def solicitud(usuaria):
    request = RequestFactory().get("/")
    request.user = usuaria
    request.taller = usuaria.taller
    return request


@pytest.fixture
def taller_prendido(db):
    return fabricas.crear_taller(asistente_limite_mes=600, asistente_limite_dia=40)


def test_disponible_solo_con_clave_dueña_y_taller_prendido(settings, taller_prendido):
    settings.ANTHROPIC_API_KEY = "clave-de-prueba"
    duena = fabricas.crear_usuaria(taller_prendido)
    costurera = fabricas.crear_usuaria(taller_prendido, rol=Usuario.Rol.COSTURERA)
    apagado = fabricas.crear_usuaria(fabricas.crear_taller())
    solo_dia = fabricas.crear_usuaria(fabricas.crear_taller(asistente_limite_dia=40))

    assert disponible(solicitud(duena))
    assert not disponible(solicitud(costurera))
    assert not disponible(solicitud(apagado))
    assert not disponible(solicitud(solo_dia))

    settings.ANTHROPIC_API_KEY = ""
    assert not disponible(solicitud(duena))


@pytest.mark.parametrize("direccion", ["/asistente/", "/asistente/preguntar/", "/asistente/nueva/"])
def test_las_direcciones_responden_404_si_no_esta_disponible(client, settings, db, direccion):
    settings.ANTHROPIC_API_KEY = "clave-de-prueba"
    client.force_login(fabricas.crear_usuaria(fabricas.crear_taller()))

    metodo = client.get if direccion == "/asistente/" else client.post
    assert metodo(direccion).status_code == 404


@pytest.mark.parametrize("direccion", ["/asistente/", "/asistente/preguntar/", "/asistente/nueva/"])
def test_las_direcciones_no_son_para_la_costurera(client, settings, taller_prendido, direccion):
    settings.ANTHROPIC_API_KEY = "clave-de-prueba"
    client.force_login(fabricas.crear_usuaria(taller_prendido, rol=Usuario.Rol.COSTURERA))

    metodo = client.get if direccion == "/asistente/" else client.post
    assert metodo(direccion).status_code == 403
