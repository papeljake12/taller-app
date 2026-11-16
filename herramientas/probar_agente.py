"""Prueba real del agente con la clave (cierre de la tanda 8, docs/13-plan-tanda-8.md, sección 5).

Hace 10 tareas (4 pedidos, 3 abonos y 3 gastos) con el ciclo de verdad (asistente/conversacion.py),
las herramientas de verdad y Claude de verdad, sobre el "Taller de ejemplo" de la base de
trabajo (corre antes `cargar_ejemplos`). Nadie toca Guardar: las herramientas solo proponen, así
que no se guarda ningún pedido, abono ni gasto. Después escribe 3 resúmenes de la mañana y los
borra al terminar.

Por cada tarea imprime: qué herramienta propuso el borrador (o si preguntó), las filas, vueltas,
segundos, tokens y costo. Al final, el costo medio y el más alto, y el tiempo medio y el más
largo. No imprime la clave. Cuesta unos centavos de dólar. Nunca corre dentro de pytest.

Uso (con ANTHROPIC_API_KEY en .env):
    uv run python herramientas/probar_agente.py
"""

import os
import statistics
import sys
import time
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.local")

import django  # noqa: E402

django.setup()

from django.utils import timezone  # noqa: E402

from asistente import conversacion, resumen  # noqa: E402
from asistente.cliente import ClienteAnthropic  # noqa: E402
from asistente.contratos import Contexto  # noqa: E402
from asistente.models import ResumenDelDia  # noqa: E402
from asistente.uso import costo_usd  # noqa: E402
from cuentas.models import Taller, Usuario  # noqa: E402
from pedidos.ejemplos import NOMBRE_TALLER  # noqa: E402
from pedidos.models import Pedido  # noqa: E402

TAREAS = [
    ("pedido", "Vino la profe del Colegio Nuevo Amanecer, quiere 30 uniformes de diario para el "
               "15 de diciembre y dejó 500 mil.", None),
    ("pedido", "Me encargaron 20 camisas polo bordadas para la Ferretería La Esquina, para el 10 "
               "de diciembre. No dejaron abono.", None),
    ("pedido", "Anota un pedido nuevo: 12 vestidos de comparsa para la Comparsa Brisa Caribe, "
               "entrega el 20 de enero, total 2 millones 400 mil.", None),
    ("pedido", "Una señora quiere un vestido de grado a la medida para el 5 de diciembre, cobro "
               "380 mil.", None),
    ("abono", "Me abonaron 300 mil de Tambores del Río", None),
    ("abono", "La ferretería pagó 200 mil", None),
    ("abono", "Abonaron 500 mil a este pedido", "restaurante"),
    ("gasto", "Pagué el agua del taller, 65 mil", None),
    ("gasto", "Compré 30 metros de lino blanco a 18 mil el metro", None),
    ("gasto", "Gasté 25 mil en transporte para llevar los overoles", None),
]


def contexto_de(taller, duena, pedido=None):
    return Contexto(taller=taller, usuaria=duena, hoy=timezone.localdate(),
                    pedido_actual=pedido, url_base="http://127.0.0.1:8000/")


def main():
    taller = Taller.objects.filter(nombre=NOMBRE_TALLER).first()
    if taller is None:
        print("Falta el taller de ejemplo: corre cargar_ejemplos.")
        return 1
    duena = Usuario.objects.filter(taller=taller, rol=Usuario.Rol.DUENA).order_by("pk").first()
    restaurante = Pedido.objects.filter(taller=taller, detalle__startswith="18 camisas").first()
    cliente = ClienteAnthropic()
    costos, tiempos = [], []

    for numero, (tipo, pregunta, pantalla) in enumerate(TAREAS, 1):
        pedido = restaurante if pantalla == "restaurante" else None
        pagina = f"La dueña está en el pedido {pedido.pk} ({pedido.detalle})." if pedido else \
            "La dueña está en Hoy."
        inicio = time.monotonic()
        respuesta = conversacion.preguntar(
            cliente=cliente, ctx=contexto_de(taller, duena, pedido), mensajes=[],
            pregunta=pregunta, pagina=pagina,
        )
        segundos = time.monotonic() - inicio
        costo = costo_usd(respuesta.uso)
        costos.append(costo)
        tiempos.append(segundos)
        tarjetas = [r.tarjeta for r in respuesta.resultados if r.tarjeta is not None]
        borradores = [t for t in tarjetas if t.tipo == "borrador"]
        opciones = [t for t in tarjetas if t.tipo == "opciones"]
        if borradores:
            que = "BORRADOR"
        elif opciones:
            que = "PREGUNTÓ CON OPCIONES"
        else:
            que = "PREGUNTÓ O CONTESTÓ"
        print(f"\n{numero}. [{tipo}] {pregunta}")
        print(f"   {que} · estado={respuesta.estado} vueltas={respuesta.vueltas} "
              f"esfuerzo={respuesta.esfuerzo} segundos={segundos:.1f} costo=US$ {costo:.4f} "
              f"cache_lectura={respuesta.uso.cache_lectura}")
        for tarjeta in borradores:
            for fila in tarjeta.datos["filas"]:
                valor = f" | {fila['valor']}" if fila["valor"] is not None else ""
                aviso = f" | AVISO: {fila['aviso']}" if fila["aviso"] else ""
                print(f"     - {fila['titulo']}: {fila['detalle']}{valor}{aviso}")
        for tarjeta in opciones:
            print(f"     opciones: {tarjeta.datos['opciones']}")
        print(f"   texto: {respuesta.texto[:300]}")

    print("\n--- Resúmenes de la mañana ---")
    hoy = timezone.localdate()
    antes = ResumenDelDia.objects.filter(taller=taller, fecha=hoy).first()
    for vez in range(3):
        ResumenDelDia.objects.filter(taller=taller, fecha=hoy).delete()
        inicio = time.monotonic()
        escrito = resumen.escribir(taller, hoy, cliente)
        segundos = time.monotonic() - inicio
        print(f"\nResumen {vez + 1}: {'guardado' if escrito else 'NO se guardó'} "
              f"segundos={segundos:.1f}")
        if escrito:
            print(f"   {escrito.texto}")
    ResumenDelDia.objects.filter(taller=taller, fecha=hoy).delete()
    if antes is not None:
        ResumenDelDia.objects.create(taller=taller, fecha=hoy, texto=antes.texto)

    print(f"\nTareas: costo medio US$ {statistics.mean(costos):.4f}, el más alto US$ "
          f"{max(costos):.4f}, total US$ {sum(costos):.4f}. Tiempo medio "
          f"{statistics.mean(tiempos):.1f} s, el más largo {max(tiempos):.1f} s.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
