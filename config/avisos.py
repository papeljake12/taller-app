"""Aviso corto de confirmación ("Abono registrado.") después de guardar algo.

    from config.avisos import avisar

    def registrar(request, ...):
        ...
        respuesta = render(request, "pedidos/_pagos.html", contexto)
        return avisar(request, respuesta, "Abono registrado.")

- Si la respuesta es de HTMX y la página se queda, el texto va en la cabecera HX-Trigger
  ({"aviso": "Abono registrado."}), junto con lo que ya llevara (por ejemplo cerrar-ventana).
  static/js/app.js lo muestra como una píldora negra abajo, que se va sola.
- Si la respuesta lleva a otra página (una redirección, HX-Redirect o HX-Refresh), el texto va
  como mensaje de Django: base.html lo deja en la página siguiente y app.js lo muestra allí.
- Una página completa que se queda (sin HTMX y sin redirección) no lo muestra: después de
  guardar, una página completa siempre redirige.

Los textos son los de la demo (demo/index.html): cortos, con punto final.
Un formulario con errores no lleva aviso: solo lo que de verdad se guardó.
"""

import json

from django.contrib import messages

from config.ventanas import es_htmx

AVISO = "aviso"


def _disparos(valor):
    """Lo que ya dice HX-Trigger, como diccionario: "cerrar-ventana" -> {"cerrar-ventana": ""}."""
    valor = (valor or "").strip()
    if not valor:
        return {}
    if valor.startswith("{"):
        try:
            return json.loads(valor)
        except ValueError:
            return {}
    return {nombre.strip(): "" for nombre in valor.split(",") if nombre.strip()}


def se_va_a_otra_pagina(respuesta):
    return (
        300 <= respuesta.status_code < 400
        or respuesta.has_header("HX-Redirect")
        or respuesta.has_header("HX-Refresh")
    )


def avisar(request, respuesta, texto):
    """Agrega el aviso `texto` a `respuesta` (ver arriba) y devuelve la misma respuesta."""
    if se_va_a_otra_pagina(respuesta):
        messages.success(request, texto)
    elif es_htmx(request):
        disparos = _disparos(respuesta.get("HX-Trigger"))
        disparos[AVISO] = texto
        # En ASCII (las tildes van como \u00e9): una cabecera no lleva letras de otros idiomas.
        respuesta["HX-Trigger"] = json.dumps(disparos)
    return respuesta
