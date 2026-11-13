# Rediseño: Cotizador

## Qué cambió en la pantalla

- **Arriba:** el título "Cotizador" con "El precio se actualiza mientras escribes" al lado, y el
  botón "Empezar de nuevo". En celular ese botón se vuelve redondo (con una X) porque arriba
  solo caben botones redondos; antes había un segundo botón repetido dentro de la página y ya
  no hace falta.
- **A la izquierda**, cuatro tarjetas con su título: "Para quién", "Qué prenda", "Cuánto cuesta
  hacer una" y "Tu ganancia". "Guardar esta prenda en mi lista" quedó abajo, en el pie de "Tu
  ganancia".
- **"Mis prendas guardadas"** ya no es una lista de las que se abren como un campo: ahora es un
  menú (un botón plano con una flechita) en la parte de arriba de "Qué prenda". Cada opción
  elige la prenda y pasa sus costos a los campos, igual que antes. Si todavía no hay ninguna
  guardada, el menú lo dice en una línea y explica cómo guardar la primera. "Quitar de mi
  lista" sigue ahí (con su pregunta de confirmación) cuando hay una prenda elegida.
- **A la derecha**, la tarjeta del resultado, que se queda quieta cuando se baja la página en
  computador: "Total de la cotización" con el total grande, las cinco cuentas (el precio por
  unidad en negrita; la ganancia ya no va en verde), la nota del redondeo y, abajo, en columna:
  "Crear pedido con esta cotización" (el botón negro), "Enviar por WhatsApp" y "Copiar
  cotización", los dos con su ícono.
- Ya no existe la "pantalla fija": la página se desplaza normal.

## Archivos y para qué

- `cotizador/templates/cotizador/inicio.html`, `_formulario.html`, `_que_prenda.html`,
  `_resultado.html`: el nuevo orden y las piezas del diseño.
- `cotizador/vistas.py`: ahora entiende que una opción del menú llega como `elegir`, y le pasa
  a la pantalla la lista de prendas guardadas.
- `cotizador/formularios.py`: el campo de la prenda elegida pasó a ser un campo escondido
  (la elección se hace con los botones del menú).
- `static/css/app.css` (apartado "Cotizador"): tres reglas pequeñas para que el título del
  total quede pegado al total, como en el diseño.
- `cotizador/tests/test_cotizador.py`: pruebas puestas al día.

## Decisiones

- **Cada opción del menú es un botón de enviar** (con `name="elegir"`), no un enlace. Así
  funciona igual con y sin JavaScript, y lo que la usuaria ya escribió no se pierde.
- **El resultado sigue sin parpadear** (`data-sin-animar`): como cambia con cada tecla, no se
  desvanece. La prueba que lo revisaba midiendo la pantalla fija se borró; la comprobación
  quedó en `test_mientras_se_escribe_el_resultado_no_se_anima_ni_avisa`.
- **"Empezar de nuevo" en celular** usa el ícono de cerrar (X) porque en el diseño de celular
  el botón de texto de arriba se esconde y no hay un ícono de "reiniciar" en la colección.
  Si David prefiere otro ícono, es un cambio de una palabra.

## Qué se probó

- Las 78 pruebas del Cotizador pasan: cifras, calcular sin JavaScript, guardar/elegir/quitar
  prendas (con las de otro taller, que no se pueden elegir ni quitar), crear el pedido con la
  "Tela", copiar y WhatsApp, y que el resultado lleva `data-sin-animar`. Los permisos de la
  costurera y el aislamiento entre talleres están en `tests/test_permisos.py` y
  `tests/test_aislamiento.py`.
- Capturas en 1366, 1920 y celular comparadas con `diseno/cotizador.html` (ver informe).
