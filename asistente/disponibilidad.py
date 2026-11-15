"""¿Le sale el asistente a quien abrió la página?

Solo si hay clave de la API, si es la dueña de un taller y si David prendió el asistente de
ese taller (los dos límites mayores que 0). Haberse acabado las preguntas no lo esconde: el
panel dice cuándo vuelve.
"""

from django.conf import settings

from cuentas import permisos


def disponible(request) -> bool:
    if not settings.ANTHROPIC_API_KEY or not permisos.es_duena(request):
        return False
    taller = getattr(request, "taller", None)
    return bool(taller and taller.asistente_limite_mes > 0 and taller.asistente_limite_dia > 0)
