# Instrucciones del proyecto

Aplicación web para que un taller de confección lleve pedidos, pagos, tallas, clientes,
telas y gastos desde el celular. El dueño del proyecto es David. La primera clienta es un
taller pequeño que hace dotaciones, uniformes y vestidos de comparsa.

Lee estos documentos antes de escribir código:

- `docs/01-plan.md`: qué se construye y en qué etapas.
- `docs/02-modelo-de-datos.md`: qué se guarda. Es la fuente de verdad de los modelos.
- `docs/03-pantallas.md`: qué hace cada pantalla y cuándo está lista.
- `docs/04-permisos.md`: quién puede ver y hacer qué.
- `docs/05-tareas.md`: la lista de tareas. Un commit por tarea.
- `docs/06-pruebas.md`: qué se prueba y cómo.
- `docs/07-forma-de-trabajo.md`: ramas, commits y cómo explicar los cambios.
- `docs/08-diseno.md`: colores, tipografía, piezas y reglas de alineación.
- `docs/09-plan-de-construccion.md`: en qué orden se construye, cómo se agrupa en tandas y
  cómo se reparte entre varios agentes.
- `diseno/`: el diseño aprobado, una página por pantalla. Es la fuente de verdad visual.
- `demo/index.html`: la primera demo. Sirve para el comportamiento y los textos de cada
  función. Su aspecto ya no vale: fue reemplazado por `diseno/`.

## Stack (ya decidido, no cambiarlo sin preguntar)

- Python 3.12 y Django 5.2 LTS.
- PostgreSQL.
- Plantillas de Django, HTMX 2.x y JavaScript propio. Sin React, sin Bootstrap, sin Tailwind.
- Dependencias con `uv` (`pyproject.toml` y `uv.lock`).
- Servidor: VPS con NGINX, Gunicorn y Whitenoise.
- Seguridad de acceso: autenticación de Django y `django-axes`.
- PDF con ReportLab. Excel con openpyxl.
- Pruebas con `pytest` y `pytest-django`.
- Todos los archivos estáticos son locales: fuentes, HTMX e íconos. Nada desde un CDN.

## Reglas

1. **Idioma.** Todo lo que ve la usuaria está en español. Los nombres de modelos, campos,
   vistas y URL también van en español, sin tildes ni ñ (`pedido`, `abono`, `confeccion`).
2. **Varios talleres.** Cada dato pertenece a un taller. Toda consulta se filtra por el taller
   de la usuaria que inició sesión. Nunca se confía en un id que llega por la URL sin
   comprobar que es de su taller.
3. **Plata.** Los valores se guardan como enteros en pesos colombianos. Sin decimales y sin
   `float`. El saldo siempre se calcula (total menos abonos); no se guarda.
4. **Fechas.** Zona horaria `America/Bogota`. Las fechas de entrega son fechas sin hora.
5. **Secretos.** Ninguna clave ni contraseña en el repo. Van en `.env`, que Git ignora.
   `.env.example` lista las variables sin valores reales.
6. **Dependencias.** No agregar librerías sin preguntarle a David y explicar para qué sirven.
7. **Diseño.** Copiar medidas, colores, íconos y textos de las páginas de `diseno/` y seguir
   `docs/08-diseno.md`. No rediseñar. En resumen: panel con marco negro que termina en azul,
   fuente Inter, botones principales negros, azul para gráficas y "en proceso", ámbar para
   "pendiente", rojo solo para atrasos y deudas, verde solo para pagado y entregado. Las
   tarjetas de una misma fila terminan a la misma altura.
8. **Celular también.** Cada pantalla debe funcionar en 390 px de ancho sin desbordarse y
   verse como su referencia en 1280 px.
9. **Pruebas.** Cada tarea trae sus pruebas. No se da por terminada si alguna falla.
10. **Explicaciones.** Por cada tarea, escribir en `docs/bitacora/TNN.md`, en lenguaje sencillo
    y sin tecnicismos, qué cambió y por qué. David está aprendiendo y quiere entender cada
    decisión. Se trabaja por tandas: al final de cada una hay que detenerse para que David
    revise, y nada se une a la rama principal sin su aprobación.
11. **Datos inventados.** No inventar datos reales (precios, teléfonos, nombres de clientes).
    Los datos de ejemplo van marcados como ejemplo y solo en el comando de datos de prueba.

## Si trabajas con varios agentes

El detalle está en "Reglas para los agentes" de `docs/09-plan-de-construccion.md`. Lo esencial:

- Hay un coordinador (la sesión principal), agentes de carril y un revisor.
- Cada agente toca solo los archivos de su carril y trabaja en su propia copia (worktree).
- Los archivos compartidos quedan congelados al final de la tanda 2 y solo los cambia el
  coordinador: `config/`, `models.py`, migraciones, `pedidos/calculos.py`, los `urls.py`,
  `static/css/app.css`, `static/js/app.js`, `templates/base.html`, `templates/_menu.html`,
  `templates/piezas/` y `docs/05-tareas.md`.
- Nadie crea migraciones en paralelo.
- Si eres un agente de carril y necesitas un cambio en un archivo congelado, pídeselo al
  coordinador en vez de hacerlo.
- Ningún carril se une sin pasar por el revisor y sin que todas las pruebas pasen.

## Comandos

- Instalar: `uv sync` (crea `.venv` con Python 3.12 y las librerías de `uv.lock`).
- Configurar: copiar `.env.example` como `.env` y llenar los valores. El usuario de
  PostgreSQL necesita el permiso `CREATEDB`, porque las pruebas crean una base temporal.
- Correr en local: `uv run python manage.py runserver` (usa `config/settings/local.py`).
- Pruebas: `uv run pytest` (usa `config/settings/pruebas.py` y la base temporal `test_taller`).
- Revisar la configuración: `uv run python manage.py check`
- Migraciones: `uv run python manage.py makemigrations` y `uv run python manage.py migrate`
- Datos de ejemplo: `uv run python manage.py cargar_ejemplos` (se crea en la tanda 2, con T22).

## Lo que no debes hacer

- No tocar el servidor de producción ni su base de datos.
- No borrar migraciones ya subidas.
- No cambiar el stack, el diseño ni el modelo de datos sin proponerlo primero.
- No adelantar funciones de etapas posteriores.
