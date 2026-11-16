"""El ciclo de una pregunta: Claude pide herramientas, la aplicación las corre, Claude contesta.

Carril B (T29). Reglas y pasos: docs/11-plan-tanda-7.md, sección 1.4.

1. Al historial se le agrega la pregunta (`role: "user"`) y, justo después, un mensaje
   `role: "system"` con la fecha de hoy, el nombre del taller y la pantalla. Ese mensaje
   queda en el historial y nunca se reescribe.
2. El esfuerzo se elige una sola vez (asistente/esfuerzo.py) y vale para todas las vueltas.
3. Hasta 5 vueltas: se le manda todo a Claude; si pide herramientas, se corren todas y sus
   resultados vuelven juntos en un solo mensaje. Si después de la 5.ª sigue pidiendo, una
   última llamada sin herramientas le pide contestar con lo que ya tiene.
4. Antes de leer lo que contestó se mira por qué paró: si no quiso (`refusal`) o se cortó
   (`max_tokens`), no se lee nada y la conversación queda como estaba.
5. Plazo total de 50 segundos, revisado antes de cada llamada.

El historial es solo-agregar: lo que ya estaba nunca se cambia ni se reordena, y lo que
contesta Claude (con sus bloques thinking) se guarda tal cual. Las instrucciones (`sistema`)
y las herramientas son siempre las mismas, byte a byte, entre llamadas y entre talleres: así
Claude reusa lo que tiene en caché y cada pregunta cuesta menos. Por eso la fecha, el taller
y la pantalla van en el mensaje `role: "system"` y nunca en `sistema`.
"""

import json
import time
from dataclasses import dataclass, field

import anthropic

from asistente import esfuerzo, herramientas as herramientas_del_taller
from asistente.contratos import ErrorDeHerramienta, Resultado, Uso
from asistente.esquemas import ESQUEMAS
from asistente.instrucciones import INSTRUCCIONES
from config.piezas import fecha_larga

MENSAJE_SIN_SERVICIO = "No pude contestar ahora. Intenta de nuevo en un rato."
MENSAJE_RECHAZO = "Eso no te lo puedo contestar. Pregúntame algo de tu taller."
MENSAJE_CORTADO = (
    "La respuesta me salió muy larga y se cortó. Pregúntame algo más puntual."
)
MAXIMO_VUELTAS = 5
PLAZO_SEGUNDOS = 50
# El bloque que va después de los resultados cuando ya no quedan vueltas.
CONTESTA_YA = "Contesta con lo que ya tienes."


@dataclass(frozen=True)
class Respuesta:
    estado: str  # ok | error | rechazo | cortado
    texto: str  # el de Claude o el mensaje amable; SIEMPRE se muestra escapado
    resultados: list[Resultado]  # las herramientas que funcionaron, en orden (vacía si no fue ok)
    uso: Uso  # suma de todas las llamadas, también si falló
    mensajes: list[dict]  # historial nuevo; si no fue ok, el mismo que entró
    cobrada: bool  # False si ninguna llamada llegó a responder
    reiniciar: bool = False  # True si el historial ya no sirve (BadRequestError): borrarlo
    # Para el registro del servidor (sin el texto de la pregunta):
    vueltas: int = 0  # cuántas llamadas a Claude respondieron
    esfuerzo: str = ""  # "medium" o "high"
    stop_reason: str = ""  # por qué paró la última respuesta ("" si ninguna respondió)
    modelos: tuple[str, ...] = field(default_factory=tuple)  # quién contestó cada vuelta


def sistema() -> list[dict]:
    """Las instrucciones tal como van a Claude. Siempre iguales."""
    return [{"type": "text", "text": INSTRUCCIONES, "cache_control": {"type": "ephemeral"}}]


def contexto(ctx, pagina: str, nota: str = "") -> str:
    """El mensaje `role: "system"` de una pregunta: hoy, el taller, la pantalla y, si la dueña
    guardó algún borrador desde la última respuesta, qué guardó (tanda 8). Así lo guardado se le
    cuenta a Claude sin tocar el historial."""
    fecha = fecha_larga(ctx.hoy)
    fecha = fecha[:1].lower() + fecha[1:]  # "sábado, 14 de noviembre"
    partes = [f"Hoy es {fecha} de {ctx.hoy.year}.", f"Taller: {ctx.taller.nombre}."]
    if pagina:
        partes.append(pagina)
    if nota:
        partes.append(f"Desde tu última respuesta, la dueña tocó Guardar y quedó guardado: {nota}.")
    return " ".join(partes)


def _texto_de(contenido) -> str:
    """La unión de los bloques de texto de una respuesta."""
    textos = [b.get("text", "").strip() for b in contenido if b.get("type") == "text"]
    return "\n\n".join(t for t in textos if t)


def _correr(pedidas, ctx):
    """Corre cada herramienta pedida. Devuelve (bloques tool_result, resultados que sirvieron)."""
    bloques, buenos = [], []
    for pedida in pedidas:
        try:
            resultado = herramientas_del_taller.ejecutar(pedida["name"], pedida.get("input"), ctx)
        except ErrorDeHerramienta as error:
            bloques.append(
                {
                    "type": "tool_result",
                    "tool_use_id": pedida["id"],
                    "content": str(error),
                    "is_error": True,
                }
            )
            continue
        buenos.append(resultado)
        bloques.append(
            {
                "type": "tool_result",
                "tool_use_id": pedida["id"],
                "content": json.dumps(resultado.datos, ensure_ascii=False, sort_keys=True),
            }
        )
    return bloques, buenos


def preguntar(
    *, cliente, ctx, mensajes, pregunta, pagina, herramientas=None, nota=""
) -> Respuesta:
    """Hace una pregunta a Claude con el historial de la conversación.

    `pagina` es el texto de la pantalla (asistente/pagina.py), no la ruta. `herramientas`
    None quiere decir todas (`esquemas.ESQUEMAS`). `mensajes` no se toca: la respuesta trae
    un historial nuevo. `nota`: lo que la dueña guardó desde la última respuesta (tanda 8).
    """
    inicio = time.monotonic()
    lista_de_herramientas = ESQUEMAS if herramientas is None else herramientas
    nivel = esfuerzo.elegir(pregunta)
    historial = [
        *mensajes,
        {"role": "user", "content": pregunta},
        {"role": "system", "content": contexto(ctx, pagina, nota)},
    ]
    uso = Uso()
    resultados = []
    vueltas = 0
    modelos = []
    sin_herramientas = False
    ultima_parada = ""

    def fin(estado, texto, *, reiniciar=False):
        exito = estado == "ok"
        return Respuesta(
            estado=estado,
            texto=texto,
            resultados=resultados if exito else [],
            uso=uso,
            mensajes=historial if exito else mensajes,
            cobrada=vueltas > 0,
            reiniciar=reiniciar,
            vueltas=vueltas,
            esfuerzo=nivel,
            stop_reason=ultima_parada,
            modelos=tuple(modelos),
        )

    while True:
        queda = PLAZO_SEGUNDOS - (time.monotonic() - inicio)
        if queda <= 0:
            return fin("error", MENSAJE_SIN_SERVICIO)
        try:
            # Cada llamada espera como mucho lo que le queda a la pregunta (T35).
            respuesta = cliente.enviar(
                sistema=sistema(),
                herramientas=lista_de_herramientas,
                mensajes=historial,
                esfuerzo=nivel,
                sin_herramientas=sin_herramientas,
                plazo=queda,
            )
        except anthropic.BadRequestError:
            # El historial ya no le sirve a la API (por ejemplo, bloques thinking de otra
            # versión de las instrucciones): la vista borra la conversación.
            return fin("error", MENSAJE_SIN_SERVICIO, reiniciar=True)
        except (anthropic.RateLimitError, anthropic.APIStatusError, anthropic.APIConnectionError):
            # APIConnectionError incluye cuando se acaba el tiempo de espera.
            return fin("error", MENSAJE_SIN_SERVICIO)

        vueltas += 1
        uso += respuesta.uso
        modelos.append(respuesta.modelo)
        ultima_parada = respuesta.stop_reason

        # Primero por qué paró; el contenido se lee después.
        if respuesta.stop_reason == "refusal":
            return fin("rechazo", MENSAJE_RECHAZO)
        if respuesta.stop_reason == "max_tokens":
            return fin("cortado", MENSAJE_CORTADO)

        historial.append({"role": "assistant", "content": respuesta.contenido})
        pedidas = [b for b in respuesta.contenido if b.get("type") == "tool_use"]

        if respuesta.stop_reason != "tool_use" or not pedidas:
            return fin("ok", _texto_de(respuesta.contenido))
        if sin_herramientas:
            # Se le dijo que no pidiera más y pidió igual: sin resultados no se puede guardar
            # esa respuesta (la siguiente llamada daría error), así que no se guarda nada.
            return fin("error", MENSAJE_SIN_SERVICIO)

        bloques, buenos = _correr(pedidas, ctx)
        resultados.extend(buenos)
        if vueltas >= MAXIMO_VUELTAS:
            bloques.append({"type": "text", "text": CONTESTA_YA})
            sin_herramientas = True
        historial.append({"role": "user", "content": bloques})
