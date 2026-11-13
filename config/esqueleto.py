"""Respuesta de las acciones que todavía no están hechas (esqueleto de la tanda 2).

Cada acción del esqueleto ya comprueba que el pedido (o lo que toque) es del taller de la
usuaria, y después responde "todavía no" con el número de la tarea que la construye.
"""

from django.http import HttpResponse


def todavia_no(tarea):
    return HttpResponse(
        f"Esta parte llega con {tarea}.", status=501, content_type="text/plain; charset=utf-8"
    )
