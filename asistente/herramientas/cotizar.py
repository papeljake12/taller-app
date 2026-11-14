"""La cotización con los precios guardados del Cotizador.

Carril C (T32). Firma de cada herramienta: `def nombre(ctx, **entrada) -> Resultado`.
Contratos y reglas de `Resultado.datos`: asistente/contratos.py y docs/11-plan-tanda-7.md
(secciones 1.1 y 1.2). La entrada llega ya revisada por `asistente.herramientas.ejecutar()`
(las fechas ya son `date`).
"""

from asistente.contratos import Contexto, Resultado


def cotizar(ctx: Contexto, *, prenda, cantidad, ganancia_pct, abono_pct) -> Resultado:
    raise NotImplementedError("Carril C (T32)")
