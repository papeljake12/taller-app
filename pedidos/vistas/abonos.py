"""Abonos (T08) y recibo en PDF (T09): la tarjeta "Pagos" del pedido por dentro.

Cada acción busca el pedido en el taller de la usuaria y el abono dentro de ese pedido:
si alguno no es de ahí, responde 404 y no cambia nada.

Con HTMX, cada acción devuelve solo la tarjeta Pagos (pedidos/_pagos.html), que reemplaza
a la que está en la página. Sin JavaScript, los formularios hacen un envío normal y vuelven
al pedido.
"""

from dataclasses import dataclass

from django.http import HttpResponse
from django.shortcuts import redirect, render
from django.urls import reverse
from django.views.decorators.http import require_GET, require_http_methods, require_POST

from config.ventanas import es_htmx, responder_ventana
from cuentas.aislamiento import obtener_o_404
from pedidos import calculos, mensajes
from pedidos.formularios.abonos import FormularioAbono
from pedidos.models import Abono, Pedido
from pedidos.recibo import nombre_del_recibo, recibo_en_pdf


@dataclass
class Pagos:
    """Lo que dibuja la tarjeta Pagos."""

    abonos: list
    abonado: int
    saldo: int
    porcentaje: int
    texto_cobro: str
    enlace_cobro: str  # '' si el cliente no tiene un WhatsApp que sirva
    form: FormularioAbono
    por_quitar: Abono | None = None  # el abono que espera la confirmación para quitarse


def contexto_pagos(request, pedido, form=None, por_quitar=None):
    """Los datos de la tarjeta Pagos (pedidos/_pagos.html): {"pedido": ..., "pagos": ...}.

    La usa el pedido por dentro para dibujar la tarjeta, y las acciones de aquí para
    devolverla sola. `pedido` ya es del taller de la usuaria (obtener_o_404).
    """
    texto = mensajes.texto_cobro(pedido)
    return {
        "pedido": pedido,
        "pagos": Pagos(
            abonos=list(pedido.abonos.all()),
            abonado=calculos.abonado(pedido),
            saldo=calculos.saldo(pedido),
            porcentaje=calculos.porcentaje_pagado(pedido),
            texto_cobro=texto,
            enlace_cobro=mensajes.enlace_whatsapp(pedido.cliente.whatsapp, texto),
            form=form if form is not None else FormularioAbono(),
            por_quitar=por_quitar,
        ),
    }


def _pedido(request, pk):
    """El pedido del taller, con sus cuentas (abonado y saldo) en la misma consulta."""
    consulta = calculos.con_cuentas(Pedido.objects.select_related("cliente", "taller"))
    return obtener_o_404(request, consulta, pk=pk)


def _abono(request, pedido, pk):
    """El abono, solo si es de ese pedido y del taller. Si no, 404."""
    return obtener_o_404(request, Abono.objects.filter(pedido=pedido), pk=pk)


def _con_tarjeta(request):
    """True si la petición viene de la tarjeta Pagos (HTMX) y espera la tarjeta de vuelta.

    Las páginas aparte (sin JavaScript) usan la ventana; si alguien las abre con
    JavaScript, sus envíos apuntan a #ventana y se responden volviendo al pedido.
    """
    return es_htmx(request) and request.headers.get("HX-Target") != "ventana"


def _tarjeta(request, pedido, status=200, **extra):
    return render(request, "pedidos/_pagos.html", contexto_pagos(request, pedido, **extra),
                  status=status)


def _volver_al_pedido(request, pedido):
    url = reverse("pedidos:detalle", args=[pedido.pk]) + "#pagos"
    if es_htmx(request):
        return HttpResponse(headers={"HX-Redirect": url})
    return redirect(url)


@require_POST
def nuevo(request, pk):
    """Registrar un abono. Si pasa del saldo se guarda igual (como en la demo): el saldo
    queda en 0 y la tarjeta dice "Pedido pagado"."""
    pedido = _pedido(request, pk)
    form = FormularioAbono(
        request.POST, instance=Abono(pedido=pedido, registrado_por=request.user)
    )
    if not form.is_valid():
        form.enfocar()  # el cursor vuelve al campo que hay que corregir
        if _con_tarjeta(request):
            return _tarjeta(request, pedido, status=422, form=form)
        contexto = {
            "form": form,
            "pedido": pedido,
            "accion": reverse("pedidos:abono_nuevo", args=[pedido.pk]),
            "titulo_pagina": "Registrar abono",
        }
        return responder_ventana(request, "pedidos/_abono_nuevo.html", contexto, status=422)
    form.save()
    if _con_tarjeta(request):
        # El formulario vuelve vacío y con el cursor listo para el siguiente abono.
        return _tarjeta(request, _pedido(request, pk), form=FormularioAbono().enfocar())
    return _volver_al_pedido(request, pedido)


@require_http_methods(["GET", "POST"])
def quitar(request, pk, abono):
    """Quitar un abono, con un paso de confirmación.

    GET pregunta: con HTMX, la tarjeta trae la pregunta en el lugar del abono (y con
    ?cancelar=1 vuelve a quedar como estaba); sin JavaScript, una página con la pregunta.
    POST lo quita.
    """
    pedido = _pedido(request, pk)
    abono = _abono(request, pedido, abono)
    if request.method == "POST":
        abono.delete()
        if _con_tarjeta(request):
            return _tarjeta(request, _pedido(request, pk))
        return _volver_al_pedido(request, pedido)
    if "cancelar" in request.GET:
        if _con_tarjeta(request):
            return _tarjeta(request, pedido)
        return _volver_al_pedido(request, pedido)
    if _con_tarjeta(request):
        return _tarjeta(request, pedido, por_quitar=abono)
    contexto = {
        "abono": abono,
        "pedido": pedido,
        "accion": reverse("pedidos:abono_quitar", args=[pedido.pk, abono.pk]),
        "titulo_pagina": "Quitar abono",
    }
    return responder_ventana(request, "pedidos/_abono_quitar.html", contexto)


@require_GET
def recibo(request, pk, abono):
    """El recibo de un abono en PDF, para descargar."""
    pedido = _pedido(request, pk)
    abono = _abono(request, pedido, abono)
    respuesta = HttpResponse(recibo_en_pdf(pedido, abono), content_type="application/pdf")
    nombre = nombre_del_recibo(pedido, abono)
    respuesta["Content-Disposition"] = f'attachment; filename="{nombre}"'
    return respuesta
