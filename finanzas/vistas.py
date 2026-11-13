"""Resumen del mes y gastos (T17) y la descarga para Excel (T18).

Esqueleto de la tanda 2: la pantalla abre con sus tarjetas vacías y las acciones responden
"todavía no".
"""

from django.shortcuts import render
from django.utils import timezone
from django.views.decorators.http import require_POST

from config.esqueleto import todavia_no
from cuentas.aislamiento import obtener_o_404
from finanzas.models import Gasto


def resumen(request):
    return render(request, "finanzas/resumen.html", {"hoy": timezone.localdate()})


@require_POST
def gasto_nuevo(request):
    return todavia_no("T17")


@require_POST
def gasto_quitar(request, pk):
    obtener_o_404(request, Gasto, pk=pk)
    return todavia_no("T17")


def excel(request):
    return todavia_no("T18")
