"""Pantalla Hoy (T06): la de entrada, y sus acciones sin recargar la página.

Todas las cuentas salen de pedidos/calculos.py y los mensajes de pedidos/mensajes.py. Aquí
solo se arman las frases y los botones de cada tarjeta, siempre con los datos del taller de
la usuaria (request.taller).

Las acciones de las tarjetas de "lo que hay que hacer hoy" ("Marcar como listo", "Marcar como
entregado" y "Confirmar pedido") cambian la etapa del pedido. Con HTMX responden lo de adentro
de la lista de tarjetas y, con hx-swap-oob, las partes que dependen de ella: la frase de cosas
pendientes, las cifras, "Quién te debe", "Pedidos por etapa", el estado de arriba ("N pedidos
atrasados") y el contador de atrasados del menú. Sin JavaScript, vuelven a Hoy.
No llevan aviso corto (config/avisos.py): el cambio se ve justo donde se tocó (la tarjeta
cambia o se cierra).

Permisos (T21, docs/04-permisos.md): la costurera ve las cifras de producción, entregas y
atrasados, pero no "Cobrado", "Gastado", "Por cobrar", ni la gráfica, ni "Quién te debe". En las
tarjetas no ve valores y solo marca como listo o entregado los pedidos de los que es la
encargada (lo mismo que en el pedido por dentro). Esas partes ni se calculan para ella: así
no pueden aparecer en ninguna respuesta.
"""

from dataclasses import dataclass, replace
from urllib.parse import urlencode

from django.http import Http404, HttpResponse
from django.shortcuts import redirect, render
from django.template.loader import render_to_string
from django.urls import reverse
from django.utils import timezone
from django.utils.dates import MONTHS
from django.utils.text import capfirst
from django.views.decorators.http import require_POST

from config.menu import construir_menu
from config.piezas import pesos
from config.ventanas import es_htmx
from cuentas.aislamiento import obtener_o_404
from cuentas.permisos import exigir_mover_etapa, puede_mover_etapa, puede_ver_plata
from pedidos import calculos, mensajes
from pedidos.calculos import Etiqueta
from pedidos.models import Pedido

Estado = Pedido.Estado

# Las acciones de las tarjetas: a qué etapa pasa el pedido y desde cuáles se puede.
# Desde otra etapa no cambia nada (por ejemplo, si alguien ya lo entregó desde otro
# celular): la tarjeta se vuelve a dibujar con lo que hay.
ACCIONES = {
    "listo": (Estado.LISTO, (Estado.CONFIRMADO, Estado.CORTE, Estado.CONFECCION)),
    "entregado": (Estado.ENTREGADO, (Estado.LISTO,)),
    "confirmado": (Estado.CONFIRMADO, (Estado.COTIZADO,)),
}

# Las partes que cambian, además de la lista de tarjetas, cuando se hace una acción.
CAMBIAN_CON_UNA_ACCION = ("hoy_cuenta", "hoy_estado", "cifras", "quien_debe", "etapas", "hoy_menu")
# Las que tienen plata: la costurera no las recibe (T21).
PARTES_CON_PLATA = ("quien_debe",)


# --- Tu mes -------------------------------------------------------------------------------------


@dataclass(frozen=True)
class Cifra:
    nombre: str
    valor: object
    explica: str
    url: str
    alerta: bool = False


def _plural(cantidad, singular, plural):
    return f"{cantidad} {singular if cantidad == 1 else plural}"


def cifras(taller, hoy, con_plata=False):
    """Las cifras de "Tu mes", cada una con su enlace y de dónde sale el número.

    La dueña: Cobrado y Gastado del mes (a Resumen), Por cobrar y En producción (a Pedidos con
    su filtro). La costurera, sin plata: en producción, se entregan esta semana y atrasados.
    """
    datos = calculos.cifras_de_hoy(taller, hoy)
    lista = reverse("pedidos:lista")

    def filtro(clave):
        return f"{lista}?{urlencode({'filtro': clave})}"

    if con_plata:
        resumen = reverse("finanzas:resumen")
        return [
            Cifra(
                "Cobrado",
                pesos(calculos.cobrado_en(taller, hoy.year, hoy.month)),
                "Los abonos que recibiste este mes",
                resumen,
            ),
            Cifra(
                "Gastado",
                pesos(calculos.gastado_en(taller, hoy.year, hoy.month)),
                "Los gastos que anotaste este mes",
                resumen,
            ),
            Cifra(
                "Por cobrar",
                pesos(datos["por_cobrar"]),
                "Lo que te deben los pedidos confirmados: "
                + _plural(datos["pedidos_con_saldo"], "pedido con saldo", "pedidos con saldo"),
                filtro("saldo"),
            ),
            Cifra(
                "En producción",
                datos["en_produccion"],
                "Pedidos confirmados que no se han entregado: "
                f"{datos['por_confirmar']} por confirmar",
                filtro("produccion"),
            ),
        ]
    return [
        Cifra(
            "En producción",
            datos["en_produccion"],
            "Pedidos confirmados que no se han entregado",
            filtro("produccion"),
        ),
        Cifra(
            "Se entregan esta semana",
            datos["entregas_7_dias"],
            "Pedidos que se entregan en los próximos 7 días",
            filtro("semana"),
        ),
        Cifra(
            "Atrasados",
            datos["atrasados"],
            "Pasó la fecha de entrega" if datos["atrasados"] else "Todo va a tiempo",
            filtro("atrasados"),
            alerta=datos["atrasados"] > 0,
        ),
    ]


# --- Lo que hay que hacer hoy -------------------------------------------------------------------


@dataclass(frozen=True)
class FilaPendiente:
    """Un pedido de las tarjetas de hoy, con lo que dice y la acción que sigue.

    siguiente:
      - "listo": atrasado y sin terminar: "Marcar como listo" y "Avisar".
      - "entregar": listo: "Marcar como entregado" y "Avisar".
      - "confirmar": cotizado: "Confirmar pedido" y "Avisar" (preguntar si confirma).
      - "ver": se entrega pronto (o no le toca nada a quien mira): "Ver el pedido".
    mensaje: {"texto", "enlace"} para "Avisar". Sin WhatsApp guardado, el enlace es "" y el
    botón copia el texto.
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
    """La tarjeta y su acción. Con el `request` de una costurera (T21): sin saldo; las acciones
    que cambian la etapa solo si es la encargada; y sin "Avisar" de un listo ni de un cotizado,
    porque esos mensajes dicen plata."""
    pedido = pendiente.pedido
    # Sin saber quién pregunta, no se muestra plata ni se deja mover (falla cerrado).
    con_plata = request is not None and puede_ver_plata(request)
    puede_mover = request is not None and puede_mover_etapa(request, pedido)
    if pedido.estado == Estado.LISTO:
        # Un listo atrasado sigue en el grupo de los atrasados, pero lo que sigue es entregarlo.
        siguiente = "entregar"
        mensaje = _mensaje(pedido, mensajes.texto_listo(pedido)) if con_plata else None
    elif pendiente.motivo == "atrasado":
        siguiente, mensaje = "listo", _mensaje(pedido, mensajes.texto_atraso(pedido))
    elif pendiente.motivo == "cotizado" and con_plata:
        siguiente, mensaje = "confirmar", _mensaje(pedido, mensajes.texto_confirmar(pedido))
    else:
        siguiente, mensaje = "ver", None
    if siguiente in ("entregar", "listo", "confirmar") and not puede_mover:
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


# --- La gráfica ---------------------------------------------------------------------------------


def grafica(taller, hoy):
    return {"meses": calculos.grafica_cobrado_y_gastado(taller, hoy)}


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
    """La insignia junto al número de una etapa: "1 atrasado" en rojo y, en Entregado, cuántos
    todavía deben, en naranja. Nada en verde. None si no hay nada que decir. Sin plata (la
    costurera), Entregado no dice si deben.
    """
    if etapa.atrasados:
        return Etiqueta(_plural(etapa.atrasados, "atrasado", "atrasados"), "rojo")
    if etapa.estado == Estado.ENTREGADO and etapa.con_saldo and con_plata:
        return Etiqueta(f"{etapa.con_saldo} con saldo", "naranja")
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


def saludo(ahora):
    """"¡Buenos días!" antes de las 12, "¡Buenas tardes!" antes de las 18, si no "¡Buenas noches!"."""
    if ahora.hour < 12:
        return "¡Buenos días!"
    if ahora.hour < 18:
        return "¡Buenas tardes!"
    return "¡Buenas noches!"


def frase_de_pendientes(cantidad):
    """"Tienes 3 cosas pendientes hoy", "Tienes 1 cosa pendiente hoy" o "No tienes nada..."."""
    if not cantidad:
        return "No tienes nada pendiente hoy"
    if cantidad == 1:
        return "Tienes 1 cosa pendiente hoy"
    return f"Tienes {cantidad} cosas pendientes hoy"


def contexto_de_hoy(request, hoy):
    """Todo lo que necesitan las partes de Hoy. Sin plata para la costurera (T21)."""
    taller = request.taller
    con_plata = puede_ver_plata(request)
    lista_pendientes = pendientes(taller, hoy, request)
    atrasados = calculos.cifras_de_hoy(taller, hoy)["atrasados"]
    contexto = {
        "hoy": hoy,
        "saludo": saludo(timezone.localtime()),
        "frase_pendientes": frase_de_pendientes(len(lista_pendientes)),
        "atrasados": atrasados,
        "frase_atrasados": _plural(atrasados, "pedido atrasado", "pedidos atrasados"),
        "mes": capfirst(str(MONTHS[hoy.month])),
        "titulo_cifras": "Tu mes" if con_plata else "El taller hoy",
        "cifras": cifras(taller, hoy, con_plata),
        "pendientes": lista_pendientes,
        "etapas": etapas(taller, hoy, con_plata),
    }
    if con_plata:
        lista_deudores = deudores(taller, hoy)
        contexto["deudores"] = lista_deudores
        contexto["total_por_cobrar"] = sum(f["deudor"].saldo for f in lista_deudores)
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
    """Marcar como listo, como entregado o confirmar un pedido desde las tarjetas de Hoy.

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
