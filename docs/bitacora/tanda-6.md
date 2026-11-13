# Tanda 6. Cierre — resumen

Con esta tanda quedan hechas las 25 tareas de la etapa 2 (la aplicación base).

## Lo que se hizo

| Tarea | Qué quedó |
|---|---|
| T21 | Permisos por rol en todas las pantallas. La costurera ve y mueve el trabajo, pero no ve plata en ninguna parte (ni en páginas, ni en partes que llegan sin recargar, ni en mensajes, PDF o Excel). Clientes, Cotizador, Resumen, Mi taller y el Excel son solo de la dueña. Una prueba por cada fila de `docs/04-permisos.md`, como dueña y como costurera. |
| T23 | La revisión final: diez revisores compararon cada pantalla con su página de `diseno/` en 1280 px y 390 px, y como costurera. Encontraron 69 diferencias; se corrigieron, salvo unas pocas que se dejaron a propósito (están en `docs/bitacora/T23.md`). |
| T24 | La configuración de producción, Whitenoise para los estilos y la guía paso a paso para publicar en el servidor, con la copia de seguridad diaria: `docs/guia-publicacion.md` y los archivos de `herramientas/servidor/`. No se tocó ningún servidor. |

Cada tarea tiene su explicación en `docs/bitacora/T21.md`, `T23.md` y `T24.md`.

## Cómo se hizo

- **T21** lo hizo un solo agente, porque toca todas las vistas. Después, tres revisores lo
  atacaron por separado:
  - uno revisó fila por fila de la tabla;
  - otro recorrió todas las direcciones como costurera buscando plata;
  - otro intentó hacer a mano lo prohibido.

  No encontraron nada grave. El coordinador corrigió los detalles menores: quitar tallas y la
  foto quedó solo para la dueña, una pantalla vieja se recarga sola si la costurera toca algo
  que ya no le toca, y Hoy no muestra plata si no sabe quién pregunta.
- **T23 y T24** se hicieron al mismo tiempo, cada una en su copia.

## Un tropiezo

Durante la noche se acabó el cupo de uso (a las 3:10 a. m.). El arreglo de la revisión final y
el arreglo de la guía quedaron a medias, sin guardar. En la mañana se retomaron: los agentes
revisaron lo que había quedado a medias, lo conservaron (estaba bien y sus pruebas pasaban) y
terminaron. No se perdió nada.

## Qué se probó

- `uv run pytest`: 1215 pruebas, todas pasan, también en orden al azar.
- La prueba que una vez falló en la tanda 5 no volvió a aparecer en ninguna de las corridas
  de esta tanda; no se encontró ninguna que dependa de la hora o del orden.
- Capturas finales de todas las pantallas en `docs/capturas/tanda-6/` (como dueña) y de las
  de la costurera en `docs/capturas/tanda-6/costurera/`. Ninguna se sale del ancho, ningún
  archivo falla y no hay errores en el navegador.
- `check --deploy` con los ajustes de producción pasa (con valores de mentira en las pruebas).

## Para que tú decidas o revises

- **La guía para publicar** (`docs/guia-publicacion.md`). Léela con calma antes de contratar el
  servidor: nada de eso se probó en un servidor de verdad.
- **Gunicorn 26.2 y no la 27.0.1.** El agente de T24 escogió la versión anterior porque la
  27.0.1 había salido el día antes; la regla 6 dice que las librerías te las preguntamos: la
  explicación está en `docs/bitacora/T24.md`. Whitenoise y Gunicorn sí estaban en el stack
  aprobado de `CLAUDE.md`.
- **Lo que quedó pendiente de las tandas anteriores**:
  - el ámbar de las telas (tanda 5);
  - los dos mensajes nuevos de Hoy (tanda 4);
  - la nota de las fotos (tanda 4);
  - el texto "No hay entregas ese día." (tanda 5).
- **Tu nombre en la lista de encargadas sale como "david"**, porque tu usuario no tiene
  "nombre visible". Ponlo en `/admin/` (Usuarios → david → Nombre visible).

## Qué no se pudo comprobar

- Nada se probó en un servidor ni en un celular de verdad, ni en Safari o Firefox.
- El Excel no se abrió en Excel ni en Google Sheets (solo se leyó de vuelta en las pruebas).
