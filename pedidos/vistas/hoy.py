"""Pantalla Hoy: la de entrada. Sus tarjetas llegan con T06."""

from django.shortcuts import render
from django.utils import timezone


def hoy(request):
    return render(request, "pedidos/hoy.html", {"hoy": timezone.localdate()})
