"""Prueba corta del agente con la clave real (tanda 8, T38, paso 11 de docs/13-plan-tanda-8.md).

Antes de lanzar los carriles comprueba, con el cliente de verdad (asistente/cliente.py), que:

1. Las 13 herramientas (las 10 de consulta y las 3 que proponen borradores, todas `strict`) se
   aceptan sin error 400, y que con el pedido de las 10:30 Claude busca lo que necesita y pide
   `proponer_pedido`. Las herramientas NO corren: se le devuelven resultados inventados,
   marcados como ejemplo. No se guarda nada en la base.
2. La nota de lo guardado viaja en el mensaje `role: "system"` de la siguiente pregunta
   (asistente/conversacion.py, `contexto(..., nota)`) sin error 400.
3. Una llamada sin herramientas (como el resumen de la mañana) no manda `tools` ni
   `tool_choice` y contesta texto.

Imprime, por llamada: motivo de parada, herramientas pedidas, tokens y costo. No imprime la
clave. Cuesta unos pocos centavos de dólar. Nunca corre dentro de pytest.

Uso (con ANTHROPIC_API_KEY en .env):
    uv run python herramientas/humo_agente.py
"""

import json
import os
import sys
import time
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.local")

import django  # noqa: E402

django.setup()

from datetime import date  # noqa: E402

from django.conf import settings  # noqa: E402

from asistente import borradores, conversacion  # noqa: E402
from asistente.cliente import ClienteAnthropic  # noqa: E402
from asistente.contratos import Uso  # noqa: E402
from asistente.esquemas import ESQUEMAS  # noqa: E402
from asistente.uso import costo_usd  # noqa: E402

HOY = "Hoy es domingo, 15 de noviembre de 2026. Taller: Taller de ejemplo. La dueña está en Hoy."
PEDIDO = (
    "Vino la profe del Colegio Ejemplo, quiere 30 uniformes de diario para el 15 de "
    "diciembre y dejó 500 mil."
)

# Resultados inventados para cada herramienta (todo es de ejemplo).
RESULTADOS = {
    "buscar_clientes": {"clientes": [
        {"id": 7, "nombre": "Colegio Ejemplo", "tipo": "colegio", "pedidos": 1,
         "ha_comprado": 0, "debe": 0, "cotizacion_abierta": False, "tiene_whatsapp": True},
    ]},
    "cotizar": {"prenda": "Uniforme de diario (ejemplo)", "cantidad": 30, "costo": 59200,
                "precio_unidad": 77000, "total": 2310000, "abono": 1155000,
                "ganancia": 533000, "metros_totales": "66.00"},
    "telas": {"cantidad": 1, "metros": "18.00", "telas": [
        {"nombre": "Dril azul (ejemplo)", "metros": "18.00", "minimo": "10.00", "baja": False},
    ]},
    "proponer_pedido": {
        "borrador": "listo",
        "filas": [
            {"titulo": "Pedido nuevo", "detalle": "Colegio Ejemplo · 30 uniformes de diario",
             "valor": 2310000, "aviso": ""},
            {"titulo": "Abono de hoy", "detalle": "Después del abono falta $ 1.810.000",
             "valor": 500000, "aviso": ""},
            {"titulo": "Tela", "detalle": "66 m de dril azul. Tienes 18 m.", "valor": None,
             "aviso": "Te faltan 48 m de dril azul."},
        ],
        "nota": borradores.NOTA_PARA_CLAUDE,
    },
}


def informe(numero, respuesta, segundos):
    pedidas = [b["name"] for b in respuesta.contenido if b.get("type") == "tool_use"]
    u = respuesta.uso
    print(
        f"{numero}. parada={respuesta.stop_reason} modelo={respuesta.modelo} "
        f"herramientas={pedidas or '-'} entrada={u.entrada} salida={u.salida} "
        f"cache_escritura={u.cache_escritura} cache_lectura={u.cache_lectura} "
        f"costo=US$ {costo_usd(u):.4f} segundos={segundos:.1f}"
    )
    return pedidas


def enviar(cliente, **datos):
    inicio = time.monotonic()
    respuesta = cliente.enviar(sistema=conversacion.sistema(), plazo=45, **datos)
    return respuesta, time.monotonic() - inicio


def main():
    if not settings.ANTHROPIC_API_KEY:
        print("Falta ANTHROPIC_API_KEY en .env.")
        return 1
    cliente = ClienteAnthropic()
    total = Uso()
    numero = 0

    # 1. El pedido de las 10:30, con las 13 herramientas.
    mensajes = [{"role": "user", "content": PEDIDO}, {"role": "system", "content": HOY}]
    propuso = False
    for _ in range(5):
        respuesta, segundos = enviar(cliente, herramientas=ESQUEMAS, mensajes=mensajes,
                                     esfuerzo="high")
        numero += 1
        total += respuesta.uso
        pedidas = informe(numero, respuesta, segundos)
        mensajes.append({"role": "assistant", "content": respuesta.contenido})
        if respuesta.stop_reason != "tool_use":
            print("   texto:", conversacion._texto_de(respuesta.contenido)[:400])
            break
        propuso = propuso or "proponer_pedido" in pedidas
        mensajes.append({"role": "user", "content": [
            {"type": "tool_result", "tool_use_id": b["id"],
             "content": json.dumps(RESULTADOS.get(b["name"], {"ejemplo": True}),
                                   ensure_ascii=False, sort_keys=True)}
            for b in respuesta.contenido if b.get("type") == "tool_use"
        ]})
        for b in respuesta.contenido:
            if b.get("type") == "tool_use":
                print(f"   {b['name']}: {json.dumps(b['input'], ensure_ascii=False)}")
    print(f"   ¿pidió proponer_pedido? {'sí' if propuso else 'NO'}")

    # 2. La siguiente pregunta lleva la nota de lo guardado en el mensaje del sistema.
    ctx = type("Ctx", (), {"hoy": date(2026, 11, 15),
                           "taller": type("T", (), {"nombre": "Taller de ejemplo"})()})()
    sistema_nota = conversacion.contexto(
        ctx, "La dueña está en Hoy.",
        "pedido 123 (Colegio Ejemplo, 30 uniformes de diario, total $ 2.310.000), abono de "
        "$ 500.000 al pedido 123",
    )
    mensajes += [{"role": "user", "content": "¿Qué quedó guardado?"},
                 {"role": "system", "content": sistema_nota}]
    respuesta, segundos = enviar(cliente, herramientas=ESQUEMAS, mensajes=mensajes,
                                 esfuerzo="medium")
    numero += 1
    total += respuesta.uso
    informe(numero, respuesta, segundos)
    print("   texto:", conversacion._texto_de(respuesta.contenido)[:400])

    # 3. Sin herramientas, como el resumen de la mañana.
    puntos = {"atrasos": [{"cliente": "Ferretería Ejemplo", "detalle": "8 overoles",
                           "dias": 2}],
              "cobros": [{"cliente": "Ferretería Ejemplo", "saldo": 480000, "vencida": True}]}
    respuesta, segundos = enviar(
        cliente, herramientas=[], esfuerzo="medium",
        mensajes=[{"role": "user", "content": "Escribe en un párrafo corto el resumen de la "
                   "mañana con estos puntos (datos de ejemplo): "
                   + json.dumps(puntos, ensure_ascii=False)}],
    )
    numero += 1
    total += respuesta.uso
    informe(numero, respuesta, segundos)
    print("   texto:", conversacion._texto_de(respuesta.contenido)[:400])

    print(f"Total: US$ {costo_usd(total):.4f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
