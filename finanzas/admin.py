"""Panel de administración: gastos."""

from django.contrib import admin

from cuentas.admin import SinAgregar
from finanzas.models import Gasto


@admin.register(Gasto)
class GastoAdmin(SinAgregar, admin.ModelAdmin):
    list_display = ["concepto", "categoria", "valor", "fecha", "taller"]
    list_filter = ["taller", "categoria"]
    search_fields = ["concepto"]
    date_hierarchy = "fecha"
    readonly_fields = ["taller"]
