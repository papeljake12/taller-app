"""Cronología del pedido: lo que ha pasado, día por día, del más reciente al más antiguo.

No tiene modelo propio: arma los eventos con lo que el pedido ya guarda.
- El pedido creado (fecha de creación, quién lo creó y su valor).
- Cada abono (su fecha, su valor y quién lo registró). Es plata: solo la ve quien puede ver
  plata (la costurera no recibe ni los abonos ni el valor del pedido).
- Las tallas. Las que llegaron por el enlace del cliente se juntan por día ("12 personas
  enviaron su talla por el enlace", quién: "Enlace"); las agregadas a mano van una por una.

Todo sale del pedido que se pasa, que ya es del taller de la usuaria: otro taller no aparece.
"""

from dataclasses import dataclass, field

from django.template.loader import render_to_string
from django.utils import timezone

from pedidos.models import Talla

MESES = (
    "enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto", "septiembre",
    "octubre", "noviembre", "diciembre",
)


def dia_y_mes(fecha):
    """"7 de noviembre"."""
    return f"{fecha.day} de {MESES[fecha.month - 1]}"


def fecha_completa(fecha):
    """"5 de noviembre de 2026"."""
    return f"{dia_y_mes(fecha)} de {fecha.year}"


@dataclass
class Evento:
    """Una línea de la cronología. `valor` (en pesos) va entre `antes` y `despues`."""

    antes: str
    quien: str = ""
    valor: int | None = None
    despues: str = ""
    # Para ordenar los eventos de un mismo día: el más reciente primero.
    momento: object = field(default=None, repr=False)


@dataclass
class Dia:
    nombre: str
    eventos: list


def nombre_del_dia(dia, hoy):
    """"Hoy", "Ayer" o "7 de noviembre" (con el año si no es el de hoy)."""
    if dia == hoy:
        return "Hoy"
    if (hoy - dia).days == 1:
        return "Ayer"
    return dia_y_mes(dia) if dia.year == hoy.year else fecha_completa(dia)


def _quien(usuaria):
    return usuaria.nombre if usuaria is not None else ""


def _persona(cantidad):
    if cantidad == 1:
        return "1 persona envió su talla por el enlace."
    return f"{cantidad} personas enviaron su talla por el enlace."


def eventos_del_pedido(pedido, con_plata=True):
    """Los eventos del pedido como pares (día, Evento), sin ordenar."""
    eventos = []
    creado = timezone.localtime(pedido.creado)
    if con_plata:
        eventos.append(
            (creado.date(), Evento("Se creó el pedido por ", _quien(pedido.creado_por),
                                   pedido.total, ".", creado))
        )
        for abono in pedido.abonos.select_related("registrado_por"):
            momento = timezone.localtime(abono.creado)
            eventos.append(
                (abono.fecha, Evento("Se registró un abono de ", _quien(abono.registrado_por),
                                     abono.valor, ".", momento))
            )
    else:
        eventos.append(
            (creado.date(), Evento("Se creó el pedido.", _quien(pedido.creado_por), None, "", creado))
        )
    del_enlace = {}
    for talla in pedido.tallas.all():
        momento = timezone.localtime(talla.creado)
        if talla.origen == Talla.Origen.ENLACE:
            dia, cantidad, ultimo = del_enlace.get(momento.date(), (momento.date(), 0, momento))
            del_enlace[momento.date()] = (dia, cantidad + 1, max(ultimo, momento))
        else:
            eventos.append(
                (momento.date(), Evento(f"Se agregó a mano la talla de {talla.nombre}.", "", None, "", momento))
            )
    for dia, cantidad, ultimo in del_enlace.values():
        eventos.append((dia, Evento(_persona(cantidad), "Enlace", None, "", ultimo)))
    return eventos


def cronologia(pedido, con_plata=True, hoy=None):
    """La cronología agrupada por día: una lista de `Dia`, del más reciente al más antiguo."""
    hoy = hoy or timezone.localdate()
    por_dia = {}
    for dia, evento in eventos_del_pedido(pedido, con_plata):
        por_dia.setdefault(dia, []).append(evento)
    resultado = []
    for dia in sorted(por_dia, reverse=True):
        eventos = sorted(por_dia[dia], key=lambda e: e.momento, reverse=True)
        resultado.append(Dia(nombre_del_dia(dia, hoy), eventos))
    return resultado


def html_oob(request, pedido):
    """La tarjeta Cronología lista para mandarla con hx-swap-oob: así se actualiza sola
    cuando cambia un abono o una talla."""
    from cuentas.permisos import puede_ver_plata

    contexto = {
        "pedido": pedido,
        "cronologia": cronologia(pedido, puede_ver_plata(request)),
        "oob": True,
    }
    return render_to_string("pedidos/_cronologia.html", contexto, request=request)
