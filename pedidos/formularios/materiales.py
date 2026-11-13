"""Formulario de materiales (T12): agregar uno a la lista de compras del pedido."""

from django import forms

from pedidos.models import Material


class MaterialForm(forms.ModelForm):
    class Meta:
        model = Material
        fields = ["nombre", "cantidad"]
        labels = {"nombre": "Material", "cantidad": "Cantidad (opcional)"}
        error_messages = {
            "nombre": {
                "required": "Escribe el nombre del material.",
                "max_length": "Escribe máximo 60 letras.",
            },
            "cantidad": {"max_length": "Escribe máximo 30 letras."},
        }
        widgets = {
            "nombre": forms.TextInput(
                attrs={"placeholder": "Ej.: Tela dril azul", "autocomplete": "off"}
            ),
            "cantidad": forms.TextInput(attrs={"placeholder": "Ej.: 24 m", "autocomplete": "off"}),
        }

    def __init__(self, *args, **kwargs):
        # "material-nombre" en la página, para no chocar con el nombre de una talla.
        kwargs.setdefault("auto_id", "material-%s")
        super().__init__(*args, **kwargs)


class CompradoForm(forms.Form):
    """Cómo debe quedar el material al tocar su casilla: "si" (comprado) o "no".

    La casilla lo manda sola; si llega otra cosa (o nada), no se adivina: no se cambia.
    """

    MENSAJE = "No se pudo marcar el material. Toca la casilla otra vez."

    comprado = forms.ChoiceField(
        choices=[("si", "Comprado"), ("no", "No comprado")],
        error_messages={"required": MENSAJE, "invalid_choice": MENSAJE},
    )
