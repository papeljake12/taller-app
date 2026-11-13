"""Piezas comunes de los formularios: leer un valor en pesos y el campo de pesos.

Archivo compartido: lo cambia el coordinador. Lo usan el nuevo pedido, los abonos y, más
adelante, los gastos y el cotizador, para que todos acepten lo mismo.
"""

import re

from django import forms

# Solo números ("380000") o con puntos de mil cada tres cifras ("1.260.000").
# Más que esto no es un valor del taller: es un error al escribir (un cero de más).
MAXIMO_PESOS = 1_000_000_000

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


class CampoPesos(forms.CharField):
    """Un valor en pesos, escrito con o sin puntos y con o sin el signo $.

    Los mensajes se cambian en cada formulario (abono, gasto...) con error_messages o
    heredando la clase.
    """

    default_error_messages = {
        "required": "Escribe el valor del abono.",
        "invalid": "Escribe solo el valor en pesos, por ejemplo 380.000.",
        "cero": "El abono debe ser mayor que 0.",
        "grande": "Revisa el valor: es demasiado grande.",
    }

    def to_python(self, value):
        texto = super().to_python(value)
        if texto in self.empty_values:
            return None
        pesos = leer_pesos(texto)
        if pesos is None:
            raise forms.ValidationError(self.error_messages["invalid"], code="invalid")
        return pesos

    def validate(self, value):
        super().validate(value)
        if value is None:
            return
        if value <= 0:
            raise forms.ValidationError(self.error_messages["cero"], code="cero")
        if value > MAXIMO_PESOS:
            raise forms.ValidationError(self.error_messages["grande"], code="grande")
