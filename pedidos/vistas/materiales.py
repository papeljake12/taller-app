"""Materiales de un pedido (T12): agregar, marcar como comprado y quitar.

Cada acción responde solo la tarjeta "Materiales" (con HTMX) o vuelve al pedido (sin
JavaScript). Un material se busca siempre dentro de su pedido, y el pedido dentro del
taller de la usuaria: el número de un material de otro pedido responde 404.

Agregar y quitar dicen "Material agregado." y "Material quitado." (config/avisos.py; la demo
no trae texto para estas dos). Marcar la casilla no lleva aviso: se ve justo donde se tocó.
"""

from django.shortcuts import redirect, render
from django.urls import reverse
from django.views.decorators.http import require_POST

from config.avisos import avisar
from config.ventanas import es_htmx
from cuentas.aislamiento import obtener_o_404
from pedidos import calculos
from pedidos.formularios.materiales import CompradoForm, MaterialForm
from pedidos.models import Material, Pedido


def contexto_de_materiales(pedido, form=None, avisos=()):
    """La lista de compras del pedido, "N de M comprados" y el formulario para agregar.

    `avisos`: un mensaje arriba de la lista, cuando no se pudo marcar un material.
    """
    comprados, total = calculos.materiales_comprados(pedido)
    return {
        "materiales": pedido.materiales.all(),
        "materiales_comprados": comprados,
        "materiales_total": total,
        "form_material": form or MaterialForm(),
        "avisos_materiales": avisos,
    }


def _material(request, pedido, pk):
    """Un material de ese pedido. Si es de otro pedido o de otro taller: 404."""
    return obtener_o_404(request, Material.objects.filter(pedido=pedido), pk=pk)


def _responder(request, pedido, form=None, avisos=(), status=200):
    if es_htmx(request):
        contexto = {"pedido": pedido, **contexto_de_materiales(pedido, form, avisos)}
        return render(request, "pedidos/_materiales.html", contexto, status=status)
    if status == 200:
        return redirect(reverse("pedidos:detalle", args=[pedido.pk]) + "#pedido-materiales")
    # Sin JavaScript y con errores: la página completa, con los mensajes en su tarjeta.
    # detalle.py usa este módulo para armar la página; se importa aquí adentro para que
    # los dos módulos no se importen el uno al otro al arrancar.
    from pedidos.vistas import detalle

    contexto = detalle.contexto_del_pedido(request, detalle.obtener_pedido(request, pedido.pk))
    contexto.update(contexto_de_materiales(pedido, form, avisos))
    return render(request, "pedidos/pedido.html", contexto, status=status)


@require_POST
def nuevo(request, pk):
    pedido = obtener_o_404(request, Pedido, pk=pk)
    form = MaterialForm(request.POST)
    if not form.is_valid():
        return _responder(request, pedido, form, status=422)
    material = form.save(commit=False)
    material.pedido = pedido
    material.save()
    return avisar(request, _responder(request, pedido), "Material agregado.")


@require_POST
def comprado(request, pk, material):
    """Marca o desmarca: el formulario dice cómo debe quedar ("si" o "no")."""
    pedido = obtener_o_404(request, Pedido, pk=pk)
    material = _material(request, pedido, material)
    form = CompradoForm(request.POST)
    if not form.is_valid():
        return _responder(request, pedido, avisos=form.errors["comprado"], status=422)
    material.comprado = form.cleaned_data["comprado"] == "si"
    material.save(update_fields=["comprado", "actualizado"])
    return _responder(request, pedido)


@require_POST
def quitar(request, pk, material):
    pedido = obtener_o_404(request, Pedido, pk=pk)
    _material(request, pedido, material).delete()
    return avisar(request, _responder(request, pedido), "Material quitado.")
