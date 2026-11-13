"""Mi taller (T20): nombre y logo del taller, y las costureras.

Esqueleto de la tanda 2: la pantalla abre con sus tarjetas vacías y las acciones responden
"todavía no".
"""

from django.shortcuts import render
from django.views.decorators.http import require_POST

from config.esqueleto import todavia_no
from cuentas.aislamiento import obtener_o_404
from cuentas.models import Usuario


def mi_taller(request):
    return render(request, "cuentas/mi_taller.html")


@require_POST
def costurera_nueva(request):
    return todavia_no("T20")


@require_POST
def costurera_editar(request, pk):
    obtener_o_404(request, Usuario, pk=pk)
    return todavia_no("T20")
