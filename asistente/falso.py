"""Un Claude de mentira para las pruebas: contesta lo que diga un guion, sin salir a internet.

Archivo congelado (docs/11-plan-tanda-7.md, sección 1.3): solo lo cambia el coordinador.

Cómo se usa en una prueba:

    from asistente import falso

    def test_algo(monkeypatch, settings, ...):
        claude = falso.instalar(monkeypatch, settings, [
            falso.usa(("quien_debe", {}, "toolu_1")),   # primera vuelta: pide una herramienta
            falso.texto("Te deben $ 5.790.000."),         # segunda vuelta: contesta
        ])
        ...
        assert claude.llamadas[1]["mensajes"][-1]["content"][0]["type"] == "tool_result"

`instalar` pone una clave de prueba y hace que `asistente.cliente.obtener_cliente()` devuelva
este cliente. Cada llamada a `enviar` se guarda (copiada) en `llamadas` y devuelve lo
siguiente del guion; si lo siguiente es una excepción, la lanza.

La forma de los bloques copia la de las respuestas reales de Claude Opus 5.5 (la prueba corta
con la clave de T26, 14 de noviembre de 2026):
    {"type": "thinking", "thinking": "", "signature": "..."}      (a veces no viene)
    {"type": "text", "text": "..."}
    {"type": "tool_use", "id": "toolu_...", "name": "...", "input": {...},
     "caller": {"type": "direct"}}
El bloque thinking a veces viene antes de pedir herramientas y a veces no: usa(...,
pensamiento_antes=False) para el segundo caso.
"""

import copy
import itertools

from asistente.contratos import RespuestaClaude, Uso

MODELO = "claude-opus-5-5"

_numero = itertools.count(1)


class ClienteFalso:
    def __init__(self, guion):
        self.guion = list(guion)
        self.llamadas = []

    def enviar(self, **datos):
        self.llamadas.append(copy.deepcopy(datos))
        if not self.guion:
            raise AssertionError("El guion del cliente falso se acabó: Claude no tenía más que decir.")
        siguiente = self.guion.pop(0)
        if isinstance(siguiente, BaseException):
            raise siguiente
        return siguiente


class ClienteProhibido:
    """El cliente de los ajustes de pruebas: falla si alguna prueba intenta usar a Claude."""

    def enviar(self, **datos):
        raise AssertionError(
            "Las pruebas no llaman a Claude. Usa asistente.falso.instalar() con un guion."
        )


def _uso(entrada=1200, salida=80, cache_escritura=0, cache_lectura=0):
    return Uso(entrada, salida, cache_escritura, cache_lectura)


def _respuesta(contenido, stop_reason, **uso):
    return RespuestaClaude(
        contenido=contenido,
        stop_reason=stop_reason,
        uso=_uso(**uso),
        modelo=MODELO,
        id_peticion=f"req_falso_{next(_numero)}",
    )


def pensamiento():
    """Un bloque thinking como los de Opus 5.5: sin texto, con firma."""
    return {"type": "thinking", "thinking": "", "signature": f"firma-falsa-{next(_numero)}"}


def texto(t, **uso):
    """Claude contesta con texto y termina."""
    return _respuesta([{"type": "text", "text": t}], "end_turn", **uso)


def usa(*llamadas, pensamiento_antes=True, texto_antes=None, **uso):
    """Claude pide una o varias herramientas: cada llamada es (nombre, entrada, id)."""
    contenido = [pensamiento()] if pensamiento_antes else []
    if texto_antes:
        contenido.append({"type": "text", "text": texto_antes})
    for nombre, entrada, id_llamada in llamadas:
        contenido.append(
            {
                "type": "tool_use",
                "id": id_llamada,
                "name": nombre,
                "input": entrada,
                "caller": {"type": "direct"},
            }
        )
    return _respuesta(contenido, "tool_use", **uso)


def rechazo(**uso):
    """Claude no contesta por sus reglas de seguridad."""
    return _respuesta([], "refusal", **uso)


def cortada(t="Te deben", **uso):
    """La respuesta se cortó por largo (max_tokens)."""
    return _respuesta([{"type": "text", "text": t}], "max_tokens", **uso)


def instalar(monkeypatch, settings, guion):
    """Pone una clave de prueba y hace que obtener_cliente() devuelva un ClienteFalso."""
    falso = ClienteFalso(guion)
    settings.ANTHROPIC_API_KEY = "clave-de-prueba"
    monkeypatch.setattr("asistente.cliente.obtener_cliente", lambda: falso)
    return falso
