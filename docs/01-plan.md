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

- Asistente del taller (tanda 7): la dueña le pregunta por sus pedidos, abonos, telas y
  gastos y le contesta con las cifras; redacta mensajes y cotiza. Solo consulta. En la tanda 8,
  tareas con confirmación. Ver `docs/10-asistente.md`.
- IA para crear pedidos desde un mensaje o dictado.
- Avisos automáticos: entregas de la semana, saldos vencidos, fechas de dotación.
- Ficha de producción por pedido, para imprimir.
- Lista de compras automática con los materiales que faltan.
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
