"""Pantalla Hoy (T06): la de entrada, y sus acciones sin recargar la página.

Todas las cuentas salen de pedidos/calculos.py y los mensajes de pedidos/mensajes.py. Aquí
solo se arman las frases y los botones de cada tarjeta, siempre con los datos del taller de
la usuaria (request.taller).

Las acciones de "Qué hacer hoy" ("Marcar como listo" y "Marcar como entregado") cambian la
etapa del pedido. Con HTMX responden lo de adentro de la lista de "Qué hacer hoy" (así la
lista, que en el computador se desplaza por dentro, no vuelve arriba) y, con hx-swap-oob, las
otras partes que dependen de ella: la cuenta de pendientes, las cifras, "Quién te debe",
"Pedidos por etapa" y el contador de atrasados del menú. Sin JavaScript, vuelven a Hoy.
No llevan aviso corto (config/avisos.py): el cambio se ve justo donde se tocó (la fila cambia
o se cierra) y la demo tampoco lo tiene al cambiar de etapa.

"Trabajos del taller" (_trabajos.html) es de T13.

Permisos (T21, docs/04-permisos.md): la costurera ve las cifras de producción, entregas y
atrasados, pero no "Por cobrar", ni "Cobrado y gastado", ni "Quién te debe". En "Qué hacer
hoy" no ve valores ni "Cobrar el saldo", y solo marca como listo o entregado los pedidos de
los que es la encargada (lo mismo que en el pedido por dentro). Esas partes ni se calculan
para ella: así no pueden aparecer en ninguna respuesta.
"""

from dataclasses import dataclass, replace
from urllib.parse import urlencode

from django.http import Http404, HttpResponse
from django.shortcuts import redirect, render
from django.template.loader import render_to_string
from django.urls import reverse
from django.utils import timezone
from django.utils.dates import MONTHS
from django.views.decorators.http import require_POST

from config.menu import construir_menu
from config.piezas import pesos
from config.ventanas import es_htmx
from cuentas.aislamiento import obtener_o_404
from cuentas.permisos import exigir_mover_etapa, puede_mover_etapa, puede_ver_plata
from pedidos import calculos, fotos, mensajes
from pedidos.calculos import Etiqueta
from pedidos.models import Pedido

Estado = Pedido.Estado

# Las acciones de "Qué hacer hoy": a qué etapa pasa el pedido y desde cuáles se puede.
# Desde otra etapa no cambia nada (por ejemplo, si alguien ya lo entregó desde otro
# celular): la tarjeta se vuelve a dibujar con lo que hay.
ACCIONES = {
    "listo": (Estado.LISTO, (Estado.CONFIRMADO, Estado.CORTE, Estado.CONFECCION)),
    "entregado": (Estado.ENTREGADO, (Estado.LISTO,)),
}

# Las partes que cambian, además de la lista de "Qué hacer hoy", cuando se hace una acción.
CAMBIAN_CON_UNA_ACCION = ("hoy_cuenta", "cifras", "quien_debe", "etapas", "hoy_menu")
# Las que tienen plata: la costurera no las recibe (T21).
PARTES_CON_PLATA = ("quien_debe",)


# --- Las cuatro cifras ------------------------------------------------------------------------


@dataclass(frozen=True)
class Cifra:
    nombre: str
    valor: object
    apoyo: str
    url: str
    alerta: bool
    # En celular van 2 por 2 en otro orden (diseno/hoy-celular.html): clase orden-celular-N.
    # Con 0 se quedan en el orden del computador (la costurera, que ve tres).
    orden_celular: int
    # La plata va un poco más pequeña en celular (diseno/hoy-celular.html: "Por cobrar").
    dinero: bool = False

    @property
    def clase(self):
        clases = []
        if self.orden_celular:
            clases.append(f"orden-celular-{self.orden_celular}")
        if self.dinero:
            clases.append("cifra--dinero")
        return " ".join(clases)


def _plural(cantidad, singular, plural):
    return f"{cantidad} {singular if cantidad == 1 else plural}"


def apoyo_mas_cercana(dias):
    """'La más cercana: en 3 días', 'hoy' o 'mañana'. Sin entregas: 'Nada para esta semana'."""
    if dias is None:
        return "Nada para esta semana"
    if dias == 0:
        return "La más cercana: hoy"
    if dias == 1:
        return "La más cercana: mañana"
    return f"La más cercana: en {dias} días"


def cifras(taller, hoy, con_plata=False):
    """Las cuatro cifras de arriba, en el orden del computador, cada una con su filtro.

    Sin plata (la costurera), son tres: sin "Por cobrar". Esas tres no cambian de orden en
    celular: van 2 y 1 a lo ancho (static/css/app.css), en el mismo orden en que se llega a
    ellas con el teclado.
    """
    datos = calculos.cifras_de_hoy(taller, hoy)
    lista = reverse("pedidos:lista")

    def filtro(clave):
        return f"{lista}?{urlencode({'filtro': clave})}"

    produccion = [
        Cifra(
            "En producción",
            datos["en_produccion"],
            f"{datos['por_confirmar']} por confirmar"
            if datos["por_confirmar"]
            else "Sin cotizaciones pendientes",
            filtro("produccion"),
            alerta=False,
            orden_celular=1,
        ),
        Cifra(
            "Entregas en 7 días",
            datos["entregas_7_dias"],
            apoyo_mas_cercana(datos["dias_mas_cercana"]),
            filtro("semana"),
            alerta=False,
            orden_celular=3,
        ),
        Cifra(
            "Atrasados",
            datos["atrasados"],
            "Pasó la fecha de entrega" if datos["atrasados"] else "Todo va a tiempo",
            filtro("atrasados"),
            alerta=datos["atrasados"] > 0,
            orden_celular=2,
        ),
    ]
    if not con_plata:
        return [replace(cifra, orden_celular=0) for cifra in produccion]
    return [
        *produccion,
        Cifra(
            "Por cobrar",
            pesos(datos["por_cobrar"]),
            _plural(datos["pedidos_con_saldo"], "pedido con saldo", "pedidos con saldo"),
            filtro("saldo"),
            alerta=False,
            orden_celular=4,
            dinero=True,
        ),
    ]


# --- Qué hacer hoy ----------------------------------------------------------------------------


@dataclass(frozen=True)
class FilaPendiente:
    """Un pedido de "Qué hacer hoy" con lo que dice su fila y la acción que sigue.

    siguiente:
      - "listo": atrasado y sin terminar: "Marcar como listo" y "Avisar al cliente".
      - "entregar": listo: "Cobrar el saldo" (si debe) y "Marcar como entregado".
      - "ver": se entrega pronto: abrir el pedido.
      - "confirmar": cotizado: "Preguntar si confirma".
    mensaje: {"texto", "enlace"} para "Avisar al cliente" o "Preguntar si confirma". Sin
    WhatsApp guardado, el enlace es "" y el botón copia el texto.
    """

    pedido: Pedido
    motivo: str
    etiqueta: Etiqueta | None
    detalle: str
    etapa: str
    saldo: int
    siguiente: str
    mensaje: dict | None


def frase_de_etapa(pedido):
    """'En confección con Carmen', 'Ya está listo'... Vacía para un cotizado."""
    if pedido.estado == Estado.COTIZADO:
        return ""
    if pedido.estado == Estado.LISTO:
        return "Ya está listo"
    if pedido.estado == Estado.ENTREGADO:
        return "Ya se entregó"
    nombre = Estado(pedido.estado).label
    return f"{nombre} con {pedido.encargada.nombre}" if pedido.encargada else nombre


def _mensaje(pedido, texto):
    return {"texto": texto, "enlace": mensajes.enlace_whatsapp(pedido.cliente.whatsapp, texto)}


def fila_pendiente(pendiente, hoy, request=None):
    """La fila y su acción. Con el `request` de una costurera (T21): sin saldo; "Marcar como
    listo" y "Marcar como entregado" solo si es la encargada; y en un cotizado, "Ver el
    pedido" en vez de "Preguntar si confirma", porque ese mensaje dice el precio."""
    pedido = pendiente.pedido
    # Sin saber quién pregunta, no se muestra plata ni se deja mover (falla cerrado).
    con_plata = request is not None and puede_ver_plata(request)
    puede_mover = request is not None and puede_mover_etapa(request, pedido)
    if pedido.estado == Estado.LISTO:
        # Un listo atrasado sigue en el grupo de los atrasados, pero lo que sigue es entregarlo.
        siguiente, mensaje = "entregar", None
    elif pendiente.motivo == "atrasado":
        siguiente, mensaje = "listo", _mensaje(pedido, mensajes.texto_atraso(pedido))
    elif pendiente.motivo == "cotizado" and con_plata:
        siguiente, mensaje = "confirmar", _mensaje(pedido, mensajes.texto_confirmar(pedido))
    else:
        siguiente, mensaje = "ver", None
    if siguiente in ("entregar", "listo") and not puede_mover:
        siguiente, mensaje = "ver", None
    return FilaPendiente(
        pedido=pedido,
        motivo=pendiente.motivo,
        etiqueta=calculos.etiqueta_entrega(pedido, hoy),
        # El detalle termina en punto en la frase: si ya trae uno, no se repite.
        detalle=pedido.detalle.strip().rstrip("."),
        etapa=frase_de_etapa(pedido),
        saldo=calculos.saldo(pedido) if con_plata else 0,
        siguiente=siguiente,
        mensaje=mensaje,
    )


def pendientes(taller, hoy, request=None):
    return [fila_pendiente(p, hoy, request) for p in calculos.que_hacer_hoy(taller, hoy)]


# --- Cobrado y gastado ------------------------------------------------------------------------


def nota_de_la_grafica(meses):
    """Cómo leer los números del eje. Sin datos, lo dice.

    Con un millón o más, el eje puede mezclar "500 mil" y "1 M": la nota solo explica la M.
    """
    maximo = max((max(m.cobrado, m.gastado) for m in meses), default=0)
    if maximo >= 1_000_000:
        return "M = millones de pesos."
    if maximo > 0:
        return "Valores en miles de pesos."
    return "Todavía no hay cobros ni gastos en estos seis meses."


def grafica(taller, hoy):
    meses = calculos.grafica_cobrado_y_gastado(taller, hoy)
    return {
        "meses": meses,
        "cobrado_del_mes": meses[-1].cobrado,
        "nombre_del_mes": str(MONTHS[hoy.month]).lower(),
        "nota_grafica": nota_de_la_grafica(meses),
    }


# --- Quién te debe y pedidos por etapa ----------------------------------------------------------


def deudores(taller, hoy):
    """Los que deben, cada uno con el enlace a sus pedidos con saldo en Pedidos."""
    lista = reverse("pedidos:lista")
    return [
        {
            "deudor": deudor,
            "url": f"{lista}?{urlencode({'filtro': 'saldo', 'q': deudor.cliente.nombre})}",
        }
        for deudor in calculos.quien_te_debe(taller, hoy)
    ]


def aviso_de_etapa(etapa, con_plata=False):
    """La etiqueta debajo del número de una etapa: "1 atrasado" en rojo; en Entregado,
    "Pagado" en verde si ninguno debe, o cuántos deben en rojo. None si no hay nada que decir.
    Sin plata (la costurera), Entregado no dice si deben.
    """
    if etapa.atrasados:
        return Etiqueta(_plural(etapa.atrasados, "atrasado", "atrasados"), "rojo")
    if etapa.estado == Estado.ENTREGADO and etapa.cantidad and con_plata:
        if etapa.con_saldo:
            return Etiqueta(f"{etapa.con_saldo} con saldo", "rojo")
        return Etiqueta("Pagado", "verde")
    return None


def etapas(taller, hoy, con_plata=False):
    return [
        {
            "nombre": etapa.nombre,
            "cantidad": etapa.cantidad,
            "aviso": aviso_de_etapa(etapa, con_plata),
        }
        for etapa in calculos.pedidos_por_etapa(taller, hoy)
    ]


# --- La página y las acciones -------------------------------------------------------------------


def contexto_de_hoy(request, hoy):
    """Todo lo que necesitan las tarjetas de Hoy. Sin plata para la costurera (T21)."""
    taller = request.taller
    con_plata = puede_ver_plata(request)
    contexto = {
        "hoy": hoy,
        "cifras": cifras(taller, hoy, con_plata),
        "pendientes": pendientes(taller, hoy, request),
        "etapas": etapas(taller, hoy, con_plata),
        "trabajos": fotos.trabajos(request),  # T13
    }
    if con_plata:
        contexto["deudores"] = deudores(taller, hoy)
        contexto.update(grafica(taller, hoy))
    return contexto


def menu_de_hoy(request):
    """Las entradas del menú lateral, para cambiar su contador de atrasados con hx-swap-oob.

    La acción tiene su propia dirección: se marca "Hoy" como la sección actual, que es la
    pantalla donde está la usuaria.
    """
    return [replace(e, actual=e.clave == "hoy") for e in construir_menu(request)["secciones"]]


def hoy(request):
    return render(request, "pedidos/hoy.html", contexto_de_hoy(request, timezone.localdate()))


@require_POST
def accion(request, pk, accion):
    """Marcar como listo o como entregado desde "Qué hacer hoy".

    Como cambiar la etapa en el pedido: la dueña siempre, la costurera solo si es la
    encargada (si no, 403). Primero se busca el pedido en el taller: el de otro, 404.
    """
    if accion not in ACCIONES:
        raise Http404("Esa acción no existe.")
    pedido = obtener_o_404(request, Pedido, pk=pk)
    exigir_mover_etapa(request, pedido)
    nueva, desde = ACCIONES[accion]
    if pedido.estado in desde:
        pedido.estado = nueva
        pedido.save(update_fields=["estado", "actualizado"])
    if not es_htmx(request):
        return redirect(reverse("pedidos:hoy") + "#hoy-que-hacer")
    contexto = contexto_de_hoy(request, timezone.localdate())
    contexto["menu_lateral"] = menu_de_hoy(request)
    html = render_to_string("pedidos/_hoy_pendientes.html", contexto, request=request)
    for parte in CAMBIAN_CON_UNA_ACCION:
        if parte in PARTES_CON_PLATA and not puede_ver_plata(request):
            continue
        html += render_to_string(f"pedidos/_{parte}.html", {**contexto, "oob": True}, request)
    return HttpResponse(html)
