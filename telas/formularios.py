"""Formularios de Telas (T16): "Nueva tela" y los metros de "Entró" y "Usé".

Los metros se escriben como los escribe la gente: "2,5" o "2.5" (en Colombia la coma es la
de los decimales, pero el teclado del celular a veces solo trae el punto), y también "6 m".
Se guardan con dos decimales, como dice el modelo (docs/02-modelo-de-datos.md). El taller
no llega del formulario: lo pone la vista con `request.taller`.
"""

import re
from decimal import Decimal

from django import forms

from pedidos.calculos import sin_tildes
from telas.models import Tela

# Hasta seis cifras y, si se quiere, una coma o un punto con uno o dos decimales.
# "1.000" no se acepta: con tres cifras después del punto no se sabe si es mil metros o un
# metro, y guardar el que no era cambiaría el inventario sin avisar.
FORMA_DE_METROS = re.compile(r"\d{1,6}(?:[.,]\d{1,2})?")

# Más que esto en un solo "Entró" o en una tela nueva no es un rollo de tela: es un cero
# de más al escribir.
MAXIMO_METROS = Decimal("10000")

# Lo más que cabe en el inventario de una tela (ocho cifras, dos de ellas decimales).
TOPE_DE_LA_TELA = Decimal("999999.99")

MENSAJE_NOMBRE_REPETIDO = "Ya tienes una tela con ese nombre. Búscala en la lista."


def leer_metros(texto):
    """'2,5' -> Decimal('2.5'). None si lo escrito no son metros.

    Se quitan los espacios de los lados y una "m" al final ("6 m"). Un espacio en medio no:
    "2 5" podría ser 2,5 o 25. Solo cifras comunes (0 a 9).
    """
    limpio = str(texto or "").strip().lower().removesuffix("m").strip()
    if not limpio.isascii() or not FORMA_DE_METROS.fullmatch(limpio):
        return None
    return Decimal(limpio.replace(",", "."))


class CampoMetros(forms.CharField):
    """Metros de tela, con coma o con punto. Con `con_cero`, 0 también sirve (y vacío es 0).

    Los mensajes se cambian en cada formulario con error_messages.
    """

    default_error_messages = {
        "required": "Escribe cuántos metros.",
        "invalid": "Escribe solo los metros, por ejemplo 2,5.",
        "cero": "Los metros deben ser más que 0.",
        "grande": "Revisa los metros: son demasiados.",
    }

    def __init__(self, *, con_cero=False, **kwargs):
        self.con_cero = con_cero
        kwargs.setdefault("required", not con_cero)
        kwargs.setdefault(
            "widget", forms.TextInput(attrs={"inputmode": "decimal", "autocomplete": "off"})
        )
        super().__init__(**kwargs)

    def to_python(self, value):
        texto = super().to_python(value)
        if texto in self.empty_values:
            return Decimal("0") if self.con_cero else None
        metros = leer_metros(texto)
        if metros is None:
            raise forms.ValidationError(self.error_messages["invalid"], code="invalid")
        return metros

    def validate(self, value):
        super().validate(value)
        if value is None:
            return
        if value <= 0 and not self.con_cero:
            raise forms.ValidationError(self.error_messages["cero"], code="cero")
        if value > MAXIMO_METROS:
            raise forms.ValidationError(self.error_messages["grande"], code="grande")


class FormularioTela(forms.ModelForm):
    """"Nueva tela": el nombre, los metros que hay y cuándo avisar. Como en la demo."""

    nombre = forms.CharField(
        label="Tela",
        max_length=60,
        widget=forms.TextInput(
            attrs={"placeholder": "Ej.: Dril azul", "autocomplete": "off", "autofocus": True}
        ),
        error_messages={
            "required": "Escribe el nombre de la tela.",
            "max_length": "Escribe máximo 60 letras en el nombre.",
        },
    )
    metros = CampoMetros(
        label="Metros que tienes",
        con_cero=True,
        help_text="Si todavía no tienes, déjalo vacío.",
        error_messages={"invalid": "Escribe solo los metros que tienes, por ejemplo 18 o 6,5."},
    )
    minimo = CampoMetros(
        label="Avisarme cuando queden (metros)",
        con_cero=True,
        help_text="Vacío o 0: sin aviso.",
        error_messages={"invalid": "Escribe solo los metros, por ejemplo 10."},
    )

    class Meta:
        model = Tela
        fields = ["nombre", "metros", "minimo"]

    def __init__(self, *args, taller, **kwargs):
        super().__init__(*args, **kwargs)
        self.taller = taller

    def clean_nombre(self):
        nombre = " ".join(self.cleaned_data["nombre"].split())
        if not nombre:
            raise forms.ValidationError("Escribe el nombre de la tela.", code="required")
        # "Pique blanco" y "piqué blanco" son la misma tela.
        buscado = sin_tildes(nombre)
        nombres = Tela.objects.del_taller(self.taller).values_list("nombre", flat=True)
        if any(sin_tildes(otro) == buscado for otro in nombres):
            raise forms.ValidationError(MENSAJE_NOMBRE_REPETIDO, code="repetido")
        return nombre

    def enfocar(self):
        """Deja el cursor en el primer campo con error (HTMX lo pone en `autofocus`)."""
        nombre = next((n for n in self.fields if n in self.errors), None)
        if nombre:
            for campo in self.fields.values():
                campo.widget.attrs.pop("autofocus", None)
            self.fields[nombre].widget.attrs["autofocus"] = True
        return self


class FormularioMovimiento(forms.Form):
    """Los metros de un "Entró" o de un "Usé". Cuál de los dos es lo dice `tipo`.

    Que "Usé" no pida más de lo que queda lo revisa la vista, con la tela ya apartada para
    que nadie más la cambie al mismo tiempo (telas/vistas.py).
    """

    PREGUNTAS = {
        "entro": ("¿Cuántos metros entraron?", "Escribe cuántos metros entraron."),
        "uso": ("¿Cuántos metros usaste?", "Escribe cuántos metros usaste."),
    }

    metros = CampoMetros(
        widget=forms.TextInput(
            attrs={"inputmode": "decimal", "autocomplete": "off", "autofocus": True,
                   "placeholder": "Ej.: 2,5"}
        ),
    )

    def __init__(self, *args, tipo, **kwargs):
        super().__init__(*args, **kwargs)
        self.tipo = tipo
        pregunta, falta = self.PREGUNTAS[tipo]
        campo = self.fields["metros"]
        campo.label = pregunta
        campo.error_messages = {**campo.error_messages, "required": falta}
