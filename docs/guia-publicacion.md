# Guía para publicar la aplicación en el servidor (VPS)

Esta guía la sigues tú, David, paso por paso. Claude Code no entra al servidor: preparó los
ajustes, los archivos de configuración y esta guía, pero nada se ha probado todavía en un
servidor de verdad. Si un comando responde algo distinto a lo que dice aquí, detente y
pregunta antes de seguir.

Al final la aplicación queda en `https://TU_DOMINIO`, con copia de seguridad todas las noches.

## Antes de empezar

### Cómo leer esta guía

- Los bloques grises son comandos. Se copian y se pegan en la terminal, uno por uno, y se
  oprime Enter. Debajo de cada uno se explica qué hace.
- **Todo lo que empieza por `TU_` es un valor que tú reemplazas** antes de oprimir Enter. Por
  ejemplo, si tu dominio es `taller.midominio.com`, donde dice `TU_DOMINIO` escribes
  `taller.midominio.com`. Los archivos de `herramientas/servidor/` también traen estos
  valores para reemplazar; la guía dice cómo.
- Las contraseñas y claves que generes van en tu gestor de contraseñas (por ejemplo,
  Bitwarden) y en el archivo `.env` del servidor. **Nunca** en el repositorio, ni en un
  chat, ni en una captura de pantalla.
- Pegar en la terminal del servidor: clic derecho (en la ventana de PowerShell) o
  Ctrl+Shift+V.

### Los valores que vas a reemplazar

| En la guía | Qué es | Ejemplo (no es real) |
|---|---|---|
| `TU_IP` | La dirección IP del servidor, la da el proveedor | `203.0.113.10` |
| `TU_DOMINIO` | El nombre con el que se entra a la aplicación | `taller.midominio.com` |
| `TU_USUARIO` | Tu usuario de Linux en el servidor (lo creas en el paso 4) | `david` |
| `TU_CORREO` | Tu correo, para los avisos del certificado https | `tucorreo@ejemplo.com` |
| `TU_CUENTA_GITHUB/TU_REPOSITORIO` | El repositorio privado en GitHub | `micuenta/taller-app` |

### Cómo queda armado

```
Celular ──https──> NGINX (puertos 80 y 443) ──> Gunicorn (127.0.0.1:8000) ──> Django ──> PostgreSQL
                     │
                     └── /media/ (fotos y logos): los entrega NGINX directo desde /srv/taller/media
```

- **NGINX** es el portero: recibe a los celulares, pone el candado de https, entrega las
  fotos subidas y le pasa todo lo demás a Gunicorn.
- **Gunicorn** mantiene encendida la aplicación de Django, con 3 procesos que atienden a la
  vez. Los estilos, fuentes e íconos los entrega Whitenoise desde ahí mismo.
- **systemd** es el que enciende Gunicorn cuando arranca el servidor y lo vuelve a encender
  si se cae.

Carpetas en el servidor:

| Carpeta | Qué hay |
|---|---|
| `/srv/taller/app` | El código (copia del repositorio) y el `.env` con los secretos |
| `/srv/taller/media` | Las fotos de los pedidos y los logos que suben las usuarias |
| `/srv/taller/copias` | Las copias de seguridad de los últimos 14 días |

Archivos de configuración que trae el repositorio, en `herramientas/servidor/`:

| Archivo | Para qué | Paso |
|---|---|---|
| `taller.service` | El servicio de systemd que enciende Gunicorn | 12 |
| `nginx-taller.conf` | El sitio de NGINX | 13 |
| `copia-de-seguridad.sh` | La copia de la base de datos y de las fotos | 17 |
| `cron-copia.txt` | La línea que la corre todas las noches | 17 |
| `actualizar.sh` | Pone en el servidor la versión nueva de la aplicación | 20 |

---

## 1. Alquilar el servidor

Un VPS es un computador en internet que alquilas por mes. Para un taller alcanza con el
plan pequeño de cualquier proveedor conocido (DigitalOcean, Hetzner, Vultr, Linode, entre
otros):

- Sistema: **Ubuntu 24.04 LTS** (la guía es para esa versión).
- 1 o 2 núcleos (vCPU), **2 GB de memoria** y 25 GB de disco o más.
- Ubicación: la más cercana a Colombia que ofrezca (por ejemplo, Estados Unidos este).
- Si el proveedor ofrece "copias automáticas" (backups o snapshots) por un poco más, vale la
  pena: son una red extra, aparte de la copia diaria de esta guía.
- Si te deja agregar una **llave SSH** al crearlo, hazlo (ver paso 3). Si no, te da una
  contraseña para `root`.

Anota la dirección IP que te da (`TU_IP`).

## 2. Apuntar el dominio al servidor

En la página donde compraste el dominio, busca la sección **DNS** y crea un registro:

| Tipo | Nombre | Valor |
|---|---|---|
| `A` | `taller` (o `@` si la aplicación va en el dominio principal) | `TU_IP` |

Lo más sencillo es usar un subdominio propio para la aplicación, como
`taller.midominio.com`. Si la pones en el dominio principal (`@`) y tienes otras cosas en
subdominios (`www`, un panel de correo) que solo funcionan con `http`, no prendas
`DJANGO_HSTS_SUBDOMINIOS` en el `.env` (paso 16): esas otras cosas dejarían de abrir.

Si el proveedor del servidor te dio también una dirección IPv6, crea además un registro
`AAAA` con ese valor. El cambio puede tardar desde minutos hasta unas horas en verse. Para
comprobarlo, en PowerShell de tu computador:

```
nslookup TU_DOMINIO
```

Debe responder con `TU_IP`. Mientras no lo haga, puedes seguir hasta el paso 13; el paso 14
(https) sí necesita que el dominio ya apunte al servidor.

## 3. Primera entrada al servidor

Primero, en tu computador, crea tu llave SSH si todavía no tienes una. Es un par de archivos:
uno privado, que nunca sale de tu computador, y uno público, que se copia al servidor. Con
ella entras sin contraseña y nadie puede adivinarla. En PowerShell:

```
ssh-keygen -t ed25519
```

Oprime Enter para aceptar la ubicación y escribe una frase de paso (la pide al usar la
llave). Si ya agregaste la llave al crear el servidor, salta el siguiente comando. Si no,
cópiala al servidor (pide la contraseña de `root` que te dio el proveedor):

```
type $env:USERPROFILE\.ssh\id_ed25519.pub | ssh root@TU_IP "mkdir -p ~/.ssh && cat >> ~/.ssh/authorized_keys"
```

Ahora entra:

```
ssh root@TU_IP
```

La primera vez pregunta si confías en el servidor: escribe `yes`. Ya estás dentro: la línea
de la terminal termina en `#`. Actualiza todo y pon la hora de Bogotá:

```
apt update && apt upgrade -y
```

Descarga e instala las actualizaciones de Ubuntu. Si pregunta algo en una pantalla azul,
deja la opción que viene marcada y oprime Enter.

```
timedatectl set-timezone America/Bogota
```

La hora del servidor queda en la de Bogotá.

```
systemctl restart cron
```

Reinicia cron, el programa que corre la copia de cada noche. Ya estaba encendido con la hora
anterior (la de Londres, UTC) y no se entera del cambio hasta reiniciarse: sin esto, la copia
"de las 2:30" saldría a las 9:30 de la noche de aquí, en plena jornada.

```
dpkg-reconfigure -plow unattended-upgrades
```

Activa las actualizaciones de seguridad automáticas. Responde `Yes`.

## 4. Tu usuario (no trabajar como root)

`root` puede hacer cualquier cosa, incluso borrar todo sin preguntar. Se trabaja con un
usuario normal que pide permiso (`sudo`) para lo delicado.

```
adduser TU_USUARIO
```

Crea tu usuario. Pide una contraseña (guárdala en tu gestor: `sudo` la pedirá) y unos datos
que puedes dejar en blanco con Enter.

```
usermod -aG sudo,adm TU_USUARIO
```

Le da permiso de usar `sudo` (grupo `sudo`) y de leer los registros de todo el servidor (grupo
`adm`). Sin `adm`, `journalctl -u taller` (pasos 12 y 22) solo muestra una parte y esconde
justo los avisos de systemd del tipo "Failed to start", que son los que necesitas cuando la
aplicación no arranca. Como todavía no has entrado con ese usuario, los grupos ya valen la
primera vez que entres. (Si algún día agregas un grupo a un usuario que ya está dentro, debe
salir con `exit` y volver a entrar para que valga.)

```
rsync --archive --chown=TU_USUARIO:TU_USUARIO ~/.ssh /home/TU_USUARIO
```

Copia tu llave SSH a tu usuario, para que entres con ella.

**Sin cerrar esta ventana**, abre otra ventana de PowerShell y entra con tu usuario:

```
ssh TU_USUARIO@TU_IP
```

Si entra sin pedir la contraseña del servidor (solo la frase de tu llave), sigue. Si no,
no sigas: vuelve a la primera ventana y revisa el paso anterior. Ya dentro con tu usuario,
apaga la entrada de `root` y la entrada con contraseña:

```
sudo nano /etc/ssh/sshd_config.d/00-taller.conf
```

Abre un archivo nuevo en el editor `nano`. Escribe estas tres líneas:

```
PermitRootLogin no
PasswordAuthentication no
KbdInteractiveAuthentication no
```

Guarda con Ctrl+O y Enter, y sal con Ctrl+X. (El nombre empieza por `00` a propósito: SSH
hace caso a la primera vez que lee cada ajuste, y así este se lee antes que los demás.)

```
sudo sshd -t && sudo systemctl restart ssh
```

Revisa que el archivo esté bien escrito y reinicia SSH con los cambios.

```
sudo sshd -T | grep -E "permitrootlogin|passwordauthentication"
```

Debe decir `permitrootlogin no` y `passwordauthentication no`. Desde ahora entras siempre con
`ssh TU_USUARIO@TU_IP` (o `ssh TU_USUARIO@TU_DOMINIO` cuando el dominio ya apunte).

## 5. El cortafuegos

Cierra todas las puertas del servidor menos tres: SSH (22) para entrar tú, y 80 y 443 para
la aplicación.

```
sudo ufw allow OpenSSH
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
```

Abre esas tres puertas. **La de SSH va primero**: si se activa el cortafuegos sin ella, te
quedas por fuera.

```
sudo ufw enable
sudo ufw status
```

Lo enciende (responde `y`) y muestra las reglas: deben aparecer `OpenSSH`, `80/tcp` y
`443/tcp`, con `ALLOW`.

## 6. Instalar los programas

```
sudo apt install -y postgresql nginx git curl certbot python3-certbot-nginx
```

Instala PostgreSQL (la base de datos), NGINX, git (para traer el código), curl (para hacer
pruebas) y certbot (el certificado de https).

## 7. Crear la base de datos

Primero genera una contraseña fuerte para el usuario de la base:

```
openssl rand -hex 24
```

Muestra 48 letras y números al azar. **Cópiala a tu gestor de contraseñas** como "Base de
datos del taller". La vas a usar dos veces: aquí y en el `.env` (paso 10).

```
sudo -u postgres psql
```

Entra a PostgreSQL como su administrador. La línea cambia a `postgres=#`. Escribe, una por
una:

```
CREATE ROLE taller LOGIN;
\password taller
```

Crea el usuario `taller` y le pone contraseña: pega la que generaste (no se ve mientras la
escribes) y otra vez para confirmar. Así la contraseña no queda guardada en el historial.

```
CREATE DATABASE taller OWNER taller;
ALTER ROLE taller SET client_encoding TO 'utf8';
ALTER ROLE taller SET default_transaction_isolation TO 'read committed';
ALTER ROLE taller SET timezone TO 'UTC';
\q
```

Crea la base `taller`, de ese usuario, con los ajustes que recomienda Django, y sale. (Las
fechas se guardan en UTC y la aplicación las muestra en hora de Bogotá.) PostgreSQL solo
acepta conexiones desde el mismo servidor: desde internet no se puede llegar a la base.

```
psql -h localhost -U taller -d taller -c "select 'la base responde';"
```

Pide la contraseña y debe responder `la base responde`.

## 8. Las carpetas y uv

```
sudo mkdir -p /srv/taller/media /srv/taller/copias
sudo chown -R $USER:$USER /srv/taller
chmod 755 /srv/taller /srv/taller/media
chmod 700 /srv/taller/copias
```

Crea las carpetas de la aplicación, de las fotos y de las copias, y las deja a tu nombre
(`$USER` es tu usuario; no hay que reemplazarlo). NGINX puede leer las fotos; las copias
solo las puedes leer tú, porque tienen todos los datos del taller.

```
curl -LsSf https://astral.sh/uv/install.sh | sh
source $HOME/.local/bin/env
uv --version
```

Instala `uv`, el mismo programa que usas en tu computador para las librerías de Python, y
comprueba que quedó (muestra su versión).

## 9. Traer el código desde GitHub

El repositorio es privado, así que el servidor necesita permiso para leerlo. Se usa una
**llave de despliegue** (deploy key): una llave SSH que solo sirve para leer ese repositorio
y nada más de tu cuenta. Si un día alguien entra al servidor, no puede tocar tu GitHub.

```
ssh-keygen -t ed25519 -C "servidor-taller" -f ~/.ssh/github_taller -N ""
cat ~/.ssh/github_taller.pub
```

Crea la llave del servidor y muestra su parte pública (una línea que empieza por
`ssh-ed25519`). Cópiala. En GitHub, abre el repositorio → **Settings** → **Deploy keys** →
**Add deploy key**. Título: `Servidor del taller`. Pega la línea. **No** marques "Allow write
access": el servidor solo lee.

```
nano ~/.ssh/config
```

Escribe estas líneas, para que git use esa llave con GitHub, y guarda (Ctrl+O, Enter,
Ctrl+X):

```
Host github.com
    IdentityFile ~/.ssh/github_taller
    IdentitiesOnly yes
```

```
ssh -T git@github.com
```

La primera vez pregunta si confías en GitHub: `yes`. Debe responder "successfully
authenticated" (y que no da acceso a una terminal, eso es normal).

```
git clone git@github.com:TU_CUENTA_GITHUB/TU_REPOSITORIO.git /srv/taller/app
cd /srv/taller/app
git log --oneline -1
```

Copia el código en `/srv/taller/app` y muestra la última versión, que debe ser la última que
aprobaste en `main`.

> **Otra opción: un token.** En vez de la llave se puede usar un "fine-grained personal access
> token" de GitHub con permiso solo de lectura (Contents: Read-only) sobre ese repositorio.
> Funciona, pero vence y queda guardado en el servidor como una contraseña de tu cuenta. La
> llave de despliegue es más sencilla y más segura.

## 10. El archivo .env del servidor

El `.env` tiene los secretos y los datos de este servidor. Se parte de `.env.example`:

```
cd /srv/taller/app
cp .env.example .env
chmod 600 .env
```

Lo crea y deja que solo tu usuario lo pueda leer.

```
python3 -c "import secrets; print(secrets.token_urlsafe(50))"
```

Genera la **clave secreta de Django**: unas 67 letras, números, `-` y `_` al azar. Con ella
Django firma las sesiones: quien la tenga podría hacerse pasar por cualquier usuaria. Va solo
en el `.env` del servidor (no la guardes en otro lado; si se pierde, se genera otra y lo único
que pasa es que todas tienen que volver a entrar).

```
nano .env
```

Deja el archivo así: quita el `#` del comienzo de la línea
`# DJANGO_SETTINGS_MODULE=config.settings.produccion` (está debajo de "Qué ajustes usar",
no es la primera del archivo) y llena los valores:

```
DJANGO_SETTINGS_MODULE=config.settings.produccion
DJANGO_SECRET_KEY=la-clave-que-acabas-de-generar
DJANGO_DEBUG=False
DJANGO_ALLOWED_HOSTS=TU_DOMINIO
DJANGO_CSRF_TRUSTED_ORIGINS=https://TU_DOMINIO
DJANGO_HSTS_SEGUNDOS=3600
DJANGO_HSTS_SUBDOMINIOS=
DJANGO_MEDIA_ROOT=/srv/taller/media
DJANGO_STATIC_ROOT=
DB_NAME=taller
DB_USER=taller
DB_PASSWORD=la-contraseña-del-paso-7
DB_HOST=localhost
DB_PORT=5432
ANTHROPIC_API_KEY=
```

Las líneas de comentario (las que empiezan por `#`) se pueden dejar. Nunca escribas un
comentario al lado de un valor, en la misma línea. Guarda y sal (Ctrl+O, Enter, Ctrl+X).

Qué hace cada una, en corto (la explicación larga está en `docs/bitacora/T24.md`):

- `DJANGO_SETTINGS_MODULE`: usar los ajustes de producción (`config/settings/produccion.py`).
- `DJANGO_ALLOWED_HOSTS` y `DJANGO_CSRF_TRUSTED_ORIGINS`: el dominio. Django rechaza las
  visitas y los formularios que lleguen con otro nombre.
- `DJANGO_HSTS_SEGUNDOS` y `DJANGO_HSTS_SUBDOMINIOS`: ver el paso 16.
- `DJANGO_MEDIA_ROOT`: dónde se guardan las fotos y los logos. Es obligatoria y debe ser
  `/srv/taller/media`, la misma carpeta que entrega NGINX (paso 13) y que guarda la copia de
  seguridad (paso 17).

## 11. Instalar las librerías y preparar la base de datos

Todos estos comandos se corren dentro de `/srv/taller/app`. En el servidor se usa
`.venv/bin/python manage.py ...` (la aplicación ya instalada) en vez de `uv run`, para que
uv no instale las herramientas de desarrollo.

```
uv sync --no-dev --locked
```

Instala Python 3.12 y las librerías con las versiones exactas de `uv.lock`. `--no-dev` deja
por fuera las de las pruebas; `--locked` se niega a seguir si `uv.lock` no coincide con
`pyproject.toml`.

```
.venv/bin/python manage.py check --deploy --fail-level WARNING
```

Revisa que los ajustes estén listos para publicar. Debe terminar en
`System check identified no issues (2 silenced).` Si habla de `DEBUG` o de la clave, revisa
en el `.env` la línea `DJANGO_SETTINGS_MODULE` (que no tenga `#` al comienzo). Si dice "Falta la variable...", falta
esa línea en el `.env`.

```
.venv/bin/python manage.py migrate
```

Crea las tablas de la aplicación en la base de datos.

```
.venv/bin/python manage.py createcachetable
```

Crea la tabla `cache_django`, la memoria compartida de los 3 procesos de Gunicorn. La usa el
límite de envíos por minuto del formulario público de tallas.

```
.venv/bin/python manage.py collectstatic --noinput
```

Reúne los estilos, fuentes, íconos y HTMX en `staticfiles/`, les pone una huella en el nombre
y los comprime. Al final dice cuántos archivos copió.

```
.venv/bin/python manage.py createsuperuser
```

Crea tu usuario administrador para el panel `/admin/`. Usa una contraseña fuerte y distinta
de las demás (guárdala en tu gestor).

## 12. Encender la aplicación con Gunicorn

```
sudo cp herramientas/servidor/taller.service /etc/systemd/system/taller.service
sudo sed -i "s/TU_USUARIO/$USER/g" /etc/systemd/system/taller.service
grep -n "User=" /etc/systemd/system/taller.service
```

Copia el servicio al lugar donde systemd los busca y cambia `TU_USUARIO` por tu usuario
(`$USER` se llena solo). La última línea debe mostrar `User=` con tu usuario.

```
sudo systemctl daemon-reload
sudo systemctl enable --now taller
systemctl status taller
```

systemd lee el servicio nuevo, lo enciende y lo deja encendido para cuando el servidor se
reinicie. El estado debe decir `active (running)` en verde. (Sal con `q`.) Si dice `failed`,
mira el paso 22.

```
curl -sI -H "Host: TU_DOMINIO" -H "X-Forwarded-Proto: https" http://127.0.0.1:8000/entrar/ | head -n 1
```

Le pide la pantalla de "Entrar" a Gunicorn directamente, como lo hará NGINX. Debe responder
`HTTP/1.1 200 OK`.

## 13. NGINX

```
DOMINIO=TU_DOMINIO
```

Guarda tu dominio en una variable para los comandos que siguen. **Aquí sí reemplazas tú**
`TU_DOMINIO` (por ejemplo, `DOMINIO=taller.midominio.com`).

```
sudo cp herramientas/servidor/nginx-taller.conf /etc/nginx/sites-available/taller
sudo sed -i "s/TU_DOMINIO/$DOMINIO/g" /etc/nginx/sites-available/taller
grep -n "server_name" /etc/nginx/sites-available/taller
```

Copia el sitio y cambia `TU_DOMINIO` por tu dominio (`$DOMINIO` se llena solo). La última
línea debe mostrar tu dominio en el primer `server_name` y `_` en los otros dos.

Qué trae el sitio: `client_max_body_size 12m` (para fotos y logos de hasta 10 MB; sin esto
NGINX rechaza las de más de 1 MB), `location /media/` (las fotos subidas, directo desde
`/srv/taller/media`), la compresión `gzip`, y el paso de todo lo demás a Gunicorn con los
encabezados `Host`, `X-Forwarded-For`, `X-Real-IP` y `X-Forwarded-Proto`. Cada línea está
explicada dentro del archivo.

```
sudo rm /etc/nginx/sites-enabled/default
sudo ln -s /etc/nginx/sites-available/taller /etc/nginx/sites-enabled/taller
```

Apaga la página de bienvenida de NGINX y enciende el sitio del taller.

```
sudo nginx -t
sudo systemctl reload nginx
```

Revisa la configuración (debe decir `syntax is ok` y `test is successful`) y la aplica.

```
curl -sI -H "Host: $DOMINIO" http://127.0.0.1/entrar/ | head -n 1
```

Le pide la pantalla de "Entrar" a NGINX con el nombre de tu dominio (funciona aunque el
dominio todavía no apunte al servidor). Debe responder `HTTP/1.1 301 Moved Permanently`:
Django manda a `https://`, que todavía no existe. Es lo esperado; se arregla en el paso
siguiente.

## 14. https con Let's Encrypt (certbot)

Necesita que `nslookup TU_DOMINIO` ya responda con `TU_IP` (paso 2).

```
sudo certbot --nginx -d TU_DOMINIO -m TU_CORREO --agree-tos --no-eff-email --redirect
```

Pide un certificado gratuito a Let's Encrypt, lo instala en el sitio de NGINX y agrega la
redirección de `http://` a `https://`. Certbot cambia el archivo
`/etc/nginx/sites-available/taller` del servidor (no el del repositorio). A `TU_CORREO`
llegan los avisos si algo falla con la renovación.

```
sudo certbot renew --dry-run
systemctl list-timers | grep certbot
```

El certificado dura 90 días y certbot lo renueva solo, dos veces al día revisa si toca. El
primer comando hace un ensayo de la renovación (debe terminar en "Congratulations, all
simulated renewals succeeded"); el segundo muestra el reloj (`certbot.timer`) que la corre.

Abre `https://TU_DOMINIO` en el navegador: debe salir la pantalla de "Entrar" con el candado.

## 15. Primera entrada: el taller y sus usuarias

1. Abre `https://TU_DOMINIO/admin/` y entra con el administrador del paso 11.
2. **Talleres → Agregar**: el nombre del taller (y el teléfono, si quiere). Guardar.
3. **Usuarios → Agregar**: el usuario y la contraseña de la dueña. En la parte "Taller",
   escoge su taller, el rol **Dueña** y el nombre que se verá. Guardar.
4. Igual para cada costurera, con el rol **Costurera**.
5. Sal del panel, abre `https://TU_DOMINIO` y entra con la dueña. Crea un pedido de prueba,
   copia su enlace de tallas y revisa que empiece por `https://`. Sube una foto de varios MB
   para probar el límite de tamaño. Después borra ese pedido.

**Datos de ejemplo:** `cargar_ejemplos` **no se corre en el servidor de verdad**. Crea un
"Taller de ejemplo" con clientes, pedidos y gastos inventados, que se mezclarían con los
reales, y cada vez que corre borra y vuelve a crear los datos de ese taller. Por eso, fuera
del computador de desarrollo se niega a correr. Si algún día montas un servidor **de prueba**
para mostrar la aplicación, ahí sí se corre con:

```
.venv/bin/python manage.py cargar_ejemplos --forzar
```

`--forzar` es la forma de decirle "sí, sé que no es mi computador".

## 16. Una semana después: HSTS a un año

HSTS le dice al navegador: "a este dominio entra siempre por https". El `.env` empieza con una
hora (3600 segundos), para que, si algo sale mal con el certificado en los primeros días, los
celulares lo olviden pronto. Cuando la aplicación lleve una semana funcionando sin problemas
con https:

```
cd /srv/taller/app
nano .env
```

Cambia la línea a `DJANGO_HSTS_SEGUNDOS=31536000` (un año) y guarda.

```
sudo systemctl restart taller
curl -sI https://TU_DOMINIO/entrar/ | grep -i strict
```

Reinicia la aplicación y muestra el encabezado: debe decir `max-age=31536000`.

`DJANGO_HSTS_SUBDOMINIOS` queda vacío (apagado): HSTS vale solo para `TU_DOMINIO` y no para
sus subdominios. Si la aplicación va en un subdominio propio (`taller.midominio.com`) o si
todos tus subdominios tienen https, puedes ponerlo en `True`. Si la aplicación va en el
dominio principal y tienes otras páginas en subdominios sin https, déjalo vacío: con un año
de HSTS, esas páginas no abrirían en los celulares que ya entraron al taller durante todo
ese año.

## 17. Copia de seguridad diaria

El script `herramientas/servidor/copia-de-seguridad.sh` hace, cada vez:

1. Una copia completa de la base de datos con `pg_dump` (formato propio de PostgreSQL, ya
   comprimido), y comprueba que se pueda leer.
2. Un archivo comprimido con la carpeta de fotos y logos.
3. Borra las copias de hace más de 14 días.

Quedan en `/srv/taller/copias`, con la fecha y la hora en el nombre:
`base-2026-11-13_0230.dump` y `media-2026-11-13_0230.tar.gz`. Lee la contraseña de la base
del `.env`, así que no hay que escribirla en otro lado.

Pruébalo a mano primero:

```
bash /srv/taller/app/herramientas/servidor/copia-de-seguridad.sh
ls -lh /srv/taller/copias
```

Debe decir "Copia lista: ..." y mostrar los dos archivos.

Ahora prográmalo para todas las noches con cron (el reloj de tareas de Linux):

```
crontab -e
```

La primera vez pregunta qué editor usar: escoge `nano` (el número 1). Baja hasta el final y
pega la última línea de `herramientas/servidor/cron-copia.txt`:

```
30 2 * * * bash /srv/taller/app/herramientas/servidor/copia-de-seguridad.sh 2>&1 | logger -t copia-taller
```

Quiere decir: a las 2:30 de la madrugada, todos los días, correr la copia y anotar lo que
diga en el registro del sistema con el nombre `copia-taller`. Guarda y sal.

```
crontab -l
```

Muestra las tareas programadas: debe aparecer la línea. Al día siguiente, revisa que corrió:

```
journalctl -t copia-taller --since yesterday
ls -lh /srv/taller/copias
```

Revísalo una vez por semana. Y de vez en cuando mira cuánto disco queda con `df -h /` (la
columna `Use%` no debería pasar de 80 %).

## 18. Sacar las copias del servidor

Las copias del paso 17 viven en el mismo disco que la aplicación. Si el disco falla, si el
proveedor cierra la cuenta, si alguien entra al servidor o si se borra algo por error, se
pierden junto con todo lo demás. **Una copia que está solo en el servidor no es una copia.**
Por eso hay que llevarlas a otro lugar, al menos una vez por semana.

La forma más sencilla: traerlas a tu computador. En PowerShell de tu computador (no en el
servidor):

```
mkdir $HOME\copias-taller
scp "TU_USUARIO@TU_DOMINIO:/srv/taller/copias/*" $HOME\copias-taller\
```

Crea la carpeta (solo la primera vez) y trae todas las copias de los últimos 14 días. Así el
servidor no tiene ninguna clave para llegar a tu computador: aunque alguien entrara al
servidor, no podría borrar estas copias.

Recomendaciones:

- Para tener una segunda copia fuera de tu casa, pon la carpeta `copias-taller` dentro de
  una carpeta que se sincronice con tu nube (Google Drive, OneDrive) o cópiala de vez en
  cuando a un disco externo.
- Las copias tienen los nombres, teléfonos y pagos de los clientes del taller: guárdalas en
  un lugar privado y no las compartas.
- Si el proveedor del servidor ofrece copias automáticas del servidor completo, actívalas
  también. Son útiles, pero no reemplazan esto: quedan en el mismo proveedor.
- Si quieres que se haga solo, en Windows se puede programar ese `scp` con el "Programador
  de tareas". Pregúntale a Claude Code cuando llegues ahí.

## 19. Restaurar una copia

Sirve si se borró algo por error, si una actualización dañó datos, o si hay que montar todo
en un servidor nuevo. **Restaurar reemplaza todo lo que hay por lo que había en esa copia**:
lo que se haya escrito después se pierde.

### En el mismo servidor

```
sudo systemctl stop taller
```

Apaga la aplicación, para que nadie escriba mientras tanto.

```
bash /srv/taller/app/herramientas/servidor/copia-de-seguridad.sh
ls -lh /srv/taller/copias
```

Hace una copia de cómo está todo ahora, por si te equivocas de fecha y quieres volver. Luego
lista las copias: escoge la fecha y hora que quieres restaurar.

```
COPIA=2026-11-12_0230
```

Escribe aquí la fecha y la hora de la copia que escogiste, tal como aparece en el nombre de
los archivos (sin `base-` ni `.dump`). Los siguientes comandos la usan.

```
sudo -u postgres dropdb taller
sudo -u postgres createdb --owner=taller taller
```

Borra la base de datos y crea una vacía con el mismo nombre y dueño. (Si `dropdb` dice que
hay conexiones abiertas, revisa que la aplicación esté apagada y que no tengas un `psql`
abierto en otra ventana.)

```
pg_restore --no-owner --single-transaction -h localhost -U taller -d taller /srv/taller/copias/base-$COPIA.dump
```

Pide la contraseña de la base y carga la copia. `--single-transaction` hace que se cargue
todo o nada: si algo falla, la base queda vacía y lo intentas de nuevo, nunca a medias.

```
mv /srv/taller/media /srv/taller/media-antes-de-restaurar
tar -xzf /srv/taller/copias/media-$COPIA.tar.gz -C /srv/taller
ls /srv/taller/media
```

Aparta las fotos de ahora (no las borra) y saca las de la copia en `/srv/taller/media`.

```
cd /srv/taller/app
.venv/bin/python manage.py migrate
.venv/bin/python manage.py collectstatic --noinput
sudo systemctl start taller
```

Si la copia es de antes de una actualización, `migrate` pone la base al día con el código
actual (si no hay nada que hacer, dice `No migrations to apply`). `collectstatic` deja los
estilos y archivos que corresponden al código que está ahora (si volviste a una versión
anterior en el paso 21, sin esto las pantallas viejas buscarían archivos de la nueva y
fallarían). Luego enciende la aplicación. Entra y revisa los últimos pedidos. Cuando estés seguro de que todo está bien,
borra las fotos apartadas con `rm -r /srv/taller/media-antes-de-restaurar`.

### En un servidor nuevo (si se perdió el servidor)

1. Haz los pasos 1 a 10 en el servidor nuevo (con el mismo dominio; en el paso 2 cambias la
   IP del registro `A` por la del servidor nuevo). Antes de entrar por SSH con el dominio,
   corre en PowerShell de tu computador `ssh-keygen -R TU_DOMINIO`: borra la huella del
   servidor viejo que tu computador recuerda. Sin esto, `ssh` se niega a entrar con el aviso
   `REMOTE HOST IDENTIFICATION HAS CHANGED` (es normal: el servidor es otro).
2. Del paso 11, haz solo `uv sync --no-dev --locked` y el `check --deploy`.
3. Desde tu computador, sube las copias más recientes que tengas (paso 18):
   `scp $HOME\copias-taller\base-FECHA.dump $HOME\copias-taller\media-FECHA.tar.gz TU_USUARIO@TU_IP:/srv/taller/copias/`
4. En el servidor nuevo: `COPIA=FECHA`, luego el `pg_restore` y el `tar -xzf` de arriba (la
   base ya está vacía: no hace falta `dropdb` ni `createdb`, ni el `mv` de las fotos).
5. Luego `migrate`, `createcachetable` y `collectstatic` del paso 11 (no `createsuperuser`:
   tu administrador viene en la copia), y sigue con los pasos 12, 13, 14, 16, 17 y 18.

### Probar que las copias sirven

Una copia que nunca se ha probado puede estar dañada sin que nadie lo sepa. Una vez al mes,
restaura la última en una base aparte, sin tocar la de verdad:

```
sudo -u postgres createdb --owner=taller taller_prueba
pg_restore --no-owner -h localhost -U taller -d taller_prueba /srv/taller/copias/base-FECHA.dump
psql -h localhost -U taller -d taller_prueba -c "select count(*) as pedidos from pedidos_pedido;"
sudo -u postgres dropdb taller_prueba
```

Crea una base de prueba, carga la copia, cuenta los pedidos (debe dar lo mismo que en la
aplicación) y borra la base de prueba. (Esta misma prueba se hizo en el computador de
desarrollo con una copia hecha por el script: dio los mismos 6 pedidos y 58 tallas.)

## 20. Actualizar la aplicación

Cuando apruebes una tanda nueva y esté unida a `main` en GitHub:

```
bash /srv/taller/app/herramientas/servidor/actualizar.sh
```

El script hace, en orden, y se detiene si algo falla:

1. Una copia de seguridad (por si hay que volver atrás).
2. Muestra la versión actual. **Anótala**: es la que usarías para volver (paso 21).
3. `git pull --ff-only`: trae los cambios de `main`.
4. `uv sync --no-dev --locked`: instala las librerías nuevas, si las hay.
5. `check --deploy`, `migrate` (los cambios de la base) y `createcachetable` (no hace nada si
   la tabla ya existe).
6. `collectstatic`: los estilos y archivos nuevos.
7. `sudo systemctl restart taller`: reinicia Gunicorn con la versión nueva (pide tu
   contraseña). Las visitas de esos dos segundos pueden ver un error y basta con recargar.

Después entra a la aplicación y revisa la pantalla que cambió. Si el paso 3 dice que no se
puede hacer "fast-forward", alguien cambió archivos en el servidor: no fuerces nada,
pregunta.

## 21. Volver a la versión anterior

Si después de actualizar algo no funciona, primero mira los registros (paso 22). Si hay que
volver a la versión anterior, usa la que anotaste en el paso 20 (por ejemplo `13c9c83`):

```
cd /srv/taller/app
git diff --stat VERSION_ANTERIOR HEAD -- "*/migrations/*"
```

Muestra si la actualización traía cambios de la base de datos (archivos de `migrations`).

**Si no muestra nada** (no hubo cambios en la base), basta con volver al código anterior:

```
git checkout VERSION_ANTERIOR
uv sync --no-dev --locked
.venv/bin/python manage.py collectstatic --noinput
sudo systemctl restart taller
```

**Si muestra archivos de `migrations`**, la base ya cambió y el código anterior no la
entiende. Lo más seguro es restaurar la copia que hizo `actualizar.sh` justo antes (la más
reciente antes de la actualización):

```
git checkout VERSION_ANTERIOR
uv sync --no-dev --locked
.venv/bin/python manage.py collectstatic --noinput
```

Vuelve al código anterior, a sus librerías y a sus estilos. Luego haz el paso 19 completo
("En el mismo servidor") con esa copia. Lo que las usuarias
hayan escrito desde la actualización se pierde, así que decide pronto.

En los dos casos el código queda "suelto" (git dice `detached HEAD`): es normal. Cuando el
arreglo esté en `main`, vuelve con:

```
git checkout main
bash herramientas/servidor/actualizar.sh
```

## 22. Ver qué pasa y resolver problemas

### Los registros

```
journalctl -u taller -f
```

Lo que va escribiendo la aplicación, en vivo (errores con todo el detalle, intentos fallidos
de entrar y bloqueos). Sal con Ctrl+C. Variantes útiles:
`journalctl -u taller --since "1 hour ago"` y `journalctl -u taller -p err` (solo errores).
Si `journalctl` dice "you are currently not seeing messages from other users and the
system", a tu usuario le falta el grupo `adm` (paso 4): mientras tanto, ponle `sudo` delante
(`sudo journalctl -u taller -f`).

```
sudo tail -n 50 /var/log/nginx/error.log
sudo tail -n 50 /var/log/nginx/access.log
```

Los errores de NGINX y las últimas visitas (con la dirección real de cada celular).

```
journalctl -t copia-taller
```

Lo que dijeron las copias de seguridad de cada noche.

### Desbloquear a alguien

Después de 5 intentos fallidos, ese usuario queda bloqueado 15 minutos en ese celular. Para
desbloquearlo antes:

```
cd /srv/taller/app
.venv/bin/python manage.py axes_reset_username USUARIO_BLOQUEADO
```

Desbloquea solo a ese usuario. `axes_reset` (sin nada más) desbloquea a todos.

### Si algo falla

| Lo que ves | Qué revisar |
|---|---|
| `502 Bad Gateway` | Gunicorn está apagado o no arranca: `systemctl status taller` y `journalctl -u taller -n 50`. Casi siempre es un error en el `.env`. |
| El servicio dice "Falta la variable ..." | Falta esa línea en `/srv/taller/app/.env`. Agrégala y `sudo systemctl restart taller`. |
| `400 Bad Request` | `DJANGO_ALLOWED_HOSTS` no tiene el dominio exacto con el que entras. |
| `403` al enviar un formulario (CSRF) | `DJANGO_CSRF_TRUSTED_ORIGINS` debe ser `https://TU_DOMINIO`, con `https://` y sin `/` al final. |
| La página "da vueltas" (demasiadas redirecciones) | NGINX no está enviando `X-Forwarded-Proto`: compara el sitio con `herramientas/servidor/nginx-taller.conf`. |
| Se ve sin estilos | Falta `collectstatic` (paso 11) o se corrió sin `DJANGO_SETTINGS_MODULE` en el `.env`. Córrelo y reinicia. |
| `Server Error (500)` en todas las páginas después de actualizar | Mira `journalctl -u taller -n 50`. Si habla de "staticfiles manifest", corre `collectstatic` y reinicia. |
| `413 Request Entity Too Large` al subir una foto | Falta `client_max_body_size 12m;` en el sitio de NGINX. |
| Las fotos no se ven | La carpeta de `DJANGO_MEDIA_ROOT` y la de `location /media/` en NGINX deben ser la misma (`/srv/taller/media`). `ls -l /srv/taller/media` debe mostrar los archivos. |
| El enlace de tallas empieza por `http://` | Igual que "da vueltas": falta `X-Forwarded-Proto` en NGINX. |
| El navegador dice que el certificado venció | `sudo certbot renew` y `sudo systemctl reload nginx`. Revisa `systemctl list-timers \| grep certbot`. |
| No hay copias nuevas | `journalctl -t copia-taller` y `crontab -l`. Corre el script a mano para ver el error. |
| El disco está lleno | `df -h /` y `du -sh /srv/taller/*`. Las copias viejas se borran solas a los 14 días. |
| No puedes entrar por SSH | Desde el panel del proveedor hay una "consola" web para entrar. Revisa `sudo ufw status` (debe estar `OpenSSH`). |

Cuando Ubuntu instala una actualización que necesita reiniciar, al entrar por SSH aparece
"System restart required". Hazlo a una hora sin uso (`sudo reboot`): la aplicación, NGINX y
PostgreSQL arrancan solos.

---

## Resumen: los comandos de siempre

| Para | Comando (dentro de `/srv/taller/app`) |
|---|---|
| Entrar al servidor | `ssh TU_USUARIO@TU_DOMINIO` (desde tu computador) |
| Actualizar la aplicación | `bash herramientas/servidor/actualizar.sh` |
| Reiniciar la aplicación | `sudo systemctl restart taller` |
| Ver si está encendida | `systemctl status taller` |
| Ver los errores | `journalctl -u taller -f` |
| Hacer una copia ya | `bash herramientas/servidor/copia-de-seguridad.sh` |
| Traer las copias (desde tu computador) | `scp "TU_USUARIO@TU_DOMINIO:/srv/taller/copias/*" $HOME\copias-taller\` |
| Desbloquear a alguien | `.venv/bin/python manage.py axes_reset_username USUARIO` |
