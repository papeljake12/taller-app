# Forma de trabajo

Cómo se hace cada tarea de `docs/05-tareas.md`. El objetivo es avanzar en pasos pequeños que
David pueda entender, revisar y deshacer.

Las tareas se agrupan en tandas (ver `docs/09-plan-de-construccion.md`). Claude Code trabaja
una tanda completa y David la revisa al final. Cada tarea sigue teniendo su propio commit.

En varias tandas el trabajo se reparte entre agentes que trabajan al mismo tiempo. Quién
hace qué y qué archivos puede tocar cada uno está en "Reglas para los agentes" del plan.

## Paso a paso de una tarea

Al empezar la tanda:

- **Proponer.** Antes de escribir código, decir en pocas líneas qué se va a crear o cambiar
  en toda la tanda y por qué. Si algo del plan no cuadra, decirlo aquí. Esperar el visto
  bueno de David.
- **Crear una rama.** Nombre: `tanda-N-descripcion`, por ejemplo `tanda-3-pedidos`.

Por cada tarea de la tanda:

1. **Leer.** La tarea, su pantalla en `docs/03-pantallas.md`, su página de `diseno/`, los
   modelos en `docs/02-modelo-de-datos.md` y, para el comportamiento, la parte equivalente
   de `demo/index.html`.
2. **Construir.** Código y pruebas juntos, siguiendo la "Receta de una pantalla" del plan.
3. **Comprobar.** Correr `uv run pytest`. Abrir la pantalla en 390 px y en 1280 px y
   compararla con su referencia.
4. **Explicar.** Escribir `docs/bitacora/TNN.md` (un archivo por tarea), en lenguaje sencillo:
   - qué hace ahora la aplicación que antes no hacía,
   - qué archivos cambiaron y para qué sirve cada uno,
   - qué se probó y qué no,
   - cualquier decisión que se tomó y su razón.
5. **Commit** de esa tarea en la rama de la tanda.
6. **Marcar** la tarea como hecha en `docs/05-tareas.md`. Cuando hay varios agentes, esto
   lo hace solo el coordinador, después de unir el carril.

Al terminar la tanda: detenerse, darle a David un resumen corto y la lista de cosas para
probar a mano. La rama se une a la principal solo cuando David la aprueba.

## Mensajes de commit

En español, en una línea, empezando por el número de tarea:

```
T08: registrar y quitar abonos, con saldo y barra de pago
```

Si hace falta contexto, una línea en blanco y dos o tres frases más.

## Cuándo detenerse y preguntar

- Hace falta una librería nueva.
- La tarea obliga a cambiar el modelo de datos, el diseño o los permisos.
- Hay dos formas razonables de hacer algo y la diferencia la notaría la usuaria.
- Una prueba vieja empieza a fallar y no es evidente por qué.
- La tarea resulta mucho más grande de lo previsto: se propone partirla.

## Lo que nunca se hace

- Subir claves, contraseñas o el archivo `.env`.
- Tocar el servidor de producción o su base de datos.
- Borrar o reescribir migraciones que ya están en la rama principal.
- Juntar varias tareas en un solo commit.
- Desactivar o borrar una prueba para que "pase".
- Decir que algo funciona sin haberlo probado. Si no se pudo probar, se dice.

## Definición de "terminado"

Una tarea está terminada cuando:

- [ ] Cumple todos los puntos "Lista cuando" de su pantalla.
- [ ] Tiene pruebas y todas pasan.
- [ ] Respeta el aislamiento entre talleres y los permisos.
- [ ] Se ve como su página de `diseno/` en celular y en computador.
- [ ] Los textos están en español y coinciden con la referencia.
- [ ] Tiene su explicación en `docs/bitacora/TNN.md`.
- [ ] Si la hizo un agente de carril, pasó por el revisor.

Una tanda está terminada cuando todas sus tareas lo están y David la aprobó.

## Tareas que son de David

Claude Code no puede hacerlas. Van en paralelo:

- [ ] Hablar 30 minutos con la clienta (preguntas en `docs/01-plan.md`).
- [ ] Crear el repositorio privado en GitHub.
- [ ] Contratar el servidor y el dominio.
- [ ] Conseguir del taller: nombre, logo, precios, lista de clientes y de costureras.
- [ ] Crear la cuenta y la clave de la API de Claude (etapa 3).
- [ ] Tramitar la cuenta de WhatsApp Business (etapa 4).
- [ ] Revisar los costos mensuales de servidor, IA y WhatsApp antes de cotizar.
- [ ] Definir precio de instalación y mensualidad.
