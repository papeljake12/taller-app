#!/usr/bin/env python
"""Herramienta de Django para tareas del proyecto: correr el servidor, migrar, etc."""

import os
import sys


def main():
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.local")
    from django.core.management import execute_from_command_line

    execute_from_command_line(sys.argv)


if __name__ == "__main__":
    main()
