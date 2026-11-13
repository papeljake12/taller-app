"""Formulario de la tarjeta Pagos (T08): registrar un abono.

El valor se escribe como lo escribe la gente: "380000", "380.000" o "$ 380.000". Se guarda
como un entero de pesos, sin decimales (regla 3 de CLAUDE.md).
"""

from django import forms
from django.utils import timezone

from pedidos.formularios.comun import CampoPesos
from pedidos.models import Abono


class FormularioAbono(forms.ModelForm):
    """Valor y fecha del abono. El pedido y quién lo registró los pone la vista."""

    valor = CampoPesos(
        label="Valor del abono (pesos)",
        widget=forms.TextInput(
            # El botón "Registrar abono" de arriba del pedido lleva a este campo.
            attrs={"id": "registrar-abono", "inputmode": "numeric", "autocomplete": "off"}
        ),
    )
    fecha = forms.DateField(
        label="Fecha",
        # Si se deja vacía, es hoy (como en la demo).
        required=False,
        widget=forms.DateInput(attrs={"type": "date"}, format="%Y-%m-%d"),
        error_messages={"invalid": "Escribe una fecha válida."},
    )

    class Meta:
        model = Abono
        fields = ["valor", "fecha"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # La fecha empieza en hoy (en Bogotá).
        self.fields["fecha"].initial = timezone.localdate

    def enfocar(self):
        """Deja el cursor en el primer campo con error, o en el valor si no hay errores.

        HTMX pone el cursor en el campo con `autofocus` cuando cambia la tarjeta, así quien
        escribe desde el celular no tiene que volver a tocar el campo.
        """
        nombre = next((n for n in self.fields if n in self.errors), "valor")
        self.fields[nombre].widget.attrs["autofocus"] = True
        return self

    def clean_fecha(self):
        return self.cleaned_data.get("fecha") or timezone.localdate()
