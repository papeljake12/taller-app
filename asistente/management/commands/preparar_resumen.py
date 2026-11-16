"""Prepara el resumen de la mañana del agente (T43), uno por taller con el asistente prendido.

    uv run python manage.py preparar_resumen
    uv run python manage.py preparar_resumen --taller 3
    uv run python manage.py preparar_resumen --de-nuevo

Lo corre la tarea de la madrugada del servidor (herramientas/servidor/cron-resumen.txt), a las
5:00 de Bogotá. Por cada taller con el asistente prendido en /admin (los dos límites mayores que
0) le pide el párrafo a Claude con asistente.resumen.escribir y escribe una línea con lo que
pasó. Si el taller ya tiene el resumen de hoy, no lo repite (no se paga dos veces), salvo con
--de-nuevo, que lo reemplaza. Sin la clave de Anthropic no llama a nadie y lo dice.

No cuenta como pregunta: solo anota los tokens del día.
"""

import logging

from django.core.management.base import BaseCommand
from django.utils import timezone

from asistente import cliente as cliente_claude
from asistente import resumen
from asistente.models import ResumenDelDia
from cuentas.models import Taller

registro = logging.getLogger("asistente")


class Command(BaseCommand):
    help = "Prepara el resumen de la mañana de los talleres con el asistente prendido."

    def add_arguments(self, parser):
        parser.add_argument(
            "--taller", type=int, metavar="ID", help="Solo el taller con este número (id)."
        )
        parser.add_argument(
            "--de-nuevo", action="store_true", help="Reemplazar el resumen de hoy si ya existe."
        )

    def handle(self, *args, **opciones):
        claude = cliente_claude.obtener_cliente()
        if claude is None:
            self.stdout.write(self.style.WARNING(
                "No hay clave de Anthropic (ANTHROPIC_API_KEY en el .env): no preparé ningún "
                "resumen."
            ))
            return

        talleres = Taller.objects.filter(
            asistente_limite_mes__gt=0, asistente_limite_dia__gt=0
        ).order_by("pk")
        if opciones["taller"] is not None:
            talleres = talleres.filter(pk=opciones["taller"])
            if not talleres.exists():
                self.stdout.write(self.style.WARNING(
                    f"El taller {opciones['taller']} no existe o tiene el asistente apagado."
                ))
                return

        hoy = timezone.localdate()
        for taller in talleres:
            self.stdout.write(self._preparar(taller, hoy, claude, opciones["de_nuevo"]))

    def _preparar(self, taller, hoy, claude, de_nuevo):
        nombre = f'"{taller.nombre}" ({taller.pk})'
        if not de_nuevo and ResumenDelDia.objects.del_taller(taller).filter(fecha=hoy).exists():
            return f"{nombre}: ya tenía el resumen de hoy (con --de-nuevo lo repito)."
        if not resumen.puntos_del_dia(taller, hoy):
            return f"{nombre}: no hay nada pendiente hoy; no le escribí a Claude."
        try:
            guardado = resumen.escribir(taller, hoy, claude)
        except Exception:  # noqa: BLE001 (un taller que falla no deja sin resumen a los demás)
            registro.exception("Resumen del día: taller %s, falló al prepararlo.", taller.pk)
            guardado = None
        if guardado is None:
            return self.style.WARNING(
                f"{nombre}: no se pudo preparar el resumen (el motivo quedó en el registro)."
            )
        return self.style.SUCCESS(f"{nombre}: listo el resumen de hoy.")
