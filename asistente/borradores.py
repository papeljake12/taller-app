"""El borrador: lo que el agente deja listo para que la dueña lo guarde con un toque (tanda 8).

Reglas: docs/13-plan-tanda-8.md, sección 1.1. Ninguna herramienta escribe en la base. Las
herramientas `proponer_*` arman aquí un borrador: una lista de acciones que se guardan juntas
(o todas o ninguna) y las filas que se ven en la tarjeta. Lo guarda `asistente.guardar`,
llamado desde la vista `confirmar` cuando ella toca Guardar.

La firma. Las acciones viajan dentro de una firma (`django.core.signing`) con el taller, la
usuaria y una clave al azar. Así lo que se guarda es exactamente lo que se mostró: en el
navegador no se puede cambiar. La firma vence a las dos horas y sirve una sola vez (su clave
queda en `BorradorUsado` al guardar). Nunca va a Claude: él solo ve las filas en texto.

Una acción es {"tipo": ..., "datos": {...}} con datos que caben en JSON: fechas en texto ISO,
metros en texto ("66.00"), plata en enteros. Una acción puede apuntar a una anterior del mismo
borrador con "@0", "@1"...: el abono del pedido nuevo lleva "pedido": "@0".

Archivo de la base (coordinador): los carriles lo usan, no lo cambian.
"""

import secrets
from dataclasses import asdict

from django.core import signing

from asistente.contratos import Contexto, Fila, Resultado, Tarjeta

SAL = "asistente.borrador"
VIGENCIA_SEGUNDOS = 2 * 60 * 60  # dos horas
TIPOS = ("pedido", "etapa", "abono", "gasto", "tela_pedido")  # T41 agrega más

# Lo que ve la dueña cuando un borrador ya no sirve.
MENSAJES = {
    "vencido": "Este borrador venció. Pídemelo otra vez.",
    "usado": "Este borrador ya se guardó.",
    "ajeno": "Este borrador ya no sirve.",
    "danado": "Este borrador ya no sirve.",
    "reemplazado": "Este borrador ya no sirve: lo cambié por otro.",
}

# Lo que lee Claude junto con las filas.
NOTA_PARA_CLAUDE = (
    "Nada se ha guardado todavía. La dueña ve este borrador en una tarjeta y lo guarda ella "
    "misma con el botón Guardar. No digas que quedó guardado."
)


class BorradorInvalido(Exception):
    """El borrador no se puede guardar. `motivo`: vencido, usado, ajeno, danado o reemplazado."""

    def __init__(self, motivo):
        super().__init__(MENSAJES[motivo])
        self.motivo = motivo


def es_referencia(valor):
    """True si el valor apunta a otra acción del mismo borrador ("@0")."""
    return isinstance(valor, str) and valor.startswith("@") and valor[1:].isdigit()


def _revisar(acciones):
    if not acciones:
        raise ValueError("Un borrador necesita por lo menos una acción.")
    for i, accion in enumerate(acciones):
        if accion.get("tipo") not in TIPOS:
            raise ValueError(f"Tipo de acción desconocido: {accion.get('tipo')!r}.")
        for valor in accion.get("datos", {}).values():
            if es_referencia(valor) and int(valor[1:]) >= i:
                raise ValueError("Una acción solo puede apuntar a una anterior.")


def armar(ctx: Contexto, acciones: list[dict], filas: list[Fila], titulo="Para guardar"):
    """La tarjeta del borrador, pendiente y con su firma."""
    _revisar(acciones)
    clave = secrets.token_hex(16)
    firma = signing.dumps(
        {"t": ctx.taller.pk, "u": ctx.usuaria.pk, "c": clave, "a": acciones},
        salt=SAL,
        compress=True,
    )
    return Tarjeta(
        "borrador",
        titulo,
        {
            "estado": "pendiente",
            "clave": clave,
            "firma": firma,
            "filas": [asdict(fila) for fila in filas],
        },
    )


def resultado(ctx: Contexto, acciones, filas, revisado, titulo="Para guardar") -> Resultado:
    """Lo que devuelve una herramienta `proponer_*`: la tarjeta para ella y, para Claude, las
    filas en texto, sin la firma."""
    return Resultado(
        datos={
            "borrador": "listo",
            "filas": [asdict(fila) for fila in filas],
            "nota": NOTA_PARA_CLAUDE,
        },
        revisado=revisado,
        tarjeta=armar(ctx, acciones, filas, titulo),
    )


def opciones(que: str, opciones_: list[tuple[int, str]], revisado: str) -> Resultado:
    """Hay dos o más parecidos: no se arma borrador. Claude pregunta y la tarjeta trae un chip
    por opción (que manda esa opción como pregunta). `que`: cliente, pedido, prenda o tela."""
    return Resultado(
        datos={
            "escoger": que,
            "opciones": [{"id": id_, "nombre": nombre} for id_, nombre in opciones_],
        },
        revisado=revisado,
        tarjeta=Tarjeta("opciones", f"¿Cuál {que}?", {"opciones": [n for _, n in opciones_]}),
    )


def abrir(firma: str, ctx: Contexto):
    """(clave, acciones) del borrador firmado. Lanza BorradorInvalido si venció, si es de otro
    taller u otra usuaria, si está dañado o si ya se guardó."""
    from asistente.models import BorradorUsado

    try:
        datos = signing.loads(firma or "", salt=SAL, max_age=VIGENCIA_SEGUNDOS)
    except signing.SignatureExpired:
        raise BorradorInvalido("vencido") from None
    except signing.BadSignature:
        raise BorradorInvalido("danado") from None
    if datos.get("t") != ctx.taller.pk or datos.get("u") != ctx.usuaria.pk:
        raise BorradorInvalido("ajeno")
    clave = datos.get("c", "")
    if BorradorUsado.objects.filter(clave=clave).exists():
        raise BorradorInvalido("usado")
    acciones = datos.get("a") or []
    try:
        _revisar(acciones)
    except ValueError:
        raise BorradorInvalido("danado") from None
    return clave, acciones
