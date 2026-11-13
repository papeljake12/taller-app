"""Direcciones del proyecto. Cada app tiene las suyas en su propio urls.py."""

from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path

from config.vistas import piezas, piezas_barras, piezas_etapa, piezas_filas, piezas_ventana

urlpatterns = [
    path("admin/", admin.site.urls),
    path("", include("cuentas.urls")),
    path("", include("pedidos.urls")),
    path("cotizador/", include("cotizador.urls")),
    path("telas/", include("telas.urls")),
    path("resumen/", include("finanzas.urls")),
    # Página interna con todas las piezas del diseño. Solo responde en desarrollo.
    path("piezas/", piezas, name="piezas"),
    path("piezas/animaciones/filas/", piezas_filas, name="piezas_filas"),
    path("piezas/animaciones/etapa/", piezas_etapa, name="piezas_etapa"),
    path("piezas/animaciones/barras/", piezas_barras, name="piezas_barras"),
    path("piezas/animaciones/ventana/", piezas_ventana, name="piezas_ventana"),
]

# En el computador de desarrollo, Django mismo entrega los archivos subidos (logos, fotos).
# En el servidor lo hace NGINX (T24).
urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
