"""Clientes: la lista con buscador, crear y editar (T04), y los mensajes de WhatsApp (T19).

T19 agrega el aviso de la próxima fecha de dotación (_clientes_dotacion.html), con su
ventana para escribirles a los clientes empresa (?escribir=empresas), y el botón
"Escribirle" de cada cliente (_clientes_acciones.html). Los textos salen de
pedidos/mensajes.py. Con WhatsApp guardado, el botón abre el chat con el mensaje escrito;
sin WhatsApp, copia el mensaje. Nada se envía solo.

Permisos (T21, docs/04-permisos.md): Clientes es solo de la dueña. La costurera recibe 403
en la lista, en "Nuevo cliente" y al editar uno de su taller (el de otro taller, 404).

Aviso corto al guardar (config/avisos.py): "Cliente creado." y "Cliente guardado.". La demo
no crea ni edita clientes aparte (salen de los pedidos), así que no trae texto para esto: son
del mismo estilo que "Pedido guardado." y "Nombre guardado.". Como al guardar se vuelve a la
lista, el aviso sale en la página siguiente.
"""

from dataclasses import dataclass
from datetime import date

from django.db import IntegrityError, transaction
from django.http import HttpResponse
from django.shortcuts import redirect, render
from django.urls import reverse
from django.utils import timezone

from config.avisos import avisar
from config.piezas import dia_y_mes
from config.ventanas import es_htmx, responder_ventana
from cuentas.aislamiento import obtener_o_404
from cuentas.permisos import exigir_duena, solo_duena
from pedidos import calculos, mensajes
from pedidos.formularios.clientes import MENSAJE_NOMBRE_REPETIDO, ClienteForm
from pedidos.models import Cliente, Pedido


def apoyo(cuentas):
    """La línea junto al título: "6 clientes · 4 te deben"."""
    total = len(cuentas)
    if not total:
        return "Todavía no tienes clientes"
    deben = sum(1 for c in cuentas if c.debe > 0)
    clientes = "1 cliente" if total == 1 else f"{total} clientes"
    if not deben:
        return f"{clientes} · ninguno te debe"
    return f"{clientes} · {deben} te {'debe' if deben == 1 else 'deben'}"


def clientes_con_deuda_vencida(taller, hoy):
    """Ids de los clientes con un pedido atrasado que todavía tiene saldo: su deuda va en rojo."""
    pedidos = calculos.con_cuentas(Pedido.objects.del_taller(taller))
    return {p.cliente_id for p in pedidos if p.saldo > 0 and calculos.esta_atrasado(p, hoy)}


def mensaje(numero, texto):
    """El texto y el enlace de WhatsApp. Sin un número que sirva, el enlace es "" y se copia."""
    return {"texto": texto, "enlace": mensajes.enlace_whatsapp(numero, texto)}


def fechas_de_dotacion():
    """'el 30 de abril, el 31 de agosto y el 20 de diciembre' (calculos.FECHAS_DOTACION)."""
    # El año no se muestra: se usa uno bisiesto para que cualquier día y mes exista.
    fechas = [f"el {dia_y_mes(date(2000, mes, dia))}" for mes, dia in calculos.FECHAS_DOTACION]
    return ", ".join(fechas[:-1]) + " y " + fechas[-1]


def cuanto_falta(dias):
    if dias == 0:
        return "es hoy"
    if dias == 1:
        return "falta 1 día"
    return f"faltan {dias} días"


@dataclass(frozen=True)
class EmpresaParaEscribir:
    """Un cliente empresa en la ventana "Escribirles": su nombre y el mensaje de dotación."""

    cliente: Cliente
    mensaje: dict


@dataclass(frozen=True)
class AvisoDeDotacion:
    """El aviso azul (.banner) de Clientes (diseno/clientes.html).

    titulo: "Dotación del 20 de diciembre: faltan 39 días".
    apoyo: las tres fechas y cuántos clientes empresa hay.
    boton: "Escribirles a los 2"; vacío si no hay clientes empresa (no se muestra).
    """

    fecha: date
    titulo: str
    apoyo: str
    boton: str
    texto: str  # el mensaje de dotación (mensajes.texto_dotacion)
    empresas: list


def aviso_de_dotacion(taller, hoy=None):
    hoy = hoy or timezone.localdate()
    fecha = calculos.proxima_dotacion(hoy)
    texto = mensajes.texto_dotacion(taller, hoy)
    empresas = [
        EmpresaParaEscribir(cliente, mensaje(cliente.whatsapp, texto))
        for cliente in calculos.clientes_empresa(taller)
    ]
    total = len(empresas)
    if total == 0:
        tienes, boton = "Todavía no tienes clientes empresa.", ""
    elif total == 1:
        tienes, boton = "Tienes 1 cliente empresa.", "Escribirle a tu cliente empresa"
    else:
        tienes, boton = f"Tienes {total} clientes empresa.", f"Escribirles a los {total}"
    return AvisoDeDotacion(
        fecha=fecha,
        titulo=f"Dotación del {dia_y_mes(fecha)}: {cuanto_falta((fecha - hoy).days)}",
        apoyo=f"Las empresas entregan dotación {fechas_de_dotacion()}. {tienes}",
        boton=boton,
        texto=texto,
        empresas=empresas,
    )


@solo_duena
def clientes(request):
    hoy = timezone.localdate()
    if request.GET.get("escribir") == "empresas":
        # La ventana del botón "Escribirles a los 2" del aviso de dotación.
        contexto = {"aviso": aviso_de_dotacion(request.taller, hoy),
                    "titulo_pagina": "Escribirles por la dotación"}
        return responder_ventana(request, "pedidos/_clientes_dotacion_empresas.html", contexto)

    cuentas = calculos.cuentas_de_clientes(request.taller)
    busqueda = request.GET.get("q", "").strip()
    filas = [
        c for c in cuentas
        if calculos.coincide(busqueda, c.cliente.nombre, c.cliente.get_tipo_display(),
                             c.cliente.whatsapp)
    ]
    # "Escribirle": el mismo mensaje para todos, con el WhatsApp de cada uno. La tabla
    # (_clientes_tabla.html, de T04) le pasa a _clientes_acciones.html solo el cliente.
    oferta = mensajes.texto_oferta(request.taller)
    vencidos = clientes_con_deuda_vencida(request.taller, hoy)
    for fila in filas:
        fila.cliente.mensaje = mensaje(fila.cliente.whatsapp, oferta)
    contexto = {"filas": filas, "busqueda": busqueda, "hay_clientes": bool(cuentas), "vencidos": vencidos,
                "apoyo": apoyo(cuentas)}
    # El buscador pide solo la tabla mientras se escribe.
    solo_la_tabla = (
        es_htmx(request)
        and request.headers.get("HX-Target") == "clientes-lista"
        and not request.headers.get("HX-History-Restore-Request")
    )
    if solo_la_tabla:
        return render(request, "pedidos/_clientes_tabla.html", contexto)
    contexto["aviso"] = aviso_de_dotacion(request.taller, hoy)
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
            else:
                respuesta = redirect("pedidos:clientes")
            return avisar(request, respuesta, "Cliente guardado." if cliente else "Cliente creado.")
    if cliente:
        accion = reverse("pedidos:cliente_editar", args=[cliente.pk])
        titulo = "Editar cliente"
    else:
        accion = reverse("pedidos:cliente_nuevo")
        titulo = "Nuevo cliente"
    contexto = {"form": form, "cliente": cliente, "accion": accion, "titulo_pagina": titulo}
    status = 422 if form.is_bound else 200
    return responder_ventana(request, "pedidos/_cliente_form.html", contexto, status=status)


@solo_duena
def nuevo(request):
    datos = request.POST if request.method == "POST" else None
    return _formulario(request, ClienteForm(datos, taller=request.taller))


def editar(request, pk):
    cliente = obtener_o_404(request, Cliente, pk=pk)
    exigir_duena(request)
    datos = request.POST if request.method == "POST" else None
    form = ClienteForm(datos, instance=cliente, taller=request.taller)
    return _formulario(request, form, cliente)
