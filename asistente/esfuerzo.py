"""Cuánto piensa Claude en cada pregunta: "medium" o "high".

Carril B (T30). Una regla en el código, no con IA, y una sola vez por pregunta: "high" si la
pregunta (sin tildes) habla de plata (debe, saldo, cobr, gast, vend, cotiz, cuanto, precio,
abono); si no, "medium".
"""

MEDIO = "medium"
ALTO = "high"


def elegir(pregunta: str) -> str:
    raise NotImplementedError("Carril B (T30)")
