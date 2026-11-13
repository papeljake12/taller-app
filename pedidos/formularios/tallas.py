"""Formulario de la tarjeta "Tallas" (T10): agregar a mano la talla de una persona.

Las tallas que se pueden elegir salen del pedido (adulto o niño, más "A la medida"). Si es
a la medida, el modelo exige pecho, cintura y cadera (pedidos/models.py, Talla.clean).
"""

from decimal import ROUND_HALF_UP, Decimal, InvalidOperation

from django import forms

from pedidos.models import Pedido, Talla

MEDIDA_MINIMA = Decimal("1")
MEDIDA_MAXIMA = Decimal("300")


def nombre_de_talla(talla):
    """Cómo se le muestra una talla a la usuaria: "M", "10" o "A la medida"."""
    return "A la medida" if talla == Pedido.MEDIDA else talla


class MedidaField(forms.Field):
    """Una medida en centímetros. Acepta "92", "92,5", "92.5" o "92 cm"; guarda un decimal."""

    mensaje = "Escribe la medida en centímetros, entre 1 y 300. Por ejemplo: 92 o 92,5."

    def to_python(self, valor):
        texto = str(valor or "").strip().lower().removesuffix("cm").strip().replace(",", ".")
        if not texto:
            return None
        try:
            numero = Decimal(texto)
        except InvalidOperation:
            raise forms.ValidationError(self.mensaje, code="invalid") from None
        if not numero.is_finite() or not MEDIDA_MINIMA <= numero <= MEDIDA_MAXIMA:
            raise forms.ValidationError(self.mensaje, code="invalid")
        # Una medida se anota con un decimal como mucho: 92,25 queda en 92,3.
        return numero.quantize(Decimal("0.1"), rounding=ROUND_HALF_UP)

    def prepare_value(self, valor):
        if isinstance(valor, Decimal):
            return f"{valor.normalize():f}".replace(".", ",")
        return valor


def _campo_medida(etiqueta):
    return MedidaField(
        label=etiqueta,
        required=False,
        widget=forms.TextInput(attrs={"inputmode": "decimal", "autocomplete": "off"}),
    )


class TallaForm(forms.ModelForm):
    """Nombre, talla, medidas y nota de una persona. El pedido y el origen los pone la vista."""

    talla = forms.ChoiceField(
        label="Talla", error_messages={"required": "Elige la talla.",
                                       "invalid_choice": "Elige una de las tallas de la lista."}
    )
    pecho = _campo_medida("Pecho (cm)")
    cintura = _campo_medida("Cintura (cm)")
    cadera = _campo_medida("Cadera (cm)")
    largo = _campo_medida("Largo (cm)")

    class Meta:
        model = Talla
        fields = ("nombre", "talla", "pecho", "cintura", "cadera", "largo", "nota")
        labels = {"nombre": "Nombre", "nota": "Nota (opcional)"}
        error_messages = {
            "nombre": {
                "required": "Escribe el nombre de la persona.",
                "max_length": "Escribe máximo 60 letras en el nombre.",
            },
            "nota": {"max_length": "Escribe máximo 200 letras en la nota."},
        }
        widgets = {
            "nombre": forms.TextInput(attrs={"autocomplete": "off"}),
            "nota": forms.TextInput(attrs={"autocomplete": "off"}),
        }

    def __init__(self, *args, pedido, **kwargs):
        kwargs.setdefault("instance", Talla(pedido=pedido, origen=Talla.Origen.MANUAL))
        super().__init__(*args, **kwargs)
        self.fields["talla"].choices = [("", "Elige la talla")] + [
            (talla, nombre_de_talla(talla)) for talla in pedido.opciones_de_talla
        ]
