"""El cliente que le habla a Claude (T29): qué le manda a la librería y qué devuelve.

La librería `anthropic` se reemplaza por una de mentira que guarda lo que recibe. Nada de esto
sale a internet (conftest.py además corta el envío dentro de la librería).
"""

import json
from types import SimpleNamespace

import pytest
from anthropic.types.beta import BetaTextBlock, BetaThinkingBlock, BetaToolUseBlock

from asistente import cliente, falso
from asistente.contratos import RespuestaClaude, Uso
from asistente.conversacion import sistema
from asistente.esquemas import ESQUEMAS

MENSAJES = [
    {"role": "user", "content": "¿Quién me debe plata?"},
    {"role": "system", "content": "Hoy es sábado, 14 de noviembre de 2026."},
]


class LibreriaFalsa:
    """Hace las veces de `anthropic.Anthropic`: guarda cómo se armó y qué se le pidió."""

    creados = []

    def __init__(self, **opciones):
        self.opciones = opciones
        self.pedidos = []  # (camino, datos)
        self.beta = SimpleNamespace(messages=SimpleNamespace(create=self._crear("beta")))
        self.messages = SimpleNamespace(create=self._crear("normal"))
        LibreriaFalsa.creados.append(self)

    def _crear(self, camino):
        def crear(**datos):
            self.pedidos.append((camino, datos))
            return respuesta_de_la_libreria()

        return crear


def respuesta_de_la_libreria(**uso):
    """Una respuesta como las que devuelve la librería, con bloques de verdad."""
    return SimpleNamespace(
        content=[
            BetaThinkingBlock(type="thinking", thinking="", signature="firma-de-prueba"),
            BetaTextBlock(type="text", text="Voy a revisar los saldos."),
            BetaToolUseBlock(
                type="tool_use",
                id="toolu_1",
                name="quien_debe",
                input={},
                caller={"type": "direct"},
            ),
        ],
        stop_reason="tool_use",
        usage=SimpleNamespace(
            input_tokens=uso.get("entrada", 1500),
            output_tokens=uso.get("salida", 90),
            cache_creation_input_tokens=uso.get("escritura", None),
            cache_read_input_tokens=uso.get("lectura", 3200),
        ),
        model="claude-opus-5-5",
        _request_id="req_de_prueba",
    )


@pytest.fixture
def libreria(monkeypatch, settings):
    LibreriaFalsa.creados = []
    monkeypatch.setattr(cliente.anthropic, "Anthropic", LibreriaFalsa)
    settings.ANTHROPIC_API_KEY = "clave-de-prueba"
    settings.ASISTENTE_FALLBACKS = True
    return LibreriaFalsa


def enviar(**cambios):
    datos = {
        "sistema": sistema(),
        "herramientas": ESQUEMAS,
        "mensajes": MENSAJES,
        "esfuerzo": "high",
        **cambios,
    }
    return cliente.ClienteAnthropic().enviar(**datos)


def ultimo_pedido(libreria):
    return libreria.creados[-1].pedidos[-1]


# --- Cómo se arma la librería ---------------------------------------------------------------


def test_arma_la_libreria_con_la_clave_explicita_45_segundos_y_un_reintento(libreria):
    cliente.ClienteAnthropic()

    assert libreria.creados[-1].opciones == {
        "api_key": "clave-de-prueba",
        "timeout": 45.0,
        "max_retries": 1,
    }


# --- Qué manda ------------------------------------------------------------------------------


def test_manda_lo_que_pide_el_plan_por_el_camino_beta_con_el_respaldo(libreria, settings):
    enviar()
    camino, datos = ultimo_pedido(libreria)

    assert camino == "beta"
    assert datos == {
        "model": settings.ASISTENTE_MODELO,
        "max_tokens": 8000,
        "system": sistema(),
        "tools": ESQUEMAS,
        "tool_choice": {"type": "auto"},
        "messages": MENSAJES,
        "output_config": {"effort": "high"},
        "cache_control": {"type": "ephemeral"},
        "betas": ["server-side-fallback-2026-07-01"],
        "fallbacks": "default",
    }


def test_nunca_manda_thinking_temperature_ni_tool_choice_forzado(libreria):
    enviar()
    enviar(sin_herramientas=True, esfuerzo="medium")

    for _camino, datos in libreria.creados[0].pedidos + libreria.creados[1].pedidos:
        for prohibido in ("thinking", "temperature", "top_p", "top_k", "budget_tokens"):
            assert prohibido not in datos
            assert prohibido not in json.dumps(datos["output_config"])
        assert datos["tool_choice"]["type"] in ("auto", "none")


def test_sin_herramientas_manda_tool_choice_none_y_las_herramientas_igual(libreria):
    enviar(sin_herramientas=True)
    _camino, datos = ultimo_pedido(libreria)

    assert datos["tool_choice"] == {"type": "none"}
    # Las herramientas siguen yendo, idénticas: así no cambia lo que Claude tiene en caché.
    assert datos["tools"] == ESQUEMAS


def test_el_esfuerzo_va_dentro_de_output_config(libreria):
    enviar(esfuerzo="medium")

    assert ultimo_pedido(libreria)[1]["output_config"] == {"effort": "medium"}


def test_sin_el_respaldo_usa_el_camino_normal_sin_betas_ni_fallbacks(libreria, settings):
    settings.ASISTENTE_FALLBACKS = False
    enviar()
    camino, datos = ultimo_pedido(libreria)

    assert camino == "normal"
    assert "betas" not in datos
    assert "fallbacks" not in datos
    assert datos["output_config"] == {"effort": "high"}
    assert datos["cache_control"] == {"type": "ephemeral"}


def test_las_instrucciones_van_con_su_marca_de_cache():
    assert sistema() == [
        {
            "type": "text",
            "text": sistema()[0]["text"],
            "cache_control": {"type": "ephemeral"},
        }
    ]
    assert sistema()[0]["text"]


# --- Qué devuelve ---------------------------------------------------------------------------


def test_devuelve_los_bloques_tal_cual_con_el_thinking_y_los_tokens(libreria):
    respuesta = enviar()

    assert isinstance(respuesta, RespuestaClaude)
    # Lo que importa: cada bloque es el to_dict(mode="json") de la librería, sin tocar.
    esperado = [b.to_dict(mode="json") for b in respuesta_de_la_libreria().content]
    assert respuesta.contenido == esperado
    assert respuesta.stop_reason == "tool_use"
    # Lo que no viene (None) cuenta como 0.
    assert respuesta.uso == Uso(entrada=1500, salida=90, cache_escritura=0, cache_lectura=3200)
    assert respuesta.modelo == "claude-opus-5-5"
    assert respuesta.id_peticion == "req_de_prueba"


def test_los_bloques_vuelven_como_json_puro(libreria):
    respuesta = enviar()

    # Se pueden guardar en la sesión y mandar de vuelta sin cambiar nada.
    assert json.loads(json.dumps(respuesta.contenido)) == respuesta.contenido


def test_sin_id_de_peticion_queda_vacio():
    sin_id = respuesta_de_la_libreria()
    sin_id._request_id = None

    assert cliente.traducir(sin_id).id_peticion == ""


# --- obtener_cliente ------------------------------------------------------------------------


def test_obtener_cliente_sin_clave_es_none(settings):
    settings.ANTHROPIC_API_KEY = ""

    assert cliente.obtener_cliente() is None


def test_obtener_cliente_con_clave_da_el_de_los_ajustes(settings, libreria):
    settings.ASISTENTE_CLIENTE = "asistente.cliente.ClienteAnthropic"

    assert isinstance(cliente.obtener_cliente(), cliente.ClienteAnthropic)


def test_en_las_pruebas_el_cliente_de_los_ajustes_es_el_prohibido(settings):
    settings.ANTHROPIC_API_KEY = "clave-de-prueba"

    assert isinstance(cliente.obtener_cliente(), falso.ClienteProhibido)


def test_anthropic_se_arma_solo_en_cliente_py():
    """La lista del revisor: `Anthropic(` solo en asistente/cliente.py (y la prueba corta).

    Fuera de las pruebas, que lo nombran para reemplazarlo."""
    from pathlib import Path

    raiz = Path(__file__).resolve().parents[2]
    encontrados = set()
    for archivo in raiz.rglob("*.py"):
        relativo = archivo.relative_to(raiz)
        # Las pruebas sí lo nombran (para reemplazarlo o para comprobar el corte de internet).
        if relativo.parts[0] in (".venv", ".claude") or archivo.name.startswith("test_"):
            continue
        if "Anthropic(" in archivo.read_text(encoding="utf-8"):
            encontrados.add(relativo.as_posix())

    assert encontrados <= {"asistente/cliente.py", "herramientas/humo_asistente.py"}
