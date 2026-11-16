"""Panel de administración: telas y su historial."""

from django.contrib import admin

from cuentas.admin import SinAgregar
from telas.models import MovimientoTela, Tela, TelaPedido


class MovimientoEnLinea(admin.TabularInline):
    model = MovimientoTela
    extra = 0


@admin.register(Tela)
class TelaAdmin(SinAgregar, admin.ModelAdmin):
    list_display = ["nombre", "metros", "minimo", "taller"]
    list_filter = ["taller"]
    search_fields = ["nombre"]
    readonly_fields = ["taller"]
    inlines = [MovimientoEnLinea]


@admin.register(TelaPedido)
class TelaPedidoAdmin(SinAgregar, admin.ModelAdmin):
    list_display = ["pedido", "tela", "metros"]
    list_filter = ["tela__taller"]
