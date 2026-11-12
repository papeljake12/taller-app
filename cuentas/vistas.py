"""Entrar y salir de la aplicación."""

from django.conf import settings
from django.contrib.auth.views import LoginView, LogoutView
from django.shortcuts import render

from cuentas.formularios import EntrarForm


class Entrar(LoginView):
    template_name = "cuentas/entrar.html"
    authentication_form = EntrarForm
    # Si ya tiene la sesión abierta, no le vuelve a pedir los datos: la lleva a Hoy.
    redirect_authenticated_user = True


class Salir(LogoutView):
    """Cierra la sesión. Solo acepta formularios (POST), nunca un simple enlace."""


def bloqueado(request, original_response=None, credentials=None):
    """Lo que se ve después de varios intentos fallidos seguidos (lo llama django-axes)."""
    minutos = int(settings.AXES_COOLOFF_TIME.total_seconds() // 60)
    contexto = {"intentos": settings.AXES_FAILURE_LIMIT, "minutos": minutos}
    return render(request, "cuentas/bloqueado.html", contexto, status=429)
