"""En qué pantalla está la dueña cuando pregunta.

Carril B (T30). Reglas: docs/11-plan-tanda-7.md, sección 1.4 ("Pantalla").

`contexto_de_pagina(taller, ruta)` recibe la dirección que tiene abierta (con su `?...`) y
devuelve dos cosas:
- una frase para Claude, que va en el mensaje `role: "system"` de la pregunta
  ("Pantalla actual: Pedidos, con el filtro «Atrasados»."), y
- el pedido abierto, si es un pedido de su taller; si no, None.

Reglas:
- La dirección la manda el navegador, así que no se confía en ella: se lee con `resolve()`
  de Django, y cualquier cosa rara (una dirección inventada, de otra página web, con un
  número gigante) da la frase genérica, sin error.
- El pedido se busca solo entre los del taller. Si es de otro taller o no existe, se ignora
  sin dejar rastro: la frase es la misma de la lista de Pedidos, sin su número.
- La frase puede decir el cliente y el detalle del pedido, nunca notas, teléfonos ni tallas.
- Lo que la dueña buscó (`q`) se recorta y se le quitan los saltos de línea.
"""

from urllib.parse import parse_qs, urlsplit

from django.urls import resolve
from django.utils import timezone

from config.menu import MI_TALLER, SECCIONES
from config.piezas import mes_y_anio
from pedidos.calculos import FILTROS
from pedidos.models import Pedido

GENERICA = "Pantalla actual: otra pantalla de la aplicación."
MAXIMO_BUSQUEDA = 80
MAXIMO_DATO = 160  # el detalle de un pedido tiene hasta 160 letras
ID_MAXIMO = 2**63 - 1  # el número más grande que cabe en la base

_NOMBRES_DE_FILTRO = dict(FILTROS)
# Cada dirección con el nombre de su sección del menú: "pedidos:nuevo" -> "Pedidos".
_SECCION_DE = {
    vista: seccion.nombre for seccion in (*SECCIONES, MI_TALLER) for vista in seccion.vistas
}


def _limpio(texto, maximo=MAXIMO_BUSQUEDA):
    """En una sola línea, sin espacios de más y con tope de largo."""
    return " ".join(str(texto or "").split())[:maximo].strip()


def _primero(consulta, clave):
    valores = consulta.get(clave) or [""]
    return valores[0]


def _frase(seccion, *detalles):
    extra = "".join(f", {d}" for d in detalles if d)
    return f"Pantalla actual: {seccion}{extra}."


def _pedido(taller, pk):
    if not isinstance(pk, int) or not 1 <= pk <= ID_MAXIMO:
        return None
    return Pedido.objects.del_taller(taller).select_related("cliente").filter(pk=pk).first()


def _detalle(taller, kwargs):
    pedido = _pedido(taller, kwargs.get("pk"))
    if pedido is None:
        return _frase(_SECCION_DE["pedidos:detalle"]), None
    cliente = _limpio(pedido.cliente.nombre, MAXIMO_DATO)
    detalle = _limpio(pedido.detalle, MAXIMO_DATO)
    texto = (
        f"Pantalla actual: el pedido {pedido.pk} de {cliente}, «{detalle}». "
        "Si dice «este pedido», es este."
    )
    return texto, pedido


def _lista(consulta):
    filtro = _primero(consulta, "filtro")
    q = _limpio(_primero(consulta, "q"))
    nombre_filtro = _NOMBRES_DE_FILTRO.get(filtro) if filtro != "todos" else None
    return _frase(
        "Pedidos",
        f"con el filtro «{nombre_filtro}»" if nombre_filtro else "",
        f"buscando «{q}»" if q else "",
    )


def _clientes(consulta):
    q = _limpio(_primero(consulta, "q"))
    return _frase("Clientes", f"buscando «{q}»" if q else "")


def _resumen(consulta):
    from finanzas.vistas import mes_elegido

    mes = mes_elegido(_primero(consulta, "mes"), timezone.localdate())
    texto_mes = mes_y_anio(mes)
    return f"Pantalla actual: Resumen de {texto_mes[:1].lower()}{texto_mes[1:]}."


def contexto_de_pagina(taller, ruta: str):
    """(texto para Claude, pedido abierto o None). Un pedido de otro taller se ignora."""
    try:
        partes = urlsplit(str(ruta or ""))
        if partes.scheme or partes.netloc or not partes.path.startswith("/"):
            return GENERICA, None
        coincidencia = resolve(partes.path)
        consulta = parse_qs(partes.query)
    except Exception:  # cualquier dirección que no es de la aplicación
        return GENERICA, None

    vista = coincidencia.view_name
    if vista == "pedidos:detalle":
        return _detalle(taller, coincidencia.kwargs)
    if vista == "pedidos:lista":
        return _lista(consulta), None
    if vista == "pedidos:clientes":
        return _clientes(consulta), None
    if vista == "finanzas:resumen":
        return _resumen(consulta), None
    seccion = _SECCION_DE.get(vista)
    if seccion is None:
        return GENERICA, None
    return _frase(seccion), None
