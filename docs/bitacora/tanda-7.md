# Tanda 7. Asistente del taller

## Plan (antes de empezar)

Rama `tanda-7-asistente`, sacada de `bot-propuesta`. Qué se construye: `docs/10-asistente.md`.
Cómo: `docs/11-plan-tanda-7.md`.

1. **Base (el coordinador, solo):**
   - T25: documentos, piezas nuevas de la maqueta, librería `anthropic`, ajustes, la tabla
     `UsoAsistente`, los límites del taller y los gastos por fechas en `calculos.py`.
   - T26: el esqueleto de la app `asistente/` con los contratos que comparten los carriles,
     el botón y el panel en `base.html`, los estilos y los atajos.
2. **Pausa con David:** aprueba las piezas nuevas de la maqueta y pone la clave en `.env`
   para una prueba corta de 3 llamadas a Claude.
3. **Cuatro carriles a la vez** (agentes Opus 5.5, cada uno en su copia):
   - A, consultas: T27 y T28.
   - B, motor: T29 y T30.
   - C, mensajes y cotizar: T31 y T32.
   - D, panel y uso: T33 y T34.
4. **Unión** en orden A, C, B, D, con todas las pruebas después de cada una. Luego T35
   (integración y capturas) y T36 (20 preguntas reales).

## Lo que se hizo

| Tarea | Qué quedó | Quién |
|---|---|---|
| T25 | Documentos, piezas nuevas de la maqueta (aprobadas por David), librería `anthropic`, tabla de uso, límites por taller y costo en `/admin` | Coordinador |
| T26 | El esqueleto: contratos, botón, panel, Ctrl J, la caja de Hoy que le pregunta al asistente y el ícono propio (el botón con carita, escogido por David). Prueba corta con la clave: funcionó | Coordinador |
| T27, T28 | Las consultas: pedidos, entregas, telas, clientes, quién debe, cuentas del mes y gastos | Carril A |
| T29, T30 | El motor: hablar con Claude, el ciclo de herramientas, las instrucciones, la pantalla y el esfuerzo | Carril B |
| T31, T32 | El mensaje de WhatsApp (sin que el número vaya a Anthropic) y la cotización | Carril C |
| T33, T34 | El panel, la conversación en la sesión, el cupo de preguntas y Mi taller | Carril D |
| T35 | La integración: prueba de punta a punta, el plazo de cada llamada, el panel al lado sin apretar la hoja y las capturas | Coordinador |
| T36 | 20 preguntas reales con la clave, en esfuerzo medio y alto | Coordinador |

Cada tarea tiene su explicación en `docs/bitacora/T25.md` a `T35.md`.

## Cómo se hizo

- La base (T25 y T26) la hizo el coordinador solo. Antes de seguir, David aprobó la maqueta,
  pidió que la caja de Hoy fuera como la de Shopify, escogió el ícono y puso la clave.
- Los cuatro carriles trabajaron al tiempo, cada uno en su copia y con su propia base de
  pruebas, para no pisarse. **Un tropiezo:** la herramienta que crea las copias falló en este
  Windows (la ruta `c:\` contra `C:/`) y además las sacaba de `main`; el coordinador las creó a
  mano desde la rama de la tanda.
- Cada carril pasó por la lista del revisor (sección 4 del plan) antes de unirse. Ninguno
  pidió cambios en archivos congelados. Se unieron en orden A, C, B, D, con todas las pruebas
  después de cada unión.

## Pruebas a mano (T35)

`uv run python herramientas/capturas.py --tanda 7`: 38 capturas en `docs/capturas/tanda-7/`,
todas sin problemas (nada se sale, sin errores de JavaScript). Lo encontrado y corregido:

- Con el panel abierto en 1280 px, en el pedido se montaban los nombres de las etapas: ahora,
  con el panel abierto y menos de 1440 px, la hoja pasa a una columna.
- En celular, al llegar al final de la conversación se movía la hoja de atrás: ya no.

No se pudo capturar el estado "sin preguntas" en la aplicación (habría que gastar el cupo del
día); lo comprueban las pruebas.

## Prueba real (T36): 20 preguntas, cada una en esfuerzo medio y alto

Con `herramientas/probar_asistente.py`, sobre el taller de ejemplo de la base local, con la
clave del espacio de trabajo de desarrollo. 8 consultas, 4 de plata, 3 de "este pedido",
3 mensajes y 2 cotizaciones.

| Esfuerzo | Preguntas | Costo medio | Costo (90 %) | Tiempo medio | Tiempo (90 %) | Máximo |
|---|---|---|---|---|---|---|
| Medio | 20 | 1,28 ¢ | 1,79 ¢ | 6,1 s | 9,2 s | 13,7 s |
| Alto | 20 | 1,24 ¢ | 1,80 ¢ | 6,5 s | 8,7 s | 11,2 s |

(¢ = centavos de dólar.)

- **Todas las cifras fueron correctas.** Se revisaron contra los cálculos de la aplicación:
  quién debe ($ 5.790.000), lo vendido en el mes, los gastos en telas, el saldo de "este
  pedido", las tallas que faltan y las dos cotizaciones (por ejemplo, 30 polos con 40 % de
  ganancia: $ 58.500 cada uno y $ 1.755.000 en total). Las que el script marcó "leer" se
  leyeron una por una.
- **Escribe como se pidió:** texto plano, tuteando, frases cortas y sin repetir las listas de
  las tarjetas.
- **La caché funciona en todas las preguntas** (más de 9.000 tokens leídos de caché cada vez).
- **Se encontró y corrigió un error:** con esfuerzo alto, cuando el cliente no tenía WhatsApp
  guardado, Claude decía "no pude dejarte listo el mensaje" en vez de prepararlo (la tarjeta
  igual trae "Copiar"). Se agregó a las instrucciones que lo prepare de todos modos y avise que
  lo puede copiar. Repetidas las tres preguntas de mensajes en los dos esfuerzos: las seis
  salieron bien.
- **Tiempo:** la más larga tardó 15 segundos, lejos del plazo de 50 y de los 120 del servidor.
- **Costo de la prueba:** "Uso del asistente" en `/admin` anotó 47 preguntas y 0,70 USD (la de
  ensayo, las 40 y las 6 repetidas). Con la prueba corta de T26 (unos 4 centavos) debería dar
  unos 0,74 USD en la consola de Anthropic, espacio de trabajo de desarrollo. **David:
  compáralo cuando quieras.**

**Decisión sobre el esfuerzo:** medio y alto cuestan y tardan lo mismo, y los dos acertaron
las cifras. La regla (alto para plata, medio para lo demás) se queda como está. Si algún día
una respuesta de plata sale floja en medio, se puede subir todo a alto sin que cueste más.

**Costo por mes:** con unas 300 preguntas, entre 4 y 6 USD por taller. El estimado del plan
(20 a 35 USD) era mucho más alto. Ya está anotado en `docs/10-asistente.md`.

## Lo que queda para David

- Comparar el costo de la prueba con la consola de Anthropic.
- Al publicar: el apartado "Una sola vez, con la tanda 7" del paso 20 de
  `docs/guia-publicacion.md` (120 segundos, hilos, la clave del espacio de trabajo "taller"
  y prender el asistente del taller en `/admin`).
- Avisarle a la clienta que, al usar el asistente, sus datos del taller (sin teléfonos, notas
  ni tallas) pasan por Anthropic, y confirmar los términos comerciales de Anthropic.
