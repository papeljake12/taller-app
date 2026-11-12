"""Ayudas de plantilla para las piezas del diseño. Se cargan con {% load piezas %}.

- {% icono "hoy" %}: dibuja un ícono de static/iconos/iconos.svg.
- {{ fecha|fecha_larga }}: "Miércoles, 11 de noviembre".
- {% control form.campo %}: dibuja el control de un campo con la pieza Campo.
"""

from django import template
from django.templatetags.static import static
from django.utils.dates import MONTHS, WEEKDAYS
from django.utils.html import format_html
from django.utils.text import capfirst

register = template.Library()


@register.simple_tag
def icono(nombre, tamano=18, trazo="1.75"):
    """Un ícono de línea. Lo lee el lector de pantalla por el texto que lo acompaña."""
    return format_html(
        '<svg class="icono" aria-hidden="true" focusable="false" width="{tamano}" '
        'height="{tamano}" viewBox="0 0 24 24" fill="none" stroke="currentColor" '
        'stroke-width="{trazo}" stroke-linecap="round" stroke-linejoin="round">'
        '<use href="{archivo}#{nombre}"></use></svg>',
        tamano=tamano,
        trazo=trazo,
        archivo=static("iconos/iconos.svg"),
        nombre=nombre,
    )


@register.filter
def fecha_larga(fecha):
    """La fecha como en el diseño: día con mayúscula inicial y mes en minúscula.

    Django en español de Colombia escribe "Noviembre" con mayúscula; la ortografía (y el
    diseño) dicen "noviembre".
    """
    if not fecha:
        return ""
    dia = str(WEEKDAYS[fecha.weekday()]).lower()
    mes = str(MONTHS[fecha.month]).lower()
    return f"{capfirst(dia)}, {fecha.day} de {mes}"


@register.simple_tag
def control(campo):
    """El control de un campo de formulario (input, select...) con la clase de la pieza.

    Django agrega solo los avisos para lectores de pantalla (aria-invalid y
    aria-describedby), que apuntan a los textos de ayuda y de error de _campo.html.
    """
    return campo.as_widget(attrs={"class": "campo__control"})
