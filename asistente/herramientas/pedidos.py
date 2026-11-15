"""Consultas de pedidos: buscar_pedidos, ver_pedido y entregas.

Carril A (T27). Firma de cada herramienta: `def nombre(ctx, **entrada) -> Resultado`.
Contratos y reglas de `Resultado.datos`: asistente/contratos.py y docs/11-plan-tanda-7.md
(secciones 1.1 y 1.2). La entrada llega ya revisada por `asistente.herramientas.ejecutar()`
(las fechas ya son `date`).

Tres reglas para todo el archivo:

1. Toda consulta arranca de `Pedido.objects.del_taller(ctx.taller)`: nunca se ve lo de otro
   taller, y un id ajeno responde igual que uno que no existe.
2. Las cifras (abonado, saldo, tallas, materiales, filtros y orden) salen de
   pedidos/calculos.py, las mismas de las pantallas. Aquí no se suma plata.
3. `datos` (lo que lee Claude) va sin teléfonos, sin notas, sin el token del enlace de
   tallas y sin nombres ni medidas de las tallas: de tallas, solo cuántas hay de cada una.

Aquí viven también las piezas que comparten las otras herramientas de consulta (plata.py y
catalogo.py): la forma de un pedido en `datos`, la de una insignia en una tarjeta y el tope de
filas de las tarjetas.
"""

from urllib.parse import urlencode

from django.urls import reverse

from asistente.contratos import Contexto, Enlace, ErrorDeHerramienta, Resultado, Tarjeta
from config.piezas import fecha_corta
from pedidos import calculos
from pedidos.models import Pedido

# Cuántos pedidos van a Claude como mucho; los demás solo se cuentan (`total`).
TOPE_PEDIDOS = 20
# Cuántas filas muestra una tarjeta dentro de la respuesta; las demás quedan en "y N más".
FILAS_DE_TARJETA = 6
# Lo más largo que puede pedir `entregas` (dos meses).
DIAS_DE_ENTREGAS = 62

NO_ENCONTRE_PEDIDO = "No encontré ese pedido."
SIN_PEDIDO_ABIERTO = (
    "No hay un pedido abierto en pantalla. Pregúntale a la dueña de cuál pedido habla, o "
    "búscalo con buscar_pedidos y usa su id."
)

# Lo que dice "Revisé..." y el enlace del final, según el filtro de buscar_pedidos.
REVISADO_POR_FILTRO = {
    "todos": "Revisé tus pedidos",
    "produccion": "Revisé tus pedidos en producción",
    "semana": "Revisé las entregas de los próximos 7 días",
    "atrasados": "Revisé tus pedidos atrasados",
    "saldo": "Revisé los pedidos con saldo",
    "entregados": "Revisé tus pedidos entregados",
    "cotizados": "Revisé tus pedidos cotizados",
}
ENLACE_POR_FILTRO = {
    "produccion": "Ver los pedidos en producción",
    "semana": "Ver los pedidos de esta semana",
    "atrasados": "Ver los pedidos atrasados",
    "saldo": "Ver los pedidos con saldo",
    "entregados": "Ver los pedidos entregados",
}
FILTROS_DE_LA_LISTA = {clave for clave, _ in calculos.FILTROS}


# --- Piezas comunes ---------------------------------------------------------------------------


def pedidos_del_taller(ctx):
    """Los pedidos del taller de quien pregunta, con abonado, saldo y tallas ya contados."""
    return calculos.con_cuentas(Pedido.objects.del_taller(ctx.taller)).select_related(
        "cliente", "encargada"
    )


def url_de_la_lista(filtro="todos", texto=""):
    """La pantalla Pedidos con su filtro y lo buscado (?filtro=...&q=...)."""
    parametros = {"filtro": filtro if filtro in FILTROS_DE_LA_LISTA else "todos"}
    if texto:
        parametros["q"] = texto
    return f"{reverse('pedidos:lista')}?{urlencode(parametros)}"


def insignia(etiqueta):
    """Una calculos.Etiqueta como diccionario, para guardarla en la tarjeta (va a la sesión)."""
    if etiqueta is None:
        return None
    return {"texto": etiqueta.texto, "tono": etiqueta.tono, "circulo": etiqueta.circulo}


def sobran(lista):
    """Cuántas filas no caben en la tarjeta: lo que dice "y N más"."""
    return max(0, len(lista) - FILAS_DE_TARJETA)


def pedido_en_datos(pedido, hoy):
    """Un pedido tal como lo lee Claude: sin teléfono, sin notas, sin token y sin tallas."""
    return {
        "id": pedido.pk,
        "cliente_id": pedido.cliente_id,
        "cliente": pedido.cliente.nombre,
        "detalle": pedido.detalle,
        "cantidad": pedido.cantidad,
        "fecha_entrega": pedido.fecha_entrega.isoformat(),
        "estado": pedido.get_estado_display(),
        "encargada": pedido.encargada.nombre if pedido.encargada else None,
        "dias_para_entrega": calculos.dias_para_entrega(pedido, hoy),
        "atrasado": calculos.esta_atrasado(pedido, hoy),
        "total": pedido.total,
        "abonado": calculos.abonado(pedido),
        "saldo": calculos.saldo(pedido),
    }


def lista_con_tope(pedidos, hoy):
    """{total, mostrados, pedidos}: hasta TOPE_PEDIDOS pedidos y cuántos son en total."""
    mostrados = pedidos[:TOPE_PEDIDOS]
    return {
        "total": len(pedidos),
        "mostrados": len(mostrados),
        "pedidos": [pedido_en_datos(p, hoy) for p in mostrados],
    }


def fila_de_tarjeta(pedido, hoy, con_saldo=False):
    """Una fila de las tarjetas de pedidos: cliente con su insignia, qué pidió y, a la
    derecha, la fecha de entrega o el saldo."""
    if con_saldo:
        etiqueta = calculos.etiqueta_pago(pedido, hoy)
    else:
        etiqueta = calculos.etiqueta_urgencia(pedido, hoy) or calculos.etiqueta_etapa(pedido)
    return {
        "cliente": pedido.cliente.nombre,
        "detalle": pedido.detalle,
        "fecha": fecha_corta(pedido.fecha_entrega),
        "saldo": calculos.saldo(pedido),
        "url": reverse("pedidos:detalle", args=[pedido.pk]),
        "etiqueta": insignia(etiqueta),
    }


def revisar_fechas(desde, hasta, nombre_desde="desde", nombre_hasta="hasta"):
    if desde and hasta and desde > hasta:
        raise ErrorDeHerramienta(
            f"La fecha {nombre_desde} ({desde.isoformat()}) es después de {nombre_hasta} "
            f"({hasta.isoformat()}). Vuelve a pedirla con {nombre_desde} antes de {nombre_hasta}."
        )


# --- buscar_pedidos ---------------------------------------------------------------------------


def buscar_pedidos(ctx: Contexto, *, texto, filtro, entrega_desde, entrega_hasta) -> Resultado:
    """Los pedidos por texto, filtro de la pantalla Pedidos o fecha de entrega."""
    revisar_fechas(entrega_desde, entrega_hasta, "entrega_desde", "entrega_hasta")
    filtro = filtro or "todos"
    texto = (texto or "").strip()

    pedidos = pedidos_del_taller(ctx)
    if filtro == "cotizados":
        # "Cotizados" no es un filtro de la pantalla: son los que no se han confirmado.
        pedidos = pedidos.filter(estado=Pedido.Estado.COTIZADO)
    else:
        pedidos = calculos.filtrar_pedidos(pedidos, filtro, ctx.hoy)
    if entrega_desde:
        pedidos = pedidos.filter(fecha_entrega__gte=entrega_desde)
    if entrega_hasta:
        pedidos = pedidos.filter(fecha_entrega__lte=entrega_hasta)
    # El mismo buscador de la pantalla Pedidos: cliente, prenda o encargada, sin tildes.
    elegidos = [
        p
        for p in pedidos
        if calculos.coincide(
            texto, p.cliente.nombre, p.detalle, p.encargada.nombre if p.encargada else ""
        )
    ]
    elegidos = calculos.ordenar_pedidos(elegidos)

    con_saldo = filtro == "saldo"
    tarjeta = None
    if elegidos:
        tarjeta = Tarjeta(
            tipo="pedidos",
            titulo="Pedidos",
            datos={
                "filas": [
                    fila_de_tarjeta(p, ctx.hoy, con_saldo) for p in elegidos[:FILAS_DE_TARJETA]
                ],
                "con_saldo": con_saldo,
                "mas": sobran(elegidos),
            },
        )
    return Resultado(
        datos=lista_con_tope(elegidos, ctx.hoy),
        revisado=f"Busqué «{texto}» en tus pedidos" if texto else REVISADO_POR_FILTRO[filtro],
        tarjeta=tarjeta,
        enlace=Enlace(
            ENLACE_POR_FILTRO.get(filtro, "Ver los pedidos"), url_de_la_lista(filtro, texto)
        ),
    )


# --- ver_pedido -------------------------------------------------------------------------------


def ver_pedido(ctx: Contexto, *, pedido_id) -> Resultado:
    """Un pedido por dentro. Sin id, el que la dueña tiene abierto en pantalla."""
    if pedido_id is None:
        if ctx.pedido_actual is None:
            raise ErrorDeHerramienta(SIN_PEDIDO_ABIERTO)
        pedido_id = ctx.pedido_actual.pk
    # Se busca otra vez dentro del taller, aunque venga de la pantalla: un id ajeno o que no
    # existe dan la misma respuesta.
    pedido = pedidos_del_taller(ctx).filter(pk=pedido_id).first()
    if pedido is None:
        raise ErrorDeHerramienta(NO_ENCONTRE_PEDIDO)

    hoy = ctx.hoy
    abonos = list(pedido.abonos.all())
    recibidas, esperadas = calculos.tallas_recibidas(pedido)
    por_talla = calculos.tallas_por_talla(pedido)
    comprados, materiales = calculos.materiales_comprados(pedido)
    faltan = [m for m in pedido.materiales.all() if not m.comprado]
    cliente = pedido.cliente

    datos = {
        "pedido": pedido_en_datos(pedido, hoy),
        "pagos": {
            "total": pedido.total,
            "abonado": calculos.abonado(pedido),
            "saldo": calculos.saldo(pedido),
            "abonos": [{"fecha": a.fecha.isoformat(), "valor": a.valor} for a in abonos],
        },
        # Solo cuántas tallas llegaron de cada una: nunca nombres ni medidas.
        "tallas": {
            "recibidas": recibidas,
            "esperadas": esperadas,
            "por_talla": [{"talla": talla, "cantidad": n} for talla, n in por_talla],
        },
        "materiales": {
            "comprados": comprados,
            "total": materiales,
            "faltan": [{"nombre": m.nombre, "cantidad": m.cantidad} for m in faltan],
        },
        "cliente": {
            "id": cliente.pk,
            "nombre": cliente.nombre,
            "tipo": cliente.tipo,
            "tiene_whatsapp": bool(cliente.whatsapp_digitos),
        },
        "enlace_tallas_abierto": pedido.tallas_abiertas,
    }
    url = reverse("pedidos:detalle", args=[pedido.pk])
    tarjeta = Tarjeta(
        tipo="pedido",
        titulo=f"Pedido de {cliente.nombre}",
        datos={
            "cliente": cliente.nombre,
            "detalle": pedido.detalle,
            "url": url,
            "etapa": insignia(calculos.etiqueta_etapa(pedido)),
            "fecha": fecha_corta(pedido.fecha_entrega),
            "urgencia": insignia(calculos.etiqueta_urgencia(pedido, hoy)),
            "total": pedido.total,
            "abonado": calculos.abonado(pedido),
            "saldo": calculos.saldo(pedido),
            "pago": insignia(calculos.etiqueta_pago(pedido, hoy)),
            "tallas": f"{recibidas} de {esperadas}",
            "materiales": f"{comprados} de {materiales} comprados" if materiales else "",
        },
    )
    return Resultado(
        datos=datos,
        revisado=f"Revisé el pedido de {pedido.detalle}",
        tarjeta=tarjeta,
        enlace=Enlace("Ver el pedido", url),
    )


# --- entregas ---------------------------------------------------------------------------------


def entregas(ctx: Contexto, *, desde, hasta) -> Resultado:
    """Los pedidos en producción con entrega entre dos fechas y, aparte, los atrasados."""
    revisar_fechas(desde, hasta)
    dias = (hasta - desde).days
    if dias > DIAS_DE_ENTREGAS:
        raise ErrorDeHerramienta(
            f"El rango es de {dias} días y el máximo es {DIAS_DE_ENTREGAS}. Pide un rango más "
            "corto (por ejemplo, un mes)."
        )
    hoy = ctx.hoy
    pedidos = pedidos_del_taller(ctx)
    orden = ("fecha_entrega", "pk")
    en_rango = list(
        calculos.pedidos_en_produccion(pedidos)
        .filter(fecha_entrega__gte=desde, fecha_entrega__lte=hasta)
        .order_by(*orden)
    )
    atrasados = list(calculos.pedidos_atrasados(pedidos, hoy).order_by(*orden))

    # En la tarjeta van primero los atrasados (lo urgente) y después los del rango, sin repetir.
    vistos = set()
    para_tarjeta = []
    for pedido in atrasados + en_rango:
        if pedido.pk not in vistos:
            vistos.add(pedido.pk)
            para_tarjeta.append(pedido)
    tarjeta = None
    if para_tarjeta:
        tarjeta = Tarjeta(
            tipo="entregas",
            titulo="Entregas",
            datos={
                "filas": [fila_de_tarjeta(p, hoy) for p in para_tarjeta[:FILAS_DE_TARJETA]],
                "mas": sobran(para_tarjeta),
            },
        )
    return Resultado(
        datos={
            "desde": desde.isoformat(),
            "hasta": hasta.isoformat(),
            "entregas": lista_con_tope(en_rango, hoy),
            "atrasados": lista_con_tope(atrasados, hoy),
        },
        revisado=f"Revisé tus entregas del {fecha_corta(desde)} al {fecha_corta(hasta)}",
        tarjeta=tarjeta,
        enlace=Enlace(
            "Ver el calendario",
            f"{reverse('pedidos:calendario')}?{urlencode({'mes': f'{desde:%Y-%m}'})}",
        ),
    )
