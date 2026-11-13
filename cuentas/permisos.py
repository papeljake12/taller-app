"""Quién puede hacer qué (T21): la tabla de docs/04-permisos.md, en un solo lugar.

Hay dos roles dentro de un taller:

- Dueña: maneja todo su taller.
- Costurera: ve y actualiza el trabajo, pero no ve la plata (total, abonos, saldo, "Por
  cobrar", precios ni cotizaciones). Cambia la etapa de un pedido solo si es la encargada.

Las plantillas esconden (con `es_duena` y `puede_ver_plata`, que deja en todas las
plantillas el procesador de contexto `contexto`) y las vistas rechazan. Ocultar un botón no
basta: cada vista revisa el permiso, porque un formulario se puede enviar a mano.

Cómo se usa en una vista:

    from cuentas.permisos import exigir_duena, solo_duena

    @solo_duena                      # pantallas y acciones sin número en la dirección
    def resumen(request): ...

    def quitar(request, pk):         # con número: primero se busca en el taller (404 si es
        gasto = obtener_o_404(...)   # de otro), y después se revisa el rol (403)
        exigir_duena(request)

El orden importa: el número de algo de otro taller responde 404 ("no encontrado") a
cualquiera, para no revelar que existe. Solo lo del propio taller responde 403 ("sin
permiso"), con la página templates/403.html.
"""

from functools import wraps

from django.core.exceptions import PermissionDenied

SOLO_LA_DUENA = "Esta parte es solo para la dueña del taller."
SOLO_LA_ENCARGADA = (
    "Solo la encargada del pedido o la dueña del taller pueden cambiar su etapa."
)


def _usuaria(request_o_usuaria):
    return getattr(request_o_usuaria, "user", request_o_usuaria)


def es_duena(request_o_usuaria):
    """True si quien inició sesión es la dueña de un taller."""
    usuaria = _usuaria(request_o_usuaria)
    return bool(
        getattr(usuaria, "is_authenticated", False)
        and getattr(usuaria, "taller_id", None)
        and usuaria.es_duena
    )


def puede_ver_plata(request_o_usuaria):
    """Total, abonos, saldo, "Por cobrar", precios y cotizaciones: solo la dueña."""
    return es_duena(request_o_usuaria)


def puede_mover_etapa(request_o_usuaria, pedido):
    """La dueña siempre; la costurera, solo si es la encargada del pedido."""
    usuaria = _usuaria(request_o_usuaria)
    if es_duena(usuaria):
        return True
    return bool(getattr(usuaria, "is_authenticated", False)) and (
        pedido.encargada_id is not None and pedido.encargada_id == usuaria.pk
    )


def exigir_duena(request):
    """Responde 403 ("sin permiso") si no es la dueña."""
    if not es_duena(request):
        raise PermissionDenied(SOLO_LA_DUENA)


def exigir_mover_etapa(request, pedido):
    """Responde 403 si no puede cambiar la etapa de ese pedido."""
    if not puede_mover_etapa(request, pedido):
        raise PermissionDenied(SOLO_LA_ENCARGADA)


def solo_duena(vista):
    """Para una vista que solo usa la dueña (por ejemplo, Resumen o Clientes)."""

    @wraps(vista)
    def envuelta(request, *args, **kwargs):
        exigir_duena(request)
        return vista(request, *args, **kwargs)

    return envuelta


def contexto(request):
    """Lo que las plantillas preguntan: `es_duena` y `puede_ver_plata`.

    Lo deja config/menu.py (el procesador de contexto del menú) en todas las plantillas.
    """
    return {"es_duena": es_duena(request), "puede_ver_plata": puede_ver_plata(request)}
