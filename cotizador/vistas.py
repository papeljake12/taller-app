"""Cotizador (T15): datos a la izquierda, resultado a la derecha, y "Mis prendas".

Toda la pantalla es un solo formulario (cotizador/_formulario.html, id="cotizador"):
- Mientras se escribe, HTMX lo manda a `calcular`, que devuelve solo la tarjeta del
  resultado (_resultado.html, id="resultado"). Las cuentas salen de calculos.cotizar.
- Al elegir una de "Mis prendas", `calcular` ve que la prenda elegida no es la que ya se
  pasó a los campos (`aplicada`) y devuelve el formulario entero con sus costos.
- "Guardar esta prenda", "Quitar de mi lista" y "Crear pedido con esta cotización" mandan
  el formulario entero (con lo escrito) y reciben el formulario entero, o, al crear el
  pedido, la orden de ir a él (HX-Redirect).
Sin JavaScript todo funciona igual con envíos normales: cada respuesta es la página entera.

Aviso corto (config/avisos.py, textos de la demo): "Prenda guardada en tu lista.", "Prenda
quitada de tu lista." y, al crear el pedido, "Pedido creado como cotizado." (este llega a la
página del pedido). Sin JavaScript no hay aviso corto: el de la prenda sale como nota en la
tarjeta "Qué prenda".

Todo se busca en el taller de la usuaria (cuentas/aislamiento.py): una prenda de otro taller
no se puede elegir, ni guardar encima, ni quitar.

Permisos (T21, docs/04-permisos.md): el cotizador es solo de la dueña (habla de precios). La
costurera recibe 403 en todas sus direcciones; el número de una prenda de otro taller, 404.
"""

from datetime import timedelta

from django.db import IntegrityError, transaction
from django.http import HttpResponse
from django.shortcuts import redirect, render
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.http import require_http_methods, require_POST

from config.avisos import avisar
from config.piezas import metros
from config.ventanas import es_htmx
from cotizador.formularios import (
    CAMPOS_DE_LA_PRENDA,
    FormularioCotizacion,
    datos_con_la_prenda,
)
from cotizador.models import PrendaGuardada
from cuentas.aislamiento import del_taller, obtener_o_404
from cuentas.permisos import exigir_duena, solo_duena
from pedidos import mensajes
from pedidos.models import Material, Pedido
from pedidos.vistas.lista import crear_pedido as crear_pedido_cotizado

# Si no se escribe la entrega estimada, el pedido se crea para dentro de 15 días (como en
# la demo). Se puede cambiar después en el pedido.
DIAS_PARA_ENTREGAR = 15

AVISO_DE_ERRORES = "Revisa los campos marcados."


def prendas_del_taller(request):
    return del_taller(request, PrendaGuardada)


def formulario(request, datos=None):
    return FormularioCotizacion(datos or None, prendas=prendas_del_taller(request))


def contexto_cotizador(request, form, **extra):
    """Lo que dibuja la pantalla: el formulario, el resultado y los mensajes para enviar."""
    cotizacion = form.cotizacion()
    errores_del_precio = form.errores_del_precio()
    # Con un valor del precio mal escrito, ese valor cuenta como 0 y el total sale mal: no se
    # puede copiar, enviar ni crear el pedido hasta que se corrija.
    lista = form.lista(cotizacion) and not errores_del_precio
    texto = ""
    enlace = ""
    if lista:
        texto = mensajes.texto_cotizacion(
            request.taller, cotizacion, form.dato("prenda"), form.dato("cliente"),
            form.dato("entrega") or None,
        )
        enlace = mensajes.enlace_whatsapp(form.dato("whatsapp"), texto)
    return {
        "form": form,
        "cotizacion": cotizacion,
        "lista": lista,
        "texto_cotizacion": texto,
        "enlace_whatsapp": enlace,
        "hay_prendas": prendas_del_taller(request).exists(),
        # La prenda guardada que está elegida en "Mis prendas" (para "Quitar de mi lista").
        "elegida": form.dato("guardada") or None,
        "errores_del_precio": errores_del_precio,
        **extra,
    }


def responder(request, contexto, status=200, solo_resultado=False):
    """La página entera (sin JavaScript), el formulario entero o solo el resultado (HTMX)."""
    if not es_htmx(request):
        return render(request, "cotizador/inicio.html", contexto, status=status)
    if solo_resultado:
        return render(request, "cotizador/_resultado.html", contexto, status=status)
    respuesta = render(request, "cotizador/_formulario.html", contexto, status=status)
    if request.headers.get("HX-Target") == "resultado":
        # El cálculo mientras se escribe apunta al resultado: aquí se cambia el formulario
        # entero. Los botones ya apuntan al formulario (hx-target="#cotizador"), y a ellos
        # no se les manda: si el resultado cambió mientras tanto, el botón ya no está en
        # la página y HTMX no podría buscar desde él.
        respuesta["HX-Retarget"] = "#cotizador"
        respuesta["HX-Reswap"] = "outerHTML"
    return respuesta


def responder_con_aviso(request, contexto, texto):
    """El formulario después de guardar o quitar una prenda, con el aviso corto `texto`.

    Sin JavaScript no hay aviso corto: el mismo texto sale como nota en "Qué prenda"."""
    if not es_htmx(request):
        contexto["mensaje_prenda"] = texto
    return avisar(request, responder(request, contexto), texto)


def _datos(request):
    return request.POST if request.method == "POST" else request.GET


@solo_duena
@require_http_methods(["GET"])
def inicio(request):
    contexto = contexto_cotizador(request, formulario(request))
    return render(request, "cotizador/inicio.html", contexto)


@solo_duena
@require_http_methods(["GET", "POST"])
def calcular(request):
    """El resultado, que se actualiza mientras se escribe.

    Si se acaba de elegir una de "Mis prendas" (`guardada` no es la `aplicada`), sus costos
    pasan a los campos y vuelve el formulario entero.
    """
    datos = _datos(request)
    if datos.get("guardada", "") == datos.get("aplicada", ""):
        return responder(request, contexto_cotizador(request, formulario(request, datos)),
                         solo_resultado=True)
    prenda = _prenda_elegida(request, datos.get("guardada"))
    form = formulario(request, datos_con_la_prenda(datos, prenda))
    return responder(request, contexto_cotizador(request, form))


def _prenda_elegida(request, texto):
    """La prenda guardada con ese id en el taller, o None (vacío, inventado o de otro taller)."""
    if not str(texto or "").isdigit():
        return None
    return prendas_del_taller(request).filter(pk=int(texto)).first()


# --- Mis prendas ----------------------------------------------------------------------------


@solo_duena
@require_POST
def prenda_guardar(request):
    """Guarda en "Mis prendas" la prenda con sus costos. Si ya hay una con ese nombre (sin
    mirar mayúsculas), le cambia los costos en vez de crear otra."""
    form = formulario(request, request.POST)
    if not form.exigir_nombre():
        contexto = contexto_cotizador(request, form, aviso=[AVISO_DE_ERRORES])
        return responder(request, contexto, status=422)
    prenda = guardar_prenda(request, form.cleaned_data)
    form = formulario(request, _con_la_elegida(request.POST, prenda))
    return responder_con_aviso(request, contexto_cotizador(request, form),
                               "Prenda guardada en tu lista.")


def _con_la_elegida(datos, prenda):
    """Los mismos datos, con la prenda elegida en "Mis prendas" (sin volver a pasar sus
    costos: lo escrito se queda)."""
    nuevos = datos.copy()
    nuevos["guardada"] = nuevos["aplicada"] = str(prenda.pk)
    return nuevos


def guardar_prenda(request, datos):
    valores = {nombre: datos[nombre] or 0 for nombre in CAMPOS_DE_LA_PRENDA}
    nombre = datos["prenda"]
    for _intento in range(2):
        # Primero la que se llama exactamente igual: desde /admin/ puede haber "Camisa" y
        # "camisa", y cambiarle el nombre a la otra chocaría con la que ya se llama así.
        prendas = prendas_del_taller(request)
        prenda = (
            prendas.filter(nombre=nombre).first()
            or prendas.filter(nombre__iexact=nombre).first()
        )
        if prenda is None:
            prenda = PrendaGuardada(taller=request.taller)
        prenda.nombre = nombre
        for campo, valor in valores.items():
            setattr(prenda, campo, valor)
        try:
            with transaction.atomic():
                prenda.save()
            return prenda
        except IntegrityError:
            # Otra persona la guardó en el mismo momento: se cambia esa.
            continue
    raise IntegrityError("No se pudo guardar la prenda.")


@require_POST
def prenda_quitar(request, pk):
    """Quita una prenda de "Mis prendas", con un paso de confirmación.

    El primer envío pregunta (la pregunta sale en la tarjeta "Qué prenda"); "Sí, quitar"
    vuelve con confirmar=si y la quita; "Cancelar" vuelve con cancelar=si. Lo escrito en el
    cotizador se queda como estaba.
    """
    prenda = obtener_o_404(request, PrendaGuardada, pk=pk)
    exigir_duena(request)
    datos = request.POST
    if datos.get("confirmar") == "si":
        prenda.delete()
        form = formulario(request, datos_con_la_prenda(datos, None))
        return responder_con_aviso(request, contexto_cotizador(request, form),
                                   "Prenda quitada de tu lista.")
    form = formulario(request, _con_la_elegida(datos, prenda))
    por_quitar = None if datos.get("cancelar") == "si" else prenda
    return responder(request, contexto_cotizador(request, form, por_quitar=por_quitar))


# --- Crear el pedido ------------------------------------------------------------------------


@solo_duena
@require_POST
def crear_pedido(request):
    """Crea el pedido en "cotizado" con el total de la cotización y la tela que lleva."""
    form = formulario(request, request.POST)
    if not form.exigir_para_pedido():
        contexto = contexto_cotizador(request, form, aviso=[*form.non_field_errors(),
                                                            AVISO_DE_ERRORES])
        return responder(request, contexto, status=422)
    pedido = pedido_de_la_cotizacion(request, form)
    destino = reverse("pedidos:detalle", args=[pedido.pk])
    if es_htmx(request):
        respuesta = HttpResponse(headers={"HX-Redirect": destino})
    else:
        respuesta = redirect(destino)
    # Lleva a otra página: el aviso va como mensaje y sale en la página del pedido.
    return avisar(request, respuesta, "Pedido creado como cotizado.")


@transaction.atomic
def pedido_de_la_cotizacion(request, form):
    """El pedido nace como los de "Nuevo pedido" (mismo cliente si ya existe) y con un
    material "Tela" con los metros de todo el pedido, como en la demo."""
    datos = form.cleaned_data
    cotizacion = form.cotizacion()
    entrega = datos["entrega"] or timezone.localdate() + timedelta(days=DIAS_PARA_ENTREGAR)
    pedido = crear_pedido_cotizado(
        request,
        {
            "cliente": datos["cliente"],
            "tipo": datos["tipo"],
            "whatsapp": datos["whatsapp"],
            "detalle": f"{datos['cantidad']} × {datos['prenda']}",
            "cantidad": datos["cantidad"],
            "tallaje": Pedido.Tallaje.ADULTO,
            "fecha_entrega": entrega,
            "total": cotizacion.total,
        },
    )
    if cotizacion.metros_totales > 0:
        Material.objects.create(
            pedido=pedido, nombre="Tela", cantidad=metros(cotizacion.metros_totales)
        )
    return pedido
