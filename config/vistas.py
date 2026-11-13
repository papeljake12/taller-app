"""Página interna "Piezas": muestra todas las piezas del diseño juntas, para revisarlas.

Solo existe en el computador de desarrollo (DEBUG). En el servidor responde 404.
Los valores que muestra son de ejemplo, copiados de las páginas de diseno/.
"""

import time
from datetime import date

from django import forms
from django.conf import settings
from django.http import Http404, HttpResponse
from django.shortcuts import render
from django.templatetags.static import static
from django.urls import reverse
from django.utils import timezone

from config.menu import construir_menu
from pedidos.calculos import MesDeGrafica


class EjemploForm(forms.Form):
    """Formulario de ejemplo para ver la pieza Campo con y sin error."""

    cliente = forms.CharField(label="Cliente", max_length=80)
    tipo = forms.ChoiceField(
        label="Tipo de cliente",
        choices=[("empresa", "Empresa"), ("comparsa", "Comparsa"), ("colegio", "Colegio"),
                 ("particular", "Particular")],
    )
    fecha_entrega = forms.DateField(
        label="Fecha de entrega", widget=forms.DateInput(attrs={"type": "date"})
    )
    cantidad = forms.IntegerField(
        label="Para cuántas personas", min_value=1, max_value=2000,
        help_text="De 1 a 2000.",
        # Los mismos mensajes del formulario de verdad (pedidos/formularios/lista.py), en tú.
        error_messages={"min_value": "Escribe un número entre 1 y 2000.",
                        "max_value": "Escribe un número entre 1 y 2000.",
                        "invalid": "Escribe un número entero, por ejemplo 20."},
    )
    whatsapp = forms.CharField(label="WhatsApp (opcional)", required=False)
    notas = forms.CharField(label="Notas", required=False, widget=forms.Textarea(attrs={"rows": 3}))


ETAPAS = ["Cotizado", "Confirmado", "En corte", "En confección", "Listo", "Entregado"]

# Los colores de docs/08-diseno.md, para verlos en /piezas/ (las pruebas los comparan con
# static/css/app.css).
COLORES = [
    ("--marco", "#0A0A0A"), ("--menu-actual", "#2B2B2B"), ("--menu-campo", "#262626"),
    ("--hoja", "#FFFFFF"), ("--negro", "#1A1A1A"),
    ("--texto-2", "#616161"), ("--texto-3", "#8A8A8A"), ("--linea", "#EBEBEB"),
    ("--borde", "#E3E3E3"), ("--borde-campo", "#8A8A8A"), ("--suave", "#F7F7F7"),
    ("--gris", "#F1F1F1"), ("--riel", "#EDEDED"), ("--enlace", "#005BD3"),
    ("--azul", "#2563C9"), ("--gris-grafica", "#B5B5B5"), ("--rojo", "#C5280C"),
    ("--gris-fondo", "#EBEBEB"), ("--azul-fondo", "#E0F0FF"), ("--verde-fondo", "#CDFEE1"),
    ("--ambar-fondo", "#FFEF9D"), ("--naranja-fondo", "#FFD6A4"), ("--rojo-fondo", "#FEDAD9"),
]

# Todos los íconos de static/iconos/iconos.svg
ICONOS = [
    "tijeras", "contraer", "buscar", "hoy", "pedidos", "calendario", "clientes", "cotizador",
    "telas", "resumen", "mi-taller", "mas", "visto", "cerrar", "salir", "sumar", "atras",
    "adelante", "arriba", "abajo", "foto", "prenda", "descargar", "subir", "whatsapp",
    "recibo", "reloj", "copiar", "enlace", "editar", "papelera", "informacion",
]

# Los valores de ejemplo de la gráfica de diseno/hoy.html, de junio a noviembre.
MESES_GRAFICA = [
    MesDeGrafica(date(2026, mes, 1), cobrado, gastado)
    for mes, cobrado, gastado in (
        (6, 2_100_000, 800_000), (7, 2_900_000, 1_100_000), (8, 3_600_000, 1_300_000),
        (9, 1_900_000, 700_000), (10, 2_660_000, 600_000), (11, 4_460_000, 939_000),
    )
]


def piezas(request):
    if not settings.DEBUG:
        raise Http404
    vacio = EjemploForm(prefix="vacio")
    con_errores = EjemploForm(
        {"errores-cliente": "Panadería de ejemplo", "errores-tipo": "empresa",
         "errores-cantidad": "0"},
        prefix="errores",
    )
    con_errores.is_valid()
    pasos = [
        {"nombre": nombre, "valor": i,
         "estado": "hecho" if i < 2 else "actual" if i == 2 else "pendiente"}
        for i, nombre in enumerate(ETAPAS)
    ]
    fotos = [
        {"url": static("ejemplo/foto-comparsa.jpg"), "nombre": "Polleras de comparsa",
         "descripcion": "Foto de ejemplo: pollera de comparsa de colores"},
        {"url": static("ejemplo/foto-grado.jpg"), "nombre": "Vestido de grado",
         "descripcion": "Foto de ejemplo: vestido largo de grado azul"},
        {"url": static("ejemplo/foto-fiesta.jpg"), "nombre": "Vestido de fiesta",
         "descripcion": "Foto de ejemplo: vestido corto de fiesta con lunares"},
        {"url": static("ejemplo/foto-comunion.jpg"), "nombre": "Vestido de primera comunión",
         "descripcion": "Foto de ejemplo: vestido blanco de primera comunión"},
    ]
    contexto = {
        # El menú de esta página muestra contadores de ejemplo, para ver cómo quedan.
        "menu": construir_menu(request, contadores={"pedidos": 1, "telas": 2}),
        "hoy": timezone.localdate(),
        "vacio": vacio,
        "con_errores": con_errores,
        "pasos": pasos,
        "fotos": fotos,
        "meses_grafica": MESES_GRAFICA,
        "filas": _filas_de_ejemplo(request),
        # Los colores de docs/08-diseno.md (rediseño del 2026-11-13)
        "colores": COLORES,
        "iconos": ICONOS,
    }
    return render(request, "piezas/muestrario.html", contexto)


# --- Animaciones de ejemplo en /piezas/ ---------------------------------------------------
# Pequeñas acciones de mentira para ver las animaciones: un botón que tarda ("cargando"),
# filas que entran y salen, el cambio de etapa, la ventana y el aviso corto. Solo en
# desarrollo; no guardan nada en la base (las filas viven en la sesión).

DEMORA_EJEMPLO = 1.0  # segundos: lo bastante para ver el botón "cargando"


def _solo_desarrollo(request):
    if not settings.DEBUG:
        raise Http404


def _filas_de_ejemplo(request):
    return request.session.get("piezas_filas", [1, 2, 3])


def piezas_filas(request):
    """Agrega una fila al final (?accion=agregar) o quita una (?quitar=N). Tarda un segundo."""
    from config.avisos import avisar

    _solo_desarrollo(request)
    filas = _filas_de_ejemplo(request)
    texto = ""
    if request.method == "POST":
        time.sleep(DEMORA_EJEMPLO)
        if request.POST.get("quitar"):
            numero = int(request.POST["quitar"])
            filas = [fila for fila in filas if fila != numero]
            texto = "Fila quitada (ejemplo)."
        else:
            filas = filas + [max(filas, default=0) + 1]
            texto = "Fila agregada (ejemplo)."
        request.session["piezas_filas"] = filas
    respuesta = render(request, "piezas/_animaciones_filas.html", {"filas": filas})
    return avisar(request, respuesta, texto) if texto else respuesta


def piezas_etapa(request):
    """Mueve los pasos de ejemplo a la etapa tocada (para ver la transición del paso)."""
    _solo_desarrollo(request)
    actual = int(request.POST.get("estado", 2)) if request.method == "POST" else 2
    pasos = [
        {"nombre": nombre, "valor": i,
         "estado": "hecho" if i < actual else "actual" if i == actual else "pendiente"}
        for i, nombre in enumerate(ETAPAS)
    ]
    return render(request, "piezas/_animaciones_etapa.html", {"pasos": pasos})


def piezas_barras(request):
    """La tarjeta de barras otra vez: al llegar, las barras crecen hasta su valor."""
    _solo_desarrollo(request)
    return render(request, "piezas/_animaciones_barras.html", {"meses_grafica": MESES_GRAFICA})


def piezas_ventana(request):
    """Una ventana de ejemplo. "Guardar" la cierra (con su transición) y muestra el aviso."""
    from config.avisos import avisar
    from config.ventanas import CERRAR_VENTANA, responder_ventana

    _solo_desarrollo(request)
    if request.method == "POST":
        time.sleep(DEMORA_EJEMPLO)
        respuesta = HttpResponse(status=200, headers=CERRAR_VENTANA)
        return avisar(request, respuesta, "Guardado (ejemplo).")
    return responder_ventana(request, "piezas/_animaciones_ventana.html",
                             {"accion": reverse("piezas_ventana"), "objetivo": "#ventana"})
