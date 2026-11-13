"""Resumen del mes y gastos (T17) y la descarga para Excel (T18).

El resumen muestra el mes que llega en la dirección (?mes=2026-11). Si falta o no sirve, es
el mes de hoy en Bogotá. Todas las cuentas (vendido, cobrado, gastado, "te quedó", la
gráfica, las ventas por tipo y quién tiene qué) salen de pedidos/calculos.py, siempre con
el taller de la usuaria.

Registrar y quitar un gasto: con HTMX, la acción devuelve solo lo de adentro de la lista de
la tarjeta "Gastos del mes" (finanzas/_gastos_lista.html) y, con hx-swap-oob, la cabeza de
la tarjeta y las cifras y la gráfica, que cambian con el gasto. Sin JavaScript, los
formularios hacen un envío normal y vuelven al resumen. Al registrar o quitar, un aviso
corto lo confirma (config/avisos.py): "Gasto registrado." (el de la demo) y "Gasto
quitado." (la demo no tiene; va en su mismo estilo).

Permisos (T21, docs/04-permisos.md): Resumen, gastos y Excel son solo de la dueña. La
costurera recibe 403 (también al bajar el Excel desde cualquier pantalla); el número de un
gasto de otro taller, 404.
"""

import re
from dataclasses import dataclass
from datetime import date

from django.http import HttpResponse
from django.shortcuts import redirect, render
from django.template.loader import render_to_string
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.http import require_GET, require_http_methods

from config.avisos import avisar
from config.ventanas import es_htmx, responder_ventana
from cuentas.aislamiento import del_taller, obtener_o_404
from cuentas.permisos import exigir_duena, solo_duena
from finanzas.excel import TIPO_DE_ARCHIVO, libro_del_taller, nombre_del_archivo
from finanzas.formularios import PRIMER_ANIO, FormularioGasto
from finanzas.models import Gasto
from pedidos import calculos

# "2026-11": cuatro cifras del año, un guion y dos del mes (solo cifras comunes, de 0 a 9).
FORMA_DEL_MES = re.compile(r"([0-9]{4})-([0-9]{2})")

# Años que se pueden pedir por la dirección: de PRIMER_ANIO (el mismo de los gastos) a este.
# Fuera de ahí, un año escrito mal ("0001", "9999") rompería el mes anterior o el siguiente.
ULTIMO_ANIO = 2999

# Avisos cortos después de guardar (config/avisos.py). El primero es el de la demo
# (demo/index.html); para quitar, la demo no tiene: va uno corto del mismo estilo.
AVISO_REGISTRADO = "Gasto registrado."
AVISO_QUITADO = "Gasto quitado."


def mes_elegido(texto, hoy=None):
    """El primer día del mes de "2026-11". Si falta o no sirve, el del mes de hoy."""
    coincide = FORMA_DEL_MES.fullmatch(str(texto or "").strip())
    if coincide:
        anio, mes = int(coincide.group(1)), int(coincide.group(2))
        if PRIMER_ANIO <= anio <= ULTIMO_ANIO and 1 <= mes <= 12:
            return date(anio, mes, 1)
    return (hoy or timezone.localdate()).replace(day=1)


def texto_del_mes(mes):
    """'2026-11', como va en la dirección (?mes=)."""
    return f"{mes.year:04d}-{mes.month:02d}"


def url_del_mes(mes):
    return f"{reverse('finanzas:resumen')}?mes={texto_del_mes(mes)}"


@dataclass(frozen=True)
class Barra:
    """Una fila con barra: el nombre, el valor y el ancho de la barra (de 0 a 100)."""

    nombre: str
    valor: int
    porcentaje: int


def barras(filas):
    """[(nombre, valor), ...] -> barras medidas contra la más grande, que llega al 100 %."""
    maximo = max((valor for _, valor in filas), default=0)
    return [Barra(nombre, valor, calculos.porcentaje(valor, maximo)) for nombre, valor in filas]


def gastos_del_mes(request, mes):
    """Los gastos del taller con fecha en ese mes, del más nuevo al más viejo."""
    return del_taller(request, Gasto).filter(
        fecha__gte=mes, fecha__lt=calculos.sumar_meses(mes, 1)
    )


def contexto_de_la_plata(request, mes, form=None, por_quitar=None):
    """Lo que cambia con un gasto: las cifras, la gráfica y la tarjeta "Gastos del mes".

    `form` es el formulario "Registrar gasto" abierto en la tarjeta; sin él, la tarjeta
    muestra solo la lista, como en el diseño. `por_quitar` es el gasto que espera la
    confirmación para quitarse.
    """
    grafica = calculos.grafica_cobrado_y_gastado(request.taller, hoy=mes)
    return {
        "mes": mes,
        "texto_mes": texto_del_mes(mes),
        "cifras": calculos.resumen_del_mes(request.taller, mes.year, mes.month),
        "grafica": grafica,
        # La nota de la gráfica: sus líneas dicen "2 M" o, si todo es poco, "500 mil".
        "grafica_en_millones": max(max(m.cobrado, m.gastado) for m in grafica) >= 1_000_000,
        "gastos": list(gastos_del_mes(request, mes)),
        "form": form,
        "por_quitar": por_quitar,
    }


def contexto_resumen(request, mes):
    """Todo lo que dibuja la pantalla Resumen para ese mes."""
    taller = request.taller
    return {
        **contexto_de_la_plata(request, mes),
        "mes_anterior": texto_del_mes(calculos.sumar_meses(mes, -1)),
        "mes_siguiente": texto_del_mes(calculos.sumar_meses(mes, 1)),
        "ventas": barras(calculos.ventas_por_tipo(taller, mes.year, mes.month)),
        "personas": barras(calculos.en_produccion_por_persona(taller)),
    }


@solo_duena
@require_GET
def resumen(request):
    mes = mes_elegido(request.GET.get("mes"))
    return render(request, "finanzas/resumen.html", contexto_resumen(request, mes))


# --- Gastos -----------------------------------------------------------------------------


def _con_tarjeta(request):
    """True si la petición viene de la tarjeta de gastos (HTMX) y la espera de vuelta.

    Las páginas aparte (sin JavaScript) usan la ventana; si alguien las abre con
    JavaScript, sus envíos apuntan a #ventana y se responden volviendo al resumen.
    """
    return es_htmx(request) and request.headers.get("HX-Target") != "ventana"


def _tarjeta(request, mes, status=200, con_cifras=True, **extra):
    """La tarjeta "Gastos del mes": lo de adentro de su lista y, aparte (hx-swap-oob), su
    cabeza y, si el gasto cambió algo, las cifras y la gráfica.

    La tarjeta y la caja de su lista se quedan en la página (finanzas/_gastos.html): en
    computador la lista se desplaza por dentro y así no vuelve al principio con cada acción.
    """
    contexto = contexto_de_la_plata(request, mes, **extra)
    html = render_to_string("finanzas/_gastos_lista.html", contexto, request=request)
    contexto["oob"] = True
    html += render_to_string("finanzas/_gastos_cabeza.html", contexto, request=request)
    if con_cifras:
        html += render_to_string("finanzas/_cifras.html", contexto, request=request)
        html += render_to_string("finanzas/_grafica.html", contexto, request=request)
    return HttpResponse(html, status=status)


def _volver_al_mes(request, mes):
    url = url_del_mes(mes) + "#gastos"
    if es_htmx(request):
        return HttpResponse(headers={"HX-Redirect": url})
    return redirect(url)


def _pagina_del_formulario(request, form, mes, status=200):
    """"Registrar gasto" como página aparte, para cuando no hay JavaScript."""
    contexto = {
        "form": form,
        "texto_mes": texto_del_mes(mes),
        "accion": reverse("finanzas:gasto_nuevo"),
        "titulo_pagina": "Registrar gasto",
    }
    return responder_ventana(request, "finanzas/_gasto_nuevo.html", contexto, status=status)


@solo_duena
@require_http_methods(["GET", "POST"])
def gasto_nuevo(request):
    """Registrar un gasto, del mes que se está viendo o de otra fecha, si se cambia.

    GET abre el formulario: con HTMX, dentro de la tarjeta (y con ?cancelar=1 la tarjeta
    vuelve a quedar sin él); sin JavaScript, como página aparte. POST lo registra.
    """
    if request.method == "GET":
        mes = mes_elegido(request.GET.get("mes"))
        if "cancelar" in request.GET:
            if _con_tarjeta(request):
                return _tarjeta(request, mes, con_cifras=False)
            return _volver_al_mes(request, mes)
        form = FormularioGasto().enfocar()
        if _con_tarjeta(request):
            return _tarjeta(request, mes, con_cifras=False, form=form)
        return _pagina_del_formulario(request, form, mes)
    mes = mes_elegido(request.POST.get("mes"))
    form = FormularioGasto(request.POST, instance=Gasto(taller=request.taller))
    if not form.is_valid():
        form.enfocar()  # el cursor vuelve al campo que hay que corregir
        if _con_tarjeta(request):
            return _tarjeta(request, mes, status=422, con_cifras=False, form=form)
        return _pagina_del_formulario(request, form, mes, status=422)
    gasto = form.save()
    mes_del_gasto = gasto.fecha.replace(day=1)
    if _con_tarjeta(request) and mes_del_gasto == mes:
        # El formulario queda abierto, vacío y con el cursor listo para el siguiente gasto.
        respuesta = _tarjeta(request, mes, form=FormularioGasto().enfocar())
    else:
        # Sin JavaScript, o si la fecha es de otro mes: se abre el mes del gasto, para verlo.
        respuesta = _volver_al_mes(request, mes_del_gasto)
    return avisar(request, respuesta, AVISO_REGISTRADO)


@require_http_methods(["GET", "POST"])
def gasto_quitar(request, pk):
    """Quitar un gasto, con un paso de confirmación.

    GET pregunta: con HTMX, la tarjeta trae la pregunta en el lugar del gasto (y con
    ?cancelar=1 vuelve a quedar como estaba); sin JavaScript, una página con la pregunta.
    POST lo quita.
    """
    gasto = obtener_o_404(request, Gasto, pk=pk)
    exigir_duena(request)
    mes = gasto.fecha.replace(day=1)
    if request.method == "POST":
        gasto.delete()
        if _con_tarjeta(request):
            respuesta = _tarjeta(request, mes)
        else:
            respuesta = _volver_al_mes(request, mes)
        return avisar(request, respuesta, AVISO_QUITADO)
    if "cancelar" in request.GET:
        if _con_tarjeta(request):
            return _tarjeta(request, mes, con_cifras=False)
        return _volver_al_mes(request, mes)
    if _con_tarjeta(request):
        return _tarjeta(request, mes, con_cifras=False, por_quitar=gasto)
    contexto = {
        "gasto": gasto,
        "accion": reverse("finanzas:gasto_quitar", args=[gasto.pk]),
        "titulo_pagina": "Quitar gasto",
    }
    return responder_ventana(request, "finanzas/_gasto_quitar.html", contexto)


# --- Descarga para Excel ------------------------------------------------------------------


@solo_duena
@require_GET
def excel(request):
    """Todo lo del taller en un archivo de Excel (finanzas/excel.py), para descargar.

    Es el mismo archivo desde Hoy, Pedidos y Resumen (piezas/_boton_excel.html).
    """
    respuesta = HttpResponse(libro_del_taller(request.taller), content_type=TIPO_DE_ARCHIVO)
    nombre = nombre_del_archivo(request.taller, timezone.localdate())
    respuesta["Content-Disposition"] = f'attachment; filename="{nombre}"'
    return respuesta
