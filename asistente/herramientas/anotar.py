"""Proponer un abono a un pedido o un gasto del taller (T40, carril B).

Reglas: docs/13-plan-tanda-8.md, secciones 1.1, 1.2 y 1.6. No guarda nada: arma un borrador
con `asistente.borradores` y la dueña lo guarda con un toque (`asistente.guardar`).

Cuatro reglas para todo el archivo:

1. Todo pedido sale de `Pedido.objects.del_taller(ctx.taller)`: uno de otro taller responde
   igual que uno que no existe ("No encontré ese pedido.").
2. Lo que ella mandó se revisa con el MISMO formulario de la pantalla (`FormularioAbono` de la
   tarjeta Pagos y `FormularioGasto` del Resumen del mes). Si la pantalla no lo deja, el
   agente tampoco, y Claude recibe el mismo mensaje para preguntarle o corregir.
3. Las cifras de la tarjeta son de la aplicación: el "Falta" sale de `calculos.saldo`.
4. Si hay dos o más pedidos posibles, no se arma borrador: se pregunta cuál (`opciones`).

La entrada llega ya revisada por `asistente.herramientas.ejecutar()`: el 0 y el "" de Claude
llegan como None y la fecha ya es `date`.
"""

from asistente import borradores
from asistente.contratos import Contexto, ErrorDeHerramienta, Fila, Resultado
from config.piezas import pesos
from finanzas.formularios import FormularioGasto
from finanzas.models import Gasto
from pedidos import calculos
from pedidos.cronologia import dia_y_mes
from pedidos.formularios.abonos import FormularioAbono
from pedidos.models import Abono, Pedido

NO_ENCONTRE_PEDIDO = "No encontré ese pedido."
SIN_SALDO_DEL_CLIENTE = "No encontré un pedido con saldo de ese cliente."
SIN_PEDIDO_NI_CLIENTE = (
    "No sé a qué pedido va el abono: no hay un pedido abierto en pantalla. Pregúntale a la "
    "dueña de qué cliente es, y vuelve a pedirlo con su nombre o con el id del pedido."
)


# --- Piezas comunes ---------------------------------------------------------------------------


def _pedidos(ctx):
    """Los pedidos del taller de quien pregunta, con abonado y saldo ya contados."""
    return calculos.con_cuentas(Pedido.objects.del_taller(ctx.taller)).select_related("cliente")


def _pedido_por_id(ctx, pedido_id):
    pedido = _pedidos(ctx).filter(pk=pedido_id).first()
    if pedido is None:
        raise ErrorDeHerramienta(NO_ENCONTRE_PEDIDO)
    return pedido


def _primer_error(form):
    for errores in form.errors.values():
        if errores:
            return errores[0]
    return "Revisa los datos."


def _texto(valor):
    """Lo que iría escrito en la caja de la pantalla: vacío si no hay nada."""
    return "" if valor is None else str(valor)


def _titulo(que, fecha, hoy):
    """'Abono de hoy' o 'Abono del 12 de noviembre'."""
    if fecha is None or fecha == hoy:
        return f"{que} de hoy"
    return f"{que} del {dia_y_mes(fecha)}"


# --- proponer_abono ---------------------------------------------------------------------------


def _con_saldo_del_cliente(ctx, cliente):
    """Los pedidos con saldo de los clientes cuyo nombre se parece a lo que dijo ella."""
    pedidos = _pedidos(ctx).filter(saldo__gt=0)
    parecidos = [p for p in pedidos if calculos.coincide(cliente, p.cliente.nombre)]
    return calculos.ordenar_pedidos(parecidos)


def _elegir_pedido(ctx, pedido_id, cliente):
    """El pedido del abono, o un Resultado de `opciones` si hay dos o más posibles."""
    if pedido_id is not None:
        return _pedido_por_id(ctx, pedido_id)
    cliente = (cliente or "").strip()
    actual = ctx.pedido_actual
    # El pedido de la pantalla, salvo que ella hable de otro cliente.
    if actual is not None and (not cliente or calculos.coincide(cliente, actual.cliente.nombre)):
        return _pedido_por_id(ctx, actual.pk)
    if not cliente:
        raise ErrorDeHerramienta(SIN_PEDIDO_NI_CLIENTE)
    posibles = _con_saldo_del_cliente(ctx, cliente)
    if not posibles:
        raise ErrorDeHerramienta(SIN_SALDO_DEL_CLIENTE)
    if len(posibles) == 1:
        return posibles[0]
    if len({p.cliente_id for p in posibles}) == 1:
        # Un solo cliente: el chip dice qué pidió ("40 uniformes de diario").
        opciones_ = [(p.pk, p.detalle) for p in posibles]
        revisado = f"Revisé los pedidos de {posibles[0].cliente.nombre}"
    else:
        opciones_ = [(p.pk, f"{p.cliente.nombre} · {p.detalle}") for p in posibles]
        revisado = f"Revisé los pedidos de los clientes parecidos a «{cliente}»"
    return borradores.opciones("pedido", opciones_, revisado)


def proponer_abono(ctx: Contexto, *, pedido_id, cliente, valor, fecha) -> Resultado:
    """El borrador de un abono a un pedido que ya existe, con lo que falta después."""
    pedido = _elegir_pedido(ctx, pedido_id, cliente)
    if isinstance(pedido, Resultado):
        return pedido

    form = FormularioAbono(
        data={"valor": _texto(valor), "fecha": fecha.isoformat() if fecha else ""},
        instance=Abono(pedido=pedido, registrado_por=ctx.usuaria),
    )
    if not form.is_valid():
        raise ErrorDeHerramienta(_primer_error(form))
    valor = form.cleaned_data["valor"]

    saldo = calculos.saldo(pedido)
    falta = max(0, saldo - valor)
    detalle = f"{pedido.cliente.nombre} · {pedido.detalle} · "
    detalle += f"Falta {pesos(falta)}" if falta else "Queda pagado"
    aviso = ""
    if valor > saldo:
        # La tarjeta Pagos lo deja guardar: el saldo queda en 0.
        aviso = (
            f"Es más de lo que debe ({pesos(saldo)}). Se guarda igual y el pedido queda pagado."
            if saldo
            else "Este pedido ya está pagado. Se guarda igual."
        )

    accion = {
        "tipo": "abono",
        "datos": {
            "pedido": pedido.pk,
            "valor": valor,
            "fecha": fecha.isoformat() if fecha else None,
        },
    }
    fila = Fila(_titulo("Abono", fecha, ctx.hoy), detalle, valor, aviso)
    return borradores.resultado(ctx, [accion], [fila], f"Revisé el pedido de {pedido.detalle}")


# --- proponer_gasto ---------------------------------------------------------------------------


def proponer_gasto(ctx: Contexto, *, concepto, categoria, valor, fecha, pedido_id) -> Resultado:
    """El borrador de un gasto del taller, con su pedido si ella lo dijo."""
    pedido = _pedido_por_id(ctx, pedido_id) if pedido_id is not None else None

    form = FormularioGasto(
        data={
            "concepto": _texto(concepto),
            "categoria": _texto(categoria),
            "valor": _texto(valor),
            "fecha": fecha.isoformat() if fecha else "",
        },
        instance=Gasto(taller=ctx.taller, pedido=pedido),
    )
    if not form.is_valid():
        raise ErrorDeHerramienta(_primer_error(form))
    limpio = form.cleaned_data

    detalle = f"{limpio['concepto']} · {Gasto.Categoria(limpio['categoria']).label}"
    if pedido is not None:
        detalle += f" · Pedido: {pedido.detalle}"
    accion = {
        "tipo": "gasto",
        "datos": {
            "concepto": limpio["concepto"],
            "categoria": limpio["categoria"],
            "valor": limpio["valor"],
            "fecha": fecha.isoformat() if fecha else None,
            "pedido": pedido.pk if pedido is not None else None,
        },
    }
    fila = Fila(_titulo("Gasto", fecha, ctx.hoy), detalle, limpio["valor"])
    return borradores.resultado(ctx, [accion], [fila], "Preparé el gasto")
