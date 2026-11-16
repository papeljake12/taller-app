"""Proponer un abono a un pedido o un gasto del taller (T40, carril B).

Reglas: docs/13-plan-tanda-8.md, secciones 1.1 y 1.2. No guarda nada: arma un borrador con
`asistente.borradores` y la dueña lo guarda con un toque (`asistente.guardar`).
"""

from asistente.contratos import Contexto, Resultado


def proponer_abono(ctx: Contexto, *, pedido_id, cliente, valor, fecha) -> Resultado:
    raise NotImplementedError


def proponer_gasto(ctx: Contexto, *, concepto, categoria, valor, fecha, pedido_id) -> Resultado:
    raise NotImplementedError
