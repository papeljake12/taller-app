#!/usr/bin/env bash
# Actualiza la aplicación en el servidor con lo último de la rama principal (main).
#
#   bash /srv/taller/app/herramientas/servidor/actualizar.sh
#
# Hace, en orden: una copia de seguridad, git pull, instala las librerías, migra la base,
# reúne los archivos estáticos, revisa los ajustes y reinicia Gunicorn. Si un paso falla, se
# detiene ahí y la aplicación sigue corriendo con la versión anterior (salvo que la falla
# sea después de migrar: ver "Volver a la versión anterior" en docs/guia-publicacion.md).

set -euo pipefail
cd /srv/taller/app
PYTHON=.venv/bin/python

echo "== 1/7 Copia de seguridad antes de actualizar"
bash herramientas/servidor/copia-de-seguridad.sh

echo "== 2/7 Versión actual (anótala por si hay que volver):"
git log --oneline -1

echo "== 3/7 Traer los cambios"
git pull --ff-only

echo "== 4/7 Instalar las librerías (las de uv.lock, sin las de desarrollo)"
uv sync --no-dev --locked

echo "== 5/7 Revisar los ajustes y migrar la base de datos"
"$PYTHON" manage.py check --deploy --fail-level WARNING
"$PYTHON" manage.py migrate --noinput
"$PYTHON" manage.py createcachetable

echo "== 6/7 Reunir los archivos estáticos"
"$PYTHON" manage.py collectstatic --noinput

echo "== 7/7 Reiniciar la aplicación (pide tu contraseña)"
sudo systemctl restart taller
sleep 2
systemctl is-active taller

echo "Listo. Versión nueva:"
git log --oneline -1
