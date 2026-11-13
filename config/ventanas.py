"""Responder con una ventana (<dialog id="ventana"> de base.html).

    from config.ventanas import responder_ventana

    def nuevo(request):
        ...
        return responder_ventana(request, "pedidos/_nuevo.html", {"form": form, "accion": ...})

Si la petición viene de HTMX, devuelve solo el contenido de la ventana. Si no (el enlace se
abrió sin JavaScript), devuelve una página completa con el mismo contenido en una tarjeta.
En esa página "Cancelar" es un enlace a `volver`: el que mande la vista o, si no, la página
de la que se venía (si es de esta misma aplicación), o Hoy.
Un formulario con errores se responde con status=422: HTMX lo dibuja igual.
Para cerrar la ventana después de guardar, la respuesta lleva la cabecera
CERRAR_VENTANA (static/js/app.js la escucha).
"""

from urllib.parse import urlsplit

from django.shortcuts import render
from django.urls import reverse
from django.utils.http import url_has_allowed_host_and_scheme


CERRAR_VENTANA = {"HX-Trigger": "cerrar-ventana"}


def es_htmx(request):
    return request.headers.get("HX-Request") == "true"


def volver(request, contexto=None):
    """A dónde lleva "Cancelar" en la página: `volver` del contexto, la página anterior o Hoy.

    La anterior solo sirve si es de este mismo sitio y no es esta misma página (al enviar un
    formulario con errores, la anterior es el formulario).
    """
    if contexto and contexto.get("volver"):
        return contexto["volver"]
    anterior = request.headers.get("Referer", "")
    if anterior and url_has_allowed_host_and_scheme(
        anterior, allowed_hosts={request.get_host()}, require_https=request.is_secure()
    ) and urlsplit(anterior).path != request.path:
        return anterior
    return reverse("pedidos:hoy")


def responder_ventana(request, plantilla, contexto=None, status=200):
    contexto = {**(contexto or {}), "plantilla_ventana": plantilla}
    if es_htmx(request):
        return render(request, plantilla, contexto, status=status)
    contexto["volver"] = volver(request, contexto)
    return render(request, "piezas/pagina_ventana.html", contexto, status=status)
