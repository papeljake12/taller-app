"""Piezas comunes de los formularios: leer un valor en pesos.

Archivo compartido: lo cambia el coordinador. Lo usan el nuevo pedido, los abonos y, más
adelante, los gastos y el cotizador, para que todos acepten lo mismo.
"""

import re

# Solo números ("380000") o con puntos de mil cada tres cifras ("1.260.000").
FORMA_DE_PESOS = re.compile(r"\d+|\d{1,3}(?:\.\d{3})+")


def leer_pesos(texto):
    """'$ 1.260.000' -> 1260000. None si lo escrito no es un valor en pesos enteros.

    Se quitan el signo $ y los espacios. Los puntos solo valen como puntos de mil, cada tres
    cifras: "380.5" o "1.260.00" no se aceptan, porque guardarían otro valor sin avisar. Una
    coma tampoco: en Colombia es la de los decimales, y la plata se guarda sin centavos.
    Solo cifras comunes (0 a 9): otras cifras de Unicode no se aceptan.
    """
    limpio = re.sub(r"[\s$]", "", str(texto or ""))
    if not limpio.isascii() or not FORMA_DE_PESOS.fullmatch(limpio):
        return None
    return int(limpio.replace(".", ""))
