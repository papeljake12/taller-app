"""Pedidos (T05): la lista con filtros y buscador, "Nuevo pedido" y el buscador del menú.

Todas las cuentas (saldo, tallas, etiquetas, filtros y orden) salen de pedidos/calculos.py.
Todo se filtra por el taller de la usuaria (cuentas/aislamiento.py).

Permisos (T21, docs/04-permisos.md): la costurera ve todos los pedidos, pero sin valores: sin
las columnas Total y Pago, ni "Por cobrar", ni el filtro "Con saldo". No crea pedidos y el buscador no le muestra
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

from config.avisos import avisar
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
    """Un pedido con lo que muestra su fila: etapa, pago (solo si quien la ve puede ver la
    plata), fecha de entrega y tallas."""

    pedido: Pedido
    etapa: Etiqueta
    pago: Etiqueta | None  # None si quien la ve no puede ver la plata
    fecha: str  # "11 nov"
    entrega_nota: str  # "2 días tarde", "en 3 días", "hoy", "mañana" o ""
    atrasado: bool
    tallas_recibidas: int
    tallas_esperadas: int


MESES_CORTOS = ("ene", "feb", "mar", "abr", "may", "jun", "jul", "ago", "sep", "oct", "nov", "dic")


def fecha_de_entrega(fecha):
    """"11 nov", como en diseno/pedidos.html."""
    return f"{fecha.day} {MESES_CORTOS[fecha.month - 1]}"


def _dias(cantidad):
    return f"{cantidad} {'día' if cantidad == 1 else 'días'}"


def nota_de_entrega(pedido, hoy):
    """Lo que acompaña la fecha: "2 días tarde" si va atrasado; "hoy", "mañana" o "en 3 días"
    si se entrega en los próximos 7 días; si no, nada."""
    dias = calculos.dias_para_entrega(pedido, hoy)
    if calculos.esta_atrasado(pedido, hoy):
        return f"{_dias(-dias)} tarde"
    if calculos.esta_pronto(pedido, hoy):
        return {0: "hoy", 1: "mañana"}.get(dias, f"en {_dias(dias)}")
    return ""


def filas_de(pedidos, hoy, con_plata=True):
    """Las filas de la tabla, en el orden de la lista (calculos.ordenar_pedidos)."""
    filas = []
    for pedido in calculos.ordenar_pedidos(pedidos):
        recibidas, esperadas = calculos.tallas_recibidas(pedido)
        filas.append(
            FilaPedido(
                pedido=pedido,
                etapa=calculos.etiqueta_etapa(pedido),
                pago=calculos.etiqueta_pago(pedido, hoy) if con_plata else None,
                fecha=fecha_de_entrega(pedido.fecha_entrega),
                entrega_nota=nota_de_entrega(pedido, hoy),
                atrasado=calculos.esta_atrasado(pedido, hoy),
                tallas_recibidas=recibidas,
                tallas_esperadas=esperadas,
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


def cifras_de(request, conteos, total, url_lista):
    """La barra de cifras de arriba de Pedidos. "Por cobrar" no la ve la costurera."""
    cuantos = {clave: conteo for clave, _, conteo in conteos}
    cifras = {
        "activos": total - cuantos["entregados"],
        "produccion": cuantos["produccion"],
        "semana": cuantos["semana"],
        "atrasados": cuantos["atrasados"],
        "url_produccion": _con_busqueda(url_lista, "produccion", ""),
        "url_semana": _con_busqueda(url_lista, "semana", ""),
        "url_atrasados": _con_busqueda(url_lista, "atrasados", ""),
    }
    if puede_ver_plata(request):
        cifras["por_cobrar"] = calculos.por_cobrar(request.taller)
        cifras["url_saldo"] = _con_busqueda(url_lista, "saldo", "")
    return cifras


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
    conteos = calculos.conteo_de_filtros(pedidos_del_taller, hoy)
    contexto = {
        "total": total,
        "filtro": filtro,
        "q": q,
        # La fila del buscador se ve si hay algo buscado o si se tocó la lupa sin JavaScript.
        "ver_buscador": bool(q) or "buscar" in request.GET,
        "url_buscar": _con_busqueda(url_lista, filtro, q) + "&buscar=1",
        "cifras": cifras_de(request, conteos, total, url_lista),
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
            for clave, nombre, conteo in conteos
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
        respuesta = HttpResponse(headers={"HX-Redirect": destino})
    else:
        respuesta = redirect(destino)
    # Lleva al pedido nuevo: el aviso de la demo sale allí (config/avisos.py lo deja como mensaje).
    return avisar(request, respuesta, "Pedido guardado.")


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
