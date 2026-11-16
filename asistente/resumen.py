"""El resumen de la mañana (T43, carril C): los puntos del día, el párrafo y lo que pinta Hoy.

Reglas: docs/13-plan-tanda-8.md, secciones 1.5 y 1.6, y docs/12-agente.md ("Avisa sin que le
pregunten").

- `puntos_del_dia(taller, hoy)`: lo que hay que contarle hoy. Todo sale de pedidos/calculos.py:
  entregas de hoy y de mañana, atrasados, deudas vencidas, telas que no alcanzan o se están
  acabando y pedidos que todavía esperan tallas.
- `escribir(taller, hoy, cliente)`: una sola llamada a Claude, sin herramientas, para escribir el
  párrafo a partir de los puntos. Toda cifra en pesos del párrafo tiene que estar en las cifras
  de algún punto; si no, no se guarda. Los tokens se anotan, pero no cuenta como pregunta. La
  llama la tarea de la madrugada (`manage.py preparar_resumen`).
- `para_hoy(request)`: lo que dibuja la tarjeta "Tu resumen de hoy" (asistente/_resumen_hoy.html).
  Las filas se calculan al abrir Hoy, así siempre están al día; el párrafo es el guardado.

Lo que va a Anthropic: la fecha y, de cada punto, el tipo, el cliente, el detalle del pedido, las
telas y las cifras. Nunca teléfonos, notas, nombres ni medidas de tallas, ni el token del enlace
de tallas: esos solo viven en los botones, que se arman en el servidor y van al navegador de ella.
"""

import json
import logging
import re
from dataclasses import dataclass
from datetime import timedelta
from urllib.parse import urljoin

import anthropic
from django.db import transaction
from django.db.models import Max
from django.urls import reverse
from django.utils import timezone
from django.utils.dates import WEEKDAYS

from asistente import uso
from asistente.contratos import Enlace
from asistente.disponibilidad import disponible
from config.piezas import dia_y_mes, fecha_larga, metros, pesos
from pedidos import calculos, mensajes
from pedidos.models import Abono, Pedido
from telas.models import Tela

registro = logging.getLogger("asistente")

Estado = Pedido.Estado

TIPOS = ("entrega", "atraso", "cobro", "tallas", "tela")
# Pedidos sin entregar que todavía pueden recibir tallas.
ESPERAN_TALLAS = (Estado.CONFIRMADO, Estado.CORTE, Estado.CONFECCION)

ESFUERZO = "medium"
PLAZO_SEGUNDOS = 45

INSTRUCCIONES_RESUMEN = """\
Eres el asistente de un taller de confección en Colombia. Cada madrugada le dejas a la dueña \
un resumen corto de su día, que ella lee al abrir la aplicación.

Te llega la fecha de hoy y una lista de puntos en JSON. Cada punto trae su tipo (entrega, \
atraso, cobro, tela o tallas), el cliente o el título, el pedido, un detalle y las cifras en \
pesos que puedes mencionar.

Cómo escribes
- Un solo párrafo corto, de dos a cinco frases, que empieza con "Buenos días."
- En español, con palabras sencillas y tuteando a la dueña: "Hoy entregas...", "Te debe...". \
Nunca la trates de "usted".
- Texto plano. Sin Markdown: nada de asteriscos, numerales (#), negrillas, listas ni viñetas. \
Sin emojis.
- Primero cuenta las entregas de hoy y de mañana y lo que va atrasado. Si no hay entregas hoy, \
dilo en pocas palabras. Después nombra lo demás: a quién cobrar, la tela que se está acabando \
y los pedidos que esperan tallas.
- Debajo de tu párrafo la aplicación muestra el cobro, la tela y las tallas, cada uno con su \
botón. No los copies uno por uno: nómbralos en una frase.
- La plata va en pesos colombianos, con el signo, un espacio y puntos de miles, sin \
decimales: $ 480.000. Usa solo las cifras que vienen en los puntos, tal cual. No sumes ni \
restes: no escribas ninguna cifra en pesos que no esté en los puntos.
- Las fechas van en palabras ("el lunes"), nunca con el formato AAAA-MM-DD.
- No inventes nada que no esté en los puntos. Sin despedidas.
- Contesta solo con el párrafo.
"""


@dataclass(frozen=True)
class PuntoDelDia:
    """Una cosa que el agente le cuenta en la mañana.

    `titulo` y `detalle` son lo que se ve en la fila ("Ferretería La Esquina" y "Debe $ 480.000.
    Su último abono fue hace 20 días."); `texto` los junta. `pedido` es el detalle del pedido, que
    solo va al párrafo. `cifras` son los pesos que el párrafo puede mencionar.
    """

    tipo: str  # entrega | atraso | cobro | tela | tallas
    titulo: str
    detalle: str
    etiqueta: dict | None = None  # {"texto", "color", "circulo"}: rojo solo atraso y vencida
    boton: Enlace | None = None  # "Cobrar", "Pedir tallas", "Ver telas" o "Ver pedido"
    cifras: tuple[int, ...] = ()
    pedido: str = ""

    @property
    def texto(self) -> str:
        return f"{self.titulo} · {self.detalle}"

    def para_claude(self) -> dict:
        """Lo único de este punto que va a Anthropic. Sin el botón, que lleva el teléfono y el
        token del enlace de tallas."""
        datos = {"tipo": self.tipo, "titulo": self.titulo}
        if self.pedido:
            datos["pedido"] = self.pedido
        datos["detalle"] = self.detalle
        datos["cifras"] = list(self.cifras)
        return datos


# --- Frases -----------------------------------------------------------------------------------


def _dias(numero):
    return "1 día" if numero == 1 else f"{numero} días"


def _dia_con_nombre(fecha):
    """"el lunes 9 de noviembre"."""
    return f"el {str(WEEKDAYS[fecha.weekday()]).lower()} {dia_y_mes(fecha)}"


def _etapa(pedido):
    """Cómo va el pedido, sin el nombre de la encargada (no va a Anthropic)."""
    if pedido.estado == Estado.LISTO:
        return "Ya está listo."
    if pedido.estado == Estado.CONFIRMADO:
        return "Está confirmado, todavía sin cortar."
    return f"Va {Estado(pedido.estado).label.lower()}."


def _sin_punto(texto):
    return texto.strip().rstrip(".")


def _juntar(partes):
    """"a", "a y b", "a, b y c"."""
    if len(partes) <= 1:
        return "".join(partes)
    return ", ".join(partes[:-1]) + " y " + partes[-1]


def _minuscula(texto):
    return texto[:1].lower() + texto[1:]


def hora(momento):
    """"5:00 a. m.", "12:30 p. m.", en la hora de Bogotá."""
    local = timezone.localtime(momento)
    doce = local.hour % 12 or 12
    return f"{doce}:{local.minute:02d} {'a. m.' if local.hour < 12 else 'p. m.'}"


# --- Los botones ------------------------------------------------------------------------------


def _ver_pedido(pedido):
    return Enlace("Ver pedido", reverse("pedidos:detalle", args=[pedido.pk]))


def _por_whatsapp(texto_boton, pedido, mensaje):
    """El botón que abre WhatsApp con el mensaje escrito. Sin número guardado, "Ver pedido"."""
    enlace = mensajes.enlace_whatsapp(pedido.cliente.whatsapp, mensaje)
    return Enlace(texto_boton, enlace) if enlace else _ver_pedido(pedido)


# --- Los puntos -------------------------------------------------------------------------------


def _pedidos(taller):
    return calculos.con_cuentas(Pedido.objects.del_taller(taller)).select_related(
        "cliente", "taller"
    )


def entregas(taller, hoy):
    """Los pedidos sin entregar que se entregan hoy o mañana."""
    manana = hoy + timedelta(days=1)
    consulta = calculos.pedidos_en_produccion(_pedidos(taller)).filter(
        fecha_entrega__in=(hoy, manana)
    )
    puntos = []
    for pedido in consulta.order_by("fecha_entrega", "pk"):
        es_hoy = pedido.fecha_entrega == hoy
        saldo = calculos.saldo(pedido)
        detalle = f"Se entrega {'hoy' if es_hoy else 'mañana'}. {_etapa(pedido)}"
        if saldo:
            detalle += f" Debe {pesos(saldo)}."
        puntos.append(
            PuntoDelDia(
                tipo="entrega",
                titulo=pedido.cliente.nombre,
                pedido=_sin_punto(pedido.detalle),
                detalle=detalle,
                etiqueta={"texto": "Hoy" if es_hoy else "Mañana", "color": "ambar",
                          "circulo": "vacio"},
                boton=_ver_pedido(pedido),
                cifras=(saldo,) if saldo else (),
            )
        )
    return puntos


def atrasos(taller, hoy):
    """Los pedidos sin entregar a los que ya se les pasó la fecha."""
    puntos = []
    for pedido in calculos.pedidos_atrasados(_pedidos(taller), hoy).order_by("fecha_entrega", "pk"):
        dias = -calculos.dias_para_entrega(pedido, hoy)
        saldo = calculos.saldo(pedido)
        detalle = f"Era para {_dia_con_nombre(pedido.fecha_entrega)}. {_etapa(pedido)}"
        if saldo:
            detalle += f" Debe {pesos(saldo)}."
        puntos.append(
            PuntoDelDia(
                tipo="atraso",
                titulo=pedido.cliente.nombre,
                pedido=_sin_punto(pedido.detalle),
                detalle=detalle,
                etiqueta={"texto": f"Atrasado {_dias(dias)}", "color": "rojo",
                          "circulo": "alerta"},
                boton=_ver_pedido(pedido),
                cifras=(saldo,) if saldo else (),
            )
        )
    return puntos


def cobros(taller, hoy):
    """Las deudas vencidas de "Quién te debe": los clientes con algún pedido atrasado."""
    puntos = []
    for deudor in calculos.quien_te_debe(taller, hoy):
        if not deudor.atrasado:
            continue
        cliente = deudor.cliente
        detalle = f"Debe {pesos(deudor.saldo)}."
        ultimo = (
            Abono.objects.del_taller(taller)
            .filter(pedido__cliente=cliente)
            .aggregate(fecha=Max("fecha"))["fecha"]
        )
        if ultimo is not None:
            hace = (hoy - ultimo).days
            cuando = "hoy" if hace <= 0 else f"hace {_dias(hace)}"
            detalle += f" Su último abono fue {cuando}."
        # El mensaje de cobro es de un pedido: el suyo con saldo de fecha más vieja (el
        # atrasado, casi siempre).
        pedido = (
            calculos.pedidos_con_saldo(Pedido.objects.del_taller(taller))
            .select_related("cliente", "taller")
            .filter(cliente=cliente)
            .order_by("fecha_entrega", "pk")
            .first()
        )
        puntos.append(
            PuntoDelDia(
                tipo="cobro",
                titulo=cliente.nombre,
                pedido=_sin_punto(pedido.detalle) if pedido else "",
                detalle=detalle,
                etiqueta={"texto": "Vencida", "color": "rojo", "circulo": ""},
                boton=_por_whatsapp("Cobrar", pedido, mensajes.texto_cobro(pedido))
                if pedido
                else None,
                cifras=(deudor.saldo,),
            )
        )
    return puntos


def telas(taller, hoy=None):
    """Una sola fila con las telas que no alcanzan para lo apartado y las que se están acabando."""
    partes_, vistas = [], set()
    for fila in calculos.telas_que_no_alcanzan(taller):
        vistas.add(fila.tela.pk)
        partes_.append(f"{fila.tela.nombre} (faltan {metros(fila.faltan)})")
    bajas = calculos.telas_bajas(Tela.objects.del_taller(taller)).exclude(pk__in=vistas)
    for tela in bajas.order_by("metros", "nombre"):
        partes_.append(f"{tela.nombre} (quedan {metros(tela.metros)})")
    if not partes_:
        return []
    varias = len(partes_) > 1
    detalle = _juntar([partes_[0]] + [_minuscula(p) for p in partes_[1:]]) + "."
    return [
        PuntoDelDia(
            tipo="tela",
            titulo="Telas por acabarse" if varias else "Tela por acabarse",
            detalle=detalle,
            etiqueta={"texto": f"{len(partes_)} telas", "color": "ambar", "circulo": "vacio"}
            if varias
            else None,
            boton=Enlace("Ver telas", reverse("telas:inicio")),
        )
    ]


def tallas(taller, hoy=None, url_base=""):
    """Pedidos sin entregar con el enlace de tallas abierto y menos tallas que personas.

    `url_base` es el comienzo de la dirección pública ("https://.../"), para el enlace que va en
    el mensaje de WhatsApp.
    """
    consulta = _pedidos(taller).filter(estado__in=ESPERAN_TALLAS, tallas_abiertas=True)
    faltantes = []
    for pedido in consulta:
        recibidas, esperadas = calculos.tallas_recibidas(pedido)
        if recibidas < esperadas:
            faltantes.append((esperadas - recibidas, pedido))
    puntos = []
    # Primero los que esperan más tallas.
    for faltan, pedido in sorted(faltantes, key=lambda f: (-f[0], f[1].fecha_entrega, f[1].pk)):
        _, esperadas = calculos.tallas_recibidas(pedido)
        detalle = f"{'Falta' if faltan == 1 else 'Faltan'} {faltan} de {esperadas} tallas"
        if pedido.estado != Estado.CONFIRMADO:
            detalle += f", y ya está {Estado(pedido.estado).label.lower()}"
        direccion = urljoin(url_base, reverse("pedidos:publico_tallas", args=[pedido.token_tallas]))
        puntos.append(
            PuntoDelDia(
                tipo="tallas",
                titulo=pedido.cliente.nombre,
                pedido=_sin_punto(pedido.detalle),
                detalle=detalle + ".",
                boton=_por_whatsapp("Pedir tallas", pedido, mensajes.texto_pedir_tallas(pedido, direccion)),
            )
        )
    return puntos


def puntos_del_dia(taller, hoy, url_base=""):
    """Todo lo de hoy, en el orden en que lo cuenta el párrafo."""
    return (
        entregas(taller, hoy)
        + atrasos(taller, hoy)
        + cobros(taller, hoy)
        + tallas(taller, hoy, url_base)
        + telas(taller, hoy)
    )


# --- El párrafo -------------------------------------------------------------------------------


def mensaje_para_claude(hoy, puntos):
    """El mensaje `user`: la fecha y los puntos en JSON (sin botones)."""
    datos = {
        "hoy": f"{_minuscula(fecha_larga(hoy))} de {hoy.year}",
        "puntos": [p.para_claude() for p in puntos],
    }
    return "Escribe el resumen de hoy con estos puntos:\n" + json.dumps(
        datos, ensure_ascii=False, indent=1
    )


def _texto_de(contenido):
    textos = [b.get("text", "") for b in contenido if b.get("type") == "text"]
    # Un solo párrafo: los saltos de línea y los espacios de más se vuelven un espacio.
    return " ".join(" ".join(textos).split())


def escribir(taller, hoy, cliente):
    """Pide el párrafo a Claude y lo guarda como el `ResumenDelDia` de hoy (reemplaza el que haya).

    None si no hay nada que contar (no se llama), si la API falla, si la respuesta no terminó bien
    o si trae una cifra en pesos que no está en los puntos. El registro nunca lleva el texto.
    """
    # Aquí adentro: así Hoy (que importa este archivo) no carga todas las herramientas.
    from asistente.herramientas.mensajes import cifras_en_pesos
    from asistente.models import ResumenDelDia

    puntos = puntos_del_dia(taller, hoy)
    if not puntos:
        return None
    try:
        respuesta = cliente.enviar(
            sistema=[{"type": "text", "text": INSTRUCCIONES_RESUMEN}],
            herramientas=[],
            mensajes=[
                {
                    "role": "user",
                    "content": [{"type": "text", "text": mensaje_para_claude(hoy, puntos)}],
                }
            ],
            esfuerzo=ESFUERZO,
            plazo=PLAZO_SEGUNDOS,
        )
    except anthropic.APIError as error:
        registro.warning(
            "Resumen del día: taller %s, Claude no contestó (%s).", taller.pk, type(error).__name__
        )
        return None

    # Los tokens se pagan aunque el párrafo no sirva. No cuenta como pregunta.
    uso.anotar(taller, respuesta.uso, hoy=hoy)
    if respuesta.stop_reason != "end_turn":
        registro.warning(
            "Resumen del día: taller %s, la respuesta paró por %s; no se guardó.",
            taller.pk,
            respuesta.stop_reason or "nada",
        )
        return None
    texto = _texto_de(respuesta.contenido)
    if not texto:
        registro.warning("Resumen del día: taller %s, la respuesta vino vacía.", taller.pk)
        return None
    permitidas = {cifra for punto in puntos for cifra in punto.cifras}
    malas = [cifra for cifra in cifras_en_pesos(texto) if cifra not in permitidas]
    if malas:
        registro.warning(
            "Resumen del día: taller %s, el párrafo trae %s cifra(s) que no están en los puntos; "
            "no se guardó.",
            taller.pk,
            len(malas),
        )
        return None
    with transaction.atomic():
        ResumenDelDia.objects.del_taller(taller).filter(fecha=hoy).delete()
        resumen = ResumenDelDia.objects.create(taller=taller, fecha=hoy, texto=texto)
    registro.info(
        "Resumen del día: taller %s, guardado (%s puntos, modelo %s).",
        taller.pk,
        len(puntos),
        respuesta.modelo,
    )
    return resumen


# --- Lo que pinta Hoy -------------------------------------------------------------------------

# "$ 480.000" o "$480000": va dentro de <span class="dinero"> para que no se parta.
_DINERO = re.compile(r"(\$\s?\d{1,3}(?:\.\d{3})+(?!\d)|\$\s?\d+)")


def partes(texto):
    """El texto en pedazos, marcando la plata: [{"texto", "dinero"}]. La plantilla escapa todo."""
    return [
        {"texto": pedazo, "dinero": i % 2 == 1}
        for i, pedazo in enumerate(_DINERO.split(texto))
        if pedazo
    ]


def _boton(enlace):
    if enlace is None:
        return None
    externo = enlace.url.startswith("https://wa.me/")
    if externo:
        icono = "whatsapp"
    elif enlace.url == reverse("telas:inicio"):
        icono = "telas"
    else:
        icono = ""
    return {"texto": enlace.texto, "url": enlace.url, "icono": icono, "externo": externo}


def _fila(punto):
    return {
        "tipo": punto.tipo,
        "titulo": punto.titulo,
        "etiqueta": punto.etiqueta,
        "detalle": partes(punto.detalle),
        "boton": _boton(punto.boton),
    }


def para_hoy(request):
    """Lo que pinta la tarjeta "Tu resumen de hoy", o None si no sale.

    No sale si el asistente no está disponible para quien abrió Hoy (solo la dueña, con clave y
    con el asistente prendido en su taller), ni si no hay párrafo de hoy ni filas pendientes.
    Las filas son solo de cobros, tela y tallas: las entregas y los atrasos ya tienen sus cartas
    en "Lo que hay que hacer hoy" (docs/13-plan-tanda-8.md, sección 0, punto 9).
    """
    from asistente.models import ResumenDelDia

    if not disponible(request):
        return None
    taller = request.taller
    hoy = timezone.localdate()
    url_base = request.build_absolute_uri("/")
    puntos = cobros(taller, hoy) + tallas(taller, hoy, url_base) + telas(taller, hoy)
    guardado = ResumenDelDia.objects.del_taller(taller).filter(fecha=hoy).first()
    if guardado is None and not puntos:
        return None
    return {
        "hora": hora(guardado.creado) if guardado else "",
        "parrafo": partes(guardado.texto) if guardado else [],
        "filas": [_fila(p) for p in puntos],
    }
