"""Calendario (T14): el mes con las entregas marcadas.

Esqueleto de la tanda 2: abre con sus tarjetas vacías.
"""

from django.shortcuts import render
from django.utils import timezone


def calendario(request):
    return render(request, "pedidos/calendario.html", {"hoy": timezone.localdate()})
