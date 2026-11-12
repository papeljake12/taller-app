"""Direcciones del proyecto. Cada app tiene las suyas en su propio urls.py."""

from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path("admin/", admin.site.urls),
    path("", include("pedidos.urls")),
]
