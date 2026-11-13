"""El menú de la aplicación: secciones, sección actual y contadores.

Las secciones se definen una sola vez aquí. `_menu.html` las dibuja en tres lugares: el
menú lateral, la barra de abajo en celular y el panel "Más".

Si la dirección de una sección no existe, la entrada se ve pero no lleva a ninguna parte.

Permisos (T21, docs/04-permisos.md): la costurera no ve las secciones que no puede abrir
(Clientes, Cotizador, Resumen y Mi taller). Como Clientes deja libre su lugar en la barra
de abajo del celular, ahí va Telas; así la barra sigue con cinco botones y "Más" queda con
"Buscar" y "Salir".
"""

from dataclasses import dataclass

from django.urls import NoReverseMatch, reverse

from cuentas import permisos


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
    # True si solo la ve la dueña (docs/04-permisos.md).
    solo_duena: bool = False
    # En la barra de la costurera, si no es la misma que la de la dueña.
    en_barra_costurera: bool | None = None

    def en_la_barra(self, duena):
        if duena or self.en_barra_costurera is None:
            return self.en_barra
        return self.en_barra_costurera


SECCIONES = (
    Seccion("hoy", "Hoy", "hoy", ("pedidos:hoy",), en_barra=True),
    Seccion(
        "pedidos", "Pedidos", "pedidos",
        ("pedidos:lista", "pedidos:detalle", "pedidos:nuevo", "pedidos:buscar"),
        en_barra=True,
    ),
    Seccion("calendario", "Calendario", "calendario", ("pedidos:calendario",), en_barra=True),
    Seccion(
        "clientes", "Clientes", "clientes", ("pedidos:clientes",), en_barra=True,
        solo_duena=True,
    ),
    Seccion(
        "cotizador", "Cotizador", "cotizador", ("cotizador:inicio",), en_barra=False,
        solo_duena=True,
    ),
    Seccion(
        "telas", "Telas", "telas", ("telas:inicio",), en_barra=False, en_barra_costurera=True
    ),
    Seccion(
        "resumen", "Resumen", "resumen", ("finanzas:resumen",), en_barra=False,
        solo_duena=True,
    ),
)

MI_TALLER = Seccion(
    "mi_taller", "Mi taller", "mi-taller", ("cuentas:mi_taller",), False, solo_duena=True
)


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

    Las cuentas viven en pedidos/calculos.py. Sin pendientes no se muestra el contador.
    """
    from pedidos.calculos import contadores_del_menu

    return contadores_del_menu(getattr(request, "taller", None))


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

    # La costurera no ve lo que no puede abrir. El administrador (sin taller) nunca llega a
    # una pantalla con menú: se le lleva a /admin/ (cuentas/aislamiento.py).
    duena = permisos.es_duena(request)
    visibles = [s for s in SECCIONES if duena or not s.solo_duena]
    secciones = [entrada(s) for s in visibles]
    mi_taller = entrada(MI_TALLER) if duena else None
    en_mas = [e for e, s in zip(secciones, visibles) if not s.en_la_barra(duena)]
    if mi_taller:
        en_mas.append(mi_taller)
    return {
        "secciones": secciones,
        "mi_taller": mi_taller,
        "barra": [e for e, s in zip(secciones, visibles) if s.en_la_barra(duena)],
        "mas": en_mas,
        "mas_actual": any(e.actual for e in en_mas),
    }


def menu(request):
    """Procesador de contexto: deja `menu` y `menu_contraido` en todas las plantillas, y
    también `es_duena` y `puede_ver_plata` (cuentas/permisos.py), para que cada plantilla
    sepa qué mostrar según el rol."""
    if not request.user.is_authenticated:
        return {}
    return {
        "menu": construir_menu(request),
        "menu_contraido": request.COOKIES.get("menu") == "contraido",
        **permisos.contexto(request),
    }
