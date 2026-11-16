"""Cuánto piensa Claude en cada pregunta: "medium" o "high".

Carril B (T30). Una regla en el código, no con IA, y una sola vez por pregunta: "high" si la
pregunta (en minúsculas y sin tildes) habla de plata (debe, saldo, cobr, gast, vend, cotiz,
cuanto, precio, abon) o de algo para anotar (anot, pag, compr, dej, encarg, mil, "nuevo
pedido", "pedido nuevo"), que lleva a un borrador con plata (tanda 8); si no, "medium".

Se elige una sola vez al empezar la pregunta y se usa igual en todas sus vueltas
(asistente/conversacion.py): cambiarlo a mitad de una pregunta haría que Claude no pudiera
reusar lo que ya tiene guardado en caché.
"""

from pedidos.calculos import sin_tildes

MEDIO = "medium"
ALTO = "high"

# Pedazos de palabra: "cobr" sirve para cobro, cobrar, cobré y cobrado; "gast" para gasto,
# gastos y gasté; "vend" para vendí y vendido; "cotiz" para cotizar y cotización.
PALABRAS_DE_PLATA = (
    "debe", "saldo", "cobr", "gast", "vend", "cotiz", "cuanto", "precio", "abon",
    # Tanda 8: lo que se cuenta para anotar ("me abonaron", "pagué la luz", "dejó 500 mil").
    "anot", "pag", "compr", "dej", "encarg", "mil", "nuevo pedido", "pedido nuevo",
)


def elegir(pregunta: str) -> str:
    """"high" si la pregunta habla de plata; si no, "medium"."""
    texto = sin_tildes(pregunta)
    if any(palabra in texto for palabra in PALABRAS_DE_PLATA):
        return ALTO
    return MEDIO
