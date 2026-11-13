"""Calendario (T14): el mes con las entregas marcadas, la lista de entregas y la semana más
cargada.

El calendario muestra el mes que llega en la dirección (?mes=2026-11). Si falta o no sirve,
es el mes de hoy en Bogotá: la misma regla de Resumen (finanzas/vistas.py), que se reusa.

Cada día con entregas es un botón. Tocarlo filtra la lista a ese día (?dia=2026-11-09) y
tocarlo otra vez vuelve al mes entero. Con HTMX responde solo la tarjeta de la lista
(_calendario_entregas.html) y, con hx-swap-oob, la cuadrícula del mes
(_calendario_dias.html), para que quede marcado el día elegido (aria-pressed). Sin
JavaScript, el botón envía un formulario GET y la página se dibuja entera.

Todas las cuentas salen de pedidos/calculos.py, siempre con el taller de la usuaria.
"""

import re
from dataclasses import dataclass
from datetime import date, timedelta

from django.shortcuts import render
from django.urls import reverse
from django.utils import timezone
from django.utils.cache import patch_vary_headers
from django.utils.dates import MONTHS
from django.views.decorators.http import require_GET

from config.piezas import dia_y_mes, fecha_corta
from config.ventanas import es_htmx
from finanzas.vistas import mes_elegido, texto_del_mes
from pedidos import calculos
from pedidos.calculos import Etiqueta
from pedidos.models import Pedido

Estado = Pedido.Estado

# "2026-11-09": año, mes y día con cifras comunes (de 0 a 9).
FORMA_DEL_DIA = re.compile(r"[0-9]{4}-[0-9]{2}-[0-9]{2}")

NOMBRES_DE_LA_SEMANA = ("Lun", "Mar", "Mié", "Jue", "Vie", "Sáb", "Dom")


def dia_elegido(texto, mes):
    """El día de "2026-11-09" si es una fecha de ese mes. Si falta o no sirve, None."""
    texto = str(texto or "").strip()
    if not FORMA_DEL_DIA.fullmatch(texto):
        return None
    try:
        dia = date.fromisoformat(texto)
    except ValueError:
        return None
    return dia if (dia.year, dia.month) == (mes.year, mes.month) else None


def texto_del_dia(dia):
    """'2026-11-09', como va en la dirección (?dia=)."""
    return dia.isoformat()


# --- Los días de la cuadrícula ----------------------------------------------------------------


def tono_en_el_dia(pedido, hoy):
    """El color de la entrega en su día, como la leyenda: entregado (verde), atrasado (rojo)
    o por entregar (ámbar, también los cotizados)."""
    if pedido.estado == Estado.ENTREGADO:
        return "verde"
    if calculos.esta_atrasado(pedido, hoy):
        return "rojo"
    return "ambar"


@dataclass(frozen=True)
class EntregaDelDia:
    pedido: Pedido
    tono: str


@dataclass(frozen=True)
class Dia:
    fecha: date
    fuera: bool  # de un mes vecino: solo completa la semana
    hoy: bool
    elegido: bool
    entregas: list
    url: str  # lo que pide el botón al tocarlo: el día, o el mes entero si ya estaba elegido

    @property
    def es_boton(self):
        return bool(self.entregas) and not self.fuera

    @property
    def id(self):
        return f"dia-{texto_del_dia(self.fecha)}"

    @property
    def valor(self):
        """El ?dia= que envía el botón sin JavaScript: vacío para volver al mes entero."""
        return "" if self.elegido else texto_del_dia(self.fecha)

    @property
    def descripcion(self):
        """'9 de nov, 1 entrega', para el lector de pantalla."""
        cantidad = len(self.entregas)
        return f"{fecha_corta(self.fecha)}, {cantidad} {'entrega' if cantidad == 1 else 'entregas'}"


def url_del_calendario(mes, dia=None):
    url = f"{reverse('pedidos:calendario')}?mes={texto_del_mes(mes)}"
    return f"{url}&dia={texto_del_dia(dia)}" if dia else url


def dias_del_mes(mes, entregas, hoy, elegido):
    """Las semanas del mes (de lunes a domingo), cada día con sus entregas.

    Los días de los meses vecinos van sin entregas, como en el diseño: esas son de otro mes.
    """
    por_dia = {}
    for pedido in entregas:
        por_dia.setdefault(pedido.fecha_entrega, []).append(
            EntregaDelDia(pedido, tono_en_el_dia(pedido, hoy))
        )
    dias = []
    for semana in calculos.semanas_del_mes(mes.year, mes.month):
        for fecha in semana:
            fuera = fecha.month != mes.month
            es_elegido = fecha == elegido
            dias.append(
                Dia(
                    fecha=fecha,
                    fuera=fuera,
                    hoy=fecha == hoy,
                    elegido=es_elegido,
                    entregas=[] if fuera else por_dia.get(fecha, []),
                    url=url_del_calendario(mes, None if es_elegido else fecha),
                )
            )
    return dias


# --- La lista de entregas -----------------------------------------------------------------


@dataclass(frozen=True)
class FilaEntrega:
    pedido: Pedido
    etiqueta: Etiqueta


def etiqueta_de_la_lista(pedido, hoy):
    """La etiqueta de calculos.etiqueta_entrega. Si va en producción sin afán, cuántos días
    faltan, en gris, como la demo."""
    etiqueta = calculos.etiqueta_entrega(pedido, hoy)
    if etiqueta:
        return etiqueta
    return Etiqueta(f"Faltan {calculos.dias_para_entrega(pedido, hoy)} días", "gris")


def titulo_de_la_lista(mes, dia):
    """'Entregas de noviembre' o, con un día elegido, 'Entregas del 9 de nov'."""
    if dia:
        return f"Entregas del {fecha_corta(dia)}"
    return f"Entregas de {str(MONTHS[mes.month]).lower()}"


# --- Semana más cargada -------------------------------------------------------------------------


def rango_de_la_semana(lunes):
    """'9 al 15 de noviembre' o, si la semana cambia de mes, '30 de noviembre al 6 de
    diciembre'."""
    domingo = lunes + timedelta(days=6)
    if lunes.month == domingo.month:
        return f"{lunes.day} al {dia_y_mes(domingo)}"
    return f"{dia_y_mes(lunes)} al {dia_y_mes(domingo)}"


def frase_de_la_semana(taller, hoy):
    """La frase de "Semana más cargada", con las entregas pendientes de hoy en adelante."""
    semana = calculos.semana_mas_cargada(taller, hoy)
    if semana is None:
        return "No hay entregas pendientes en las próximas semanas."
    if semana.entregas == 1:
        proxima = calculos.proxima_entrega(taller, hoy)
        return (
            "No se te juntan entregas: ninguna semana tiene más de una pendiente. "
            f"La próxima es el {fecha_corta(proxima.fecha_entrega)}."
        )
    personas = f"{semana.personas} {'persona' if semana.personas == 1 else 'personas'}"
    return (
        f"La semana más cargada que viene es la del {rango_de_la_semana(semana.lunes)}: "
        f"{semana.entregas} entregas para {personas}."
    )


# --- La pantalla ------------------------------------------------------------------------------


def contexto_calendario(request, mes, dia):
    taller = request.taller
    hoy = timezone.localdate()
    entregas = list(calculos.entregas_del_mes(taller, mes.year, mes.month))
    if dia:
        en_la_lista = [p for p in entregas if p.fecha_entrega == dia]
    else:
        en_la_lista = entregas
    return {
        "mes": mes,
        "texto_mes": texto_del_mes(mes),
        "url_mes": url_del_calendario(mes),
        "mes_anterior": texto_del_mes(calculos.sumar_meses(mes, -1)),
        "mes_siguiente": texto_del_mes(calculos.sumar_meses(mes, 1)),
        "nombres_de_la_semana": NOMBRES_DE_LA_SEMANA,
        "dias": dias_del_mes(mes, entregas, hoy, dia),
        "dia": dia,
        # Al tocar "Ver todo el mes", el cursor vuelve al día que estaba elegido (su id).
        "id_dia": f"dia-{texto_del_dia(dia)}" if dia else "",
        "titulo_lista": titulo_de_la_lista(mes, dia),
        "filas": [FilaEntrega(p, etiqueta_de_la_lista(p, hoy)) for p in en_la_lista],
        "frase_semana": frase_de_la_semana(taller, hoy),
    }


@require_GET
def calendario(request):
    mes = mes_elegido(request.GET.get("mes"))
    dia = dia_elegido(request.GET.get("dia"), mes)
    contexto = contexto_calendario(request, mes, dia)
    # Tocar un día pide solo la lista (y la cuadrícula aparte). Si el navegador vuelve atrás
    # y no tiene guardada la página, HTMX la pide entera (HX-History-Restore-Request).
    solo_lista = es_htmx(request) and request.headers.get("HX-History-Restore-Request") != "true"
    plantilla = "pedidos/_calendario_dia_elegido.html" if solo_lista else "pedidos/calendario.html"
    respuesta = render(request, plantilla, contexto)
    patch_vary_headers(respuesta, ["HX-Request"])
    return respuesta
