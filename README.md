# Pedidos del Taller

Aplicación para que un taller de confección lleve pedidos, pagos, tallas, clientes, telas y
gastos desde el celular.

Estado: en planeación. Todavía no hay código de la aplicación; solo la demo y los documentos.

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
| `diseno/` | El diseño aprobado, una página por pantalla. Se abre en el navegador |
| `demo/index.html` | La primera demo, como referencia de comportamiento y textos |
| `.env.example` | Variables de configuración, sin valores reales |

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
