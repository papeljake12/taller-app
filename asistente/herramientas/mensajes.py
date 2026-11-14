"""El mensaje de WhatsApp que Claude deja listo (carril C, T31).

Claude escribe el texto; esta herramienta lo revisa, le pone el enlace de tallas si hace falta
y arma la tarjeta con el botón "Abrir en WhatsApp". No envía nada ni guarda nada: la dueña
lo revisa y lo envía ella misma desde su celular.

Lo que se revisa antes de dejarlo listo:
- El pedido o el cliente tienen que ser del taller (`del_taller`). Uno de otro taller da el
  mismo error que uno que no existe.
- Toda cifra en pesos del texto ("$ 480.000", "$480000", "480.000 pesos") tiene que ser el
  total, lo abonado o el saldo del pedido (pedidos/calculos.py). Si el mensaje es solo de un
  cliente (sin pedido), la única cifra que puede ir es lo que debe en total, la misma de la
  pantalla Clientes. Si no cuadra, el error le dice a Claude las cifras correctas.
- Para pedir tallas, el pedido tiene que tener el enlace abierto y el texto tiene que traer
  el marcador [ENLACE]: la aplicación lo cambia por la dirección pública del formulario.

Lo que nunca le llega a Claude: el número de WhatsApp y la clave (token) del enlace de tallas.
Los dos viven solo en la tarjeta, que se guarda en la sesión y se dibuja en el panel.
`Resultado.datos` es solo `{"listo": True, "tiene_whatsapp": ...}`.
"""

import re
from urllib.parse import urlencode, urljoin

from django.urls import reverse

from asistente.contratos import Contexto, Enlace, ErrorDeHerramienta, Resultado, Tarjeta
from pedidos import calculos, mensajes
from pedidos.models import Cliente, Pedido

MARCADOR = "[ENLACE]"

NO_HAY_PEDIDO = "No encontré ese pedido."
NO_HAY_CLIENTE = "No encontré ese cliente."

# Una cifra en pesos: con puntos o comas de mil ("480.000", "1,090,000") o sin ellos ("480000").
_NUMERO = r"(\d{1,3}(?:[.,]\d{3})+(?!\d)|\d+)"
# "$ 480.000" o "$480000"...
_CON_SIGNO = re.compile(r"\$\s*" + _NUMERO)
# ... o "480.000 pesos" / "480000 COP".
_CON_PALABRA = re.compile(_NUMERO + r"\s*(?:pesos|cop)\b", re.IGNORECASE)


def cifras_en_pesos(texto):
    """Las cifras en pesos que trae el texto, como enteros y en el orden en que aparecen."""
    encontradas = []
    for patron in (_CON_SIGNO, _CON_PALABRA):
        for numero in patron.findall(texto):
            valor = int(numero.replace(".", "").replace(",", ""))
            if valor not in encontradas:
                encontradas.append(valor)
    return encontradas


# --- A quién va ---------------------------------------------------------------------------


def _pedido(ctx, pedido_id):
    pedido = (
        Pedido.objects.del_taller(ctx.taller)
        .select_related("cliente", "taller")
        .filter(pk=pedido_id)
        .first()
    )
    if pedido is None:
        raise ErrorDeHerramienta(NO_HAY_PEDIDO)
    return pedido


def _cliente(ctx, cliente_id):
    cliente = Cliente.objects.del_taller(ctx.taller).filter(pk=cliente_id).first()
    if cliente is None:
        raise ErrorDeHerramienta(NO_HAY_CLIENTE)
    return cliente


def _a_quien(ctx, pedido_id, cliente_id):
    """(pedido o None, cliente). Sin ids, el pedido abierto en la pantalla."""
    if pedido_id is not None:
        pedido = _pedido(ctx, pedido_id)
        if cliente_id is not None and cliente_id != pedido.cliente_id:
            raise ErrorDeHerramienta(
                "Ese pedido es de otro cliente. Manda solo el pedido_id del pedido."
            )
        return pedido, pedido.cliente
    if cliente_id is not None:
        return None, _cliente(ctx, cliente_id)
    if ctx.pedido_actual is not None:
        # Se vuelve a buscar en el taller: así las cifras salen frescas.
        pedido = _pedido(ctx, ctx.pedido_actual.pk)
        return pedido, pedido.cliente
    raise ErrorDeHerramienta(
        "Dime para qué pedido o cliente es el mensaje: busca su pedido_id o su cliente_id."
    )


# --- Las cifras -------------------------------------------------------------------------------


def _revisar_cifras_del_pedido(texto, pedido, motivo):
    total, abonado, saldo = pedido.total, calculos.abonado(pedido), calculos.saldo(pedido)
    if motivo == "cobro" and saldo <= 0:
        raise ErrorDeHerramienta("Ese pedido ya está pagado: no tiene saldo para cobrar.")
    validas = {total, abonado, saldo}
    malas = [cifra for cifra in cifras_en_pesos(texto) if cifra not in validas]
    if malas:
        raise ErrorDeHerramienta(
            f"La cifra {malas[0]} no es del pedido. El total es {total}, lo abonado es "
            f"{abonado} y el saldo es {saldo}; corrige la cifra."
        )


def _debe_en_total(ctx, cliente):
    """Lo que debe el cliente sumando sus pedidos (lo mismo que dice la pantalla Clientes)."""
    for cuenta in calculos.cuentas_de_clientes(ctx.taller):
        if cuenta.cliente.pk == cliente.pk:
            return cuenta.debe
    return 0


def _revisar_cifras_del_cliente(ctx, texto, cliente, motivo):
    cifras = cifras_en_pesos(texto)
    if not cifras and motivo != "cobro":
        return
    debe = _debe_en_total(ctx, cliente)
    if motivo == "cobro" and debe <= 0:
        raise ErrorDeHerramienta("Ese cliente no debe nada: no hay saldo para cobrar.")
    malas = [cifra for cifra in cifras if cifra != debe]
    if malas:
        if debe > 0:
            explicacion = f"Sin pedido, la única cifra que puede ir es lo que debe en total: {debe}"
        else:
            explicacion = "Sin pedido no puedo revisar cifras y ese cliente no debe nada"
        raise ErrorDeHerramienta(
            f"La cifra {malas[0]} no cuadra. {explicacion}. Corrige la cifra, o manda el "
            "pedido_id si el mensaje es sobre un pedido."
        )


# --- El enlace de tallas ----------------------------------------------------------------------


def _con_enlace_de_tallas(ctx, texto, pedido, motivo):
    """El texto con [ENLACE] cambiado por la dirección pública del formulario de tallas."""
    if motivo != "tallas":
        if MARCADOR in texto:
            raise ErrorDeHerramienta(
                f"El marcador {MARCADOR} solo sirve para pedir tallas (motivo tallas)."
            )
        return texto
    if pedido is None:
        raise ErrorDeHerramienta("Para pedir tallas, dime de qué pedido (pedido_id).")
    if not pedido.tallas_abiertas:
        raise ErrorDeHerramienta(
            "El enlace de tallas de ese pedido está cerrado. La dueña tiene que abrirlo en el "
            "pedido antes de pedir tallas."
        )
    if MARCADOR not in texto:
        raise ErrorDeHerramienta(
            f"Escribe el marcador {MARCADOR} donde va el enlace del formulario de tallas."
        )
    direccion = urljoin(
        ctx.url_base, reverse("pedidos:publico_tallas", args=[pedido.token_tallas])
    )
    return texto.replace(MARCADOR, direccion)


# --- La herramienta ---------------------------------------------------------------------------


def preparar_mensaje(ctx: Contexto, *, pedido_id, cliente_id, motivo, texto) -> Resultado:
    pedido, cliente = _a_quien(ctx, pedido_id, cliente_id)
    if motivo == "listo" and pedido is None:
        raise ErrorDeHerramienta("Para avisar que está listo, dime de qué pedido (pedido_id).")

    texto = texto.strip()
    if not texto:
        raise ErrorDeHerramienta("Escribe el texto del mensaje.")
    if pedido is not None:
        _revisar_cifras_del_pedido(texto, pedido, motivo)
    else:
        _revisar_cifras_del_cliente(ctx, texto, cliente, motivo)
    texto_final = _con_enlace_de_tallas(ctx, texto, pedido, motivo)

    # El número solo entra aquí: en la tarjeta, que no sale del servidor.
    enlace_whatsapp = mensajes.enlace_whatsapp(cliente.whatsapp, texto_final)

    if pedido is not None:
        revisado = f"Revisé el pedido de {pedido.detalle}"
        enlace = Enlace("Ver el pedido", reverse("pedidos:detalle", args=[pedido.pk]))
    else:
        revisado = f"Revisé los datos de {cliente.nombre}"
        enlace = Enlace(
            "Ver el cliente",
            reverse("pedidos:clientes") + "?" + urlencode({"q": cliente.nombre}),
        )

    return Resultado(
        datos={"listo": True, "tiene_whatsapp": bool(enlace_whatsapp)},
        revisado=revisado,
        tarjeta=Tarjeta(
            "mensaje",
            f"Para {cliente.nombre}",
            {
                "cliente": cliente.nombre,
                "motivo": motivo,
                "texto": texto_final,
                "enlace_whatsapp": enlace_whatsapp,
            },
        ),
        enlace=enlace,
    )
