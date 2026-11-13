"""Los textos de los mensajes para el cliente y el enlace que abre WhatsApp con el texto escrito.

Son los mismos textos de la demo (demo/index.html: textoListo, textoCobro, textoTallas,
textoDotacion, textoOferta y textoCot). Los usan el pedido por dentro, Clientes y el
cotizador. Ninguno envía nada solo: arman el texto, y la usuaria lo envía o lo copia.

Archivo compartido: lo cambia el coordinador.
"""

from urllib.parse import quote

from config.piezas import dia_y_mes, fecha_corta, pesos
from pedidos import calculos


def firma(taller):
    """'de Confecciones Ana' o, si el taller no tiene nombre, 'del taller'."""
    nombre = (getattr(taller, "nombre", "") or "").strip()
    return f"de {nombre}" if nombre else "del taller"


def enlace_whatsapp(numero, texto):
    """El enlace que abre el chat con ese número y el texto escrito. '' si el número no sirve.

    Un celular colombiano de 10 dígitos (empieza por 3) se completa con el 57 del país.
    """
    digitos = "".join(c for c in str(numero or "") if c.isdigit())
    if len(digitos) == 10 and digitos.startswith("3"):
        digitos = "57" + digitos
    if not 10 <= len(digitos) <= 15:
        return ""
    return f"https://wa.me/{digitos}?text={quote(texto)}"


def texto_listo(pedido):
    """Aviso de pedido listo, con el saldo si queda algo por pagar."""
    texto = (
        f"Hola, le escribimos {firma(pedido.taller)}. Su pedido ({pedido.detalle}) "
        "ya está listo para entregar."
    )
    saldo = calculos.saldo(pedido)
    if saldo > 0:
        texto += f" Saldo pendiente: {pesos(saldo)}."
    return texto


def texto_cobro(pedido):
    """Recordatorio del saldo."""
    return (
        f"Hola, le escribimos {firma(pedido.taller)}. Su pedido ({pedido.detalle}) tiene un "
        f"saldo pendiente de {pesos(calculos.saldo(pedido))}. La entrega está programada "
        f"para el {fecha_corta(pedido.fecha_entrega)}. ¡Gracias!"
    )


def texto_tallas(pedido):
    """Resumen de tallas para copiar: cuántas de cada una y cuántas faltan."""
    lineas = [f"Tallas: {pedido.cliente.nombre}", pedido.detalle, ""]
    lineas += [f"{talla}: {cantidad}" for talla, cantidad in calculos.tallas_por_talla(pedido)]
    recibidas, esperadas = calculos.tallas_recibidas(pedido)
    final = f"Recibidas: {recibidas} de {esperadas}"
    if esperadas > recibidas:
        final += f" (faltan {esperadas - recibidas})"
    lineas += ["", final]
    return "\n".join(lineas)


def texto_dotacion(taller, hoy=None):
    """Para los clientes empresa, antes de una fecha de dotación."""
    fecha = dia_y_mes(calculos.proxima_dotacion(hoy))
    return (
        f"Hola, le escribimos {firma(taller)}. Se acerca la entrega de dotación del {fecha}. "
        "¿Le cotizamos los uniformes para su equipo?"
    )


def texto_oferta(taller):
    """Mensaje general para un cliente ("Escribirle")."""
    return (
        f"Hola, le escribimos {firma(taller)}. Cuando necesite uniformes, dotación o vestidos, "
        "con gusto le cotizamos."
    )


def texto_cotizacion(taller, cotizacion, prenda, cliente="", entrega=None):
    """La cotización para copiar o enviar. `cotizacion` es lo que devuelve calculos.cotizar."""
    unidades = cotizacion.total // cotizacion.precio_unidad if cotizacion.precio_unidad else 0
    lineas = [f"Cotización {firma(taller)}"]
    if str(cliente).strip():
        lineas.append(f"Cliente: {str(cliente).strip()}")
    lineas += [
        f"{unidades} × {str(prenda).strip()}",
        f"Precio por unidad: {pesos(cotizacion.precio_unidad)}",
        f"Total: {pesos(cotizacion.total)}",
    ]
    if cotizacion.abono > 0:
        lineas.append(f"Abono para empezar: {pesos(cotizacion.abono)}")
    if entrega:
        lineas.append(f"Entrega estimada: {fecha_corta(entrega)}")
    return "\n".join(lineas)
