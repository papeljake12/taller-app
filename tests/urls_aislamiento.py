"""Direcciones de prueba para tests/test_aislamiento.py.

Son dos pantallas mínimas que usan cuentas/aislamiento.py igual que lo harán las
pantallas de verdad (lista y detalle). Solo existen durante las pruebas.
"""

from django.http import HttpResponse
from django.urls import path

from cuentas.aislamiento import del_taller, obtener_o_404
from cuentas.models import Usuario


def lista_de_usuarias(request):
    nombres = del_taller(request, Usuario).order_by("username").values_list("username", flat=True)
    return HttpResponse("\n".join(nombres), content_type="text/plain")


def ver_usuaria(request, pk):
    usuaria = obtener_o_404(request, Usuario, pk=pk)
    return HttpResponse(usuaria.username, content_type="text/plain")


urlpatterns = [
    path("usuarias/", lista_de_usuarias),
    path("usuarias/<int:pk>/", ver_usuaria),
]
