"""Panel de administración: clientes y pedidos, para dar soporte a los talleres."""

from django.contrib import admin

from cuentas.admin import SinAgregar
from pedidos.models import Abono, Cliente, Material, Pedido, Talla


@admin.register(Cliente)
class ClienteAdmin(SinAgregar, admin.ModelAdmin):
    list_display = ["nombre", "tipo", "whatsapp", "taller"]
    list_filter = ["taller", "tipo"]
    search_fields = ["nombre", "whatsapp"]
    readonly_fields = ["taller"]


class AbonoEnLinea(admin.TabularInline):
    model = Abono
    extra = 0


class TallaEnLinea(admin.TabularInline):
    model = Talla
    extra = 0


class MaterialEnLinea(admin.TabularInline):
    model = Material
    extra = 0


@admin.register(Pedido)
class PedidoAdmin(SinAgregar, admin.ModelAdmin):
    list_display = ["cliente", "detalle", "estado", "fecha_entrega", "total", "taller"]
    list_filter = ["taller", "estado"]
    search_fields = ["cliente__nombre", "detalle"]
    date_hierarchy = "fecha_entrega"
    readonly_fields = ["taller", "token_tallas"]
    inlines = [AbonoEnLinea, TallaEnLinea, MaterialEnLinea]
