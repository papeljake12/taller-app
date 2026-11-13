"""Responder con una ventana (<dialog id="ventana"> de base.html).

    from config.ventanas import responder_ventana

    def nuevo(request):
        ...
        return responder_ventana(request, "pedidos/_nuevo.html", {"form": form, "accion": ...})

Si la petición viene de HTMX, devuelve solo el contenido de la ventana. Si no (el enlace se
abrió sin JavaScript), devuelve una página completa con el mismo contenido en una tarjeta.
Un formulario con errores se responde con status=422: HTMX lo dibuja igual.
"""

from django.shortcuts import render


def es_htmx(request):
    return request.headers.get("HX-Request") == "true"


def responder_ventana(request, plantilla, contexto=None, status=200):
    contexto = {**(contexto or {}), "plantilla_ventana": plantilla}
    if es_htmx(request):
        return render(request, plantilla, contexto, status=status)
    return render(request, "piezas/pagina_ventana.html", contexto, status=status)
