"""Formularios del pedido por dentro (T07): etapa, fecha de entrega, encargada y WhatsApp.

Cada uno guarda una sola cosa, porque cada cambio se guarda solo, sin un botón "Guardar":
al tocar una etapa, al elegir la fecha o la encargada, o al salir del campo de WhatsApp.
Los mensajes de error van en "tú", como en el resto de la aplicación.
"""

from django import forms
from django.db.models import Q

from cuentas.aislamiento import del_taller
from cuentas.models import Usuario
from pedidos import mensajes
from pedidos.models import Pedido

# Lo único que se acepta en un número de WhatsApp, además de los dígitos.
SIGNOS_DEL_TELEFONO = set(" +-().")

# Los campos se llaman "pedido-fecha_entrega", "pedido-encargada"... en la página, para no
# chocar con los de las otras tarjetas (abonos, tallas, materiales).
ID_DE_LOS_CAMPOS = "pedido-%s"


def _guardar_al_cambiar(campo, accion):
    """Con JavaScript, el campo se guarda solo cuando cambia (HTMX lo envía a `accion`)."""
    if accion:
        campo.widget.attrs.update({"hx-post": accion, "hx-trigger": "change"})


class EtapaForm(forms.Form):
    estado = forms.ChoiceField(
        choices=Pedido.Estado.choices,
        error_messages={
            "required": "Elige una de las seis etapas.",
            "invalid_choice": "Elige una de las seis etapas.",
        },
    )


class EntregaForm(forms.ModelForm):
    class Meta:
        model = Pedido
        fields = ["fecha_entrega"]
        labels = {"fecha_entrega": "Fecha de entrega"}
        widgets = {"fecha_entrega": forms.DateInput(attrs={"type": "date"}, format="%Y-%m-%d")}
        error_messages = {
            "fecha_entrega": {
                "required": "Elige la fecha de entrega.",
                "invalid": "Escribe la fecha como día/mes/año.",
            }
        }

    def __init__(self, *args, accion="", **kwargs):
        kwargs.setdefault("auto_id", ID_DE_LOS_CAMPOS)
        super().__init__(*args, **kwargs)
        campo = self.fields["fecha_entrega"]
        # El calendario del navegador envía 2026-12-14; a mano se escribe 14/12/2026.
        campo.input_formats = ["%Y-%m-%d", "%d/%m/%Y"]
        _guardar_al_cambiar(campo, accion)


class EncargadaForm(forms.ModelForm):
    """Quién lo está haciendo: una de las usuarias activas del taller, o nadie."""

    class Meta:
        model = Pedido
        fields = ["encargada"]
        labels = {"encargada": "¿Quién lo está haciendo?"}
        error_messages = {
            "encargada": {"invalid_choice": "Elige a una persona del taller."},
        }

    def __init__(self, *args, request, accion="", **kwargs):
        kwargs.setdefault("auto_id", ID_DE_LOS_CAMPOS)
        super().__init__(*args, **kwargs)
        campo = self.fields["encargada"]
        # Solo las de este taller. Una usuaria desactivada ya no se puede elegir, pero si
        # es la encargada actual sigue apareciendo, para no borrarla sin querer.
        actual = self.instance.encargada_id
        campo.queryset = (
            del_taller(request, Usuario)
            .filter(Q(is_active=True) | Q(pk=actual))
            .order_by("nombre_visible", "first_name", "username")
        )
        campo.empty_label = "Sin asignar"
        _guardar_al_cambiar(campo, accion)


class WhatsappForm(forms.Form):
    """El WhatsApp del cliente. Vacío borra el número."""

    whatsapp = forms.CharField(
        label="WhatsApp del cliente",
        max_length=40,
        required=False,
        error_messages={"max_length": "Escribe máximo 40 caracteres."},
        widget=forms.TextInput(
            attrs={"type": "tel", "inputmode": "tel", "autocomplete": "off"}
        ),
    )

    def __init__(self, *args, **kwargs):
        kwargs.setdefault("auto_id", ID_DE_LOS_CAMPOS)
        super().__init__(*args, **kwargs)

    def clean_whatsapp(self):
        numero = self.cleaned_data["whatsapp"].strip()
        if not numero:
            return ""
        if any(not (c.isdigit() or c in SIGNOS_DEL_TELEFONO) for c in numero):
            raise forms.ValidationError("Escribe solo números, sin letras.")
        if not mensajes.enlace_whatsapp(numero, ""):
            raise forms.ValidationError(
                "Revisa el número: un celular tiene 10 dígitos, o más con el indicativo."
            )
        return numero
