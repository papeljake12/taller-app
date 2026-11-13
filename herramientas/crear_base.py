"""Crea la base de datos de PostgreSQL que dice DB_NAME en el .env, si no existe.

    uv run python herramientas/crear_base.py

Sirve para preparar un computador nuevo o la copia de trabajo de un carril (cada carril usa
su propia base, por ejemplo DB_NAME=taller_carril_a, para no pisar los datos de otro). El
usuario de DB_USER necesita el permiso CREATEDB. Después: migrate y cargar_ejemplos.
"""

import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))

from config import entorno  # noqa: E402


def main():
    entorno.cargar(RAIZ / ".env")
    import psycopg
    from psycopg import sql

    nombre = entorno.texto("DB_NAME")
    datos = {
        "dbname": "postgres",
        "user": entorno.texto("DB_USER"),
        "password": entorno.texto("DB_PASSWORD", ""),
        "host": entorno.texto("DB_HOST", "localhost"),
        "port": entorno.texto("DB_PORT", "5432"),
        "autocommit": True,
    }
    with psycopg.connect(**datos) as conexion:
        existe = conexion.execute(
            "SELECT 1 FROM pg_database WHERE datname = %s", [nombre]
        ).fetchone()
        if existe:
            print(f"La base {nombre} ya existe.")
            return
        conexion.execute(sql.SQL("CREATE DATABASE {}").format(sql.Identifier(nombre)))
        print(f"Base {nombre} creada.")


if __name__ == "__main__":
    main()
