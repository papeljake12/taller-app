"""Clientes (T04): la lista con buscador, crear y editar.

El aviso de dotación y el botón "Escribirle" llegan con T19 (tanda 5), en
_clientes_dotacion.html y _clientes_acciones.html.
"""

from django.db import IntegrityError, transaction
from django.http import HttpResponse
from django.shortcuts import redirect, render
from django.urls import reverse

from config.ventanas import es_htmx, responder_ventana
from cuentas.aislamiento import obtener_o_404
from pedidos import calculos
from pedidos.formularios.clientes import MENSAJE_NOMBRE_REPETIDO, ClienteForm
from pedidos.models import Cliente


def apoyo(cuentas):
    """La línea junto al título: "6 clientes, 4 te deben"."""
    total = len(cuentas)
    if not total:
        return "Todavía no tienes clientes"
    deben = sum(1 for c in cuentas if c.debe > 0)
    clientes = "1 cliente" if total == 1 else f"{total} clientes"
    if not deben:
        return f"{clientes}, ninguno te debe"
    return f"{clientes}, {deben} te {'debe' if deben == 1 else 'deben'}"


def clientes(request):
    cuentas = calculos.cuentas_de_clientes(request.taller)
    busqueda = request.GET.get("q", "").strip()
    filas = [
        c for c in cuentas
        if calculos.coincide(busqueda, c.cliente.nombre, c.cliente.get_tipo_display(),
                             c.cliente.whatsapp)
    ]
    contexto = {"filas": filas, "busqueda": busqueda, "hay_clientes": bool(cuentas),
                "apoyo": apoyo(cuentas)}
    # El buscador pide solo la tabla mientras se escribe.
    solo_la_tabla = (
        es_htmx(request)
        and request.headers.get("HX-Target") == "clientes-lista"
        and not request.headers.get("HX-History-Restore-Request")
    )
    if solo_la_tabla:
        return render(request, "pedidos/_clientes_tabla.html", contexto)
    return render(request, "pedidos/clientes.html", contexto)


def _formulario(request, form, cliente=None):
    """Muestra la ventana; si el formulario es válido, guarda y vuelve a la lista."""
    if request.method == "POST" and form.is_valid():
        try:
            with transaction.atomic():
                guardado = form.save(commit=False)
                guardado.taller = request.taller
                guardado.save()
        except IntegrityError:
            # Otra persona creó el mismo nombre justo al mismo tiempo.
            form.add_error("nombre", MENSAJE_NOMBRE_REPETIDO)
        else:
            if es_htmx(request):
                respuesta = HttpResponse()
                respuesta["HX-Redirect"] = reverse("pedidos:clientes")
                return respuesta
            return redirect("pedidos:clientes")
    if cliente:
        accion = reverse("pedidos:cliente_editar", args=[cliente.pk])
        titulo = "Editar cliente"
    else:
        accion = reverse("pedidos:cliente_nuevo")
        titulo = "Nuevo cliente"
    contexto = {"form": form, "cliente": cliente, "accion": accion, "titulo_pagina": titulo}
    status = 422 if form.is_bound else 200
    return responder_ventana(request, "pedidos/_cliente_form.html", contexto, status=status)


def nuevo(request):
    datos = request.POST if request.method == "POST" else None
    return _formulario(request, ClienteForm(datos, taller=request.taller))


def editar(request, pk):
    cliente = obtener_o_404(request, Cliente, pk=pk)
    datos = request.POST if request.method == "POST" else None
    form = ClienteForm(datos, instance=cliente, taller=request.taller)
    return _formulario(request, form, cliente)
