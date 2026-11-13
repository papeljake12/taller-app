"""Direcciones del resumen del mes. Archivo compartido: después de la tanda 2 solo lo
cambia el coordinador."""

from django.urls import path

from finanzas import vistas

app_name = "finanzas"

urlpatterns = [
    path("", vistas.resumen, name="resumen"),
    path("gastos/", vistas.gasto_nuevo, name="gasto_nuevo"),
    path("gastos/<int:pk>/quitar/", vistas.gasto_quitar, name="gasto_quitar"),
    path("excel/", vistas.excel, name="excel"),
]
