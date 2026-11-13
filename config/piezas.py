"""Ayudas de plantilla para las piezas del diseño. Se cargan con {% load piezas %}.

- {% icono "hoy" %}: dibuja un ícono de static/iconos/iconos.svg.
- {{ fecha|fecha_larga }}: "Miércoles, 11 de noviembre".
- {{ fecha|fecha_corta }}: "9 de nov".
- {{ fecha|dia_y_mes }}: "20 de diciembre".
- {{ fecha|mes_y_anio }}: "Noviembre de 2026".
- {{ valor|pesos }}: "$ 1.260.000" (va dentro de <span class="dinero"> para que no se parta).
- {{ metros|metros }}: "6,5 m".
- {% control form.campo %}: dibuja el control de un campo con la pieza Campo.
"""

from decimal import Decimal

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


@register.filter
def fecha_corta(fecha):
    """"9 de nov", como en las tablas y listas del diseño."""
    if not fecha:
        return ""
    return f"{fecha.day} de {str(MONTHS[fecha.month]).lower()[:3]}"


@register.filter
def dia_y_mes(fecha):
    """"20 de diciembre"."""
    if not fecha:
        return ""
    return f"{fecha.day} de {str(MONTHS[fecha.month]).lower()}"


@register.filter
def mes_y_anio(fecha):
    """"Noviembre de 2026", como en el encabezado de Calendario y Resumen."""
    if not fecha:
        return ""
    return f"{capfirst(str(MONTHS[fecha.month]).lower())} de {fecha.year}"


@register.filter
def pesos(valor):
    """La plata como en el diseño: "$ 1.260.000". Negativos: "-$ 200.000"."""
    if valor in (None, ""):
        return ""
    numero = int(valor)
    texto = f"{abs(numero):,}".replace(",", ".")
    return f"{'-' if numero < 0 else ''}$ {texto}"


@register.filter
def metros(valor):
    """Metros de tela: "60 m", "6,5 m" (coma decimal, sin ceros de más)."""
    if valor in (None, ""):
        return ""
    numero = Decimal(str(valor)).quantize(Decimal("0.01")).normalize()
    texto = f"{numero:f}".replace(".", ",")
    return f"{texto} m"
