"""Pedidos (T05): la lista con filtros y buscador, "Nuevo pedido" y el buscador del menú.

Todas las cuentas (saldo, tallas, etiquetas, filtros y orden) salen de pedidos/calculos.py.
Todo se filtra por el taller de la usuaria (cuentas/aislamiento.py).

Permisos (T21, docs/04-permisos.md): la costurera ve todos los pedidos, pero sin valores: sin
la columna Saldo ni el filtro "Con saldo". No crea pedidos y el buscador no le muestra
clientes (Clientes es solo de la dueña).
"""

from dataclasses import dataclass
from urllib.parse import urlencode

from django.db import IntegrityError, transaction
from django.http import HttpResponse
from django.shortcuts import redirect, render
from django.urls import reverse
from django.utils import timezone
from django.utils.cache import patch_vary_headers
from django.views.decorators.http import require_http_methods

from config.ventanas import es_htmx, responder_ventana
from cuentas.aislamiento import del_taller
from cuentas.permisos import puede_ver_plata, solo_duena
from pedidos import calculos
from pedidos.calculos import Etiqueta
from pedidos.formularios.lista import NuevoPedidoForm
from pedidos.models import Cliente, Pedido

CLAVES_DE_FILTRO = {clave for clave, _ in calculos.FILTROS}
# Los filtros que hablan de plata: la costurera no los tiene (T21).
FILTROS_CON_PLATA = {"saldo"}

AVISO_DE_ERRORES = "Revisa los campos marcados."


@dataclass(frozen=True)
class FilaPedido:
    """Un pedido con lo que muestra su fila: etapa, urgencia, tallas y saldo (0 si quien
    la ve no puede ver la plata)."""

    pedido: Pedido
    etapa: Etiqueta
    urgencia: Etiqueta | None
    tallas_recibidas: int
    tallas_esperadas: int
    saldo: int
    cotizado: bool


def filas_de(pedidos, hoy, con_plata=True):
    """Las filas de la tabla, en el orden de la lista (calculos.ordenar_pedidos)."""
    filas = []
    for pedido in calculos.ordenar_pedidos(pedidos):
        recibidas, esperadas = calculos.tallas_recibidas(pedido)
        filas.append(
            FilaPedido(
                pedido=pedido,
                etapa=calculos.etiqueta_etapa(pedido),
                urgencia=calculos.etiqueta_urgencia(pedido, hoy),
                tallas_recibidas=recibidas,
                tallas_esperadas=esperadas,
                saldo=calculos.saldo(pedido) if con_plata else 0,
                cotizado=pedido.estado == Pedido.Estado.COTIZADO,
            )
        )
    return filas


def buscar_pedidos(pedidos, q):
    """Los pedidos cuyo cliente, prenda o encargada contienen lo buscado (sin tildes)."""
    return [
        p
        for p in pedidos
        if calculos.coincide(
            q, p.cliente.nombre, p.detalle, p.encargada.nombre if p.encargada else ""
        )
    ]


def pedidos_para_tabla(request):
    """Los pedidos del taller con sus cuentas y lo que la fila necesita, en una consulta."""
    return calculos.con_cuentas(del_taller(request, Pedido)).select_related("cliente", "encargada")


def filtros_permitidos(request):
    """Las claves de filtro que puede usar: todas, o sin las de plata para la costurera."""
    if puede_ver_plata(request):
        return CLAVES_DE_FILTRO
    return CLAVES_DE_FILTRO - FILTROS_CON_PLATA


def _filtro_elegido(request):
    filtro = request.GET.get("filtro", "todos")
    return filtro if filtro in filtros_permitidos(request) else "todos"


def _con_busqueda(url, filtro, q):
    """La dirección de la lista con su filtro y lo buscado: ?filtro=...&q=..."""
    parametros = {"filtro": filtro}
    if q:
        parametros["q"] = q
    return f"{url}?{urlencode(parametros)}"


def lista(request):
    hoy = timezone.localdate()
    filtro = _filtro_elegido(request)
    permitidos = filtros_permitidos(request)
    q = request.GET.get("q", "").strip()
    pedidos_del_taller = del_taller(request, Pedido)
    total = pedidos_del_taller.count()
    url_lista = reverse("pedidos:lista")

    elegidos = calculos.filtrar_pedidos(pedidos_para_tabla(request), filtro, hoy)
    if q:
        elegidos = buscar_pedidos(elegidos, q)
    contexto = {
        "total": total,
        "filtro": filtro,
        "q": q,
        "filas": filas_de(elegidos, hoy, puede_ver_plata(request)),
        "url_todos": _con_busqueda(url_lista, "todos", ""),
        "filtros": [
            {
                "clave": clave,
                "texto": nombre,
                "conteo": conteo,
                "elegido": clave == filtro,
                "url": _con_busqueda(url_lista, clave, q),
            }
            for clave, nombre, conteo in calculos.conteo_de_filtros(pedidos_del_taller, hoy)
            if clave in permitidos
        ],
    }
    # El buscador pide solo la tabla mientras se escribe. Si el navegador vuelve atrás y no
    # tiene guardada la página, HTMX la pide entera (HX-History-Restore-Request).
    solo_tabla = es_htmx(request) and request.headers.get("HX-History-Restore-Request") != "true"
    plantilla = "pedidos/_lista_busqueda.html" if solo_tabla else "pedidos/lista.html"
    respuesta = render(request, plantilla, contexto)
    patch_vary_headers(respuesta, ["HX-Request"])
    return respuesta


@solo_duena
@require_http_methods(["GET", "POST"])
def nuevo(request):
    """Ventana "Nuevo pedido". Se abre desde el botón de cualquier pantalla. Solo la dueña."""
    contexto = {"accion": reverse("pedidos:nuevo"), "titulo_pagina": "Nuevo pedido",
                "volver": reverse("pedidos:lista")}
    if request.method != "POST":
        contexto["form"] = NuevoPedidoForm()
        return responder_ventana(request, "pedidos/_nuevo.html", contexto)

    form = NuevoPedidoForm(request.POST)
    if not form.is_valid():
        contexto["form"] = form
        contexto["aviso"] = [*form.non_field_errors(), AVISO_DE_ERRORES]
        return responder_ventana(request, "pedidos/_nuevo.html", contexto, status=422)

    pedido = crear_pedido(request, form.cleaned_data)
    destino = reverse("pedidos:detalle", args=[pedido.pk])
    if es_htmx(request):
        return HttpResponse(headers={"HX-Redirect": destino})
    return redirect(destino)


def cliente_para_el_pedido(request, datos):
    """El cliente con ese nombre en el taller (sin mirar mayúsculas), o uno nuevo.

    Si ya existía y no tenía WhatsApp, se le pone el que se escribió. Su tipo no se cambia.
    """
    clientes = del_taller(request, Cliente)
    cliente = clientes.filter(nombre__iexact=datos["cliente"]).first()
    if cliente is None:
        try:
            with transaction.atomic():
                return Cliente.objects.create(
                    taller=request.taller,
                    nombre=datos["cliente"],
                    tipo=datos["tipo"],
                    whatsapp=datos["whatsapp"],
                )
        except IntegrityError:
            # Otra persona lo creó en el mismo momento: se usa ese.
            cliente = clientes.get(nombre__iexact=datos["cliente"])
    if datos["whatsapp"] and not cliente.whatsapp:
        cliente.whatsapp = datos["whatsapp"]
        cliente.save(update_fields=["whatsapp", "actualizado"])
    return cliente


@transaction.atomic
def crear_pedido(request, datos):
    """El pedido nace cotizado, en el taller de la usuaria y a su nombre."""
    return Pedido.objects.create(
        taller=request.taller,
        cliente=cliente_para_el_pedido(request, datos),
        detalle=datos["detalle"],
        cantidad=datos["cantidad"],
        tallaje=datos["tallaje"],
        fecha_entrega=datos["fecha_entrega"],
        total=datos["total"],
        estado=Pedido.Estado.COTIZADO,
        creado_por=request.user,
    )


def buscar(request):
    """Resultados del buscador del menú: pedidos y clientes (la costurera, solo pedidos y sin
    valores: Clientes es solo de la dueña)."""
    hoy = timezone.localdate()
    q = request.GET.get("q", "").strip()
    con_plata = puede_ver_plata(request)
    contexto = {"q": q, "filas": [], "clientes": []}
    if q:
        pedidos = buscar_pedidos(pedidos_para_tabla(request), q)
        contexto["filas"] = filas_de(pedidos, hoy, con_plata)
    if q and con_plata:
        contexto["clientes"] = [
            c for c in del_taller(request, Cliente) if calculos.coincide(q, c.nombre)
        ]
    return render(request, "pedidos/buscar.html", contexto)
