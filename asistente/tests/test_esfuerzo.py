"""La regla de esfuerzo (T30): "high" si la pregunta habla de plata; si no, "medium"."""

import pytest

from asistente import herramientas
from asistente.esfuerzo import ALTO, MEDIO, elegir


@pytest.mark.parametrize(
    "pregunta, nivel",
    [
        # Plata: con tildes, sin tildes, en mayúsculas y con cada pedazo de palabra.
        ("¿Quién me debe plata?", ALTO),
        ("¿Cuánto me deben?", ALTO),
        ("cuanto me deben", ALTO),
        ("¿CUÁNTO COBRÉ ESTA SEMANA?", ALTO),
        ("¿Qué saldo tiene el colegio?", ALTO),
        ("¿Cuánto cobro por 15 polleras con blusa?", ALTO),
        ("Escríbele a Tambores del Río para cobrarle", ALTO),
        ("¿En qué gasté más este mes?", ALTO),
        ("¿Cuánto vendí en octubre?", ALTO),
        ("Cotízame 20 camisas", ALTO),
        ("¿Cuál es el precio de la blusa?", ALTO),
        ("¿Ya hizo el abono la ferretería?", ALTO),
        # Lo demás: consultas, mensajes que no son de cobro, tallas y telas.
        ("¿Qué tengo que entregar esta semana?", MEDIO),
        ("¿Cuántas tallas faltan?", MEDIO),
        ("¿Qué telas se están acabando?", MEDIO),
        ("Escríbele a Tambores del Río que ya está listo", MEDIO),
        ("¿Qué pedidos están atrasados?", MEDIO),
        ("Hola", MEDIO),
        ("", MEDIO),
    ],
)
def test_tabla_de_la_regla(pregunta, nivel):
    assert elegir(pregunta) == nivel


# Preguntas típicas de cada herramienta que toca plata: todas deben pensar en "high".
PREGUNTAS_DE_PLATA = {
    "quien_debe": ["¿Quién me debe plata?", "¿Quién me debe?", "¿Cuánta plata me deben?"],
    "cuentas_del_mes": [
        "¿Cuánto vendí este mes?",
        "¿Cuánto me quedó en octubre después de gastos?",
        "¿Cuánto cobré este mes?",
    ],
    "gastos": [
        "¿Cuánto gasté en telas este mes?",
        "¿En qué se me fue la plata? Muéstrame los gastos",
        "Gastos de la semana pasada",
    ],
    "cotizar": [
        "¿Cuánto cobro por 15 polleras con blusa?",
        "Cotiza 30 camisas de colegio",
        "¿Qué precio le pongo a 20 uniformes?",
    ],
    # Tanda 8: lo que se cuenta para que el agente lo anote.
    "proponer_pedido": [
        "Vino la profe del colegio, quiere 30 uniformes para el 15 de diciembre y dejó 500 mil",
        "Me encargaron 20 camisas polo para el viernes",
        "Anota un pedido nuevo de 12 vestidos para la comparsa",
    ],
    "proponer_abono": [
        "Me abonaron 300 mil de Tambores del Río",
        "La ferretería pagó lo que debía",
        "Anota un abono al colegio",
    ],
    "proponer_gasto": [
        "Pagué la luz, 180 mil",
        "Compré 30 metros de lino",
        "Anota un gasto de transporte",
    ],
}


def test_las_preguntas_tipicas_de_cada_herramienta_de_plata_piensan_en_alto():
    assert set(PREGUNTAS_DE_PLATA) == herramientas.DE_PLATA
    for nombre, preguntas in PREGUNTAS_DE_PLATA.items():
        for pregunta in preguntas:
            assert elegir(pregunta) == ALTO, (nombre, pregunta)


def test_los_niveles_son_los_que_acepta_la_api():
    assert {ALTO, MEDIO} == {"high", "medium"}
