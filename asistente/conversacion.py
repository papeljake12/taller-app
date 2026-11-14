"""El ciclo de una pregunta: Claude pide herramientas, la aplicación las corre, Claude contesta.

Carril B (T29). Reglas y pasos: docs/11-plan-tanda-7.md, sección 1.4.
"""

from dataclasses import dataclass

from asistente.contratos import Resultado, Uso

MENSAJE_SIN_SERVICIO = "No pude contestar ahora. Intenta de nuevo en un rato."
MAXIMO_VUELTAS = 5
PLAZO_SEGUNDOS = 50


@dataclass(frozen=True)
class Respuesta:
    estado: str  # ok | error | rechazo | cortado
    texto: str  # el de Claude o el mensaje amable; SIEMPRE se muestra escapado
    resultados: list[Resultado]
    uso: Uso  # suma de todas las llamadas, también si falló
    mensajes: list[dict]  # historial nuevo; si no fue ok, el mismo que entró
    cobrada: bool  # False si ninguna llamada llegó a responder
    reiniciar: bool = False  # True si el historial ya no sirve (BadRequestError): borrarlo


def preguntar(*, cliente, ctx, mensajes, pregunta, pagina, herramientas=None) -> Respuesta:
    raise NotImplementedError("Carril B (T29)")
