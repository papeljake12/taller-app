"""Cuánto piensa Claude en cada pregunta: "medium" o "high".

Carril B (T30). Una regla en el código, no con IA, y una sola vez por pregunta: "high" si la
pregunta (en minúsculas y sin tildes) habla de plata (debe, saldo, cobr, gast, vend, cotiz,
cuanto, precio, abono); si no, "medium".

Se elige una sola vez al empezar la pregunta y se usa igual en todas sus vueltas
(asistente/conversacion.py): cambiarlo a mitad de una pregunta haría que Claude no pudiera
reusar lo que ya tiene guardado en caché.
"""

from pedidos.calculos import sin_tildes

MEDIO = "medium"
ALTO = "high"

# Pedazos de palabra: "cobr" sirve para cobro, cobrar, cobré y cobrado; "gast" para gasto,
# gastos y gasté; "vend" para vendí y vendido; "cotiz" para cotizar y cotización.
PALABRAS_DE_PLATA = ("debe", "saldo", "cobr", "gast", "vend", "cotiz", "cuanto", "precio", "abono")


def elegir(pregunta: str) -> str:
    """"high" si la pregunta habla de plata; si no, "medium"."""
    texto = sin_tildes(pregunta)
    if any(palabra in texto for palabra in PALABRAS_DE_PLATA):
        return ALTO
    return MEDIO
