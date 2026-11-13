"""Formulario de la ventana "Nuevo pedido" (T05).

Los mensajes de error van en español y de tú, como los de la demo ("Escribe...", "Elige...").
El valor total se acepta como lo escribe la gente: "1260000", "1.260.000" o "$ 380.000".
"""

from django import forms

from pedidos.models import Cliente, Pedido

# Más que esto no es el valor de un pedido del taller: seguramente sobra un cero.
TOTAL_MAXIMO = 1_000_000_000

# Un número de WhatsApp tiene por lo menos 7 dígitos.
DIGITOS_MINIMOS_WHATSAPP = 7


def leer_pesos(texto):
    """'$ 1.260.000' -> 1260000. None si lo escrito no es un valor en pesos enteros.

    Se quitan el signo $, los espacios y los puntos de mil. Una coma no se acepta: en
    Colombia es la de los decimales, y la plata se guarda sin centavos.
    """
    limpio = str(texto or "").replace("$", "").replace(" ", "").replace(".", "")
    if not limpio.isascii() or not limpio.isdigit():
        return None
    return int(limpio)


class NuevoPedidoForm(forms.Form):
    cliente = forms.CharField(
        label="Cliente",
        max_length=80,
        error_messages={
            "required": "Escribe el nombre del cliente.",
            "max_length": "El nombre es muy largo: usa máximo 80 letras.",
        },
        widget=forms.TextInput(attrs={"autocomplete": "off"}),
    )
    tipo = forms.ChoiceField(
        label="Tipo de cliente",
        choices=Cliente.Tipo.choices,
        error_messages={
            "required": "Elige el tipo de cliente.",
            "invalid_choice": "Elige uno de los tipos de la lista.",
        },
    )
    detalle = forms.CharField(
        label="¿Qué pidió?",
        max_length=160,
        error_messages={
            "required": "Escribe qué pidió el cliente.",
            "max_length": "Es muy largo: usa máximo 160 letras.",
        },
        widget=forms.TextInput(
            attrs={"placeholder": "Ej.: 20 camisas polo con logo bordado", "autocomplete": "off"}
        ),
    )
    cantidad = forms.IntegerField(
        label="¿Para cuántas personas?",
        min_value=1,
        max_value=2000,
        help_text="De 1 a 2000.",
        error_messages={
            "required": "Escribe para cuántas personas es el pedido.",
            "invalid": "Escribe un número entero, por ejemplo 20.",
            "min_value": "Escribe un número entre 1 y 2000.",
            "max_value": "Escribe un número entre 1 y 2000.",
        },
        widget=forms.NumberInput(attrs={"inputmode": "numeric", "step": "1"}),
    )
    tallaje = forms.ChoiceField(
        label="Tallas",
        choices=Pedido.Tallaje.choices,
        error_messages={
            "required": "Elige las tallas: adulto o niño.",
            "invalid_choice": "Elige las tallas: adulto o niño.",
        },
    )
    fecha_entrega = forms.DateField(
        label="Fecha de entrega",
        input_formats=["%Y-%m-%d", "%d/%m/%Y"],
        error_messages={
            "required": "Elige la fecha de entrega.",
            "invalid": "Elige una fecha de entrega que exista.",
        },
        widget=forms.DateInput(attrs={"type": "date"}, format="%Y-%m-%d"),
    )
    total = forms.CharField(
        label="Valor total (pesos)",
        max_length=20,
        error_messages={
            "required": "Escribe el valor total en pesos.",
            "max_length": "Escribe el valor en pesos, solo con números. Por ejemplo: 380.000.",
        },
        widget=forms.TextInput(attrs={"inputmode": "numeric", "autocomplete": "off"}),
    )
    whatsapp = forms.CharField(
        label="WhatsApp (opcional)",
        max_length=40,
        required=False,
        error_messages={"max_length": "El número es muy largo: usa máximo 40 caracteres."},
        widget=forms.TextInput(attrs={"inputmode": "tel", "autocomplete": "off"}),
    )

    def clean_cliente(self):
        # Sin espacios de más, para que "Marcela  P." y "Marcela P." sean el mismo cliente.
        nombre = " ".join(self.cleaned_data["cliente"].split())
        if not nombre:
            raise forms.ValidationError("Escribe el nombre del cliente.")
        return nombre

    def clean_detalle(self):
        return " ".join(self.cleaned_data["detalle"].split())

    def clean_total(self):
        valor = leer_pesos(self.cleaned_data["total"])
        if valor is None:
            raise forms.ValidationError(
                "Escribe el valor en pesos, solo con números. Por ejemplo: 380.000."
            )
        if valor > TOTAL_MAXIMO:
            raise forms.ValidationError("Ese valor es demasiado alto. Revisa los ceros.")
        return valor

    def clean_whatsapp(self):
        numero = self.cleaned_data["whatsapp"].strip()
        if not numero:
            return ""
        permitidos = set("0123456789 +-()")
        digitos = sum(1 for c in numero if c.isdigit())
        if not set(numero) <= permitidos or digitos < DIGITOS_MINIMOS_WHATSAPP:
            raise forms.ValidationError(
                "Escribe solo el número de WhatsApp, con o sin espacios."
            )
        return numero
