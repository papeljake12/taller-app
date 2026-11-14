"""Las tres direcciones del asistente: abrir el panel, preguntar y empezar de nuevo.

Carril D (T33). Reglas: docs/11-plan-tanda-7.md, sección 1.5. Todas con `@solo_duena` y 404
si `not disponible(request)`. `preguntar` responde siempre 200.
"""

from django.http import Http404
from django.views.decorators.http import require_GET, require_POST

from asistente.disponibilidad import disponible
from cuentas.permisos import solo_duena


def _exigir_disponible(request):
    if not disponible(request):
        raise Http404


@require_GET
@solo_duena
def panel(request):
    _exigir_disponible(request)
    raise NotImplementedError("Carril D (T33)")


@require_POST
@solo_duena
def preguntar(request):
    _exigir_disponible(request)
    raise NotImplementedError("Carril D (T33)")


@require_POST
@solo_duena
def nueva(request):
    _exigir_disponible(request)
    raise NotImplementedError("Carril D (T33)")
