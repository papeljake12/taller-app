"""Proponer un pedido nuevo: cliente, pedido, abono que dejó y tela (T39, carril A).

Reglas: docs/13-plan-tanda-8.md, secciones 1.1, 1.2 y 1.6. No guarda nada: arma un borrador
con `asistente.borradores` y la dueña lo guarda con un toque (`asistente.guardar`).

- Cliente: el del id (si es del taller), el de nombre exacto (sin mirar mayúsculas, tildes ni
  espacios de más) o el único parecido. Con dos o más parecidos se pregunta cuál. Si no hay
  ninguno es cliente nuevo y hace falta su tipo.
- Total: el que dijo ella; si no, el del Cotizador con la prenda guardada y sus valores por
  defecto (los iniciales de FormularioCotizacion: 30 % de ganancia).
- Se valida con los formularios de la pantalla (NuevoPedidoForm y FormularioAbono), con los
  mismos datos que usa `guardar.guardar_pedido`: si la pantalla no lo deja, esto tampoco.
- Tela: la del inventario (exacta o el único parecido). Sin metros, salen de la prenda por la
  cantidad. Lo que falta sale de `calculos.falta_tela`.

A Claude solo van las filas en texto (sin la firma). Nunca el WhatsApp, el token de tallas ni
las notas del cliente.
"""

from decimal import Decimal, InvalidOperation

from asistente import borradores
from asistente.contratos import Contexto, ErrorDeHerramienta, Fila, Resultado
from asistente.guardar import _primer_error
from asistente.herramientas.cotizar import nombre_para_titulo
from config.piezas import dia_y_mes, pesos
from config.piezas import metros as texto_metros
from cotizador.formularios import CAMPOS_DEL_PRECIO, FormularioCotizacion
from cotizador.models import PrendaGuardada
from pedidos import calculos
from pedidos.formularios.abonos import FormularioAbono
from pedidos.formularios.lista import NuevoPedidoForm
from pedidos.models import Abono, Cliente, Pedido
from telas.models import Tela

# Cuántas opciones se muestran como mucho cuando hay varios parecidos.
TOPE_DE_OPCIONES = 10
# Cuántos nombres de prendas guardadas se le dicen a Claude si no encuentra la que pidió.
TOPE_DE_NOMBRES = 30
# Lo que cabe en TelaPedido.metros (8 cifras, 2 decimales).
METROS_MAXIMOS = Decimal("999999.99")
CENTESIMOS = Decimal("0.01")

TIPOS_DE_CLIENTE = "comparsa, empresa, colegio o particular"


# --- Buscar por nombre ------------------------------------------------------------------------


def _normal(texto):
    """Para comparar nombres: sin tildes, sin mayúsculas y sin espacios de más."""
    return " ".join(calculos.sin_tildes(texto).split())


def _buscar(objetos, nombre):
    """(el que es, []) o (None, [parecidos]). La lista vacía es que no hay ninguno.

    Gana el de nombre exacto; si no, los que contienen lo escrito (calculos.coincide).
    """
    buscado = _normal(nombre)
    if not buscado:
        return None, []
    exactos = [o for o in objetos if _normal(o.nombre) == buscado]
    if exactos:
        return exactos[0], []
    parecidos = [o for o in objetos if calculos.coincide(buscado, o.nombre)]
    if len(parecidos) == 1:
        return parecidos[0], []
    return None, parecidos


def _opciones(que, parecidos, revisado):
    return borradores.opciones(
        que, [(o.pk, o.nombre) for o in parecidos[:TOPE_DE_OPCIONES]], revisado
    )


# --- Cada parte del pedido --------------------------------------------------------------------


def _cliente(ctx, cliente, cliente_id, tipo_cliente):
    """(Cliente o None si es nuevo, nombre, tipo), o un Resultado con las opciones."""
    clientes = Cliente.objects.del_taller(ctx.taller)
    if cliente_id is not None:
        elegido = clientes.filter(pk=cliente_id).first()
        if elegido is None:
            raise ErrorDeHerramienta("No encontré ese cliente.")
        return elegido, elegido.nombre, elegido.tipo
    nombre = " ".join((cliente or "").split())
    elegido, parecidos = _buscar(list(clientes.order_by("nombre", "pk")), nombre)
    if elegido is not None:
        return elegido, elegido.nombre, elegido.tipo
    if parecidos:
        return _opciones("cliente", parecidos, f"Busqué «{nombre}» en tus clientes")
    if nombre and not tipo_cliente:
        raise ErrorDeHerramienta(
            f"«{nombre}» es un cliente nuevo: pregúntale qué tipo de cliente es "
            f"({TIPOS_DE_CLIENTE})."
        )
    # Sin nombre, el formulario de la pantalla dice "Escribe el nombre del cliente."
    return None, nombre, tipo_cliente or ""


def _prenda(ctx, prenda):
    """La prenda guardada en el Cotizador, o un Resultado con las opciones."""
    guardadas = list(PrendaGuardada.objects.del_taller(ctx.taller).order_by("nombre", "pk"))
    nombre = " ".join(prenda.split())
    elegida, parecidas = _buscar(guardadas, nombre)
    if elegida is not None:
        return elegida
    if parecidas:
        return _opciones("prenda", parecidas, f"Busqué «{nombre}» en tus prendas guardadas")
    if not guardadas:
        raise ErrorDeHerramienta(
            "No hay prendas guardadas en el Cotizador: pregúntale cuánto cobra por todo el "
            "pedido."
        )
    nombres = ", ".join(p.nombre for p in guardadas[:TOPE_DE_NOMBRES])
    raise ErrorDeHerramienta(
        f"No hay una prenda guardada que se llame «{nombre}». Las guardadas son: {nombres}."
    )


def _total_del_cotizador(prenda, cantidad):
    """El total que muestra el Cotizador con esa prenda, esa cantidad y sus valores por
    defecto (los iniciales de FormularioCotizacion: 30 % de ganancia y 50 % de abono)."""
    valores = {
        "metros": prenda.metros,
        "precio_metro": prenda.precio_metro,
        "insumos": prenda.insumos,
        "mano_obra": prenda.mano_obra,
        "extra": prenda.extra,
        "ganancia": FormularioCotizacion.base_fields["ganancia"].initial,
        "cantidad": cantidad,
        "abono": FormularioCotizacion.base_fields["abono"].initial,
    }
    cotizacion = calculos.cotizar(*(valores[campo] for campo in CAMPOS_DEL_PRECIO))
    if cotizacion.precio_unidad <= 0:
        raise ErrorDeHerramienta(
            f"La prenda guardada «{prenda.nombre}» no tiene costos en el Cotizador: pregúntale "
            "cuánto cobra por todo el pedido."
        )
    # Con una cantidad que la pantalla no acepta, el formulario lo dice después.
    return cotizacion.total


def _datos_del_formulario(datos):
    """Lo que se le pasa a NuevoPedidoForm: lo mismo que usa guardar.guardar_pedido."""
    return {
        "cliente": datos["cliente"],
        "tipo": datos["tipo"],
        "detalle": datos["detalle"],
        "cantidad": str(datos["cantidad"]),
        "tallaje": datos["tallaje"],
        "fecha_entrega": datos["fecha_entrega"],
        "total": str(datos["total"]),
        "whatsapp": "",
    }


def _abono_valido(ctx, abono):
    """El abono revisado con el formulario de la tarjeta Pagos."""
    form = FormularioAbono(
        data={"valor": str(abono), "fecha": ""},
        instance=Abono(registrado_por=ctx.usuaria, por_asistente=True),
    )
    if not form.is_valid():
        raise ErrorDeHerramienta(_primer_error(form))
    return form.cleaned_data["valor"]


def _tela(ctx, tela):
    """La tela del inventario, o un Resultado con las opciones."""
    telas = list(Tela.objects.del_taller(ctx.taller).order_by("nombre", "pk"))
    nombre = " ".join(tela.split())
    elegida, parecidas = _buscar(telas, nombre)
    if elegida is not None:
        return elegida
    if parecidas:
        return _opciones("tela", parecidas, f"Busqué «{nombre}» en tus telas")
    raise ErrorDeHerramienta("No encontré esa tela en Telas.")


def _leer_metros(texto, nombre_tela):
    """'66', '12.5' o '12,5' -> Decimal con dos decimales. Error si no es un número > 0."""
    try:
        numero = Decimal(texto.strip().replace(",", "."))
    except InvalidOperation:
        numero = None
    if numero is None or not numero.is_finite() or numero <= 0:
        raise ErrorDeHerramienta(
            f"Los metros de {nombre_tela} deben ser un número mayor que 0, por ejemplo 66 o 12.5."
        )
    if numero.as_tuple().exponent < -2:
        raise ErrorDeHerramienta("Los metros llevan máximo dos decimales, por ejemplo 12.25.")
    return numero.quantize(CENTESIMOS)


def _unidad(prenda):
    """'Uniforme de diario' -> 'uniforme', para decir "2,2 m por uniforme"."""
    palabras = nombre_para_titulo(prenda.nombre, 1).split()
    return palabras[0] if palabras and palabras[0].isalpha() else "prenda"


def _fecha(fecha, hoy):
    """'15 de diciembre'; con el año si no es el de hoy."""
    texto = dia_y_mes(fecha)
    return texto if fecha.year == hoy.year else f"{texto} de {fecha.year}"


def _revisado(prenda, tela):
    """'Revisé tus clientes, tu prenda «Uniforme de diario» y tus telas': solo lo que miró."""
    partes = ["tus clientes"]
    if prenda is not None:
        partes.append(f"tu prenda «{prenda.nombre}»")
    if tela is not None:
        partes.append("tus telas")
    if len(partes) == 1:
        return "Revisé tus clientes"
    return "Revisé " + ", ".join(partes[:-1]) + " y " + partes[-1]


def _fila_tela(ctx, tela, metros, prenda, cantidad):
    """(la fila "Tela", la acción tela_pedido)."""
    nombre_tela = nombre_para_titulo(tela.nombre, 1)  # "Dril azul" -> "dril azul"
    por_unidad = ""
    if metros is not None:
        necesita = _leer_metros(metros, nombre_tela)
    elif prenda is not None and prenda.metros > 0:
        necesita = (prenda.metros * cantidad).quantize(CENTESIMOS)
        por_unidad = f" ({texto_metros(prenda.metros)} por {_unidad(prenda)})"
    else:
        raise ErrorDeHerramienta(
            f"Faltan los metros de {nombre_tela}: pregúntale cuántos metros lleva todo el pedido."
        )
    if necesita > METROS_MAXIMOS:
        raise ErrorDeHerramienta("Revisa los metros: son demasiados para un pedido.")

    comprometida = calculos.tela_comprometida(ctx.taller)
    faltan = calculos.falta_tela(tela, necesita, comprometida)
    apartados = comprometida.get(tela.pk, Decimal("0"))
    tienes = f"Tienes {texto_metros(tela.metros)}"
    if apartados > 0:
        tienes += f", y {texto_metros(apartados)} ya están apartados para otros pedidos"
    fila = Fila(
        "Tela",
        f"{texto_metros(necesita)} de {nombre_tela}{por_unidad}. {tienes}.",
        None,
        f"Te faltan {texto_metros(faltan)} de {nombre_tela}." if faltan > 0 else "",
    )
    accion = {"tipo": "tela_pedido",
              "datos": {"pedido": "@0", "tela": tela.pk, "metros": str(necesita)}}
    return fila, accion


# --- La herramienta ---------------------------------------------------------------------------


def proponer_pedido(
    ctx: Contexto, *, cliente, cliente_id, tipo_cliente, detalle, cantidad, tallaje,
    fecha_entrega, prenda, total, abono, tela, metros,
) -> Resultado:
    # 1. El cliente.
    encontrado = _cliente(ctx, cliente, cliente_id, tipo_cliente)
    if isinstance(encontrado, Resultado):
        return encontrado
    cliente_existente, nombre_cliente, tipo = encontrado

    # 2. La prenda guardada (si la dijo).
    guardada = None
    if prenda:
        guardada = _prenda(ctx, prenda)
        if isinstance(guardada, Resultado):
            return guardada

    # 3. El total: el de ella o el del Cotizador.
    if total is None:
        if guardada is None:
            raise ErrorDeHerramienta(
                "Falta el total: pregúntale cuánto cobra o qué prenda guardada usar."
            )
        total = _total_del_cotizador(guardada, cantidad)

    # 4. Las reglas de la pantalla "Nuevo pedido", con los datos que se van a guardar.
    datos_pedido = {
        "cliente": nombre_cliente,
        "cliente_id": cliente_existente.pk if cliente_existente else None,
        "tipo": tipo,
        "detalle": detalle or "",
        "cantidad": cantidad,
        "tallaje": tallaje,
        "fecha_entrega": fecha_entrega.isoformat() if fecha_entrega else "",
        "total": total,
    }
    form = NuevoPedidoForm(data=_datos_del_formulario(datos_pedido))
    if not form.is_valid():
        raise ErrorDeHerramienta(_primer_error(form))
    limpio = form.cleaned_data
    datos_pedido.update(cliente=limpio["cliente"], detalle=limpio["detalle"],
                        total=limpio["total"])
    acciones = [{"tipo": "pedido", "datos": datos_pedido}]

    # 5. El abono que dejó: el pedido nace Confirmado (decisión 4 de David).
    if abono is not None:
        abono = _abono_valido(ctx, abono)
        acciones.append({"tipo": "etapa", "datos": {"pedido": "@0", "estado": "confirmado"}})
        acciones.append({"tipo": "abono",
                         "datos": {"pedido": "@0", "valor": abono, "fecha": None}})

    # 6. La tela del inventario.
    usada = fila_tela = None
    if tela:
        usada = _tela(ctx, tela)
        if isinstance(usada, Resultado):
            return usada
        fila_tela, accion = _fila_tela(ctx, usada, metros, guardada, limpio["cantidad"])
        acciones.append(accion)

    # 7. Las filas, como en diseno/asistente-agente.html.
    partes = [
        limpio["cliente"],
        limpio["detalle"],
        Pedido.Tallaje(limpio["tallaje"]).label,
        f"Se entrega el {_fecha(limpio['fecha_entrega'], ctx.hoy)}",
    ]
    if cliente_existente is None:
        partes.append("Cliente nuevo")
    if abono is not None:
        partes.append("Confirmado, porque dejó abono")
    filas = [Fila("Pedido nuevo", " · ".join(partes), limpio["total"])]
    if abono is not None:
        falta = max(0, limpio["total"] - abono)
        filas.append(Fila("Abono de hoy", f"Después del abono falta {pesos(falta)}", abono))
    if fila_tela is not None:
        filas.append(fila_tela)
    filas.append(Fila("Tallas", "El enlace para pedir las tallas queda listo al guardar."))

    return borradores.resultado(ctx, acciones, filas, _revisado(guardada, usada))
