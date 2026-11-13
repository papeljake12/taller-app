"""Formulario de la tarjeta "Gastos del mes" (T17): registrar un gasto.

Como en la demo: en qué se gastó, el tipo de gasto, el valor y la fecha (hoy, si no se
cambia). El valor se escribe como lo escribe la gente ("140000", "140.000" o "$ 140.000")
y se guarda como un entero de pesos (regla 3 de CLAUDE.md), con la misma regla que los
abonos (pedidos/formularios/comun.py, leer_pesos).
"""

from django import forms
from django.utils import timezone

from finanzas.models import Gasto
from pedidos.formularios.comun import CampoPesos

# El primer año que el Resumen deja ver (?mes=2000-01). Un gasto de antes, o de más allá del
# próximo año, es casi siempre un año mal escrito ("0202" en vez de "2026"): se guardaría en
# un mes que nadie mira y solo aparecería en el Excel.
PRIMER_ANIO = 2000


class CampoPesosGasto(CampoPesos):
    """El mismo campo de pesos de los abonos, con los mensajes de un gasto."""

    default_error_messages = {
        "required": "Escribe el valor del gasto en pesos.",
        "cero": "El gasto debe ser mayor que 0.",
    }


class FormularioGasto(forms.ModelForm):
    """Concepto, tipo, valor y fecha del gasto. El taller lo pone la vista."""

    concepto = forms.CharField(
        label="¿En qué gastaste?",
        max_length=80,
        widget=forms.TextInput(
            # El botón "Registrar gasto" de la cabeza de la tarjeta lleva a este campo.
            attrs={"id": "registrar-gasto", "placeholder": "Ej.: Tela dril azul",
                   "autocomplete": "off"}
        ),
        error_messages={
            "required": "Escribe en qué gastaste.",
            "max_length": "Escribe máximo 80 letras.",
        },
    )
    categoria = forms.ChoiceField(
        label="Tipo de gasto",
        choices=Gasto.Categoria.choices,
        # Como en la demo: la lista empieza en "Telas".
        initial=Gasto.Categoria.TELAS,
        error_messages={"invalid_choice": "Elige el tipo de gasto."},
    )
    valor = CampoPesosGasto(
        label="Valor (pesos)",
        widget=forms.TextInput(attrs={"inputmode": "numeric", "autocomplete": "off"}),
    )
    fecha = forms.DateField(
        label="Fecha",
        # Si se deja vacía, es hoy (como en la demo).
        required=False,
        widget=forms.DateInput(attrs={"type": "date"}, format="%Y-%m-%d"),
        error_messages={"invalid": "Escribe una fecha válida."},
    )

    class Meta:
        model = Gasto
        fields = ["concepto", "categoria", "valor", "fecha"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # La fecha empieza en hoy (en Bogotá).
        self.fields["fecha"].initial = timezone.localdate

    def enfocar(self):
        """Deja el cursor en el primer campo con error, o en el concepto si no hay errores.

        HTMX pone el cursor en el campo con `autofocus` cuando cambia la tarjeta: así, desde
        el celular, se puede corregir o anotar el siguiente gasto sin volver a tocar el campo.
        """
        nombre = next((n for n in self.fields if n in self.errors), "concepto")
        self.fields[nombre].widget.attrs["autofocus"] = True
        return self

    def clean_fecha(self):
        hoy = timezone.localdate()
        fecha = self.cleaned_data.get("fecha") or hoy
        if not PRIMER_ANIO <= fecha.year <= hoy.year + 1:
            raise forms.ValidationError("Revisa la fecha del gasto.")
        return fecha
