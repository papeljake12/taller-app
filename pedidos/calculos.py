"""Todas las cuentas de la aplicación, en un solo lugar.

Las reglas salen de "Cálculos" en docs/02-modelo-de-datos.md y deben dar lo mismo que la
demo. Las pantallas no hacen cuentas por su lado: llaman a estas funciones.

Tres reglas para todo el archivo:

1. La plata va en enteros de pesos. Nada de float.
2. El saldo no se guarda: siempre es total menos abonos, y nunca baja de 0.
3. Las funciones que dependen de la fecha reciben `hoy`. Si no se pasa, es la fecha de hoy
   en Bogotá. Así las pruebas pueden fijar el día.

Las consultas reciben el taller (`request.taller`) y solo miran sus datos.

Este archivo es compartido: después de la tanda 2 solo lo cambia el coordinador.
"""

import calendar
import unicodedata
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from decimal import ROUND_CEILING, ROUND_HALF_UP, Decimal

from django.db.models import (
    Count,
    ExpressionWrapper,
    F,
    IntegerField,
    OuterRef,
    Q,
    Subquery,
    Sum,
    Value,
)
from django.db.models.functions import Coalesce, Greatest
from django.utils import timezone

from finanzas.models import Gasto
from pedidos.models import Abono, Cliente, Pedido, Talla
from telas.models import Tela

Estado = Pedido.Estado

# "Pronto": la entrega cae entre hoy y estos días más.
DIAS_PRONTO = 7

# Fechas de dotación en Colombia (mes, día): artículos 230 y 232 del Código Sustantivo
# del Trabajo.
FECHAS_DOTACION = ((4, 30), (8, 31), (12, 20))

# Máximo de fotos en "Trabajos del taller".
MAXIMO_FOTOS = 8


def porcentaje(parte, todo):
    """De 0 a 100, redondeado al entero más cercano (como las barras del diseño)."""
    if todo <= 0:
        return 0
    return int((Decimal(parte) * 100 / Decimal(todo)).quantize(Decimal("1"), rounding=ROUND_HALF_UP))


def _hoy(hoy=None):
    return hoy or timezone.localdate()


def _pedidos(taller):
    return Pedido.objects.del_taller(taller)


# --- Texto: buscar sin importar tildes ni mayúsculas ----------------------------------------


def sin_tildes(texto):
    """'Ferretería' -> 'ferreteria'. Para comparar lo que se busca con lo guardado."""
    descompuesto = unicodedata.normalize("NFD", str(texto or "").lower())
    return "".join(c for c in descompuesto if not unicodedata.combining(c))


def coincide(busqueda, *partes):
    """True si lo buscado aparece en alguna de las partes. Una búsqueda vacía coincide."""
    buscado = sin_tildes(busqueda).strip()
    return not buscado or buscado in sin_tildes(" ".join(str(p or "") for p in partes))


# --- Un pedido: abonado, saldo y fechas -----------------------------------------------------


def con_cuentas(pedidos):
    """Agrega a cada pedido `abonado`, `saldo` y `num_tallas`, en la misma consulta.

    Úsese en toda lista de pedidos: así no se hace una consulta por pedido.
    """
    suma_abonos = (
        Abono.objects.filter(pedido=OuterRef("pk"))
        .values("pedido")
        .annotate(suma=Sum("valor"))
        .values("suma")
    )
    cuenta_tallas = (
        Talla.objects.filter(pedido=OuterRef("pk"))
        .values("pedido")
        .annotate(n=Count("pk"))
        .values("n")
    )
    entero = IntegerField()
    return pedidos.annotate(
        abonado=Coalesce(Subquery(suma_abonos, output_field=entero), Value(0), output_field=entero),
        num_tallas=Coalesce(Subquery(cuenta_tallas, output_field=entero), Value(0),
                            output_field=entero),
    ).annotate(
        saldo=Greatest(
            ExpressionWrapper(F("total") - F("abonado"), output_field=entero),
            Value(0),
            output_field=entero,
        )
    )


def abonado(pedido):
    """Suma de los abonos del pedido."""
    if "abonado" in pedido.__dict__:
        return pedido.__dict__["abonado"]
    return pedido.abonos.aggregate(suma=Sum("valor"))["suma"] or 0


def saldo(pedido):
    """Total menos abonado, nunca menor que 0."""
    if "saldo" in pedido.__dict__:
        return pedido.__dict__["saldo"]
    return max(0, pedido.total - abonado(pedido))


def porcentaje_pagado(pedido):
    """De 0 a 100, para la barra de pagos."""
    if pedido.total <= 0:
        return 100
    return min(100, abonado(pedido) * 100 // pedido.total)


def esta_en_produccion(pedido):
    """Ni cotizado ni entregado."""
    return pedido.estado not in (Estado.COTIZADO, Estado.ENTREGADO)


def dias_para_entrega(pedido, hoy=None):
    """Días que faltan para la entrega. Negativo si ya pasó."""
    return (pedido.fecha_entrega - _hoy(hoy)).days


def esta_atrasado(pedido, hoy=None):
    """En producción y con la fecha de entrega antes de hoy."""
    return esta_en_produccion(pedido) and dias_para_entrega(pedido, hoy) < 0


def esta_pronto(pedido, hoy=None):
    """En producción y con entrega entre hoy y 7 días."""
    return esta_en_produccion(pedido) and 0 <= dias_para_entrega(pedido, hoy) <= DIAS_PRONTO


# --- Etiquetas (texto y tono de docs/08-diseno.md) ------------------------------------------


@dataclass(frozen=True)
class Etiqueta:
    texto: str
    tono: str  # rojo, verde, ambar, azul o gris


TONO_ETAPA = {
    Estado.COTIZADO: "gris",
    Estado.CONFIRMADO: "gris",
    Estado.CORTE: "azul",
    Estado.CONFECCION: "azul",
    Estado.LISTO: "gris",
    Estado.ENTREGADO: "verde",
}


def etiqueta_etapa(pedido):
    """'En confección' en azul, 'Entregado' en verde, etc."""
    estado = Estado(pedido.estado)
    return Etiqueta(estado.label, TONO_ETAPA[estado])


def etiqueta_urgencia(pedido, hoy=None):
    """'Atrasado 2 días' (rojo) o 'Faltan 3 días' (ámbar). None si no hay urgencia."""
    dias = dias_para_entrega(pedido, hoy)
    if esta_atrasado(pedido, hoy):
        atraso = -dias
        return Etiqueta(f"Atrasado {atraso} {'día' if atraso == 1 else 'días'}", "rojo")
    if esta_pronto(pedido, hoy):
        if dias == 0:
            return Etiqueta("Se entrega hoy", "ambar")
        if dias == 1:
            return Etiqueta("Se entrega mañana", "ambar")
        return Etiqueta(f"Faltan {dias} días", "ambar")
    return None


def etiqueta_entrega(pedido, hoy=None):
    """La etiqueta de la entrega, como tagUrgencia de la demo:

    atrasado (rojo) o pronto (ámbar); si no, "Entregado" (verde) o "Por confirmar" (ámbar,
    para los cotizados). None si el pedido va en producción sin afán.
    """
    urgencia = etiqueta_urgencia(pedido, hoy)
    if urgencia:
        return urgencia
    if pedido.estado == Estado.ENTREGADO:
        return Etiqueta("Entregado", "verde")
    if pedido.estado == Estado.COTIZADO:
        return Etiqueta("Por confirmar", "ambar")
    return None


# --- Listas de pedidos: filtros, conteos y orden --------------------------------------------


def pedidos_en_produccion(pedidos):
    return pedidos.exclude(estado__in=(Estado.COTIZADO, Estado.ENTREGADO))


def pedidos_atrasados(pedidos, hoy=None):
    return pedidos_en_produccion(pedidos).filter(fecha_entrega__lt=_hoy(hoy))


def pedidos_prontos(pedidos, hoy=None):
    hoy = _hoy(hoy)
    return pedidos_en_produccion(pedidos).filter(
        fecha_entrega__gte=hoy, fecha_entrega__lte=hoy + timedelta(days=DIAS_PRONTO)
    )


def pedidos_con_saldo(pedidos):
    """No cotizados y con saldo mayor que 0."""
    return con_cuentas(pedidos).exclude(estado=Estado.COTIZADO).filter(saldo__gt=0)


def pedidos_entregados(pedidos):
    return pedidos.filter(estado=Estado.ENTREGADO)


# Los filtros de la pantalla Pedidos, en orden: (clave, nombre).
FILTROS = (
    ("todos", "Todos"),
    ("produccion", "En producción"),
    ("semana", "Esta semana"),
    ("atrasados", "Atrasados"),
    ("saldo", "Con saldo"),
    ("entregados", "Entregados"),
)


def filtrar_pedidos(pedidos, filtro, hoy=None):
    """La consulta de un filtro de la pantalla Pedidos. Un filtro desconocido es 'todos'."""
    if filtro == "produccion":
        return pedidos_en_produccion(pedidos)
    if filtro == "semana":
        return pedidos_prontos(pedidos, hoy)
    if filtro == "atrasados":
        return pedidos_atrasados(pedidos, hoy)
    if filtro == "saldo":
        return pedidos_con_saldo(pedidos)
    if filtro == "entregados":
        return pedidos_entregados(pedidos)
    return pedidos


def conteo_de_filtros(pedidos, hoy=None):
    """[(clave, nombre, cantidad), ...] para los botones de filtro."""
    return [(clave, nombre, filtrar_pedidos(pedidos, clave, hoy).count()) for clave, nombre in FILTROS]


def ordenar_pedidos(pedidos):
    """Por fecha de entrega, con los entregados al final (el más reciente primero)."""
    pendientes = sorted(
        (p for p in pedidos if p.estado != Estado.ENTREGADO), key=lambda p: (p.fecha_entrega, p.pk)
    )
    entregados = sorted(
        (p for p in pedidos if p.estado == Estado.ENTREGADO),
        key=lambda p: (p.fecha_entrega, p.pk),
        reverse=True,
    )
    return pendientes + entregados


# --- Pantalla Hoy ----------------------------------------------------------------------------


def cifras_de_hoy(taller, hoy=None):
    """Las cuatro cifras de arriba de Hoy, con su línea de apoyo."""
    hoy = _hoy(hoy)
    pedidos = _pedidos(taller)
    prontos = pedidos_prontos(pedidos, hoy).order_by("fecha_entrega")
    mas_cercana = prontos.first()
    con_saldo = pedidos_con_saldo(pedidos)
    return {
        "en_produccion": pedidos_en_produccion(pedidos).count(),
        "por_confirmar": pedidos.filter(estado=Estado.COTIZADO).count(),
        "entregas_7_dias": prontos.count(),
        "dias_mas_cercana": dias_para_entrega(mas_cercana, hoy) if mas_cercana else None,
        "atrasados": pedidos_atrasados(pedidos, hoy).count(),
        "por_cobrar": por_cobrar(taller),
        "pedidos_con_saldo": con_saldo.count(),
    }


def por_cobrar(taller):
    """Suma de los saldos de los pedidos que no están en cotizado."""
    pedidos = con_cuentas(_pedidos(taller)).exclude(estado=Estado.COTIZADO)
    return pedidos.aggregate(suma=Sum("saldo"))["suma"] or 0


@dataclass(frozen=True)
class Pendiente:
    pedido: Pedido
    motivo: str  # atrasado, listo, pronto o cotizado


def que_hacer_hoy(taller, hoy=None):
    """Atrasados, luego listos, luego entregas en 7 días, luego cotizados.

    Cada pedido aparece una sola vez, en el primer grupo que le corresponda.
    """
    hoy = _hoy(hoy)
    pedidos = con_cuentas(_pedidos(taller)).select_related("cliente", "encargada")
    grupos = (
        ("atrasado", pedidos_atrasados(pedidos, hoy)),
        ("listo", pedidos.filter(estado=Estado.LISTO)),
        ("pronto", pedidos_prontos(pedidos, hoy)),
        ("cotizado", pedidos.filter(estado=Estado.COTIZADO)),
    )
    vistos = set()
    pendientes = []
    for motivo, consulta in grupos:
        for pedido in consulta.order_by("fecha_entrega", "pk"):
            if pedido.pk not in vistos:
                vistos.add(pedido.pk)
                pendientes.append(Pendiente(pedido, motivo))
    return pendientes


def trabajos_del_taller(taller):
    """Los pedidos con foto, del más reciente al más antiguo, máximo 8."""
    return _pedidos(taller).exclude(foto="").order_by("-creado", "-pk")[:MAXIMO_FOTOS]


@dataclass(frozen=True)
class Deudor:
    cliente: Cliente
    saldo: int
    atrasado: bool  # True si tiene al menos un pedido atrasado: va en rojo
    porcentaje: int  # largo de la barra, de 0 a 100, respecto al que más debe


def quien_te_debe(taller, hoy=None):
    """Clientes con saldo (de pedidos no cotizados), del que más debe al que menos."""
    hoy = _hoy(hoy)
    pedidos = con_cuentas(_pedidos(taller)).exclude(estado=Estado.COTIZADO).select_related(
        "cliente"
    )
    por_cliente = {}
    for pedido in pedidos:
        cuenta = por_cliente.setdefault(pedido.cliente_id, [pedido.cliente, 0, False])
        cuenta[1] += pedido.saldo
        cuenta[2] = cuenta[2] or esta_atrasado(pedido, hoy)
    deudas = sorted(
        (c for c in por_cliente.values() if c[1] > 0), key=lambda c: (-c[1], c[0].nombre)
    )
    mayor = deudas[0][1] if deudas else 1
    return [
        Deudor(cliente, debe, atraso, porcentaje(debe, mayor)) for cliente, debe, atraso in deudas
    ]


@dataclass(frozen=True)
class Etapa:
    estado: str
    nombre: str
    cantidad: int
    atrasados: int
    con_saldo: int


def pedidos_por_etapa(taller, hoy=None):
    """Cuántos pedidos hay en cada etapa, cuántos van atrasados y cuántos deben plata."""
    hoy = _hoy(hoy)
    pedidos = con_cuentas(_pedidos(taller))
    cantidades = dict(pedidos.values_list("estado").annotate(n=Count("pk")))
    atrasados = dict(pedidos_atrasados(pedidos, hoy).values_list("estado").annotate(n=Count("pk")))
    deben = dict(
        pedidos.exclude(estado=Estado.COTIZADO)
        .filter(saldo__gt=0)
        .values_list("estado")
        .annotate(n=Count("pk"))
    )
    return [
        Etapa(estado, nombre, cantidades.get(estado, 0), atrasados.get(estado, 0),
              deben.get(estado, 0))
        for estado, nombre in Estado.choices
    ]


# --- Plata por mes: Hoy, Resumen y la gráfica ------------------------------------------------


def sumar_meses(dia, meses):
    """El primer día del mes que queda `meses` después (o antes, si es negativo)."""
    total = dia.year * 12 + dia.month - 1 + meses
    return date(total // 12, total % 12 + 1, 1)


def _rango_del_mes(anio, mes):
    inicio = date(anio, mes, 1)
    return inicio, sumar_meses(inicio, 1)


def _creados_en(pedidos, anio, mes):
    """Pedidos creados en ese mes, contando el día en la hora de Bogotá."""
    inicio, fin = _rango_del_mes(anio, mes)
    zona = timezone.get_current_timezone()
    return pedidos.filter(
        creado__gte=timezone.make_aware(datetime(inicio.year, inicio.month, 1), zona),
        creado__lt=timezone.make_aware(datetime(fin.year, fin.month, 1), zona),
    )


def vendido_en(taller, anio, mes):
    """Suma del total de los pedidos no cotizados creados ese mes."""
    pedidos = _creados_en(_pedidos(taller).exclude(estado=Estado.COTIZADO), anio, mes)
    return pedidos.aggregate(suma=Sum("total"))["suma"] or 0


def cobrado_en(taller, anio, mes):
    """Suma de los abonos con fecha en ese mes."""
    inicio, fin = _rango_del_mes(anio, mes)
    abonos = Abono.objects.del_taller(taller).filter(fecha__gte=inicio, fecha__lt=fin)
    return abonos.aggregate(suma=Sum("valor"))["suma"] or 0


def gastado_en(taller, anio, mes):
    """Suma de los gastos con fecha en ese mes."""
    inicio, fin = _rango_del_mes(anio, mes)
    gastos = Gasto.objects.del_taller(taller).filter(fecha__gte=inicio, fecha__lt=fin)
    return gastos.aggregate(suma=Sum("valor"))["suma"] or 0


def resumen_del_mes(taller, anio, mes):
    """Vendido, cobrado, gastado y "te quedó" (cobrado menos gastado; puede ser negativo)."""
    cobrado = cobrado_en(taller, anio, mes)
    gastado = gastado_en(taller, anio, mes)
    return {
        "vendido": vendido_en(taller, anio, mes),
        "cobrado": cobrado,
        "gastado": gastado,
        "te_quedo": cobrado - gastado,
    }


@dataclass(frozen=True)
class MesDeGrafica:
    mes: date  # primer día del mes
    cobrado: int
    gastado: int


def grafica_cobrado_y_gastado(taller, hoy=None, meses=6):
    """Cobrado y gastado de los últimos `meses` meses, incluido el actual, del más viejo al
    más nuevo."""
    hoy = _hoy(hoy)
    resultado = []
    for atras in range(meses - 1, -1, -1):
        mes = sumar_meses(hoy, -atras)
        resultado.append(
            MesDeGrafica(
                mes, cobrado_en(taller, mes.year, mes.month), gastado_en(taller, mes.year, mes.month)
            )
        )
    return resultado


def ventas_por_tipo(taller, anio, mes):
    """[(nombre del tipo, total vendido), ...] del mes, de mayor a menor. Solo tipos con ventas."""
    pedidos = _creados_en(_pedidos(taller).exclude(estado=Estado.COTIZADO), anio, mes)
    filas = pedidos.values("cliente__tipo").annotate(suma=Sum("total")).order_by("-suma")
    nombres = dict(Cliente.Tipo.choices)
    return [(nombres[f["cliente__tipo"]], f["suma"]) for f in filas if f["suma"]]


def en_produccion_por_persona(taller):
    """[(nombre, cantidad), ...] de pedidos en producción por encargada, de más a menos.

    Los que no tienen encargada van al final como "Sin asignar".
    """
    pedidos = pedidos_en_produccion(_pedidos(taller)).select_related("encargada")
    cuentas = {}
    sin_asignar = 0
    for pedido in pedidos:
        if pedido.encargada is None:
            sin_asignar += 1
        else:
            nombre = pedido.encargada.nombre
            cuentas[nombre] = cuentas.get(nombre, 0) + 1
    filas = sorted(cuentas.items(), key=lambda fila: (-fila[1], fila[0]))
    if sin_asignar:
        filas.append(("Sin asignar", sin_asignar))
    return filas


# --- Tallas y materiales de un pedido --------------------------------------------------------


def tallas_por_talla(pedido):
    """[(talla, cantidad), ...] en el orden del tallaje, solo las que tienen alguien."""
    cuentas = dict(pedido.tallas.values_list("talla").annotate(n=Count("pk")))
    return [(talla, cuentas[talla]) for talla in pedido.opciones_de_talla if cuentas.get(talla)]


def tallas_recibidas(pedido):
    """(recibidas, esperadas): "14 de 18"."""
    recibidas = pedido.__dict__.get("num_tallas")
    if recibidas is None:
        recibidas = pedido.tallas.count()
    return recibidas, pedido.cantidad


def materiales_comprados(pedido):
    """(comprados, total): "2 de 4 comprados"."""
    materiales = pedido.materiales.all()
    return sum(1 for m in materiales if m.comprado), len(materiales)


# --- Clientes y dotación ---------------------------------------------------------------------


@dataclass(frozen=True)
class CuentaDeCliente:
    cliente: Cliente
    pedidos: int
    ha_comprado: int  # suma de los totales de sus pedidos no cotizados
    debe: int  # suma de los saldos de sus pedidos no cotizados
    cotizacion_abierta: bool  # tiene algún pedido en cotizado


def cuentas_de_clientes(taller):
    """Cada cliente con lo que ha comprado y lo que debe, del que más ha comprado al que menos."""
    pedidos = con_cuentas(_pedidos(taller))
    cuentas = {
        c.pk: [c, 0, 0, 0, False] for c in Cliente.objects.del_taller(taller)
    }
    for pedido in pedidos:
        cuenta = cuentas[pedido.cliente_id]
        cuenta[1] += 1
        if pedido.estado == Estado.COTIZADO:
            cuenta[4] = True
        else:
            cuenta[2] += pedido.total
            cuenta[3] += pedido.saldo
    filas = [CuentaDeCliente(*c) for c in cuentas.values()]
    return sorted(filas, key=lambda f: (-f.ha_comprado, sin_tildes(f.cliente.nombre)))


def clientes_empresa(taller):
    """Los clientes de tipo empresa: a ellos va el aviso de dotación."""
    return Cliente.objects.del_taller(taller).filter(tipo=Cliente.Tipo.EMPRESA)


def proxima_dotacion(hoy=None):
    """La próxima fecha de dotación: hoy mismo si cae hoy."""
    hoy = _hoy(hoy)
    for anio in (hoy.year, hoy.year + 1):
        for mes, dia in FECHAS_DOTACION:
            fecha = date(anio, mes, dia)
            if fecha >= hoy:
                return fecha
    raise AssertionError("Siempre hay una fecha de dotación en los próximos 12 meses.")


# --- Telas ------------------------------------------------------------------------------------


def tela_baja(tela):
    """Tiene mínimo y quedan esos metros o menos."""
    return tela.minimo > 0 and tela.metros <= tela.minimo


def telas_bajas(telas):
    return telas.filter(minimo__gt=0, metros__lte=F("minimo"))


def telas_en_orden(taller):
    """Las telas del taller: primero las que se están acabando, después por nombre."""
    telas = list(Tela.objects.del_taller(taller))
    return sorted(telas, key=lambda t: (not tela_baja(t), sin_tildes(t.nombre)))


def resumen_de_telas(taller):
    """Cuántas telas hay, cuántos metros suman y cuáles se están acabando."""
    telas = Tela.objects.del_taller(taller)
    return {
        "cantidad": telas.count(),
        "metros": telas.aggregate(suma=Sum("metros"))["suma"] or Decimal("0"),
        "bajas": list(telas_bajas(telas).order_by("nombre")),
    }


# --- Contadores del menú ----------------------------------------------------------------------


def contadores_del_menu(taller, hoy=None):
    """Pedidos atrasados y telas que se están acabando. 0 = no se muestra el contador."""
    return {
        "pedidos": pedidos_atrasados(_pedidos(taller), hoy).count(),
        "telas": telas_bajas(Tela.objects.del_taller(taller)).count(),
    }


# --- Calendario -------------------------------------------------------------------------------


def semanas_del_mes(anio, mes):
    """Las semanas que se ven en el calendario, de lunes a domingo, con los días de los
    meses vecinos para completar."""
    return calendar.Calendar(firstweekday=0).monthdatescalendar(anio, mes)


def entregas_del_mes(taller, anio, mes):
    """Pedidos con entrega en ese mes, por fecha."""
    inicio, fin = _rango_del_mes(anio, mes)
    return (
        _pedidos(taller)
        .filter(fecha_entrega__gte=inicio, fecha_entrega__lt=fin)
        .select_related("cliente")
        .order_by("fecha_entrega", "pk")
    )


@dataclass(frozen=True)
class SemanaCargada:
    lunes: date
    entregas: int
    personas: int


def semana_mas_cargada(taller, hoy=None):
    """La semana con más entregas pendientes (en producción, de hoy en adelante).

    Si empatan, gana la de más personas y luego la más cercana. None si no hay pendientes.
    """
    hoy = _hoy(hoy)
    pendientes = pedidos_en_produccion(_pedidos(taller)).filter(fecha_entrega__gte=hoy)
    semanas = {}
    for fecha, cantidad in pendientes.values_list("fecha_entrega", "cantidad"):
        lunes = fecha - timedelta(days=fecha.weekday())
        cuenta = semanas.setdefault(lunes, [0, 0])
        cuenta[0] += 1
        cuenta[1] += cantidad
    if not semanas:
        return None
    lunes, (entregas, personas) = min(
        semanas.items(), key=lambda s: (-s[1][0], -s[1][1], s[0])
    )
    return SemanaCargada(lunes, entregas, personas)


def proxima_entrega(taller, hoy=None):
    """El pedido en producción que se entrega primero, de hoy en adelante."""
    hoy = _hoy(hoy)
    return (
        pedidos_en_produccion(_pedidos(taller))
        .filter(fecha_entrega__gte=hoy)
        .select_related("cliente")
        .order_by("fecha_entrega", "pk")
        .first()
    )


# --- Cotizador --------------------------------------------------------------------------------


@dataclass(frozen=True)
class Cotizacion:
    tela: int  # costo de la tela de una prenda
    costo: int  # costo de hacer una
    precio_unidad: int  # redondeado hacia arriba a los 500 pesos
    total: int
    abono: int  # abono para empezar
    ganancia: int  # ganancia en todo el pedido
    metros_totales: Decimal


# Más que esto no es un dato del cotizador: se toma como vacío.
LIMITE_COTIZADOR = Decimal("1000000000")


def _numero(valor):
    """Un número positivo o 0, a partir de lo que llegue (texto con coma, None, etc.).

    Lo que no es un número ("abc", "nan", "inf"), lo negativo y lo absurdamente grande
    cuentan como 0.
    """
    try:
        numero = Decimal(str(valor if valor not in (None, "") else 0).replace(",", "."))
    except ArithmeticError:
        return Decimal("0")
    if not numero.is_finite() or numero <= 0 or numero > LIMITE_COTIZADOR:
        return Decimal("0")
    return numero


def _redondear(numero):
    return int(numero.quantize(Decimal("1"), rounding=ROUND_HALF_UP))


def cotizar(metros, precio_metro, insumos, mano_obra, extra, ganancia, cantidad, abono):
    """Las fórmulas del cotizador (docs/02-modelo-de-datos.md):

    costo por prenda = metros × precio del metro + insumos + mano de obra + extra
    precio por unidad = costo × (1 + ganancia % ÷ 100), hacia arriba a los 500 pesos
    total = precio por unidad × cantidad
    abono para empezar = total × porcentaje de abono ÷ 100 (máximo 100 %)
    """
    metros = _numero(metros)
    # Como la demo: se redondea hacia arriba a 500 el costo exacto (con centavos), y solo
    # para mostrar se redondean la tela y el costo al peso.
    tela = metros * _numero(precio_metro)
    costo = tela + _numero(insumos) + _numero(mano_obra) + _numero(extra)
    con_ganancia = costo * (1 + _numero(ganancia) / 100)
    precio = int((con_ganancia / 500).to_integral_value(rounding=ROUND_CEILING)) * 500
    unidades = int(_numero(cantidad))
    total = precio * unidades
    porcentaje_abono = min(Decimal("100"), _numero(abono))
    return Cotizacion(
        tela=_redondear(tela),
        costo=_redondear(costo),
        precio_unidad=precio,
        total=total,
        abono=_redondear(total * porcentaje_abono / 100),
        ganancia=_redondear((precio - costo) * unidades),
        metros_totales=(metros * unidades).quantize(Decimal("0.01")),
    )
