"""Consultas de telas y clientes: telas y buscar_clientes.

Carril A (T27). Firma de cada herramienta: `def nombre(ctx, **entrada) -> Resultado`.
Contratos y reglas de `Resultado.datos`: asistente/contratos.py y docs/11-plan-tanda-7.md
(secciones 1.1 y 1.2). La entrada llega ya revisada por `asistente.herramientas.ejecutar()`.

Las cuentas salen de pedidos/calculos.py (telas_en_orden, tela_baja, resumen_de_telas,
cuentas_de_clientes y coincide), siempre con el taller de quien pregunta. De un cliente van a
Claude su nombre, su tipo y sus cifras, y si tiene WhatsApp guardado: nunca el número ni las
notas.
"""

from decimal import Decimal
from urllib.parse import urlencode

from django.urls import reverse

from asistente.contratos import Contexto, Enlace, Resultado, Tarjeta
from asistente.herramientas.pedidos import FILAS_DE_TARJETA, TOPE_PEDIDOS, sobran
from pedidos import calculos
from pedidos.vistas.clientes import clientes_con_deuda_vencida
from telas.vistas import fila as fila_de_tela

# Cuántos clientes van a Claude como mucho; los demás solo se cuentan.
TOPE_CLIENTES = TOPE_PEDIDOS


def metros_en_texto(valor):
    """Metros como texto con dos decimales ("6.50"): nunca un float."""
    return str(Decimal(valor).quantize(Decimal("0.01")))


# --- telas ------------------------------------------------------------------------------------


def telas(ctx: Contexto, *, solo_bajas) -> Resultado:
    """Las telas con sus metros, el mínimo para avisar y cuáles se están acabando."""
    resumen = calculos.resumen_de_telas(ctx.taller)
    todas = calculos.telas_en_orden(ctx.taller)
    elegidas = [t for t in todas if calculos.tela_baja(t)] if solo_bajas else todas

    tarjeta = None
    if elegidas:
        filas = []
        for tela in elegidas[:FILAS_DE_TARJETA]:
            estado = fila_de_tela(tela)
            filas.append(
                {
                    "nombre": tela.nombre,
                    "metros": metros_en_texto(tela.metros),
                    "etiqueta": {"texto": estado.estado, "tono": estado.tono,
                                 "circulo": estado.circulo},
                }
            )
        tarjeta = Tarjeta(
            tipo="telas",
            titulo="Telas que se están acabando" if solo_bajas else "Telas",
            datos={"filas": filas, "mas": sobran(elegidas)},
        )
    return Resultado(
        datos={
            "cantidad": resumen["cantidad"],
            "metros": metros_en_texto(resumen["metros"]),
            "bajas": len(resumen["bajas"]),
            "telas": [
                {
                    "nombre": t.nombre,
                    "metros": metros_en_texto(t.metros),
                    "minimo": metros_en_texto(t.minimo),
                    "baja": calculos.tela_baja(t),
                }
                for t in elegidas
            ],
        },
        revisado="Revisé las telas que se están acabando" if solo_bajas else "Revisé tus telas",
        tarjeta=tarjeta,
        enlace=Enlace("Ver las telas", reverse("telas:inicio")),
    )


# --- buscar_clientes --------------------------------------------------------------------------


def url_de_clientes(texto=""):
    url = reverse("pedidos:clientes")
    return f"{url}?{urlencode({'q': texto})}" if texto else url


def buscar_clientes(ctx: Contexto, *, texto, tipo) -> Resultado:
    """Clientes por nombre o tipo, con sus pedidos, lo que han comprado y lo que deben."""
    texto = (texto or "").strip()
    # Como el buscador de Clientes, pero sin mirar el WhatsApp: el número no se busca ni se
    # cuenta.
    elegidas = [
        c
        for c in calculos.cuentas_de_clientes(ctx.taller)
        if (tipo is None or c.cliente.tipo == tipo)
        and calculos.coincide(texto, c.cliente.nombre, c.cliente.get_tipo_display())
    ]
    vencidos = clientes_con_deuda_vencida(ctx.taller, ctx.hoy)
    mostradas = elegidas[:TOPE_CLIENTES]

    tarjeta = None
    if elegidas:
        tarjeta = Tarjeta(
            tipo="clientes",
            titulo="Clientes",
            datos={
                "filas": [
                    {
                        "nombre": c.cliente.nombre,
                        "tipo": c.cliente.get_tipo_display(),
                        "url": url_de_clientes(c.cliente.nombre),
                        "debe": c.debe,
                        "vencida": c.debe > 0 and c.cliente.pk in vencidos,
                        "cotizacion_abierta": c.cotizacion_abierta,
                        "ha_comprado": c.ha_comprado,
                    }
                    for c in elegidas[:FILAS_DE_TARJETA]
                ],
                "mas": sobran(elegidas),
            },
        )
    return Resultado(
        datos={
            "total": len(elegidas),
            "mostrados": len(mostradas),
            "clientes": [
                {
                    "id": c.cliente.pk,
                    "nombre": c.cliente.nombre,
                    "tipo": c.cliente.tipo,
                    "pedidos": c.pedidos,
                    "ha_comprado": c.ha_comprado,
                    "debe": c.debe,
                    "deuda_vencida": c.debe > 0 and c.cliente.pk in vencidos,
                    "cotizacion_abierta": c.cotizacion_abierta,
                    "tiene_whatsapp": bool(c.cliente.whatsapp_digitos),
                }
                for c in mostradas
            ],
        },
        revisado=f"Busqué «{texto}» en tus clientes" if texto else "Revisé tus clientes",
        tarjeta=tarjeta,
        enlace=Enlace("Ver los clientes", url_de_clientes(texto)),
    )
