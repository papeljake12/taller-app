"""Formulario del enlace público de tallas (T11): cada persona del grupo envía su talla.

Es el mismo formulario de la tarjeta "Tallas" (pedidos/formularios/tallas.py), con los
textos para quien lo llena ("Tu nombre", "Tu talla") y dos diferencias:

- La talla queda marcada como enviada por el cliente (origen "enlace").
- Las medidas solo se guardan si eligió "A la medida". Sin JavaScript se ven todos los
  campos; si alguien eligió M y además escribió el pecho, ese pecho no se guarda ni se revisa.

El pedido no llega en el formulario: lo pone la vista a partir de la clave del enlace.
"""

from django import forms

from pedidos.formularios.tallas import TallaForm
from pedidos.models import Pedido, Talla

MEDIDAS = ("pecho", "cintura", "cadera", "largo")


class TallaPublicaForm(TallaForm):
    """Nombre, talla, medidas (si es a la medida) y observaciones de una persona."""

    def __init__(self, *args, pedido, direccion, **kwargs):
        kwargs.setdefault("instance", Talla(pedido=pedido, origen=Talla.Origen.ENLACE))
        super().__init__(*args, pedido=pedido, **kwargs)
        if self.is_bound and self.data.get("talla") != Pedido.MEDIDA:
            # Las medidas no hacen falta: se descartan antes de revisarlas.
            self.data = self.data.copy()
            for campo in MEDIDAS:
                self.data.pop(campo, None)

        nombre = self.fields["nombre"]
        nombre.label = "Tu nombre y apellido"
        nombre.error_messages["required"] = "Escribe tu nombre para saber de quién es la talla."
        nombre.widget.attrs["autocomplete"] = "name"

        talla = self.fields["talla"]
        talla.label = "Tu talla"
        talla.choices = [("", "Elige tu talla"), *talla.choices[1:]]
        talla.error_messages["required"] = "Elige tu talla."
        talla.help_text = "Si ninguna te queda, elige «A la medida» y anota tus medidas."
        # Con JavaScript, al cambiar la talla se piden a la misma página los campos que van
        # debajo: las medidas aparecen solo si eligió "A la medida" (pedidos/_publico_talla.html).
        talla.widget.attrs.update({
            "hx-get": direccion,
            "hx-trigger": "change",
            "hx-target": "#publico-talla",
            "hx-swap": "outerHTML",
        })

        self.fields["largo"].label = "Largo (cm), si quieres"

        nota = self.fields["nota"]
        nota.label = "Observaciones (opcional)"
        nota.widget = forms.Textarea(attrs={
            "maxlength": 200,
            "rows": 3,
            "placeholder": "Por ejemplo: manga larga, un poco más holgado",
        })
        nota.error_messages["max_length"] = "Escribe máximo 200 letras en las observaciones."

    @property
    def es_a_la_medida(self):
        """Si la talla elegida (o la que se está eligiendo) es "A la medida"."""
        if self.is_bound:
            return self.data.get("talla") == Pedido.MEDIDA
        return self.initial.get("talla") == Pedido.MEDIDA
