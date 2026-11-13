#!/usr/bin/env bash
# Copia de seguridad del taller: la base de datos y las fotos y logos subidos.
#
#   bash /srv/taller/app/herramientas/servidor/copia-de-seguridad.sh
#
# Deja en /srv/taller/copias dos archivos con la fecha y la hora:
#   base-2026-11-13_0230.dump      la base de datos completa (formato de pg_dump, comprimido)
#   media-2026-11-13_0230.tar.gz   la carpeta de fotos y logos
# y borra los de hace más de 14 días.
#
# Lee el nombre, el usuario y la contraseña de la base, y la carpeta de fotos
# (DJANGO_MEDIA_ROOT), del .env de la aplicación, así que no hay que escribirlos en otro
# lado. Lo corre cron todas las noches (ver herramientas/servidor/cron-copia.txt y el paso 17
# de docs/guia-publicacion.md).
#
# Las rutas de abajo son las de la guía. Si usaste otras, cámbialas aquí (o pásalas como
# TALLER_APP y TALLER_COPIAS al correr el script; TALLER_MEDIA reemplaza la del .env).

set -euo pipefail
# Las copias solo las puede leer tu usuario: tienen todos los datos del taller.
umask 077

APP=${TALLER_APP:-/srv/taller/app}
COPIAS=${TALLER_COPIAS:-/srv/taller/copias}
DIAS=14

# Lee una variable del .env (las líneas son NOMBRE=valor). Quita comillas si las tiene.
leer() {
    local valor
    valor=$(grep -E "^$1=" "$APP/.env" | tail -n 1 | cut -d= -f2-) || true
    valor=${valor%\"}; valor=${valor#\"}; valor=${valor%\'}; valor=${valor#\'}
    printf '%s' "${valor:-$2}"
}

# La carpeta de fotos es la misma que usa la aplicación (DJANGO_MEDIA_ROOT del .env). No
# tiene valor por defecto: si falta, es mejor fallar que copiar otra carpeta, vacía.
MEDIA=${TALLER_MEDIA:-$(leer DJANGO_MEDIA_ROOT "")}
if [ -z "$MEDIA" ]; then
    echo "ERROR: falta DJANGO_MEDIA_ROOT en $APP/.env" >&2
    exit 1
fi
BASE=$(leer DB_NAME "")
export PGUSER=$(leer DB_USER "")
export PGPASSWORD=$(leer DB_PASSWORD "")
export PGHOST=$(leer DB_HOST localhost)
export PGPORT=$(leer DB_PORT 5432)
if [ -z "$BASE" ] || [ -z "$PGUSER" ]; then
    echo "ERROR: faltan DB_NAME o DB_USER en $APP/.env" >&2
    exit 1
fi

FECHA=$(date +%Y-%m-%d_%H%M)
mkdir -p "$COPIAS"

# 1. La base de datos. Primero se escribe con .parcial y se renombra al final: así nunca
#    queda un archivo a medias con el nombre de una copia buena.
DUMP="$COPIAS/base-$FECHA.dump"
pg_dump --format=custom --dbname="$BASE" --file="$DUMP.parcial"
# Se comprueba que la copia se puede leer antes de darla por buena.
pg_restore --list "$DUMP.parcial" > /dev/null
mv "$DUMP.parcial" "$DUMP"

# 2. Las fotos y los logos.
MEDIA_TAR="$COPIAS/media-$FECHA.tar.gz"
# Si la carpeta no existe, la ruta está mal: es mejor fallar que guardar una copia vacía.
[ -d "$MEDIA" ] || { echo "ERROR: no existe la carpeta de fotos $MEDIA" >&2; exit 1; }
tar --create --gzip --file="$MEDIA_TAR.parcial" \
    --directory="$(dirname "$MEDIA")" "$(basename "$MEDIA")"
mv "$MEDIA_TAR.parcial" "$MEDIA_TAR"

# 3. Borrar las copias de hace más de 14 días (y algún .parcial que haya quedado de un
#    intento que falló).
find "$COPIAS" -maxdepth 1 -type f \
    \( -name 'base-*.dump' -o -name 'media-*.tar.gz' -o -name '*.parcial' \) \
    -mtime +$((DIAS - 1)) -delete

echo "Copia lista: $(du -h "$DUMP" | cut -f1) de base de datos y $(du -h "$MEDIA_TAR" | cut -f1) de fotos en $COPIAS"
