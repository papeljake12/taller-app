"""Formulario público de tallas (T11): lo abre cada persona del grupo con un enlace.

No pide cuenta. La clave del enlace (Pedido.token_tallas) es lo único que dice de qué pedido
es la talla: el formulario nunca recibe el número del pedido. La página muestra el nombre
del taller, el cliente y qué pidió; nunca precios, las tallas de los demás ni el menú.

Qué responde:
- Clave que no existe: 404, con una página que lo explica (pedidos/_publico_no_existe.html).
- Enlace cerrado por la dueña (tallas_abiertas en falso): la página lo dice, y un envío
  responde 403 sin guardar nada.
- Muchos envíos seguidos desde el mismo celular: 429 ("espera un minuto"), ver LIMITE.
- Datos que no sirven: 422, con el mensaje junto a cada campo.
- Talla guardada: lleva a la misma dirección con ?listo=1, que muestra la confirmación con
  el botón para registrar a otra persona. Así, si la persona recarga, no se envía otra vez.

El envío es un formulario normal (sin HTMX), porque así las respuestas 403 y 429 se ven
como página. HTMX solo se usa al cambiar la talla: la página devuelve los campos de abajo,
con las medidas si eligió "A la medida" (pedidos/_publico_talla.html). Si mientras tanto la
dueña cerró el enlace o borró el pedido, la respuesta le pide al navegador recargar, para
que el aviso se vea como página completa y no dentro del formulario.
"""

from django.contrib.auth.decorators import login_not_required
from django.core.cache import cache
from django.http import HttpResponse
from django.shortcuts import redirect, render
from django.urls import reverse
from django.views.decorators.http import require_http_methods

from config.red import ip_del_cliente
from config.ventanas import es_htmx
from pedidos.formularios.publico import TallaPublicaForm
from pedidos.models import Pedido, Talla

# Envíos por minuto que acepta un mismo celular (la misma dirección IP) en un mismo enlace.
# Alcanza de sobra para que una persona envíe la talla de toda su familia, y frena a quien
# quiera llenar el pedido de tallas falsas.
LIMITE = 10
VENTANA_SEGUNDOS = 60

# En la sesión del navegador queda la última talla que envió, solo para mostrarle "¡Listo!"
# una vez después de guardar. No da acceso a nada más.
SESION_LISTO = "talla_publica"


def _pagina(request, parte, contexto, status=200):
    """La página pública (sin menú) con una de sus partes: formulario, listo, cerrado..."""
    return render(request, "pedidos/publico.html", {**contexto, "parte": parte}, status=status)


def _ip(request):
    # La dirección real del celular, también detrás de NGINX: si no, todos los celulares
    # contarían como uno solo (127.0.0.1). Ver config/red.py.
    return ip_del_cliente(request)


def _demasiados_envios(request, token):
    """Cuenta este envío y dice si ya pasó el límite del minuto.

    La cuenta vive en la caché de Django: hoy es la memoria de cada proceso del servidor
    (ver docs/bitacora/T11.md). El minuto empieza con el primer envío.
    """
    clave = f"tallas-publico:{token}:{_ip(request)}"
    cache.add(clave, 0, timeout=VENTANA_SEGUNDOS)
    try:
        envios = cache.incr(clave)
    except ValueError:
        # Justo se venció el minuto entre las dos líneas: empieza otro.
        cache.set(clave, 1, timeout=VENTANA_SEGUNDOS)
        envios = 1
    return envios > LIMITE


def _recargar():
    """Respuesta a HTMX para que el navegador recargue y muestre la página completa."""
    return HttpResponse(headers={"HX-Refresh": "true"})


def _talla_recien_enviada(request, pedido):
    """La talla que este navegador acaba de enviar a este pedido, si la hay (y la olvida).

    La sesión solo guarda su número: se busca dentro del pedido del enlace, así que nunca se
    muestra una talla de otro pedido. La dirección (?listo=1) no dice cuál es.
    """
    pk = request.session.pop(SESION_LISTO, None)
    if pk is None:
        return None
    return Talla.objects.filter(pk=pk, pedido=pedido).first()


def _enfocar(form):
    """El cursor va al primer campo con error o, si no hay, al nombre."""
    primero = next(iter(form.errors), "nombre") if form.is_bound else "nombre"
    form.fields.get(primero, form.fields["nombre"]).widget.attrs["autofocus"] = True


@login_not_required
@require_http_methods(["GET", "POST"])
def formulario(request, token):
    pedido = (
        Pedido.objects.select_related("cliente", "taller").filter(token_tallas=token).first()
    )
    if pedido is None:
        if es_htmx(request):
            return _recargar()
        return _pagina(request, "pedidos/_publico_no_existe.html", {}, status=404)

    contexto = {"pedido": pedido}
    if not pedido.tallas_abiertas:
        if es_htmx(request):
            return _recargar()
        status = 403 if request.method == "POST" else 200
        return _pagina(request, "pedidos/_publico_cerrado.html", contexto, status=status)

    direccion = reverse("pedidos:publico_tallas", args=[token])

    if request.method == "GET":
        if es_htmx(request) and "talla" in request.GET:
            # Cambió la talla: solo los campos de la talla y las medidas.
            form = TallaPublicaForm(
                pedido=pedido, direccion=direccion, initial={"talla": request.GET["talla"]}
            )
            return render(request, "pedidos/_publico_talla.html", {"form": form})
        if "listo" in request.GET:
            talla = _talla_recien_enviada(request, pedido)
            if talla is not None:
                return _listo(request, contexto, talla)
        form = TallaPublicaForm(pedido=pedido, direccion=direccion)
        _enfocar(form)
        return _pagina(request, "pedidos/_publico_form.html", {**contexto, "form": form})

    if _demasiados_envios(request, token):
        respuesta = _pagina(request, "pedidos/_publico_espera.html", contexto, status=429)
        respuesta["Retry-After"] = str(VENTANA_SEGUNDOS)
        return respuesta

    form = TallaPublicaForm(request.POST, pedido=pedido, direccion=direccion)
    if not form.is_valid():
        _enfocar(form)
        return _pagina(
            request, "pedidos/_publico_form.html", {**contexto, "form": form}, status=422
        )
    talla = form.save()
    request.session[SESION_LISTO] = talla.pk
    return redirect(f"{direccion}?listo=1")


def _listo(request, contexto, talla):
    """La confirmación: "¡Listo, Ana!" y el botón para registrar a otra persona."""
    nombre_talla = "a la medida" if talla.talla == Pedido.MEDIDA else talla.talla
    contexto = {**contexto, "talla": talla, "nombre_talla": nombre_talla}
    return _pagina(request, "pedidos/_publico_listo.html", contexto)
