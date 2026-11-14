"""Prueba real del asistente con la clave: 20 preguntas, cada una con esfuerzo medio y alto (T36).

Usa el ciclo, las herramientas y el Claude de verdad (asistente.cliente.ClienteAnthropic)
sobre el taller de ejemplo de la base local (`cargar_ejemplos`). Por cada pregunta anota:
si la respuesta cuadra con lo que calcula la aplicación, vueltas, segundos, los cuatro tipos
de token, si leyó de la caché y el costo. Al final, el costo medio y el percentil 90 por
esfuerzo.

Las preguntas se anotan en "Uso del asistente" de /admin (como si las hubiera hecho la dueña),
para comparar con la consola de Anthropic. Las respuestas completas quedan en un archivo JSON.

Uso (con ANTHROPIC_API_KEY en .env y los ejemplos cargados):
    uv run python herramientas/probar_asistente.py --salida resultados.json
    uv run python herramientas/probar_asistente.py --solo 9 13 --esfuerzos high

Cuesta unos centavos de dólar por pregunta. Nunca corre dentro de pytest.
"""

import argparse
import json
import os
import statistics
import sys
import time
from datetime import date
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.local")

import django  # noqa: E402

django.setup()

from django.conf import settings  # noqa: E402
from django.utils import timezone  # noqa: E402

from asistente import cliente, conversacion, esfuerzo, pagina, uso  # noqa: E402
from asistente.contratos import Contexto  # noqa: E402
from config.piezas import pesos  # noqa: E402
from cuentas.models import Usuario  # noqa: E402
from pedidos import calculos  # noqa: E402
from pedidos.ejemplos import NOMBRE_TALLER  # noqa: E402
from pedidos.models import Pedido  # noqa: E402


def preguntas(taller, hoy):
    """(tipo, pregunta, pantalla, lo que debe aparecer en la respuesta o en una tarjeta)."""

    def pedido(cliente):
        return Pedido.objects.del_taller(taller).filter(cliente__nombre=cliente).first()

    ferreteria = pedido("Ferretería La Esquina")
    restaurante = pedido("Restaurante El Fogón Costeño")
    tambores = pedido("Grupo de danza Tambores del Río")
    anterior = calculos.sumar_meses(hoy.replace(day=1), -1)
    gastos_telas = sum(
        g.valor for g in calculos.gastos_entre(taller, hoy.replace(day=1), hoy, "telas")
    )
    cotizacion = calculos.cotizar(4, 20_000, 15_000, 45_000, 0, 30, 15, 50)
    return [
        ("consulta", "¿Qué tengo que entregar esta semana?", "/", None),
        ("consulta", "¿Qué pedidos van atrasados?", "/", "Ferretería La Esquina"),
        ("consulta", "¿Qué tela se está acabando?", "/telas/", None),
        ("consulta", "¿Cuántos pedidos tengo en producción?", "/",
         str(calculos.cifras_de_hoy(taller, hoy)["en_produccion"])),
        ("consulta", "¿Qué tiene que hacer Marta?", "/", "Marta"),
        ("consulta", "Busca el pedido del colegio", "/pedidos/", "Colegio Nuevo Amanecer"),
        ("consulta", "¿Qué entregas tengo en diciembre?", "/calendario/", None),
        ("consulta", "¿Qué clientes son empresas?", "/clientes/", "Ferretería La Esquina"),
        ("plata", "¿Quién me debe plata?", "/", pesos(calculos.por_cobrar(taller))),
        ("plata", "¿Cuánto vendí este mes?", "/",
         pesos(calculos.vendido_en(taller, hoy.year, hoy.month))),
        ("plata", "¿Cuánto gasté en telas este mes?", "/resumen/", pesos(gastos_telas)),
        ("plata", "¿Cómo me fue el mes pasado?", "/",
         pesos(calculos.cobrado_en(taller, anterior.year, anterior.month))),
        ("este pedido", "¿Cuánto debe este pedido?", f"/pedidos/{ferreteria.pk}/",
         pesos(calculos.saldo(ferreteria))),
        ("este pedido", "¿Cuántas tallas faltan en este pedido?", f"/pedidos/{restaurante.pk}/",
         None),
        ("este pedido", "¿Qué materiales faltan comprar para este pedido?",
         f"/pedidos/{restaurante.pk}/", "Hilo para bordar"),
        ("mensaje", "Escríbele a Tambores del Río que ya está listo", "/", "mensaje"),
        ("mensaje", "Recuérdale a la Ferretería La Esquina lo que debe", "/", "mensaje"),
        ("mensaje", "Pídele las tallas al Colegio Nuevo Amanecer", "/", "mensaje"),
        ("cotizar", "¿Cuánto cobro por 15 vestidos de comparsa?", "/cotizador/",
         pesos(cotizacion.total)),
        ("cotizar", "¿Cuánto cobro por 30 camisas polo bordadas con 40 % de ganancia?",
         f"/pedidos/{tambores.pk}/", None),
    ]


def cuadra(esperado, respuesta):
    """True/False si se puede comprobar solo; None si hay que leerla."""
    if esperado is None:
        return None
    if esperado == "mensaje":
        return any(r.tarjeta and r.tarjeta.tipo == "mensaje" for r in respuesta.resultados)
    dentro = respuesta.texto + json.dumps(
        [r.tarjeta.datos for r in respuesta.resultados if r.tarjeta], ensure_ascii=False
    )
    numero = esperado.replace("$ ", "").replace(".", "")
    return esperado.lower() in dentro.lower() or (
        numero.isdigit() and numero in dentro.replace(".", "")
    )


def contar_pregunta(taller, hoy):
    """Suma la pregunta en "Uso del asistente" aunque el taller tenga el cupo en 0."""
    from django.db.models import F

    from asistente.models import UsoAsistente

    UsoAsistente.objects.get_or_create(taller=taller, fecha=hoy)
    UsoAsistente.objects.filter(taller=taller, fecha=hoy).update(preguntas=F("preguntas") + 1)


def percentil_90(valores):
    ordenados = sorted(valores)
    return ordenados[max(0, round(0.9 * len(ordenados)) - 1)] if ordenados else 0


def main():
    opciones = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    opciones.add_argument("--salida", type=Path, help="archivo JSON con todas las respuestas")
    opciones.add_argument("--solo", type=int, nargs="+", help="números de pregunta (1 a 20)")
    opciones.add_argument("--esfuerzos", nargs="+", default=["medium", "high"])
    opciones = opciones.parse_args()

    if not settings.ANTHROPIC_API_KEY:
        raise SystemExit("Falta ANTHROPIC_API_KEY en el .env.")
    duena = (
        Usuario.objects.filter(taller__nombre=NOMBRE_TALLER, rol=Usuario.Rol.DUENA)
        .order_by("pk").first()
    )
    if duena is None:
        raise SystemExit("Carga los ejemplos primero: uv run python manage.py cargar_ejemplos")
    taller, hoy = duena.taller, timezone.localdate()
    claude = cliente.ClienteAnthropic()
    lista = list(enumerate(preguntas(taller, hoy), start=1))
    if opciones.solo:
        lista = [(n, p) for n, p in lista if n in opciones.solo]

    elegir_original = esfuerzo.elegir
    filas = []
    try:
        for nivel in opciones.esfuerzos:
            esfuerzo.elegir = lambda pregunta, nivel=nivel: nivel
            for numero, (tipo, pregunta, ruta, esperado) in lista:
                texto, pedido = pagina.contexto_de_pagina(taller, ruta)
                ctx = Contexto(taller, duena, hoy, pedido, "http://127.0.0.1:8000/")
                inicio = time.monotonic()
                r = conversacion.preguntar(
                    cliente=claude, ctx=ctx, mensajes=[], pregunta=pregunta, pagina=texto
                )
                segundos = time.monotonic() - inicio
                uso.anotar(taller, r.uso, hoy)
                if r.cobrada:
                    contar_pregunta(taller, hoy)
                fila = {
                    "numero": numero, "tipo": tipo, "esfuerzo": nivel, "pregunta": pregunta,
                    "pantalla": ruta, "estado": r.estado, "cuadra": cuadra(esperado, r),
                    "esperado": esperado, "vueltas": r.vueltas, "segundos": round(segundos, 1),
                    "entrada": r.uso.entrada, "salida": r.uso.salida,
                    "cache_escritura": r.uso.cache_escritura,
                    "cache_lectura": r.uso.cache_lectura,
                    "costo": float(uso.costo_usd(r.uso)),
                    "herramientas": [x.revisado for x in r.resultados],
                    "tarjetas": [x.tarjeta.tipo for x in r.resultados if x.tarjeta],
                    "modelos": list(r.modelos), "texto": r.texto,
                }
                filas.append(fila)
                marca = {True: "bien", False: "NO CUADRA", None: "leer"}[fila["cuadra"]]
                print(f"{numero:>2} {nivel:<6} {r.estado:<7} {marca:<9} {fila['vueltas']} v "
                      f"{fila['segundos']:>5} s  {fila['costo'] * 100:5.2f} ¢  "
                      f"caché {fila['cache_lectura']:>5}  {pregunta}")
                print(f"      {r.texto.replace(chr(10), ' ')[:220]}")
    finally:
        esfuerzo.elegir = elegir_original
        if opciones.salida:
            opciones.salida.write_text(
                json.dumps(filas, ensure_ascii=False, indent=2), encoding="utf-8"
            )

    print()
    for nivel in opciones.esfuerzos:
        de_este = [f for f in filas if f["esfuerzo"] == nivel]
        if not de_este:
            continue
        costos = [f["costo"] * 100 for f in de_este]
        tiempos = [f["segundos"] for f in de_este]
        print(f"{nivel}: {len(de_este)} preguntas · costo medio {statistics.mean(costos):.2f} ¢ · "
              f"p90 {percentil_90(costos):.2f} ¢ · tiempo medio {statistics.mean(tiempos):.1f} s · "
              f"p90 {percentil_90(tiempos):.1f} s · máximo {max(tiempos):.1f} s · "
              f"no cuadran {sum(1 for f in de_este if f['cuadra'] is False)}")
    total = sum(f["costo"] for f in filas)
    print(f"Total: {total:.4f} USD en {len(filas)} preguntas ({date.today().isoformat()}).")


if __name__ == "__main__":
    main()
