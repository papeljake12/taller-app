"""Panel de administración: el uso del asistente de cada taller, día por día, los resúmenes de
la mañana y los borradores guardados (tanda 8).

Solo para mirar: los registros los escribe la aplicación con cada pregunta. El costo en
dólares se calcula aquí con los precios de los ajustes (no se guarda) y solo lo ve David.
"""

from decimal import ROUND_HALF_UP, Decimal

from django.contrib import admin

from asistente.models import BorradorUsado, ResumenDelDia, UsoAsistente
from asistente.uso import costo_usd

CENTAVO = Decimal("0.01")
MILESIMA = Decimal("0.001")


@admin.register(UsoAsistente)
class UsoAsistenteAdmin(admin.ModelAdmin):
    list_display = [
        "fecha",
        "taller",
        "preguntas",
        "tokens_entrada",
        "tokens_salida",
        "tokens_cache_escritura",
        "tokens_cache_lectura",
        "costo",
        "costo_por_pregunta",
    ]
    list_filter = ["taller"]
    date_hierarchy = "fecha"

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    @admin.display(description="costo (USD)")
    def costo(self, obj):
        return costo_usd(obj.uso).quantize(CENTAVO, rounding=ROUND_HALF_UP)

    @admin.display(description="por pregunta (USD)")
    def costo_por_pregunta(self, obj):
        if not obj.preguntas:
            return "—"
        return (costo_usd(obj.uso) / obj.preguntas).quantize(MILESIMA, rounding=ROUND_HALF_UP)


class SoloLectura(admin.ModelAdmin):
    """Para mirar: estos registros los escribe la aplicación."""

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(ResumenDelDia)
class ResumenDelDiaAdmin(SoloLectura):
    list_display = ["fecha", "taller", "creado"]
    list_filter = ["taller"]
    date_hierarchy = "fecha"


@admin.register(BorradorUsado)
class BorradorUsadoAdmin(SoloLectura):
    list_display = ["creado", "taller", "clave"]
    list_filter = ["taller"]
