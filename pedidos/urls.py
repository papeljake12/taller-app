"""Direcciones de la app de pedidos: todas las de la aplicación base.

Este archivo es compartido: después de la tanda 2 solo lo cambia el coordinador. Cada
vista vive en el archivo de su zona en pedidos/vistas/ y la rellena su carril.
"""

from django.urls import path

from pedidos.vistas import (
    abonos,
    calendario,
    clientes,
    detalle,
    fotos,
    hoy,
    lista,
    materiales,
    publico,
    tallas,
)

app_name = "pedidos"

urlpatterns = [
    # Hoy (T06): la pantalla de entrada y sus acciones sin recargar.
    path("", hoy.hoy, name="hoy"),
    path("hoy/<int:pk>/<str:accion>/", hoy.accion, name="hoy_accion"),
    # Pedidos (T05): lista, nuevo pedido y el buscador del menú.
    path("pedidos/", lista.lista, name="lista"),
    path("pedidos/nuevo/", lista.nuevo, name="nuevo"),
    path("buscar/", lista.buscar, name="buscar"),
    # Pedido por dentro (T07): ficha, etapa, encargada, entrega, WhatsApp y eliminar.
    path("pedidos/<int:pk>/", detalle.detalle, name="detalle"),
    path("pedidos/<int:pk>/etapa/", detalle.etapa, name="etapa"),
    path("pedidos/<int:pk>/encargada/", detalle.encargada, name="encargada"),
    path("pedidos/<int:pk>/entrega/", detalle.entrega, name="entrega"),
    path("pedidos/<int:pk>/whatsapp/", detalle.whatsapp, name="whatsapp"),
    path("pedidos/<int:pk>/eliminar/", detalle.eliminar, name="eliminar"),
    # Abonos y recibo (T08, T09).
    path("pedidos/<int:pk>/abonos/", abonos.nuevo, name="abono_nuevo"),
    path("pedidos/<int:pk>/abonos/<int:abono>/quitar/", abonos.quitar, name="abono_quitar"),
    path("pedidos/<int:pk>/abonos/<int:abono>/recibo/", abonos.recibo, name="recibo"),
    # Tallas internas y enlace público (T10, T11).
    path("pedidos/<int:pk>/tallas/", tallas.nueva, name="talla_nueva"),
    path("pedidos/<int:pk>/tallas/<int:talla>/quitar/", tallas.quitar, name="talla_quitar"),
    path("pedidos/<int:pk>/tallas/enlace/", tallas.enlace, name="tallas_enlace"),
    path("tallas/<str:token>/", publico.formulario, name="publico_tallas"),
    # Materiales (T12).
    path("pedidos/<int:pk>/materiales/", materiales.nuevo, name="material_nuevo"),
    path(
        "pedidos/<int:pk>/materiales/<int:material>/comprado/",
        materiales.comprado,
        name="material_comprado",
    ),
    path(
        "pedidos/<int:pk>/materiales/<int:material>/quitar/",
        materiales.quitar,
        name="material_quitar",
    ),
    # Foto del pedido (T13).
    path("pedidos/<int:pk>/foto/", fotos.subir, name="foto"),
    path("pedidos/<int:pk>/foto/quitar/", fotos.quitar, name="foto_quitar"),
    # Calendario (T14).
    path("calendario/", calendario.calendario, name="calendario"),
    # Clientes (T04, T19).
    path("clientes/", clientes.clientes, name="clientes"),
    path("clientes/nuevo/", clientes.nuevo, name="cliente_nuevo"),
    path("clientes/<int:pk>/editar/", clientes.editar, name="cliente_editar"),
]
