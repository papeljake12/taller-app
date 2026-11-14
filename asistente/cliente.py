"""Quién le habla a Claude.

Carril B (T29). `obtener_cliente` lo dejó la base. Reglas (docs/11-plan-tanda-7.md, 1.3):
- `anthropic.Anthropic(api_key=settings.ANTHROPIC_API_KEY, timeout=45.0, max_retries=1)`:
  la clave siempre explícita. `Anthropic(` solo aparece en este archivo.
- `client.beta.messages.create` con `model=settings.ASISTENTE_MODELO`, `max_tokens=8000`,
  `system`, `tools`, `messages`, `output_config={"effort": esfuerzo}`,
  `cache_control={"type": "ephemeral"}`, y con `settings.ASISTENTE_FALLBACKS`:
  `betas=["server-side-fallback-2026-07-01"]` y `fallbacks="default"`. Con el interruptor
  apagado, `client.messages.create` sin esos dos.
- `tool_choice` `{"type": "auto"}`, o `{"type": "none"}` con `sin_herramientas` (las
  herramientas se siguen mandando, para no cambiar lo que Claude tiene en caché). Nunca se
  manda `thinking`, `temperature` ni `tool_choice` any/tool (en Opus 5.5 dan 400).
- La respuesta vuelve como `RespuestaClaude` (asistente/contratos.py), con
  `[b.to_dict(mode="json") for b in response.content]` sin tocar: los bloques thinking
  vuelven tal cual en la siguiente llamada.

Los errores de la librería (sin conexión, límite, 400, 500) no se atrapan aquí: los atrapa
el ciclo (asistente/conversacion.py), que sabe qué decirle a la dueña.

Las pruebas nunca llegan a internet: conftest.py corta el envío de la librería, y los
ajustes de pruebas borran la clave.
"""

from typing import Protocol

import anthropic
from django.conf import settings
from django.utils.module_loading import import_string

from asistente.contratos import RespuestaClaude, Uso

MAXIMO_TOKENS = 8000
ESPERA_SEGUNDOS = 45.0
REINTENTOS = 1
BETA_RESPALDO = "server-side-fallback-2026-07-01"


class ClienteClaude(Protocol):
    def enviar(
        self,
        *,
        sistema: list[dict],
        herramientas: list[dict],
        mensajes: list[dict],
        esfuerzo: str,
        sin_herramientas: bool = False,
    ) -> RespuestaClaude: ...


def _tokens(valor):
    """Los tokens que reporta la librería; si no vienen (None), 0."""
    return valor or 0


def traducir(respuesta) -> RespuestaClaude:
    """La respuesta de la librería, pasada a diccionarios sin tocar nada."""
    uso = respuesta.usage
    return RespuestaClaude(
        contenido=[bloque.to_dict(mode="json") for bloque in respuesta.content],
        stop_reason=respuesta.stop_reason or "",
        uso=Uso(
            entrada=_tokens(getattr(uso, "input_tokens", None)),
            salida=_tokens(getattr(uso, "output_tokens", None)),
            cache_escritura=_tokens(getattr(uso, "cache_creation_input_tokens", None)),
            cache_lectura=_tokens(getattr(uso, "cache_read_input_tokens", None)),
        ),
        modelo=respuesta.model or "",
        id_peticion=getattr(respuesta, "_request_id", None) or "",
    )


class ClienteAnthropic:
    """El cliente de verdad: le habla a la API de Claude con la librería `anthropic`."""

    def __init__(self):
        self.api = anthropic.Anthropic(
            api_key=settings.ANTHROPIC_API_KEY,
            timeout=ESPERA_SEGUNDOS,
            max_retries=REINTENTOS,
        )

    def enviar(
        self,
        *,
        sistema: list[dict],
        herramientas: list[dict],
        mensajes: list[dict],
        esfuerzo: str,
        sin_herramientas: bool = False,
    ) -> RespuestaClaude:
        datos = {
            "model": settings.ASISTENTE_MODELO,
            "max_tokens": MAXIMO_TOKENS,
            "system": sistema,
            "tools": herramientas,
            "tool_choice": {"type": "none" if sin_herramientas else "auto"},
            "messages": mensajes,
            "output_config": {"effort": esfuerzo},
            "cache_control": {"type": "ephemeral"},
        }
        if settings.ASISTENTE_FALLBACKS:
            # Si Claude Opus 5.5 no quiere contestar por sus reglas de seguridad, la API
            # prueba sola con otro modelo dentro de la misma llamada.
            respuesta = self.api.beta.messages.create(
                **datos, betas=[BETA_RESPALDO], fallbacks="default"
            )
        else:
            respuesta = self.api.messages.create(**datos)
        return traducir(respuesta)


def obtener_cliente() -> ClienteClaude | None:
    """El cliente de los ajustes (`ASISTENTE_CLIENTE`), o None si no hay clave.

    Quien lo use lo llama siempre por el módulo (`cliente.obtener_cliente()`), para que las
    pruebas lo puedan cambiar con `asistente.falso.instalar()`.
    """
    if not settings.ANTHROPIC_API_KEY:
        return None
    return import_string(settings.ASISTENTE_CLIENTE)()
