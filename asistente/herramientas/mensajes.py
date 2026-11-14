"""El mensaje de WhatsApp que Claude deja listo.

Carril C (T31). Firma de cada herramienta: `def nombre(ctx, **entrada) -> Resultado`.
Contratos y reglas de `Resultado.datos`: asistente/contratos.py y docs/11-plan-tanda-7.md
(secciones 1.1 y 1.2). La entrada llega ya revisada por `asistente.herramientas.ejecutar()`
(las fechas ya son `date`).
"""

from asistente.contratos import Contexto, Resultado


def preparar_mensaje(ctx: Contexto, *, pedido_id, cliente_id, motivo, texto) -> Resultado:
    raise NotImplementedError("Carril C (T31)")
