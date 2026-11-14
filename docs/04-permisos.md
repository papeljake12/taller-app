# Quién puede hacer qué

Hay cuatro tipos de persona.

- **Dueña:** maneja todo su taller.
- **Costurera:** ve y actualiza el trabajo, pero no ve la plata.
- **Cliente con enlace:** solo abre el formulario de tallas de un pedido. No tiene cuenta.
- **Administrador (David):** entra al panel de administración de Django para crear talleres
  y dar soporte.

## Tabla de permisos

| Acción | Dueña | Costurera | Cliente con enlace |
|---|---|---|---|
| Ver la lista de pedidos | Todos | Todos, sin valores | No |
| Ver un pedido por dentro | Sí | Sí, sin la sección de pagos | No |
| Crear, editar y eliminar pedidos | Sí | No | No |
| Cambiar la etapa de un pedido | Sí | Solo si es la encargada | No |
| Elegir la encargada | Sí | No | No |
| Registrar y quitar abonos | Sí | No | No |
| Descargar recibos | Sí | No | No |
| Ver tallas | Sí | Sí | No |
| Agregar tallas a mano | Sí | Sí | No |
| Enviar su propia talla | No aplica | No aplica | Sí |
| Marcar materiales como comprados | Sí | Sí | No |
| Agregar y quitar materiales | Sí | Sí | No |
| Subir la foto del diseño | Sí | Sí | No |
| Calendario | Sí | Sí | No |
| Clientes | Sí | No | No |
| Cotizador | Sí | No | No |
| Telas: ver y registrar "Usé" | Sí | Sí | No |
| Telas: "Entró", agregar y quitar | Sí | No | No |
| Resumen, gastos y Excel | Sí | No | No |
| Mi taller | Sí | No | No |
| Asistente (tanda 7: solo consulta) | Sí, si David lo prendió | No (entra en la tanda 8) | No |

"Sin valores" significa que la costurera no ve total, abonos, saldo ni "Por cobrar". En el
tablero ve las cifras de producción, entregas y atrasados, pero no la de plata.

## Reglas que el código debe cumplir

1. **Aislamiento entre talleres.** Toda consulta se filtra por `request.user.taller`. Pedir
   por URL un pedido, cliente, tela o gasto de otro taller responde "no encontrado" (404),
   nunca "sin permiso", para no revelar que existe.
2. **El permiso se revisa en el servidor.** Ocultar un botón no basta: la vista también
   rechaza la acción.
3. **Enlace público.** Solo sirve para crear tallas del pedido de ese token. El token es
   largo y aleatorio; no se usa el id del pedido. La dueña puede cerrar el enlace.
4. **Sesiones.** Cierre de sesión por inactividad prolongada. Bloqueo por intentos fallidos.
5. **Usuarias desactivadas.** No pueden entrar, pero sus pedidos y registros se conservan.
6. **Asistente.** Sus herramientas consultan solo el taller de quien pregunta: un pedido o
   cliente de otro taller responde "no encontrado", igual que una URL. En la tanda 7 no
   escriben nada en la base. El límite de preguntas se revisa en el servidor antes de llamar a
   Claude. A Anthropic no van teléfonos, notas de clientes, nombres ni medidas de tallas, ni
   el token del enlace de tallas (`docs/10-asistente.md`).

## Pendiente por confirmar con la clienta

- Si las costureras deben ver o no los valores. La tabla asume que no.
- Si quiere que el cliente vea el estado de su pedido con un enlace (portal del cliente,
  etapa 4).
