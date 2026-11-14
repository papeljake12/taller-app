"""Foto del pedido (T13): subir, cambiar y quitar. La tarjeta "Foto del pedido" del pedido
por dentro.

La foto se revisa y se reduce en pedidos/fotos.py. Cada acción busca el pedido en el taller
de la usuaria: el número de un pedido de otro taller responde 404 y no cambia nada.

Con HTMX, cada acción devuelve solo la tarjeta (pedidos/_foto.html), que reemplaza a la que
está en la página. Sin JavaScript, el formulario hace un envío normal y vuelve al pedido.

Después de guardar, un aviso corto con los textos de la demo (config/avisos.py): "Foto
guardada." al subirla o cambiarla y "Foto quitada." al quitarla.
"""

from django.http import HttpResponse
from django.shortcuts import redirect, render
from django.template.loader import render_to_string
from django.urls import reverse
from django.views.decorators.http import require_http_methods, require_POST

from config.avisos import avisar
from config.ventanas import es_htmx, responder_ventana
from cuentas.aislamiento import obtener_o_404
from cuentas.permisos import exigir_duena
from pedidos import fotos
from pedidos.models import Pedido


def _con_tarjeta(request):
    """True si la petición viene de la tarjeta (HTMX) y espera la tarjeta de vuelta.

    La pregunta de "Quitar la foto" sin JavaScript es una página aparte; si alguien la abre
    con JavaScript, su envío apunta a #ventana y se responde volviendo al pedido.
    """
    return es_htmx(request) and request.headers.get("HX-Target") != "ventana"


def _responder(request, pedido, form=None, por_quitar=False, status=200):
    """La tarjeta sola (HTMX) o, sin JavaScript, de vuelta al pedido.

    Sin JavaScript y con errores: la página completa del pedido, con el mensaje en la tarjeta.
    """
    contexto = {"pedido": pedido, "form_foto": form, "foto_por_quitar": por_quitar}
    if _con_tarjeta(request):
        respuesta = render(request, "pedidos/_foto.html", contexto, status=status)
        if status == 200 and not por_quitar:
            # La miniatura de la tarjeta de la etapa es esta misma foto: cambia con ella.
            from pedidos.vistas import detalle

            pagina = detalle.contexto_del_pedido(
                request, detalle.obtener_pedido(request, pedido.pk), oob=True
            )
            html = render_to_string("pedidos/_etapa.html", pagina, request=request)
            respuesta.content += html.encode()
        return respuesta
    if status == 200:
        url = reverse("pedidos:detalle", args=[pedido.pk]) + "#pedido-foto"
        if es_htmx(request):
            return HttpResponse(headers={"HX-Redirect": url})
        return redirect(url)
    # detalle.py usa las vistas de las tarjetas para armar la página: se importa aquí adentro
    # para que los dos módulos no se importen el uno al otro al arrancar.
    from pedidos.vistas import detalle

    pagina = detalle.contexto_del_pedido(request, detalle.obtener_pedido(request, pedido.pk))
    pagina.update(contexto)
    return render(request, "pedidos/pedido.html", pagina, status=status)


@require_POST
def subir(request, pk):
    """Subir la foto del pedido o cambiarla por otra. La anterior se borra."""
    pedido = obtener_o_404(request, Pedido, pk=pk)
    form = fotos.FormularioFoto(request.POST, request.FILES)
    if not form.is_valid():
        return _responder(request, pedido, form=form, status=422)
    fotos.guardar(pedido, form.cleaned_data["foto"])
    return avisar(request, _responder(request, pedido), "Foto guardada.")


@require_http_methods(["GET", "POST"])
def quitar(request, pk):
    """Quitar la foto, con un paso de confirmación.

    GET pregunta: con HTMX, la tarjeta trae la pregunta en el lugar de los botones (y con
    ?cancelar=1 vuelve a quedar como estaba); sin JavaScript, una página con la pregunta.
    POST la quita y borra el archivo.
    """
    pedido = obtener_o_404(request, Pedido, pk=pk)
    # La costurera sube o cambia la foto, pero no la quita (docs/04-permisos.md).
    exigir_duena(request)
    if request.method == "POST":
        tenia_foto = bool(pedido.foto)
        fotos.quitar(pedido)
        respuesta = _responder(request, pedido)
        return avisar(request, respuesta, "Foto quitada.") if tenia_foto else respuesta
    if "cancelar" in request.GET or not pedido.foto:
        return _responder(request, pedido)
    if _con_tarjeta(request):
        return _responder(request, pedido, por_quitar=True)
    contexto = {
        "pedido": pedido,
        "accion": reverse("pedidos:foto_quitar", args=[pedido.pk]),
        "titulo_pagina": "Quitar la foto",
    }
    return responder_ventana(request, "pedidos/_foto_quitar.html", contexto)
