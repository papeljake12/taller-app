"""Panel de administración: prendas guardadas del cotizador."""

from django.contrib import admin

from cuentas.admin import SinAgregar
from cotizador.models import PrendaGuardada


@admin.register(PrendaGuardada)
class PrendaGuardadaAdmin(SinAgregar, admin.ModelAdmin):
    list_display = ["nombre", "metros", "precio_metro", "insumos", "mano_obra", "extra", "taller"]
    list_filter = ["taller"]
    search_fields = ["nombre"]
    readonly_fields = ["taller"]
