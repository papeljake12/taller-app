"""Quién le habla a Claude.

Carril B (T29) completa `ClienteAnthropic.enviar`. `obtener_cliente` ya lo deja la base.
Reglas (docs/11-plan-tanda-7.md, sección 1.3):
- `anthropic.Anthropic(api_key=settings.ANTHROPIC_API_KEY, timeout=45.0, max_retries=1)`:
  la clave siempre explícita. `Anthropic(` solo aparece en este archivo.
- `client.beta.messages.create` con `model=settings.ASISTENTE_MODELO`, `max_tokens=8000`,
  `system`, `tools`, `messages`, `output_config={"effort": esfuerzo}`,
  `cache_control={"type": "ephemeral"}`, y con `settings.ASISTENTE_FALLBACKS`:
  `betas=["server-side-fallback-2026-07-01"]` y `fallbacks="default"`.
- `tool_choice` `{"type": "auto"}`, o `{"type": "none"}` con `sin_herramientas`. Nunca se
  manda `thinking`, `temperature` ni `tool_choice` any/tool (en Opus 5.5 dan 400).
- La respuesta vuelve como `RespuestaClaude` (asistente/contratos.py), con
  `[b.to_dict(mode="json") for b in response.content]` sin tocar.

Las pruebas nunca llegan a internet: conftest.py corta el envío de la librería, y los
ajustes de pruebas borran la clave.
"""

from typing import Protocol

from django.conf import settings
from django.utils.module_loading import import_string

from asistente.contratos import RespuestaClaude


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


class ClienteAnthropic:
    def enviar(
        self,
        *,
        sistema: list[dict],
        herramientas: list[dict],
        mensajes: list[dict],
        esfuerzo: str,
        sin_herramientas: bool = False,
    ) -> RespuestaClaude:
        raise NotImplementedError("Carril B (T29)")


def obtener_cliente() -> ClienteClaude | None:
    """El cliente de los ajustes (`ASISTENTE_CLIENTE`), o None si no hay clave.

    Quien lo use lo llama siempre por el módulo (`cliente.obtener_cliente()`), para que las
    pruebas lo puedan cambiar con `asistente.falso.instalar()`.
    """
    if not settings.ANTHROPIC_API_KEY:
        return None
    return import_string(settings.ASISTENTE_CLIENTE)()
