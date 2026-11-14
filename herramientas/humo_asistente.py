"""Prueba corta del asistente con la clave real: 3 llamadas a Claude (T26, paso 17).

Comprueba, antes de construir el resto, que la forma de hablar con Claude que fija el plan
(docs/11-plan-tanda-7.md, sección 1.3) funciona de verdad:

1. Una pregunta con las 10 herramientas (esquemas `strict`), el mensaje `role: "system"` con
   la fecha y la pantalla, `output_config.effort`, caché automática y el respaldo del
   servidor (`fallbacks`). Claude debería pedir `quien_debe`.
2. Se le devuelve el resultado (inventado, marcado como ejemplo) con su respuesta anterior tal
   cual (`to_dict()`, con los bloques thinking). Debe contestar sin error 400.
3. Una segunda pregunta en la misma conversación, sin tocar lo anterior.

Imprime, por llamada: estado, modelo, motivo de parada, tipos de bloque, tokens (los cuatro)
y el costo. Con --guardar ARCHIVO deja la forma de los bloques (sin firmas) para copiarla en
asistente/falso.py. No guarda nada en la base y no imprime la clave.

Uso (con ANTHROPIC_API_KEY en .env):
    uv run python herramientas/humo_asistente.py
    uv run python herramientas/humo_asistente.py --guardar respuesta.json

Cuesta unos pocos centavos de dólar. Nunca corre dentro de pytest.
"""

import argparse
import json
import os
import sys
import time
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.local")

import django  # noqa: E402

django.setup()

import anthropic  # noqa: E402
from django.conf import settings  # noqa: E402

from asistente.contratos import Uso  # noqa: E402
from asistente.esquemas import ESQUEMAS  # noqa: E402
from asistente.uso import costo_usd  # noqa: E402

SISTEMA = [{
    "type": "text",
    "text": (
        "Eres el asistente de un taller de confección en Colombia. Contestas en español, "
        "corto y con las cifras que te dan las herramientas. Solo consultas: no creas, no "
        "cambias y no borras nada. Esta es una prueba corta del programa."
    ),
    "cache_control": {"type": "ephemeral"},
}]
CONTEXTO = (
    "Hoy es sábado 14 de noviembre de 2026. Taller: Taller de ejemplo. "
    "Pantalla actual: Hoy."
)
# Datos inventados, marcados como ejemplo: no son de ningún taller.
QUIEN_DEBE_EJEMPLO = {
    "ejemplo": True,
    "por_cobrar": 5_790_000,
    "deudores": [
        {"cliente_id": 1, "cliente": "Colegio Nuevo Amanecer (ejemplo)", "saldo": 3_300_000, "vencida": False},
        {"cliente_id": 2, "cliente": "Restaurante El Fogón Costeño (ejemplo)", "saldo": 1_260_000, "vencida": False},
        {"cliente_id": 3, "cliente": "Grupo de danza Tambores del Río (ejemplo)", "saldo": 750_000, "vencida": False},
        {"cliente_id": 4, "cliente": "Ferretería La Esquina (ejemplo)", "saldo": 480_000, "vencida": True},
    ],
}


def llamar(cliente, mensajes, esfuerzo):
    datos = {
        "model": settings.ASISTENTE_MODELO,
        "max_tokens": 8000,
        "system": SISTEMA,
        "tools": ESQUEMAS,
        "tool_choice": {"type": "auto"},
        "messages": mensajes,
        "output_config": {"effort": esfuerzo},
        "cache_control": {"type": "ephemeral"},
    }
    if settings.ASISTENTE_FALLBACKS:
        datos["betas"] = ["server-side-fallback-2026-07-01"]
        datos["fallbacks"] = "default"
    inicio = time.monotonic()
    respuesta = cliente.beta.messages.create(**datos)
    return respuesta, time.monotonic() - inicio


def informe(numero, respuesta, segundos):
    uso = respuesta.usage
    tokens = Uso(
        entrada=uso.input_tokens or 0,
        salida=uso.output_tokens or 0,
        cache_escritura=uso.cache_creation_input_tokens or 0,
        cache_lectura=uso.cache_read_input_tokens or 0,
    )
    print(f"Llamada {numero}: OK en {segundos:.1f} s · modelo {respuesta.model} · "
          f"parada {respuesta.stop_reason}")
    print(f"  bloques: {[b.type for b in respuesta.content]}")
    print(f"  tokens: entran {tokens.entrada}, salen {tokens.salida}, "
          f"caché escrita {tokens.cache_escritura}, caché leída {tokens.cache_lectura}")
    print(f"  costo: {costo_usd(tokens):.4f} USD · id {respuesta._request_id}")
    for bloque in respuesta.content:
        if bloque.type == "text":
            print("  texto:", bloque.text.replace("\n", " ")[:300])
    return tokens


def sin_firmas(contenido):
    copia = json.loads(json.dumps(contenido))
    for bloque in copia:
        for clave in ("signature", "data"):
            if clave in bloque:
                bloque[clave] = f"<{len(bloque[clave])} caracteres>"
    return copia


def main():
    opciones = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    opciones.add_argument("--guardar", type=Path, help="archivo JSON con la forma de los bloques")
    opciones = opciones.parse_args()

    if not settings.ANTHROPIC_API_KEY:
        raise SystemExit("Falta ANTHROPIC_API_KEY en el .env.")
    cliente = anthropic.Anthropic(api_key=settings.ANTHROPIC_API_KEY, timeout=45.0, max_retries=1)
    mensajes = [
        {"role": "user", "content": "¿Quién me debe plata?"},
        {"role": "system", "content": CONTEXTO},
    ]
    formas = []
    total = Uso()

    try:
        # 1. La pregunta: debería pedir quien_debe.
        primera, segundos = llamar(cliente, mensajes, "high")
        total += informe(1, primera, segundos)
        contenido = [b.to_dict(mode="json") for b in primera.content]
        formas.append(sin_firmas(contenido))
        mensajes.append({"role": "assistant", "content": contenido})
        pedidas = [b for b in contenido if b["type"] == "tool_use"]
        if primera.stop_reason != "tool_use" or not pedidas:
            print("  OJO: no pidió herramientas. La ida y vuelta de tool_use no se probó.")
        else:
            resultados = []
            for bloque in pedidas:
                if bloque["name"] == "quien_debe":
                    resultados.append({
                        "type": "tool_result", "tool_use_id": bloque["id"],
                        "content": json.dumps(QUIEN_DEBE_EJEMPLO, ensure_ascii=False, sort_keys=True),
                    })
                else:
                    resultados.append({
                        "type": "tool_result", "tool_use_id": bloque["id"], "is_error": True,
                        "content": "Esa herramienta no está en esta prueba.",
                    })
            mensajes.append({"role": "user", "content": resultados})

            # 2. La respuesta con el resultado: el historial va con los thinking tal cual.
            segunda, segundos = llamar(cliente, mensajes, "high")
            total += informe(2, segunda, segundos)
            contenido = [b.to_dict(mode="json") for b in segunda.content]
            formas.append(sin_firmas(contenido))
            mensajes.append({"role": "assistant", "content": contenido})

        # 3. Otra pregunta en la misma conversación.
        mensajes.append({"role": "user", "content": "¿Y cuál de esas deudas está vencida?"})
        mensajes.append({"role": "system", "content": CONTEXTO})
        tercera, segundos = llamar(cliente, mensajes, "medium")
        total += informe(3, tercera, segundos)
        formas.append(sin_firmas([b.to_dict(mode="json") for b in tercera.content]))
    except anthropic.APIStatusError as error:
        print(f"FALLÓ con {error.status_code}: {error.message}")
        print(f"  id {error.request_id}")
        raise SystemExit(1) from None
    except anthropic.APIConnectionError as error:
        print(f"FALLÓ la conexión: {error}")
        raise SystemExit(1) from None

    print(f"Total: {costo_usd(total):.4f} USD")
    if opciones.guardar:
        opciones.guardar.write_text(json.dumps(formas, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"Forma de los bloques guardada en {opciones.guardar}")


if __name__ == "__main__":
    main()
