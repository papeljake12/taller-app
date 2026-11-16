"""Ayudas de plantilla para las piezas del diseño. Se cargan con {% load piezas %}.

- {% icono "hoy" %}: dibuja un ícono de static/iconos/iconos.svg.
- {{ fecha|fecha_larga }}: "Miércoles, 11 de noviembre".
- {{ fecha|fecha_corta }}: "9 de nov".
- {{ fecha|dia_y_mes }}: "20 de diciembre".
- {{ fecha|mes_y_anio }}: "Noviembre de 2026".
- {{ valor|pesos }}: "$ 1.260.000" (va dentro de <span class="dinero"> para que no se parta).
- {{ metros|metros }}: "6,5 m".
- {% control form.campo %}: dibuja el control de un campo con la pieza Campo.
- {% grafica_barras meses %}: la gráfica de cobrado y gastado por mes (Hoy y Resumen).
"""

from decimal import Decimal

from django import template
from django.templatetags.static import static
from django.utils.dates import MONTHS, WEEKDAYS
from django.utils.html import format_html, format_html_join
from django.utils.safestring import mark_safe
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
def control(campo, clase=""):
    """El control de un campo de formulario (input, select...) con la clase de la pieza.

    Django agrega solo los avisos para lectores de pantalla (aria-invalid y
    aria-describedby), que apuntan a los textos de ayuda y de error de _campo.html.
    `clase` agrega otra (por ejemplo, "boton-select": una lista que se ve como botón).
    """
    return campo.as_widget(attrs={"class": f"campo__control {clase}".strip()})


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
def pesos_juntos(texto):
    """El signo y la cifra no se separan al partir la línea: "$ 450.000" con un espacio que no
    se parte (tanda 8: el detalle de las filas del borrador es texto suelto)."""
    return str(texto or "").replace("$ ", "$\u00a0")


@register.filter
def metros(valor):
    """Metros de tela: "60 m", "6,5 m" (coma decimal, sin ceros de más)."""
    if valor in (None, ""):
        return ""
    numero = Decimal(str(valor)).quantize(Decimal("0.01")).normalize()
    texto = f"{numero:f}".replace(".", ",")
    return f"{texto} m"


# --- Gráfica de barras: cobrado (azul) y gastado (gris) por mes ----------------------------

# Medidas de diseno/hoy.html (rediseño del 2026-11-13): un lienzo de 600 por 160; las barras
# nacen en la línea de abajo (y=124) y la más alta mide 112; seis grupos de dos barras de 22,
# cada 94 unidades; los meses van en y=148. Letra de 11, gris de texto; el mes actual en negro.
_ALTO_LIENZO, _BASE, _ALTO_MAXIMO, _ANCHO_BARRA, _PRIMERA_X, _Y_MESES = 160, 124, 112, 22, 62, 148
_AZUL, _GRIS, _LINEA, _EJE, _TEXTO_2, _NEGRO = (
    "#2563C9", "#B5B5B5", "#F1F1F1", "#E3E3E3", "#616161", "#1A1A1A",
)


def _paso_redondo(maximo):
    """Cada cuánto va una línea guía: 1, 2 o 5 por una potencia de 10, unas 2 o 3 líneas."""
    objetivo = maximo / 3
    potencia = 1
    while potencia * 10 <= objetivo:
        potencia *= 10
    for multiplo in (1, 2, 5, 10):
        if potencia * multiplo >= objetivo:
            return potencia * multiplo
    return potencia * 10


def _texto_eje(valor):
    """'2 M' para millones; '500 mil' para menos de un millón."""
    if valor >= 1_000_000:
        millones = valor / 1_000_000
        return f"{millones:g} M".replace(".", ",")
    return f"{valor // 1000:g} mil"


def _millones(valor):
    return f"{valor / 1_000_000:.2f}".rstrip("0").rstrip(".").replace(".", ",")


@register.simple_tag
def grafica_barras(meses, alto_computador=None):
    """La gráfica de diseno/hoy.html con los datos de calculos.grafica_cobrado_y_gastado.

    `meses` es una lista de objetos con mes (una fecha), cobrado y gastado. El último mes
    (el actual) va en negrita. Lleva una descripción para lectores de pantalla.

    `alto_computador` era de la "pantalla fija", que ya no existe: se acepta y no hace nada.
    """
    meses = list(meses)
    if not meses:
        return ""
    return _dibujar_grafica(meses)


def _dibujar_grafica(meses):
    """Un <svg> de 600 por 160 con las medidas de diseno/hoy.html."""
    maximo = max(max(m.cobrado, m.gastado) for m in meses)
    paso_x = 94 * 6 / len(meses)

    def alto(valor):
        return round(valor * _ALTO_MAXIMO / maximo) if maximo else 0

    lineas, textos_eje = [], []
    if maximo:
        paso = _paso_redondo(maximo)
        guia = paso
        while guia <= maximo:
            y = _BASE - alto(guia)
            lineas.append((y,))
            textos_eje.append((y + 4, _texto_eje(guia)))
            guia += paso
    barras, nombres = [], []
    for i, mes in enumerate(meses):
        x = round(_PRIMERA_X + i * paso_x)
        for desplazamiento, valor, color in ((0, mes.cobrado, _AZUL), (24, mes.gastado, _GRIS)):
            h = alto(valor)
            if h:
                barras.append((x + desplazamiento, _BASE - h, _ANCHO_BARRA, h, color))
        actual = i == len(meses) - 1
        nombre = str(MONTHS[mes.mes.month]).lower()[:3]
        nombres.append((x + 23, _Y_MESES, mark_safe(' font-weight="650"') if actual else "",
                        _NEGRO if actual else _TEXTO_2, nombre))
    ultimo = meses[-1]
    primero_nombre = str(MONTHS[meses[0].mes.month]).lower()
    ultimo_nombre = str(MONTHS[ultimo.mes.month]).lower()
    descripcion = (
        f"Barras de cobrado y gastado de {primero_nombre} a {ultimo_nombre}. "
        f"En {ultimo_nombre}: cobrado {_millones(ultimo.cobrado)} millones y gastado "
        f"{_millones(ultimo.gastado)} millones."
    )
    return format_html(
        '<svg class="grafica" role="img" aria-label="{}" viewBox="0 0 600 {}">{}{}{}'
        '<line x1="36" y1="{}" x2="596" y2="{}" stroke="{}" stroke-width="1"></line>{}</svg>',
        descripcion,
        _ALTO_LIENZO,
        format_html_join("", '<line x1="36" y1="{}" x2="596" y2="{}" stroke="' + _LINEA
                         + '" stroke-width="1"></line>', ((y, y) for (y,) in lineas)),
        format_html_join("", '<text x="0" y="{}" font-size="11" fill="' + _TEXTO_2
                         + '">{}</text>', textos_eje),
        format_html_join("", '<rect x="{}" y="{}" width="{}" height="{}" rx="4" fill="{}"></rect>',
                         barras),
        _BASE,
        _BASE,
        _EJE,
        format_html_join("", '<text x="{}" y="{}" font-size="11"{} text-anchor="middle" '
                         'fill="{}">{}</text>', nombres),
    )
