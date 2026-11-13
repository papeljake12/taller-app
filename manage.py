#!/usr/bin/env python
"""Herramienta de Django para tareas del proyecto: correr el servidor, migrar, etc.

Usa los ajustes de config/settings/local.py, salvo que DJANGO_SETTINGS_MODULE diga otro
(en el sistema o en el .env). En el servidor, el .env trae
DJANGO_SETTINGS_MODULE=config.settings.produccion. Ver docs/guia-publicacion.md.
"""

import sys
from pathlib import Path


def main():
    from config import entorno

    entorno.elegir_ajustes(Path(__file__).resolve().parent, "config.settings.local")
    from django.core.management import execute_from_command_line

    execute_from_command_line(sys.argv)


if __name__ == "__main__":
    main()
