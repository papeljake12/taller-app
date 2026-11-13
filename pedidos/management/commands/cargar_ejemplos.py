"""Carga los datos de ejemplo de diseno/ en el "Taller de ejemplo" (T22).

    uv run python manage.py cargar_ejemplos
    uv run python manage.py cargar_ejemplos --taller "Otro nombre"

Si el taller ya tiene datos, los borra y los vuelve a cargar (las usuarias se quedan).
Solo corre en el computador de desarrollo, salvo que se pase --forzar.
"""

from datetime import date

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from cuentas.models import Taller
from pedidos import ejemplos


class Command(BaseCommand):
    help = "Carga los pedidos, tallas, telas y gastos de ejemplo de las páginas de diseno/."

    def add_arguments(self, parser):
        parser.add_argument(
            "--taller", default=ejemplos.NOMBRE_TALLER,
            help=f'Nombre del taller (por defecto, "{ejemplos.NOMBRE_TALLER}"). Se crea si no existe.',
        )
        parser.add_argument(
            "--fecha", type=date.fromisoformat,
            help="Contar las fechas desde este día (AAAA-MM-DD) en vez de hoy.",
        )
        parser.add_argument(
            "--forzar", action="store_true", help="Correr aunque no sea el computador de desarrollo."
        )

    def handle(self, *args, **opciones):
        if not settings.DEBUG and not opciones["forzar"]:
            raise CommandError(
                "Esto borra y vuelve a cargar los datos del taller de ejemplo. Solo corre en "
                "desarrollo; para correrlo aquí, agrega --forzar."
            )
        try:
            # Todo o nada: si algo falla, tampoco queda creado el taller.
            with transaction.atomic():
                taller, creado = Taller.objects.get_or_create(nombre=opciones["taller"])
                ejemplos.cargar(taller, hoy=opciones["fecha"])
        except ValueError as error:
            raise CommandError(str(error)) from error
        accion = "Creé" if creado else "Recargué"
        self.stdout.write(self.style.SUCCESS(
            f'{accion} los datos de ejemplo en "{taller}": {len(ejemplos.PEDIDOS)} pedidos, '
            f"{len(ejemplos.GASTOS)} gastos, {len(ejemplos.TELAS)} telas y "
            f"{len(ejemplos.PRENDAS)} prendas guardadas."
        ))
