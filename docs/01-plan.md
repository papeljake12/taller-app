# Plan

## Qué es

Una aplicación para que un taller de confección lleve desde el celular sus pedidos, pagos,
tallas, clientes, telas y gastos. La primera clienta hace dotaciones, uniformes y vestidos de
comparsa. La meta es poder venderla después a otros talleres.

La primera demo está en `demo/index.html` y el diseño aprobado en `diseno/`.

## Etapas

### 1. Hablar con la clienta (30 minutos)

No es para que apruebe, sino para saber qué construir primero.

Preguntas:

1. ¿Cómo le llegan los pedidos y dónde los anota hoy?
2. ¿Cuántos pedidos maneja al mes?
3. ¿Se le ha pasado una fecha de entrega o se le ha confundido una talla?
4. ¿Cómo lleva la cuenta de abonos y saldos?
5. ¿Cuánto se demora en dar un precio?
6. ¿Trabaja sola o con costureras? ¿Cómo les paga?
7. ¿Les factura a empresas? ¿Usa facturación electrónica?
8. ¿Qué celular y qué computador usa?

### 2. Aplicación base

Lo que ya tiene la demo, pero real: usuarios, pedidos, pagos, tallas con enlace público,
clientes, cotizador, telas, gastos, recibos y Excel. Las tareas están en `docs/05-tareas.md`.

Con esta etapa ya hay algo que se puede vender.

### 3. Ahorro de trabajo

Desde el 15 de noviembre de 2026 esta etapa se ordena alrededor del **agente del taller**
(`docs/12-agente.md`, aprobado por David). La idea: "Tú le cuentas, el agente lo hace. Tú
solo confirmas." Para alguien que lleva años con el cuaderno, anotar todo a mano en la
aplicación se siente como más trabajo; con el agente, ella cuenta lo que pasó y solo revisa.

- **Asistente del taller (tanda 7, hecho):** la dueña le pregunta por sus pedidos, abonos,
  telas y gastos y le contesta con las cifras; redacta mensajes y cotiza. Ver
  `docs/10-asistente.md`.
- **El agente, lo mínimo (tanda 8: T38, T39, T40 y T43):** ella le cuenta "vino la profe,
  quiere 30 uniformes y dejó 500 mil" y el agente arma un borrador con el cliente, el pedido,
  el abono y la tela. Nada se guarda hasta que ella toca **Guardar**. Cada mañana, arriba de
  Hoy, le deja un resumen: a quién cobrar, qué tela no alcanza y qué pedidos esperan tallas.
  El plan está en `docs/13-plan-tanda-8.md`.
- **El agente, lo que sigue (T41, T42, T44 y T45):** se arma después de presentárselo a ella
  y preguntarle qué más quiere. Cambiar la etapa y anotar "Usé" y "Entró" de tela con el
  agente, descontar la tela al pasar a Corte, la lista de compras automática con la tela y los
  materiales que faltan, y avisos con la acción lista (cobros quietos, entregas cerca, tallas
  que faltan).
- Por decidir aparte (cada una pide algo nuevo): dictarle por voz, que mande WhatsApp solo y
  leer una foto del cuaderno.
- Avisos de fechas de dotación.
- Ficha de producción por pedido, para imprimir.
- Repetir un pedido anterior.
- Medidas guardadas por persona.
- Pago a costureras.
- Ganancia por pedido.
- Proveedores.

### 4. Más ventas

- Portal del cliente: ver el estado, aprobar la cotización, descargar recibos.
- Catálogo público con fotos y botón para pedir cotización.
- Pagos en línea.
- Agente de WhatsApp que responde estados, recoge tallas y crea pedidos.

### 5. Venderlo a otros talleres

- Registro de talleres nuevos.
- Planes de precio.
- Facturación electrónica, si se confirma que hace falta.
- Instalable en el celular con ícono propio.

## Qué ofrecerle a la clienta

- **Instalación:** la aplicación con su nombre, su logo, sus precios y sus clientes cargados.
- **Capacitación:** una o dos sesiones para ella y sus costureras.
- **Mensualidad:** servidor, copias de seguridad, soporte y mejoras.
- **Extras con costo aparte:** agente de WhatsApp, pagos en línea y facturación, porque cada
  uno tiene un costo mensual de terceros.

## Sin definir todavía

- Precios de instalación y mensualidad.
- Tiempos de cada etapa.
- Costos mensuales de servidor, IA y WhatsApp. Hay que consultarlos antes de cotizar.
- Nombre comercial de la aplicación.

## Stack

Django 5.2 LTS, PostgreSQL, plantillas de Django con HTMX 2.x y JavaScript propio, sobre un
VPS con NGINX, Gunicorn y Whitenoise. El detalle y las razones están en `CLAUDE.md`.
