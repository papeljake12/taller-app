"""Formulario de Clientes (T04): crear y editar un cliente en la ventana.

El taller no llega del formulario: lo pone la vista con `request.taller`. Por eso el nombre
repetido se revisa aquí a mano (la regla de la base de datos incluye el taller, que el
formulario no conoce).
"""

from django import forms

from pedidos.models import Cliente

DIGITOS_MINIMOS = 10
DIGITOS_MAXIMOS = 15
CARACTERES_DEL_NUMERO = set("0123456789 +-().")
MENSAJE_NOMBRE_REPETIDO = "Ya tienes un cliente con ese nombre. Búscalo en la lista y edítalo."


class ClienteForm(forms.ModelForm):
    class Meta:
        model = Cliente
        fields = ("nombre", "tipo", "whatsapp", "notas")
        labels = {
            "nombre": "Nombre",
            "tipo": "Tipo",
            "whatsapp": "WhatsApp (opcional)",
            "notas": "Notas (opcional)",
        }
        help_texts = {"whatsapp": "Por ejemplo: 300 123 4567."}
        error_messages = {
            "nombre": {
                "required": "Escribe el nombre del cliente.",
                "max_length": "Escribe máximo 80 letras en el nombre.",
            },
            "tipo": {
                "required": "Elige el tipo de cliente.",
                "invalid_choice": "Elige uno de los tipos de la lista.",
            },
            "whatsapp": {"max_length": "Escribe solo el número, sin más texto."},
        }
        widgets = {
            "nombre": forms.TextInput(attrs={"autocomplete": "off"}),
            "whatsapp": forms.TextInput(attrs={"inputmode": "tel", "autocomplete": "off"}),
            "notas": forms.Textarea(attrs={"rows": 3}),
        }

    def __init__(self, *args, taller, **kwargs):
        super().__init__(*args, **kwargs)
        self.taller = taller

    def clean_nombre(self):
        nombre = " ".join(self.cleaned_data["nombre"].split())
        repetido = (
            Cliente.objects.del_taller(self.taller)
            .filter(nombre__iexact=nombre)
            .exclude(pk=self.instance.pk)
        )
        if repetido.exists():
            raise forms.ValidationError(MENSAJE_NOMBRE_REPETIDO, code="repetido")
        return nombre

    def clean_whatsapp(self):
        numero = self.cleaned_data["whatsapp"].strip()
        if not numero:
            return ""
        digitos = sum(c.isdigit() for c in numero)
        if not set(numero) <= CARACTERES_DEL_NUMERO or not (
            DIGITOS_MINIMOS <= digitos <= DIGITOS_MAXIMOS
        ):
            raise forms.ValidationError(
                "Revisa el número: escribe los 10 dígitos del celular.",
                code="invalido",
            )
        return numero
