# Pedidos del Taller

Aplicación para que un taller de confección lleve pedidos, pagos, tallas, clientes, telas y
gastos desde el celular.

Estado: en construcción, por tandas (ver `docs/09-plan-de-construccion.md`). Lo que cambió
en cada tarea está explicado en `docs/bitacora/`.

## Cómo correrla en tu computador

Necesitas Python 3.12, `uv` y PostgreSQL.

1. Copia `.env.example` como `.env` y llena los valores (clave de Django y datos de la base).
2. Instala las librerías: `uv sync`
3. Prepara la base de datos: `uv run python manage.py migrate`
4. Crea tu usuario administrador: `uv run python manage.py createsuperuser`
5. Enciende la aplicación: `uv run python manage.py runserver` y abre http://127.0.0.1:8000
6. En http://127.0.0.1:8000/admin/ crea un taller y una usuaria dueña para ese taller.
   Con ella se entra a la aplicación.
7. Corre las pruebas: `uv run pytest`

## Cómo publicarla en el servidor

La guía paso a paso para el VPS (Ubuntu 24.04 con NGINX, Gunicorn y PostgreSQL), con la copia
de seguridad diaria, cómo restaurar y cómo actualizar, está en `docs/guia-publicacion.md`.

## Qué hay en este repositorio

| Ruta | Qué es |
|---|---|
| `CLAUDE.md` | Instrucciones para Claude Code: stack, reglas y comandos |
| `docs/01-plan.md` | Qué se construye y en qué etapas |
| `docs/02-modelo-de-datos.md` | Qué se guarda y cómo se calcula cada cifra |
| `docs/03-pantallas.md` | Qué hace cada pantalla y cuándo está lista |
| `docs/04-permisos.md` | Quién puede ver y hacer qué |
| `docs/05-tareas.md` | Lista de tareas en orden |
| `docs/06-pruebas.md` | Qué se prueba y cómo |
| `docs/07-forma-de-trabajo.md` | Ramas, commits y tareas de David |
| `docs/08-diseno.md` | Colores, tipografía, piezas y reglas de alineación |
| `docs/09-plan-de-construccion.md` | Orden de construcción por tandas, reparto entre varios agentes (ultracode) y las instrucciones listas para Claude Code |
| `docs/guia-publicacion.md` | Cómo publicar la aplicación en el servidor y sacarle copia de seguridad |
| `diseno/` | El diseño aprobado, una página por pantalla. Se abre en el navegador |
| `demo/index.html` | La primera demo, como referencia de comportamiento y textos |
| `.env.example` | Variables de configuración, sin valores reales |
| `pyproject.toml` y `uv.lock` | Las librerías del proyecto y sus versiones exactas |
| `config/` | Ajustes de Django por entorno y las direcciones principales |
| `cuentas/` | Talleres, usuarias, inicio y cierre de sesión |
| `pedidos/` | La app de pedidos. Por ahora solo trae la pantalla Hoy |
| `templates/` | La plantilla base (marco y menú) y las piezas del diseño |
| `static/` | Estilos, JavaScript, la fuente Inter, HTMX y los íconos, todo guardado aquí |
| `tests/` | Pruebas automáticas generales del proyecto |
| `herramientas/servidor/` | Los archivos de configuración del servidor (Gunicorn, NGINX, copia de seguridad), con valores para reemplazar |
| `docs/bitacora/` | Una explicación sencilla por cada tarea terminada |

## Cómo empezar a trabajar

1. Abre esta carpeta en VS Code.
2. Abre Claude Code y pégale la instrucción de la tanda 1 que está en
   `docs/09-plan-de-construccion.md`.
3. Al final de cada tanda, revisa lo que te explica, pruébalo y aprueba antes de seguir con
   la siguiente.

## Sobre la demo

`demo/index.html` se hizo para funcionar dentro de Claude. Si la abres directamente en el
navegador, muestra los datos de ejemplo pero no guarda nada, y no tiene IA, descargas ni
fotos. Sirve como modelo de lo que hace cada función, no como aplicación lista. Su aspecto
es el del primer diseño; el definitivo está en `diseno/`.

## Sobre las fotos de ejemplo

Las fotos de `diseno/img/` se hicieron con IA para la presentación. No son trabajos del
taller. En la aplicación se reemplazan por las fotos reales de los pedidos.
