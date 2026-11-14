"""El menú de la aplicación: secciones, sección actual y contadores.

Las secciones se definen una sola vez aquí. `_menu.html` las dibuja en el
menú lateral, y `_menu_celular.html` en la barra de abajo del celular y el panel "Más".

Si la dirección de una sección no existe, la entrada se ve pero no lleva a ninguna parte.

Rediseño (docs/08-diseno.md): dentro de Pedidos, cuando es la sección actual, el menú muestra
dos subsecciones, "Atrasados" y "Con saldo" (los filtros de la lista). Abajo va el taller con
su logo o sus iniciales, y el título de cada pantalla lleva el ícono de su sección.

Permisos (T21, docs/04-permisos.md): la costurera no ve las secciones que no puede abrir
(Clientes, Cotizador, Resumen y Mi taller), ni la subsección "Con saldo". Como Clientes deja libre su lugar en la barra
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
    subsecciones: tuple = ()


# Subsecciones de Pedidos: (filtro de la lista, nombre, True si habla de plata).
SUBSECCIONES_PEDIDOS = (("atrasados", "Atrasados", False), ("saldo", "Con saldo", True))

# Palabras que no cuentan para las iniciales del taller ("Taller de ejemplo" -> "TE").
_SIN_INICIAL = {"de", "del", "la", "las", "el", "los", "y", "e"}


def iniciales(nombre):
    """Dos letras para el cuadrito del taller cuando no tiene logo."""
    palabras = [p for p in (nombre or "").split() if p.lower() not in _SIN_INICIAL]
    return "".join(p[0] for p in palabras[:2]).upper() or "T"


def _subsecciones_de_pedidos(request, duena):
    """Atrasados y Con saldo, con su dirección. La actual es la del filtro que se ve."""
    url = _direccion(SECCIONES[1])
    if not url:
        return ()
    coincidencia = getattr(request, "resolver_match", None)
    en_lista = coincidencia is not None and coincidencia.view_name == "pedidos:lista"
    filtro = request.GET.get("filtro") if en_lista else None
    return tuple(
        Entrada(
            clave=f"pedidos-{clave}",
            nombre=nombre,
            icono="",
            url=f"{url}?filtro={clave}",
            actual=filtro == clave,
            contador=None,
        )
        for clave, nombre, con_plata in SUBSECCIONES_PEDIDOS
        if duena or not con_plata
    )


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

    duena = permisos.es_duena(request)

    def entrada(seccion):
        return Entrada(
            clave=seccion.clave,
            nombre=seccion.nombre,
            icono=seccion.icono,
            url=_direccion(seccion),
            actual=vista_actual in seccion.vistas,
            contador=contadores.get(seccion.clave) or None,
            subsecciones=(
                _subsecciones_de_pedidos(request, duena) if seccion.clave == "pedidos" else ()
            ),
        )

    # La costurera no ve lo que no puede abrir. El administrador (sin taller) nunca llega a
    # una pantalla con menú: se le lleva a /admin/ (cuentas/aislamiento.py).
    visibles = [s for s in SECCIONES if duena or not s.solo_duena]
    secciones = [entrada(s) for s in visibles]
    mi_taller = entrada(MI_TALLER) if duena else None
    en_mas = [e for e, s in zip(secciones, visibles) if not s.en_la_barra(duena)]
    if mi_taller:
        en_mas.append(mi_taller)
    actual = next((e for e in [*secciones, mi_taller] if e and e.actual), None)
    taller = getattr(request, "taller", None)
    logo = getattr(taller, "logo", None)
    return {
        "secciones": secciones,
        "mi_taller": mi_taller,
        "barra": [e for e, s in zip(secciones, visibles) if s.en_la_barra(duena)],
        "mas": en_mas,
        "mas_actual": any(e.actual for e in en_mas),
        # El ícono que va junto al título de la pantalla (base.html)
        "icono_actual": actual.icono if actual else None,
        # El taller, abajo en el menú: su logo o sus iniciales
        "taller": {
            "iniciales": iniciales(getattr(taller, "nombre", "")),
            "logo": logo.url if logo else None,
        },
    }


def asistente(request):
    """Si sale el botón del asistente y si su panel va abierto (tanda 7).

    Abierto solo si la dueña lo dejó así en este navegador (cookie asistente=abierto, que pone
    static/js/app.js en computador).
    """
    from asistente.disponibilidad import disponible

    sale = disponible(request)
    return {
        "disponible": sale,
        "abierto": sale and request.COOKIES.get("asistente") == "abierto",
    }


def menu(request):
    """Procesador de contexto: deja `menu` y `menu_contraido` en todas las plantillas, y
    también `es_duena` y `puede_ver_plata` (cuentas/permisos.py), para que cada plantilla
    sepa qué mostrar según el rol, y `asistente` (disponible y abierto)."""
    if not request.user.is_authenticated:
        return {}
    return {
        "menu": construir_menu(request),
        "menu_contraido": request.COOKIES.get("menu") == "contraido",
        "asistente": asistente(request),
        **permisos.contexto(request),
    }
