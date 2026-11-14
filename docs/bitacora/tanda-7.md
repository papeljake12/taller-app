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

(Se completa al terminar la tanda.)
