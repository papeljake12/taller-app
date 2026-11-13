"""Página interna "Piezas": muestra todas las piezas del diseño juntas, para revisarlas.

Solo existe en el computador de desarrollo (DEBUG). En el servidor responde 404.
Los valores que muestra son de ejemplo, copiados de las páginas de diseno/.
"""

from datetime import date

from django import forms
from django.conf import settings
from django.http import Http404
from django.shortcuts import render
from django.templatetags.static import static
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
        # Los valores de ejemplo de la gráfica de diseno/hoy.html, de junio a noviembre.
        "meses_grafica": [
            MesDeGrafica(date(2026, mes, 1), cobrado, gastado)
            for mes, cobrado, gastado in (
                (6, 2_100_000, 800_000), (7, 2_900_000, 1_100_000), (8, 3_600_000, 1_300_000),
                (9, 1_900_000, 700_000), (10, 2_660_000, 600_000), (11, 4_460_000, 939_000),
            )
        ],
        "colores": [
            ("--negro", "#1A1A1A"), ("--texto-2", "#555555"), ("--texto-3", "#8A8A8A"),
            ("--hoja", "#F1F1F1"), ("--tarjeta", "#FFFFFF"), ("--suave", "#F7F7F7"),
            ("--linea", "#E1E1E1"), ("--borde-control", "#C9C9C9"), ("--borde-campo", "#8A8A8A"),
            ("--riel", "#EDEDED"),
            ("--azul", "#2563C9"), ("--gris-grafica", "#A6A6A6"), ("--rojo", "#B3261E"),
            ("--verde", "#1B6E3C"),
        ],
        "iconos": ["tijeras", "contraer", "buscar", "hoy", "pedidos", "calendario",
                   "clientes", "cotizador", "telas", "resumen", "mi-taller", "mas",
                   "visto", "salir"],
    }
    return render(request, "piezas/muestrario.html", contexto)
