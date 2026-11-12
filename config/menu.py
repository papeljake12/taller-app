"""El menú de la aplicación: secciones, sección actual y contadores.

Las secciones se definen una sola vez aquí. `_menu.html` las dibuja en tres lugares: el
menú lateral, la barra de abajo en celular y el panel "Más".

Si la dirección de una sección todavía no existe (se crean en la tanda 2), la entrada se
ve pero no lleva a ninguna parte.
"""

from dataclasses import dataclass

from django.urls import NoReverseMatch, reverse


@dataclass(frozen=True)
class Seccion:
    clave: str
    nombre: str
    icono: str
    # Nombres de las direcciones que pertenecen a la sección. La primera es a donde
    # lleva el menú; con cualquiera de ellas, la sección se marca como la actual.
    vistas: tuple[str, ...]
    # En celular: True si va en la barra de abajo; False si va dentro de "Más".
    en_barra: bool


SECCIONES = (
    Seccion("hoy", "Hoy", "hoy", ("pedidos:hoy",), en_barra=True),
    Seccion("pedidos", "Pedidos", "pedidos", ("pedidos:lista",), en_barra=True),
    Seccion("calendario", "Calendario", "calendario", ("pedidos:calendario",), en_barra=True),
    Seccion("clientes", "Clientes", "clientes", ("pedidos:clientes",), en_barra=True),
    Seccion("cotizador", "Cotizador", "cotizador", ("cotizador:inicio",), en_barra=False),
    Seccion("telas", "Telas", "telas", ("telas:inicio",), en_barra=False),
    Seccion("resumen", "Resumen", "resumen", ("finanzas:resumen",), en_barra=False),
)

MI_TALLER = Seccion("mi_taller", "Mi taller", "mi-taller", ("cuentas:mi_taller",), False)


@dataclass(frozen=True)
class Entrada:
    """Una sección ya lista para dibujar."""

    clave: str
    nombre: str
    icono: str
    url: str | None
    actual: bool
    contador: int | None


def contar_pendientes(request):
    """Los contadores del menú: pedidos atrasados y telas que se están acabando.

    Llegan en la tanda 2, cuando existan los pedidos y las telas. Sin pendientes no se
    muestra el contador.
    """
    return {}


def _direccion(seccion):
    try:
        return reverse(seccion.vistas[0])
    except NoReverseMatch:
        return None


def construir_menu(request, contadores=None):
    if contadores is None:
        contadores = contar_pendientes(request)
    coincidencia = getattr(request, "resolver_match", None)
    vista_actual = coincidencia.view_name if coincidencia else None

    def entrada(seccion):
        return Entrada(
            clave=seccion.clave,
            nombre=seccion.nombre,
            icono=seccion.icono,
            url=_direccion(seccion),
            actual=vista_actual in seccion.vistas,
            contador=contadores.get(seccion.clave) or None,
        )

    secciones = [entrada(s) for s in SECCIONES]
    mi_taller = entrada(MI_TALLER)
    en_mas = [e for e, s in zip(secciones, SECCIONES) if not s.en_barra] + [mi_taller]
    return {
        "secciones": secciones,
        "mi_taller": mi_taller,
        "barra": [e for e, s in zip(secciones, SECCIONES) if s.en_barra],
        "mas": en_mas,
        "mas_actual": any(e.actual for e in en_mas),
    }


def menu(request):
    """Procesador de contexto: deja `menu` y `menu_contraido` en todas las plantillas."""
    if not request.user.is_authenticated:
        return {}
    return {
        "menu": construir_menu(request),
        "menu_contraido": request.COOKIES.get("menu") == "contraido",
    }
