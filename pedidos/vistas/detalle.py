"""Pedido por dentro (T07): la ficha, la etapa, la encargada, la fecha de entrega, el
WhatsApp del cliente y eliminar el pedido.

Cada acción guarda una sola cosa. Con HTMX responde solo la tarjeta que cambió y, con
hx-swap-oob, las otras partes de la página que dependen de ella (por ejemplo, la etiqueta
de arriba cuando cambia la etapa). Sin JavaScript, vuelve a la página del pedido.
"""

from django.http import HttpResponse
from django.shortcuts import redirect, render
from django.template.loader import render_to_string
from django.urls import reverse
from django.views.decorators.http import require_http_methods, require_POST

from config.ventanas import es_htmx, responder_ventana
from cuentas.aislamiento import del_taller, obtener_o_404
from pedidos import calculos, mensajes
from pedidos.formularios.detalle import EncargadaForm, EntregaForm, EtapaForm, WhatsappForm
from pedidos.models import Pedido
from pedidos.vistas import materiales

Estado = Pedido.Estado


# --- Los datos de cada parte ----------------------------------------------------------------


def obtener_pedido(request, pk):
    """El pedido de la usuaria, con su cliente, su encargada y sus cuentas (abonado y saldo)."""
    consulta = calculos.con_cuentas(Pedido.objects.select_related("cliente", "encargada", "taller"))
    return obtener_o_404(request, consulta, pk=pk)


def pasos_de_etapa(pedido):
    """Las seis etapas para la pieza Pasos: las de antes hechas, la actual y las que faltan."""
    actual = Estado.values.index(pedido.estado)
    return [
        {
            "valor": valor,
            "nombre": nombre,
            "estado": "hecho" if i < actual else "actual" if i == actual else "pendiente",
        }
        for i, (valor, nombre) in enumerate(Estado.choices)
    ]


def frase_de_entrega(pedido, hoy=None):
    """(frase, atrasado): "Se entrega en 33 días.", "Lleva 2 días de atraso."..."""
    if pedido.estado == Estado.ENTREGADO:
        return "Pedido entregado.", False
    dias = calculos.dias_para_entrega(pedido, hoy)
    if calculos.esta_atrasado(pedido, hoy):
        atraso = -dias
        return f"Lleva {atraso} {'día' if atraso == 1 else 'días'} de atraso.", True
    if dias < 0:
        # Un cotizado con la fecha vencida no está atrasado: todavía no se ha confirmado.
        return "La fecha de entrega ya pasó.", False
    if dias == 0:
        return "Se entrega hoy.", False
    if dias == 1:
        return "Se entrega mañana.", False
    return f"Se entrega en {dias} días.", False


def mensaje_para_el_cliente(pedido):
    """El mensaje de "Avisar al cliente": que el pedido está listo o, si debe plata, el saldo.

    None si no hay nada que avisar (un cotizado, o un pedido en producción ya pagado).
    """
    if pedido.estado == Estado.LISTO:
        texto = mensajes.texto_listo(pedido)
    elif pedido.estado != Estado.COTIZADO and calculos.saldo(pedido) > 0:
        texto = mensajes.texto_cobro(pedido)
    else:
        return None
    return {"texto": texto, "enlace": mensajes.enlace_whatsapp(pedido.cliente.whatsapp, texto)}


def aviso_de_listo(pedido):
    """El aviso de pedido listo de la tarjeta Cliente. None si la etapa no es "listo"."""
    if pedido.estado != Estado.LISTO:
        return None
    texto = mensajes.texto_listo(pedido)
    return {"texto": texto, "enlace": mensajes.enlace_whatsapp(pedido.cliente.whatsapp, texto)}


def contexto_de_la_ficha(request, pedido, **extra):
    """Lo que necesitan las partes de T07: encabezado, Etapa, Entrega, Cliente y Eliminar.

    Lo que llega en `extra` (por ejemplo, un formulario con sus errores) reemplaza lo de aquí.
    """
    frase, atrasado = frase_de_entrega(pedido)
    pedidos_del_cliente = del_taller(request, Pedido).filter(cliente=pedido.cliente_id).count()
    contexto = {
        "pedido": pedido,
        "etiqueta": calculos.etiqueta_etapa(pedido),
        "pasos": pasos_de_etapa(pedido),
        "mensaje": mensaje_para_el_cliente(pedido),
        "aviso_listo": aviso_de_listo(pedido),
        "frase_entrega": frase,
        "entrega_atrasada": atrasado,
        "pedidos_del_cliente": pedidos_del_cliente,
        "form_etapa": EtapaForm(initial={"estado": pedido.estado}),
        "form_entrega": EntregaForm(
            instance=pedido, accion=reverse("pedidos:entrega", args=[pedido.pk])
        ),
        "form_encargada": EncargadaForm(
            instance=pedido,
            request=request,
            accion=reverse("pedidos:encargada", args=[pedido.pk]),
        ),
        "form_whatsapp": WhatsappForm(initial={"whatsapp": pedido.cliente.whatsapp}),
    }
    contexto.update(extra)
    return contexto


def contexto_del_pedido(request, pedido, **extra):
    """Todo lo que necesita la página completa. Cada tarea agrega aquí lo de sus partes."""
    contexto = contexto_de_la_ficha(request, pedido, **extra)
    contexto.update(materiales.contexto_de_materiales(pedido))  # T12
    return contexto


# --- Respuestas -------------------------------------------------------------------------------


def responder(request, pedido, parte, otras=(), status=200, **extra):
    """La respuesta de una acción.

    - Con HTMX: la tarjeta `parte` y, marcadas con hx-swap-oob, las `otras` partes que
      también cambiaron. Con errores, status 422 (HTMX la dibuja igual, con los mensajes).
    - Sin JavaScript: si se guardó, vuelve al pedido; con errores, la página completa.
    """
    if not es_htmx(request):
        if status == 200:
            return redirect(reverse("pedidos:detalle", args=[pedido.pk]) + f"#pedido-{parte}")
        contexto = contexto_del_pedido(request, pedido, **extra)
        return render(request, "pedidos/pedido.html", contexto, status=status)
    contexto = contexto_de_la_ficha(request, pedido, **extra)
    html = render_to_string(f"pedidos/_{parte}.html", contexto, request=request)
    for otra in otras:
        html += render_to_string(f"pedidos/_{otra}.html", {**contexto, "oob": True}, request)
    return HttpResponse(html, status=status)


# --- Vistas -----------------------------------------------------------------------------------


def detalle(request, pk):
    pedido = obtener_pedido(request, pk)
    return render(request, "pedidos/pedido.html", contexto_del_pedido(request, pedido))


@require_POST
def etapa(request, pk):
    """Tocar una etapa la guarda. Cambian también la etiqueta de arriba, el aviso al
    cliente, la frase de la entrega y el aviso de pedido listo."""
    pedido = obtener_pedido(request, pk)
    form = EtapaForm(request.POST)
    if not form.is_valid():
        return responder(request, pedido, "etapa", status=422, form_etapa=form)
    pedido.estado = form.cleaned_data["estado"]
    pedido.save(update_fields=["estado", "actualizado"])
    return responder(
        request, pedido, "etapa", otras=("pedido_apoyo", "detalle_avisar", "entrega", "cliente")
    )


@require_POST
def entrega(request, pk):
    """La fecha de entrega. El aviso de cobro dice la fecha: también cambia."""
    pedido = obtener_pedido(request, pk)
    form = EntregaForm(request.POST, instance=pedido)
    if not form.is_valid():
        pedido.refresh_from_db(fields=["fecha_entrega"])
        return responder(request, pedido, "entrega", status=422, form_entrega=form)
    form.save(commit=False).save(update_fields=["fecha_entrega", "actualizado"])
    return responder(request, pedido, "entrega", otras=("detalle_avisar",))


@require_POST
def encargada(request, pk):
    """Quién lo está haciendo: una usuaria del taller (la lista ya viene filtrada)."""
    pedido = obtener_pedido(request, pk)
    form = EncargadaForm(request.POST, instance=pedido, request=request)
    if not form.is_valid():
        pedido.refresh_from_db(fields=["encargada"])
        return responder(request, pedido, "entrega", status=422, form_encargada=form)
    form.save(commit=False).save(update_fields=["encargada", "actualizado"])
    return responder(request, pedido, "entrega")


@require_POST
def whatsapp(request, pk):
    """El WhatsApp del cliente (se guarda en el cliente, no en el pedido)."""
    pedido = obtener_pedido(request, pk)
    form = WhatsappForm(request.POST)
    if not form.is_valid():
        return responder(request, pedido, "cliente", status=422, form_whatsapp=form)
    cliente = pedido.cliente
    cliente.whatsapp = form.cleaned_data["whatsapp"]
    cliente.save(update_fields=["whatsapp", "actualizado"])
    return responder(
        request, pedido, "cliente", otras=("detalle_avisar",), whatsapp_guardado=True
    )


@require_http_methods(["GET", "POST"])
def eliminar(request, pk):
    """GET: la ventana que pregunta si de verdad. POST: borra el pedido y vuelve a Pedidos.

    Con el pedido se borran sus abonos, tallas y materiales, y el archivo de su foto. Los
    gastos que lo nombraban se conservan, sin pedido.
    """
    pedido = obtener_o_404(request, Pedido.objects.select_related("cliente"), pk=pk)
    accion = reverse("pedidos:eliminar", args=[pedido.pk])
    if request.method == "GET":
        contexto = {"pedido": pedido, "accion": accion, "titulo_pagina": "Eliminar el pedido"}
        return responder_ventana(request, "pedidos/_detalle_eliminar.html", contexto)
    foto = pedido.foto.name
    almacen = pedido.foto.storage
    pedido.delete()
    if foto:
        almacen.delete(foto)
    lista = reverse("pedidos:lista")
    if es_htmx(request):
        return HttpResponse(status=204, headers={"HX-Redirect": lista})
    return redirect(lista)
