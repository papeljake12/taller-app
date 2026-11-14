"""Consultas de plata: quien_debe, cuentas_del_mes y gastos.

Carril A (T28). Firma de cada herramienta: `def nombre(ctx, **entrada) -> Resultado`.
Contratos y reglas de `Resultado.datos`: asistente/contratos.py y docs/11-plan-tanda-7.md
(secciones 1.1 y 1.2). La entrada llega ya revisada por `asistente.herramientas.ejecutar()`
(las fechas ya son `date`).

Toda cifra sale de pedidos/calculos.py, la misma que muestran Hoy y Resumen: aquí no se suma
plata en la base. Así "Por cobrar" da lo mismo en Hoy que en el asistente. La plata va en
enteros de pesos.
"""

from urllib.parse import urlencode

from django.urls import reverse
from django.utils.dates import MONTHS

from asistente.contratos import Contexto, Enlace, Resultado, Tarjeta
from asistente.herramientas.pedidos import (
    FILAS_DE_TARJETA,
    TOPE_PEDIDOS,
    revisar_fechas,
    sobran,
)
from config.piezas import fecha_corta
from finanzas.models import Gasto
from pedidos import calculos

# Cuántos clientes y cuántos gastos van a Claude como mucho; los demás solo se cuentan.
TOPE_DEUDORES = TOPE_PEDIDOS
TOPE_GASTOS = 30


def nombre_del_mes(mes):
    """'noviembre' (en minúscula, como se escribe en una frase)."""
    return str(MONTHS[mes]).lower()


def url_del_resumen(anio, mes, ancla=""):
    """Resumen de ese mes (?mes=2026-11), como lo arma finanzas/vistas.py."""
    return f"{reverse('finanzas:resumen')}?{urlencode({'mes': f'{anio:04d}-{mes:02d}'})}{ancla}"


def url_de_saldo(cliente=""):
    """Pedidos con saldo; con un cliente, solo los suyos (como las filas de Hoy)."""
    parametros = {"filtro": "saldo"}
    if cliente:
        parametros["q"] = cliente
    return f"{reverse('pedidos:lista')}?{urlencode(parametros)}"


# --- quien_debe -------------------------------------------------------------------------------


def quien_debe(ctx: Contexto) -> Resultado:
    """Quién te debe: por cliente, del que más debe al que menos, y el total por cobrar."""
    deudores = calculos.quien_te_debe(ctx.taller, ctx.hoy)
    mostrados = deudores[:TOPE_DEUDORES]
    por_cobrar = calculos.por_cobrar(ctx.taller)

    tarjeta = None
    if deudores:
        tarjeta = Tarjeta(
            tipo="quien_debe",
            titulo="Quién te debe",
            datos={
                "por_cobrar": por_cobrar,
                "filas": [
                    {
                        "cliente": d.cliente.nombre,
                        "saldo": d.saldo,
                        "vencida": d.atrasado,
                        "url": url_de_saldo(d.cliente.nombre),
                    }
                    for d in deudores[:FILAS_DE_TARJETA]
                ],
                "mas": sobran(deudores),
            },
        )
    return Resultado(
        datos={
            "por_cobrar": por_cobrar,
            "total": len(deudores),
            "mostrados": len(mostrados),
            "deudores": [
                {
                    "cliente_id": d.cliente.pk,
                    "cliente": d.cliente.nombre,
                    "saldo": d.saldo,
                    "vencida": d.atrasado,
                }
                for d in mostrados
            ],
        },
        revisado="Revisé los saldos de tus pedidos confirmados",
        tarjeta=tarjeta,
        enlace=Enlace("Ver los pedidos con saldo", url_de_saldo()),
    )


# --- cuentas_del_mes --------------------------------------------------------------------------


def cuentas_del_mes(ctx: Contexto, *, anio, mes) -> Resultado:
    """Vendido, cobrado, gastado y "te quedó" de un mes, y las ventas por tipo de cliente.

    Sin año, el de hoy; sin mes, el de hoy.
    """
    anio = anio or ctx.hoy.year
    mes = mes or ctx.hoy.month
    cifras = calculos.resumen_del_mes(ctx.taller, anio, mes)
    ventas = calculos.ventas_por_tipo(ctx.taller, anio, mes)
    nombre = nombre_del_mes(mes)
    return Resultado(
        datos={
            "anio": anio,
            "mes": mes,
            "vendido": cifras["vendido"],
            "cobrado": cifras["cobrado"],
            "gastado": cifras["gastado"],
            "te_quedo": cifras["te_quedo"],
            "ventas_por_tipo": [{"tipo": tipo, "total": total} for tipo, total in ventas],
        },
        revisado=f"Revisé las cuentas de {nombre} de {anio}",
        tarjeta=Tarjeta(
            tipo="cuentas",
            titulo=f"Cuentas de {nombre} de {anio}",
            datos={
                "mes": f"{nombre.capitalize()} de {anio}",
                "vendido": cifras["vendido"],
                "cobrado": cifras["cobrado"],
                "gastado": cifras["gastado"],
                "te_quedo": cifras["te_quedo"],
            },
        ),
        enlace=Enlace(f"Ver el resumen de {nombre}", url_del_resumen(anio, mes)),
    )


# --- gastos -----------------------------------------------------------------------------------


def gastos(ctx: Contexto, *, desde, hasta, categoria) -> Resultado:
    """Los gastos entre dos fechas: el total, el total por tipo y hasta 30 gastos."""
    revisar_fechas(desde, hasta)
    por_categoria = calculos.gastos_por_categoria(ctx.taller, desde, hasta)
    if categoria:
        por_categoria = [c for c in por_categoria if c["categoria"] == categoria]
    # El total es la suma de los totales por tipo que ya trae calculos (no otra consulta).
    total = sum(c["total"] for c in por_categoria)
    lista = calculos.gastos_entre(ctx.taller, desde, hasta, categoria)
    cuantos = lista.count()
    mostrados = list(lista[:TOPE_GASTOS])
    nombres = dict(Gasto.Categoria.choices)

    periodo = f"del {fecha_corta(desde)} al {fecha_corta(hasta)}"
    tipo = f" de {nombres[categoria].lower()}" if categoria else ""
    return Resultado(
        datos={
            "desde": desde.isoformat(),
            "hasta": hasta.isoformat(),
            "total": total,
            "por_categoria": [
                {"categoria": c["categoria"], "total": c["total"]} for c in por_categoria
            ],
            "cantidad": cuantos,
            "mostrados": len(mostrados),
            "gastos": [
                {
                    "fecha": g.fecha.isoformat(),
                    "concepto": g.concepto,
                    "categoria": g.categoria,
                    "valor": g.valor,
                }
                for g in mostrados
            ],
        },
        revisado=f"Revisé tus gastos{tipo} {periodo}",
        tarjeta=Tarjeta(
            tipo="gastos",
            titulo=f"Gastos{tipo} {periodo}",
            datos={
                "total": total,
                "filas": [{"nombre": c["nombre"], "total": c["total"]} for c in por_categoria],
            },
        ),
        enlace=Enlace(
            "Ver los gastos en Resumen", url_del_resumen(desde.year, desde.month, "#gastos")
        ),
    )
