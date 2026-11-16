"""Guardar un borrador cuando la dueña toca Guardar (tanda 8, docs/13-plan-tanda-8.md, 1.3).

Cada tipo de acción tiene su guardador, que vuelve a validar con el MISMO formulario de la
pantalla (los datos pudieron cambiar desde que se armó el borrador) y crea el registro con
`por_asistente=True`. Todo va en una transacción: si una acción falla, no se guarda nada.

- pedido: NuevoPedidoForm y crear_pedido (Pedidos > Nuevo pedido). El cliente se busca por
  nombre en el taller o se crea, como en la pantalla.
- etapa: EtapaForm y la regla puede_mover_etapa (pedido por dentro).
- abono: FormularioAbono (tarjeta Pagos del pedido).
- gasto: FormularioGasto (Resumen del mes).
- tela_pedido: la tela del pedido (TelaPedido), con su validación del modelo.

Nunca hay un guardador que borre. Archivo de la base (coordinador).
"""

from dataclasses import dataclass
from decimal import Decimal, InvalidOperation

from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.urls import reverse

from asistente.borradores import BorradorInvalido, es_referencia
from asistente.contratos import Contexto, Enlace
from config.piezas import metros as texto_metros
from config.piezas import pesos
from cuentas.permisos import puede_mover_etapa
from finanzas.formularios import FormularioGasto
from finanzas.models import Gasto
from pedidos.formularios.abonos import FormularioAbono
from pedidos.formularios.detalle import EtapaForm
from pedidos.formularios.lista import NuevoPedidoForm
from pedidos.models import Abono, Cliente, Pedido
from telas.models import Tela, TelaPedido


class NoSeGuardo(Exception):
    """Una acción no pasó las reglas de la pantalla. Su texto lo ve la dueña."""


@dataclass(frozen=True)
class Guardado:
    objeto: object
    enlace: Enlace | None  # "Ver el pedido"
    nota: str  # lo que se le cuenta a Claude en la siguiente pregunta


@dataclass(frozen=True)
class _Peticion:
    """Lo poco de una petición que usan las funciones de las pantallas (crear_pedido)."""

    taller: object
    user: object


def _primer_error(form):
    for errores in form.errors.values():
        if errores:
            return errores[0]
    return "Revisa los datos."


def _pedido(ctx, valor, creados):
    """El pedido de una acción: uno creado en este borrador ("@0") o un id del taller."""
    if es_referencia(valor):
        objeto = creados[int(valor[1:])]
        if not isinstance(objeto, Pedido):
            raise NoSeGuardo("El borrador está dañado.")
        return objeto
    pedido = Pedido.objects.del_taller(ctx.taller).filter(pk=valor).first()
    if pedido is None:
        raise NoSeGuardo("Ese pedido ya no existe.")
    return pedido


def _enlace_del_pedido(pedido):
    return Enlace("Ver el pedido", reverse("pedidos:detalle", args=[pedido.pk]))


def guardar_pedido(ctx, datos, creados):
    nombre = datos["cliente"]
    if datos.get("cliente_id"):
        cliente = Cliente.objects.del_taller(ctx.taller).filter(pk=datos["cliente_id"]).first()
        if cliente is None:
            raise NoSeGuardo("Ese cliente ya no existe.")
        nombre = cliente.nombre
    form = NuevoPedidoForm(
        data={
            "cliente": nombre,
            "tipo": datos["tipo"],
            "detalle": datos["detalle"],
            "cantidad": str(datos["cantidad"]),
            "tallaje": datos["tallaje"],
            "fecha_entrega": datos["fecha_entrega"],
            "total": str(datos["total"]),
            "whatsapp": "",
        }
    )
    if not form.is_valid():
        raise NoSeGuardo(_primer_error(form))
    from pedidos.vistas.lista import crear_pedido

    pedido = crear_pedido(_Peticion(ctx.taller, ctx.usuaria), form.cleaned_data)
    pedido.por_asistente = True
    pedido.save(update_fields=["por_asistente"])
    nota = (
        f"pedido {pedido.pk} ({pedido.cliente.nombre}, {pedido.detalle}, "
        f"total {pesos(pedido.total)})"
    )
    return Guardado(pedido, _enlace_del_pedido(pedido), nota)


def guardar_etapa(ctx, datos, creados):
    pedido = _pedido(ctx, datos["pedido"], creados)
    if not puede_mover_etapa(ctx.usuaria, pedido):
        raise NoSeGuardo("No puedes cambiar la etapa de ese pedido.")
    form = EtapaForm(data={"estado": datos["estado"]})
    if not form.is_valid():
        raise NoSeGuardo(_primer_error(form))
    pedido.estado = form.cleaned_data["estado"]
    pedido.save(update_fields=["estado", "actualizado"])
    return Guardado(
        pedido, _enlace_del_pedido(pedido),
        f"pedido {pedido.pk} pasó a {pedido.get_estado_display()}",
    )


def guardar_abono(ctx, datos, creados):
    pedido = _pedido(ctx, datos["pedido"], creados)
    form = FormularioAbono(
        data={"valor": str(datos["valor"]), "fecha": datos.get("fecha") or ""},
        instance=Abono(pedido=pedido, registrado_por=ctx.usuaria, por_asistente=True),
    )
    if not form.is_valid():
        raise NoSeGuardo(_primer_error(form))
    abono = form.save()
    return Guardado(
        abono, _enlace_del_pedido(pedido),
        f"abono de {pesos(abono.valor)} al pedido {pedido.pk}",
    )


def guardar_gasto(ctx, datos, creados):
    pedido = None
    if datos.get("pedido") is not None:
        pedido = _pedido(ctx, datos["pedido"], creados)
    form = FormularioGasto(
        data={
            "concepto": datos["concepto"],
            "categoria": datos["categoria"],
            "valor": str(datos["valor"]),
            "fecha": datos.get("fecha") or "",
        },
        instance=Gasto(taller=ctx.taller, pedido=pedido, por_asistente=True),
    )
    if not form.is_valid():
        raise NoSeGuardo(_primer_error(form))
    gasto = form.save()
    enlace = Enlace("Ver el resumen del mes", reverse("finanzas:resumen") + f"?mes={gasto.fecha:%Y-%m}")
    return Guardado(gasto, enlace, f"gasto de {pesos(gasto.valor)} ({gasto.concepto})")


def guardar_tela_pedido(ctx, datos, creados):
    pedido = _pedido(ctx, datos["pedido"], creados)
    tela = Tela.objects.del_taller(ctx.taller).filter(pk=datos["tela"]).first()
    if tela is None:
        raise NoSeGuardo("Esa tela ya no está en Telas.")
    try:
        metros = Decimal(str(datos["metros"]))
    except InvalidOperation:
        raise NoSeGuardo("Los metros de la tela no son válidos.") from None
    fila = TelaPedido(pedido=pedido, tela=tela, metros=metros)
    try:
        fila.full_clean()
    except ValidationError as error:
        raise NoSeGuardo(error.messages[0]) from None
    fila.save()
    return Guardado(
        fila, _enlace_del_pedido(pedido),
        f"{texto_metros(metros)} de {tela.nombre} en el pedido {pedido.pk}",
    )


GUARDADORES = {
    "pedido": guardar_pedido,
    "etapa": guardar_etapa,
    "abono": guardar_abono,
    "gasto": guardar_gasto,
    "tela_pedido": guardar_tela_pedido,
}


def guardar(ctx: Contexto, clave: str, acciones: list[dict]) -> list[Guardado]:
    """Guarda todas las acciones del borrador, o ninguna.

    Anota la clave del borrador en `BorradorUsado` dentro de la misma transacción: si dos
    toques llegan casi juntos, el segundo choca con la clave única y no guarda nada.
    Lanza NoSeGuardo (una regla de la pantalla) o BorradorInvalido("usado").
    """
    from asistente.models import BorradorUsado

    with transaction.atomic():
        try:
            with transaction.atomic():
                BorradorUsado.objects.create(taller=ctx.taller, clave=clave)
        except IntegrityError:
            raise BorradorInvalido("usado") from None
        creados, guardados = [], []
        for accion in acciones:
            guardado = GUARDADORES[accion["tipo"]](ctx, accion["datos"], creados)
            creados.append(guardado.objeto)
            guardados.append(guardado)
    return guardados
