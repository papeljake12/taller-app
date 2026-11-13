"""Direcciones del proyecto. Cada app tiene las suyas en su propio urls.py."""

from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path

from config.vistas import piezas

urlpatterns = [
    path("admin/", admin.site.urls),
    path("", include("cuentas.urls")),
    path("", include("pedidos.urls")),
    path("cotizador/", include("cotizador.urls")),
    path("telas/", include("telas.urls")),
    path("resumen/", include("finanzas.urls")),
    # Página interna con todas las piezas del diseño. Solo responde en desarrollo.
    path("piezas/", piezas, name="piezas"),
]

# En el computador de desarrollo, Django mismo entrega los archivos subidos (logos, fotos).
# En el servidor lo hace NGINX (T24).
urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
