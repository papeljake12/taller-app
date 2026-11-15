/* JavaScript propio de la aplicación.
   1. Menú que se contrae (y se recuerda en este navegador).
   2. Panel "Más" de la barra de abajo en celular.
   3. (Fotos que pasan: se quitó con "Trabajos del taller" en el rediseño del 2026-11-13.)
   4. HTMX envía la protección CSRF en cada petición, y dibuja los formularios con errores.
   5. Ventana (para "Nuevo pedido" y otros formularios cortos).
   6. Botones "Copiar".
   7. Elegir un archivo (en celular).
   8. El cursor no se pierde cuando HTMX cambia una parte de la página.
   9. Un enlace a algo que está dentro de una fila plegada (<details>) la abre.
   10. Botones que esperan: "cargando" si la acción tarda.
   11. Lo que entra y sale sin recargar (HTMX): se desvanece, y una fila que se va se cierra.
   12. Aviso corto de confirmación ("Abono registrado.").
   13. Atajo Ctrl K, menús desplegables y lo que se muestra con un botón (rediseño).
   14. Asistente: abrir y cerrar el panel (Ctrl J), enviar con Enter y los tres puntos
       mientras llega la respuesta (tanda 7).

   Las duraciones de las animaciones se leen de static/css/app.css (:root), donde se definen
   una sola vez. Si la persona pidió menos movimiento en su equipo, valen 0 y nada se anima.

   Este archivo es compartido: después de la tanda 2 solo lo cambia el coordinador. */

(function () {
  "use strict";

  /* 0. Movimiento ---------------------------------------------------------- */

  // Milisegundos de una variable de app.css ("200ms" o "0.2s"). 0 si no existe.
  function milisegundos(variable) {
    const valor = getComputedStyle(document.documentElement).getPropertyValue(variable).trim();
    const numero = parseFloat(valor);
    if (!valor || isNaN(numero)) return 0;
    return /ms$/.test(valor) ? numero : numero * 1000;
  }

  function curva(variable) {
    return getComputedStyle(document.documentElement).getPropertyValue(variable).trim() || "ease";
  }

  // Con "menos movimiento" pedido, app.css deja las duraciones en 0: no se anima nada.
  function hayMovimiento() {
    return milisegundos("--duracion") > 0 &&
      !window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  }

  // Ejecuta `despues` cuando termina la animación de CSS del elemento (o, si no llega el
  // aviso del navegador, cuando pasa su duración).
  function alTerminar(elemento, duracion, despues) {
    let hecho = false;
    function terminar() {
      if (hecho) return;
      hecho = true;
      elemento.removeEventListener("animationend", alFin);
      despues();
    }
    function alFin(evento) {
      if (evento.target === elemento) terminar();
    }
    elemento.addEventListener("animationend", alFin);
    window.setTimeout(terminar, duracion + 50);
  }

  /* 1. Menú que se contrae ------------------------------------------------- */

  const UN_ANO = 60 * 60 * 24 * 365;

  function ponerTitulos(marco, contraido) {
    // Con el menú contraído, cada ícono muestra su nombre al pasar el mouse.
    marco.querySelectorAll(".menu [data-nombre]").forEach(function (entrada) {
      if (contraido) {
        entrada.setAttribute("title", entrada.dataset.nombre);
      } else {
        entrada.removeAttribute("title");
      }
    });
  }

  let menuCambia = null;

  function contraerMenu(contraido) {
    const marco = document.querySelector("[data-marco]");
    if (!marco) return;
    // Mientras cambia, el menú pasa de ancho a angosto (o al revés) con transición
    // (.menu-cambia en app.css). Solo entonces: al abrir cada página no se anima.
    if (hayMovimiento()) {
      marco.classList.add("menu-cambia");
      window.clearTimeout(menuCambia);
      menuCambia = window.setTimeout(function () {
        marco.classList.remove("menu-cambia");
      }, milisegundos("--duracion") + 50);
    }
    marco.classList.toggle("marco--contraido", contraido);
    ponerTitulos(marco, contraido);
    // La elección se guarda en una cookie para que el servidor dibuje el menú igual.
    document.cookie = contraido
      ? "menu=contraido; path=/; max-age=" + UN_ANO + "; SameSite=Lax"
      : "menu=; path=/; max-age=0; SameSite=Lax";
    // El botón que se tocó desaparece: el foco pasa al que hace lo contrario.
    const siguiente = marco.querySelector(contraido ? ".menu__abrir" : ".menu__contraer");
    if (siguiente) siguiente.focus();
  }

  document.addEventListener("click", function (evento) {
    if (evento.target.closest("[data-menu-contraer]")) {
      contraerMenu(true);
    } else if (evento.target.closest("[data-menu-abrir]")) {
      const buscar = evento.target.closest("[data-enfocar-buscar]");
      contraerMenu(false);
      // La lupa del menú contraído abre el menú y deja el cursor en el buscador.
      if (buscar) enfocarBuscador();
    }
  });

  /* 2. Panel "Más" en celular ---------------------------------------------- */

  function botonMas() {
    return document.querySelector("[data-mas]");
  }

  function abrirMas(abierto) {
    const boton = botonMas();
    if (!boton) return;
    const panel = document.getElementById(boton.getAttribute("aria-controls"));
    if (!panel) return;
    boton.setAttribute("aria-expanded", String(abierto));
    if (abierto) {
      // Al abrirlo sube (app.css: .panel-mas:not([hidden])).
      panel.classList.remove("se-cierra");
      panel.hidden = false;
    } else if (!panel.hidden && hayMovimiento()) {
      // Al cerrarlo baja y después se esconde.
      panel.classList.add("se-cierra");
      alTerminar(panel, milisegundos("--duracion-corta"), function () {
        if (boton.getAttribute("aria-expanded") === "true") return;  // se volvió a abrir
        panel.hidden = true;
        panel.classList.remove("se-cierra");
      });
    } else {
      panel.hidden = true;
    }
  }

  document.addEventListener("click", function (evento) {
    const boton = botonMas();
    if (!boton) return;
    const abierto = boton.getAttribute("aria-expanded") === "true";
    if (evento.target.closest("[data-mas]")) {
      abrirMas(!abierto);
    } else if (abierto && !evento.target.closest("[data-panel-mas]")) {
      abrirMas(false);
    }
  });

  document.addEventListener("keydown", function (evento) {
    const boton = botonMas();
    if (evento.key === "Escape" && boton && boton.getAttribute("aria-expanded") === "true") {
      abrirMas(false);
      boton.focus();
    }
  });

  /* 4. HTMX y la protección CSRF ------------------------------------------- */

  // Django rechaza los envíos sin su ficha CSRF. La página la deja en <body data-csrf>.
  document.addEventListener("htmx:configRequest", function (evento) {
    const ficha = document.body.dataset.csrf;
    if (ficha) evento.detail.headers["X-CSRFToken"] = ficha;
  });

  // Un formulario con errores responde 422 ("datos que no sirven"): HTMX lo dibuja igual,
  // para que se vean los mensajes. Los demás errores no reemplazan nada.
  if (window.htmx) {
    window.htmx.config.responseHandling = [
      { code: "204", swap: false },
      { code: "[23]..", swap: true },
      { code: "422", swap: true },
      { code: "[45]..", swap: false, error: true },
    ];
  }

  // Si el servidor dice que esa acción no le toca (403), la página estaba desactualizada
  // (por ejemplo, le quitaron el pedido a la costurera): se recarga para mostrar lo de ahora.
  document.addEventListener("htmx:responseError", function (evento) {
    if (evento.detail.xhr && evento.detail.xhr.status === 403) window.location.reload();
  });

  /* 5. Ventana ------------------------------------------------------------- */

  // En base.html hay una sola <dialog id="ventana">. Un botón o enlace la llena así:
  //   <a href="{% url 'pedidos:nuevo' %}" hx-get="{% url 'pedidos:nuevo' %}"
  //      hx-target="#ventana">Nuevo pedido</a>
  // Sin JavaScript, el enlace abre la misma página completa. El contenido usa la plantilla
  // piezas/ventana.html. Se cierra con Escape, con [data-cerrar-ventana] o al tocar fuera.

  function ventana() {
    return document.getElementById("ventana");
  }

  // Abre con transición (app.css: .ventana[open]). Cierra con transición: primero se
  // desvanece (.se-cierra) y al terminar se cierra de verdad.
  function cerrarVentana() {
    const dialogo = ventana();
    if (!dialogo || !dialogo.open || dialogo.classList.contains("se-cierra")) return;
    if (!hayMovimiento()) {
      dialogo.close();
      return;
    }
    dialogo.classList.add("se-cierra");
    alTerminar(dialogo, milisegundos("--duracion-corta"), function () {
      dialogo.classList.remove("se-cierra");
      dialogo.close();
    });
  }

  // Una respuesta vacía para la ventana (la que solo la cierra con "cerrar-ventana") no la
  // vacía de golpe mientras se cierra, ni la vuelve a abrir vacía.
  document.addEventListener("htmx:beforeSwap", function (evento) {
    const detalle = evento.detail;
    if (detalle.target === ventana() && !String(detalle.serverResponse || "").trim()) {
      detalle.shouldSwap = false;
    }
  });

  document.addEventListener("htmx:afterSwap", function (evento) {
    const dialogo = ventana();
    if (!dialogo || evento.detail.target !== dialogo || !dialogo.firstElementChild) return;
    dialogo.classList.remove("se-cierra");
    if (!dialogo.open) dialogo.showModal();
    // El cursor va al primer campo con error (después de "Guardar" con algo mal), al
    // marcado con autofocus o, si no hay, al primer campo (no a la X de cerrar, que va
    // antes). Una ventana sin campos lo deja en su primer botón.
    const primero =
      dialogo.querySelector(".campo--error .campo__control") ||
      dialogo.querySelector("[autofocus]") ||
      dialogo.querySelector(".campo__control:not([disabled])") ||
      dialogo.querySelector("input:not([type=hidden]), select, textarea, button");
    if (primero) primero.focus();
  });

  document.addEventListener("click", function (evento) {
    const dialogo = ventana();
    if (!dialogo || !dialogo.open) return;
    // Tocar el fondo oscuro (fuera de la ventana) también la cierra.
    if (evento.target.closest("[data-cerrar-ventana]") || evento.target === dialogo) {
      cerrarVentana();
    }
  });

  // Escape también la cierra con su transición (sin esto, el navegador la cierra de golpe).
  document.addEventListener("cancel", function (evento) {
    if (evento.target !== ventana() || !hayMovimiento()) return;
    evento.preventDefault();
    cerrarVentana();
  }, true);

  // El servidor puede cerrarla después de guardar con la cabecera "HX-Trigger: cerrar-ventana".
  document.body.addEventListener("cerrar-ventana", cerrarVentana);

  document.addEventListener("close", function (evento) {
    const dialogo = ventana();
    if (evento.target !== dialogo) return;
    // Al cerrarse con transición, HTMX cambió la página mientras la ventana seguía abierta (lo
    // de atrás no se podía enfocar) y el botón que la abrió puede ya no estar. Entonces el
    // cursor va al que la respuesta marcó con autofocus (Telas: "Entró" o "Usé"), para que
    // quien usa el teclado no pierda su lugar.
    const activo = document.activeElement;
    if (!activo || activo === document.body || !activo.isConnected || dialogo.contains(activo)) {
      const marcado = document.querySelector("#contenido [autofocus]");
      if (marcado) marcado.focus();
    }
    dialogo.replaceChildren();
  }, true);

  /* 6. Botones "Copiar" ---------------------------------------------------- */

  // <button type="button" data-copiar="texto a copiar">Copiar resumen</button>
  // o, para copiar lo que dice otro elemento: data-copiar-de="#id-del-elemento".
  // Al copiar, el botón dice "Copiado" un momento.

  const COPIADO_MS = 2000;

  document.addEventListener("click", function (evento) {
    const boton = evento.target.closest("[data-copiar], [data-copiar-de]");
    if (!boton) return;
    let texto = boton.dataset.copiar;
    if (boton.dataset.copiarDe) {
      const origen = document.querySelector(boton.dataset.copiarDe);
      texto = origen ? (origen.value !== undefined ? origen.value : origen.innerText) : "";
    }
    if (!texto || !navigator.clipboard) return;
    navigator.clipboard.writeText(texto).then(function () {
      if (boton.dataset.htmlOriginal) return;
      // Se guarda el contenido entero: un botón puede traer su texto de computador y el
      // de celular (.texto-computador y .texto-celular).
      boton.dataset.htmlOriginal = boton.innerHTML;
      // "Copiado" es más corto: el botón guarda su ancho para que los de al lado no se muevan.
      boton.style.minWidth = boton.offsetWidth + "px";
      boton.textContent = "Copiado";
      // El aviso corto de la demo, que también oyen los lectores de pantalla (sección 12).
      mostrarAviso("Copiado. Ya lo puedes pegar en WhatsApp.");
      window.setTimeout(function () {
        boton.innerHTML = boton.dataset.htmlOriginal;
        boton.style.minWidth = "";
        delete boton.dataset.htmlOriginal;
      }, COPIADO_MS);
    });
  });

  // Un aviso que solo oyen los lectores de pantalla (una sola caja para toda la página).
  function avisar(texto) {
    let caja = document.getElementById("aviso-lector");
    if (!caja) {
      caja = document.createElement("div");
      caja.id = "aviso-lector";
      caja.className = "oculto";
      caja.setAttribute("role", "status");
      document.body.appendChild(caja);
    }
    caja.textContent = "";
    window.setTimeout(function () { caja.textContent = texto; }, 50);
  }

  /* 7. Elegir un archivo --------------------------------------------------- */

  // En celular el texto "Ningún archivo seleccionado" se esconde (no cabe). Al elegir uno,
  // el campo queda marcado y el nombre del archivo se vuelve a ver (static/css/app.css).
  document.addEventListener("change", function (evento) {
    const campo = evento.target;
    if (!campo.matches || !campo.matches('input[type="file"]')) return;
    if (campo.files && campo.files.length) {
      campo.setAttribute("data-elegido", "");
    } else {
      campo.removeAttribute("data-elegido");
    }
  });

  /* 8. El cursor no se pierde ---------------------------------------------- */

  // Un botón que desaparece al tocarlo ("Ver todo el mes", "Cancelar") dice a dónde va el
  // cursor después con data-foco-despues="id". Sin esto, el cursor vuelve al principio de
  // la página y quien usa el teclado pierde su lugar.
  let focoDespues = null;

  document.addEventListener("htmx:beforeRequest", function (evento) {
    const elemento = evento.detail.elt;
    focoDespues = (elemento && elemento.dataset && elemento.dataset.focoDespues) || null;
  });

  document.addEventListener("htmx:afterSettle", function () {
    if (!focoDespues) return;
    const activo = document.activeElement;
    const perdido = !activo || activo === document.body || !activo.isConnected;
    const destino = document.getElementById(focoDespues);
    if (perdido && destino) {
      destino.focus();
      focoDespues = null;
    }
  });

  /* 9. Abrir una fila plegada ---------------------------------------------- */

  // "Registrar abono" (arriba del pedido) y "Cobrar el saldo" (en Hoy) llevan al campo del
  // abono, que está dentro de la fila plegada "Registrar un abono" de la tarjeta Pagos.
  // Antes de llegar se abre la fila y el cursor queda en el campo, listo para escribir.
  function abrirHasta(id) {
    const destino = id && document.getElementById(id);
    if (!destino) return;
    const plegada = destino.closest("details");
    if (!plegada) return;
    plegada.open = true;
    // En el centro de la pantalla, para que se vea también su etiqueta ("Valor del abono").
    destino.scrollIntoView({ block: "center" });
    destino.focus({ preventScroll: true });
  }

  document.addEventListener("click", function (evento) {
    const enlace = evento.target.closest('a[href^="#"]');
    if (!enlace) return;
    const id = decodeURIComponent(enlace.getAttribute("href").slice(1));
    const destino = document.getElementById(id);
    if (!destino || !destino.closest("details")) return;
    evento.preventDefault();
    abrirHasta(id);
    if (window.history.replaceState) window.history.replaceState(null, "", "#" + id);
  });

  document.addEventListener("DOMContentLoaded", function () {
    if (window.location.hash) abrirHasta(decodeURIComponent(window.location.hash.slice(1)));
  });

  /* 10. Botones que esperan ------------------------------------------------ */

  // Si una acción tarda más que --espera-cargando, el botón que la pidió muestra un círculo
  // que gira en lugar de su texto, sin cambiar de ancho (.esta-cargando en app.css). Al
  // llegar la respuesta vuelve a ser el de antes, o lo reemplaza la parte nueva.
  // Un formulario que no debe mostrarlo (porque no cambia de página) lleva data-sin-cargando.

  function empezarEspera(boton) {
    terminarEspera(boton);
    boton.esperaCargando = window.setTimeout(function () {
      if (!boton.isConnected) return;
      boton.classList.add("esta-cargando");
      boton.setAttribute("aria-busy", "true");
    }, milisegundos("--espera-cargando"));
  }

  function terminarEspera(boton) {
    if (!boton) return;
    window.clearTimeout(boton.esperaCargando);
    boton.classList.remove("esta-cargando");
    boton.removeAttribute("aria-busy");
  }

  // Qué botón pidió la acción: el mismo elemento si es un botón o un enlace; en un
  // formulario, el botón con el que se envió. Un campo (el buscador mientras se escribe) no.
  function botonQuePide(elemento, origen) {
    if (!elemento || !elemento.matches) return null;
    if (elemento.matches("button, a, .filtro, .paso")) return elemento;
    if (elemento.tagName === "FORM" && origen && origen.type === "submit") {
      return origen.submitter || elemento.querySelector('[type="submit"]');
    }
    return null;
  }

  document.addEventListener("htmx:beforeRequest", function (evento) {
    const detalle = evento.detail;
    if (detalle.elt && detalle.elt.closest && detalle.elt.closest("[data-sin-cargando]")) return;
    const origen = detalle.requestConfig && detalle.requestConfig.triggeringEvent;
    const boton = botonQuePide(detalle.elt, origen);
    if (!boton || !detalle.xhr) return;
    detalle.xhr.botonQueEspera = boton;
    empezarEspera(boton);
  });

  document.addEventListener("htmx:afterRequest", function (evento) {
    if (evento.detail.xhr) terminarEspera(evento.detail.xhr.botonQueEspera);
  });

  // Un formulario normal (sin HTMX): el botón espera mientras llega la página siguiente.
  document.addEventListener("submit", function (evento) {
    const formulario = evento.target;
    if (evento.defaultPrevented || formulario.closest("[data-sin-cargando]")) return;
    if (formulario.target && formulario.target !== "_self") return;
    if (evento.submitter) empezarEspera(evento.submitter);
  });

  // Al volver con el botón "atrás", la página guardada no queda con botones esperando.
  window.addEventListener("pageshow", function () {
    document.querySelectorAll(".esta-cargando").forEach(terminarEspera);
  });

  /* 11. Lo que entra y sale sin recargar (HTMX) ---------------------------- */

  // Cuando HTMX cambia una parte de la página:
  //  - lo que se va se desvanece; si es un bloque (una fila de una lista), además se cierra
  //    suavemente. HTMX espera --duracion-corta antes de cambiar la página;
  //  - lo que llega aparece con un desvanecido de --duracion.
  // Se reconoce por su id: lo que tiene el mismo id antes y después "sigue" y no se anima
  // (solo cambia su contenido). Por eso las filas de las listas llevan id (id="abono-12"), y
  // un bloque que se cambia por otro en el mismo lugar (una fila por su pregunta "¿Quitar?")
  // conserva el id. Una parte que se actualiza mientras se escribe y no debe parpadear lleva
  // data-sin-animar.

  let idsAntes = null;    // ids que había antes del cambio
  let zonasNuevas = [];   // zonas cuyo contenido cambia entero (sin nada que siga)
  let saliendo = [];      // animaciones de lo que se va
  let posicionesAntes = new Map();  // dónde estaban las filas de tabla vecinas de una que se va

  function seVe(elemento) {
    return elemento.isConnected && elemento.getClientRects().length > 0;
  }

  // Sin los que están dentro de otro de la lista (se anima el de afuera).
  function deAfuera(elementos) {
    return elementos.filter(function (elemento) {
      return !elementos.some(function (otro) {
        return otro !== elemento && otro.contains(elemento);
      });
    });
  }

  function esBloque(elemento) {
    return /^(block|flex|grid|list-item|flow-root)$/.test(getComputedStyle(elemento).display);
  }

  // El modo de HTMX (outerHTML, innerHTML...) con que se cambia el objetivo.
  function modoDeCambio(detalle) {
    const elemento = detalle.elt || (detalle.requestConfig && detalle.requestConfig.elt);
    const conModo = elemento && elemento.closest && elemento.closest("[hx-swap]");
    const texto = detalle.swapOverride || (conModo && conModo.getAttribute("hx-swap")) ||
      (window.htmx && window.htmx.config.defaultSwapStyle) || "innerHTML";
    return texto.trim().split(/\s+/)[0];
  }

  const SIN_REEMPLAZO = /^(beforebegin|afterbegin|beforeend|afterend|none)$/i;

  // Las zonas que cambian: el objetivo y las partes que llegan aparte (hx-swap-oob).
  // `entera` dice si la zona misma se reemplaza (outerHTML) o solo su contenido.
  function zonasQueCambian(detalle, respuesta) {
    const zonas = [];
    const modo = modoDeCambio(detalle);
    if (detalle.target && !SIN_REEMPLAZO.test(modo)) {
      zonas.push({ zona: detalle.target, entera: /^(outerHTML|delete)$/i.test(modo) });
    }
    respuesta.querySelectorAll("[hx-swap-oob]").forEach(function (parte) {
      const valor = parte.getAttribute("hx-swap-oob");
      const dos = valor.indexOf(":");
      const modoParte = dos > -1 ? valor.slice(0, dos) : (valor === "true" ? "outerHTML" : valor);
      const zona = dos > -1 ? document.querySelector(valor.slice(dos + 1))
        : (parte.id ? document.getElementById(parte.id) : null);
      if (zona && !SIN_REEMPLAZO.test(modoParte)) {
        zonas.push({ zona: zona, entera: /^outerHTML$/i.test(modoParte) });
      }
    });
    return zonas.filter(function (z) {
      return seVe(z.zona) && !z.zona.closest("[data-sin-animar]");
    });
  }

  function cerrarBloque(elemento, duracion) {
    const estilo = getComputedStyle(elemento);
    const desde = {
      height: elemento.offsetHeight + "px",
      opacity: 1,
      paddingTop: estilo.paddingTop,
      paddingBottom: estilo.paddingBottom,
      marginTop: estilo.marginTop,
      marginBottom: estilo.marginBottom,
    };
    const hasta = {
      height: "0px", opacity: 0, paddingTop: "0px", paddingBottom: "0px",
      marginTop: "0px", marginBottom: "0px",
    };
    elemento.style.overflow = "hidden";
    return elemento.animate([desde, hasta], {
      duration: duracion, easing: curva("--curva-salida"), fill: "forwards",
    });
  }

  function desvanecer(elemento, duracion) {
    return elemento.animate([{ opacity: 1 }, { opacity: 0 }], {
      duration: duracion, easing: curva("--curva-salida"), fill: "forwards",
    });
  }

  function aparecer(elemento, duracion) {
    elemento.animate([{ opacity: 0 }, { opacity: 1 }], {
      duration: duracion, easing: curva("--curva"),
    });
  }

  document.addEventListener("htmx:beforeSwap", function (evento) {
    const detalle = evento.detail;
    if (window.htmx) window.htmx.config.defaultSwapDelay = 0;
    idsAntes = null;
    zonasNuevas = [];
    posicionesAntes = new Map();
    if (!detalle.shouldSwap || !hayMovimiento()) return;
    const plantilla = document.createElement("template");
    plantilla.innerHTML = typeof detalle.serverResponse === "string" ? detalle.serverResponse : "";
    const respuesta = plantilla.content;
    const zonas = zonasQueCambian(detalle, respuesta);
    if (!zonas.length) return;
    const idsNuevos = new Set(Array.from(respuesta.querySelectorAll("[id]"), function (e) {
      return e.id;
    }));
    idsAntes = new Set(Array.from(document.querySelectorAll("[id]"), function (e) {
      return e.id;
    }));
    let seVan = [];
    zonas.forEach(function (z) {
      const conId = Array.from(z.zona.querySelectorAll("[id]"));
      if (z.entera) conId.unshift(z.zona);
      const siguen = conId.filter(function (e) { return idsNuevos.has(e.id); });
      if (!z.entera && !siguen.length) {
        // Nada de lo que había sigue (o estaba vacía): todo el contenido sale y el nuevo entra.
        seVan = seVan.concat(Array.from(z.zona.children));
        zonasNuevas.push(z.zona);
        return;
      }
      seVan = seVan.concat(conId.filter(function (e) {
        return !idsNuevos.has(e.id) && seVe(e);
      }));
    });
    seVan = deAfuera(seVan);
    if (!seVan.length) return;
    const duracion = milisegundos("--duracion-corta");
    saliendo = seVan.map(function (elemento) {
      // Una fila (un bloque) se cierra; lo demás (una fila de tabla, un texto) se desvanece.
      const animacion = esBloque(elemento) && elemento.tagName !== "TR"
        ? cerrarBloque(elemento, duracion) : desvanecer(elemento, duracion);
      return { elemento: elemento, animacion: animacion };
    });
    // Una fila de tabla no se puede achicar: se desvanece y, después del cambio, las filas de
    // abajo suben suave a ocupar su lugar (se anotan dónde estaban).
    posicionesAntes = new Map();
    seVan.forEach(function (elemento) {
      if (elemento.tagName !== "TR" || !elemento.parentElement) return;
      Array.from(elemento.parentElement.children).forEach(function (fila) {
        if (fila.id && seVan.indexOf(fila) === -1) {
          posicionesAntes.set(fila.id, fila.getBoundingClientRect().top);
        }
      });
    });
    // HTMX lee la espera justo después de este aviso; enseguida vuelve a 0 para los demás.
    if (window.htmx) {
      window.htmx.config.defaultSwapDelay = duracion;
      Promise.resolve().then(function () { window.htmx.config.defaultSwapDelay = 0; });
    }
  });

  document.addEventListener("htmx:afterSwap", function () {
    // Lo que debía irse y sigue en la página (no era parte del cambio) vuelve a verse.
    saliendo.forEach(function (s) {
      if (s.elemento.isConnected) {
        s.animacion.cancel();
        s.elemento.style.overflow = "";
      }
    });
    saliendo = [];
    // Las filas de tabla que quedaron suben suave desde donde estaban.
    const posiciones = posicionesAntes;
    posicionesAntes = new Map();
    posiciones.forEach(function (arriba, id) {
      const fila = document.getElementById(id);
      if (!fila) return;
      const distancia = arriba - fila.getBoundingClientRect().top;
      if (Math.abs(distancia) < 1) return;
      fila.animate([{ transform: "translateY(" + distancia + "px)" }, { transform: "none" }], {
        duration: milisegundos("--duracion"), easing: curva("--curva"),
      });
    });
    if (!idsAntes) return;
    const antes = idsAntes;
    const zonas = zonasNuevas;
    idsAntes = null;
    zonasNuevas = [];
    const duracion = milisegundos("--duracion");
    let llegan = Array.from(
      document.querySelectorAll("#contenido [id], #ventana [id], .menu [id]")
    ).filter(function (e) { return !antes.has(e.id) && seVe(e); });
    zonas.forEach(function (zona) {
      if (zona.isConnected) llegan = llegan.concat(Array.from(zona.children));
    });
    deAfuera(llegan).forEach(function (elemento) { aparecer(elemento, duracion); });
  });

  // Una lista que se desplaza por dentro (.desplazable con id) no vuelve arriba cuando HTMX
  // trae otra vez la tarjeta que la contiene: queda donde estaba (lo pidió el carril de Mi
  // taller). No es una animación: vale también con menos movimiento.
  let desplazamientos = new Map();

  document.addEventListener("htmx:beforeSwap", function (evento) {
    desplazamientos = new Map();
    if (!evento.detail.shouldSwap) return;
    document.querySelectorAll(".desplazable[id]").forEach(function (lista) {
      if (lista.scrollTop) desplazamientos.set(lista.id, lista.scrollTop);
    });
  });

  document.addEventListener("htmx:afterSwap", function () {
    desplazamientos.forEach(function (arriba, id) {
      const lista = document.getElementById(id);
      if (lista && lista.scrollTop === 0) lista.scrollTop = arriba;
    });
    desplazamientos = new Map();
  });

  /* 12. Aviso corto de confirmación --------------------------------------- */

  // Después de guardar, el servidor manda el texto con config/avisos.py:
  //  - si la página se queda, en la cabecera de HTMX: HX-Trigger: {"aviso": "Abono registrado."};
  //  - si se va a otra página, como mensaje de Django, que base.html deja en #avisos-pendientes.
  // Se ve una píldora negra abajo durante --tiempo-aviso y se va. Los lectores de pantalla lo
  // oyen por la caja de avisar() (la píldora lleva aria-hidden).

  function mostrarAviso(texto) {
    const caja = document.getElementById("avisos");
    if (!texto || !caja) return;
    const aviso = document.createElement("p");
    aviso.className = "aviso-corto";
    aviso.textContent = texto;
    caja.appendChild(aviso);
    avisar(texto);
    window.setTimeout(function () {
      if (!hayMovimiento()) {
        aviso.remove();
        return;
      }
      aviso.classList.add("se-va");
      alTerminar(aviso, milisegundos("--duracion-corta"), function () { aviso.remove(); });
    }, milisegundos("--tiempo-aviso"));
  }

  document.body.addEventListener("aviso", function (evento) {
    const detalle = evento.detail || {};
    mostrarAviso(typeof detalle.value === "string" ? detalle.value : "");
  });

  document.addEventListener("DOMContentLoaded", function () {
    const pendientes = document.getElementById("avisos-pendientes");
    if (!pendientes) return;
    pendientes.querySelectorAll("[data-aviso]").forEach(function (mensaje) {
      mostrarAviso(mensaje.textContent.trim());
    });
    pendientes.remove();
  });

  /* 13. Atajo Ctrl K, menús desplegables y lo que se muestra con un botón --- */

  // Ctrl K (o Cmd K en Mac) lleva al buscador del menú, como en Shopify. Con el menú
  // contraído, primero lo abre. En celular no hay menú lateral: abre la página de buscar.
  function enfocarBuscador() {
    const campo = document.querySelector("[data-atajo-buscar]");
    if (!campo) return false;
    if (campo.offsetParent === null) {
      const marco = document.querySelector("[data-marco]");
      if (marco && marco.classList.contains("marco--contraido") &&
          window.matchMedia("(min-width: 768px)").matches) {
        contraerMenu(false);
      } else {
        const formulario = campo.closest("form");
        if (formulario && formulario.action) window.location.href = formulario.action;
        return true;
      }
    }
    campo.focus();
    campo.select();
    return true;
  }

  document.addEventListener("keydown", function (evento) {
    if ((evento.ctrlKey || evento.metaKey) && !evento.altKey && !evento.shiftKey &&
        evento.key.toLowerCase() === "k") {
      if (enfocarBuscador()) evento.preventDefault();
    }
  });

  // Menús desplegables (<details class="desplegable">): se abre uno a la vez y se cierran al
  // tocar afuera, al elegir una opción o con Escape (el cursor vuelve a su botón).
  function cerrarDesplegables(salvo) {
    document.querySelectorAll("details.desplegable[open]").forEach(function (menu) {
      if (menu !== salvo) menu.open = false;
    });
  }

  document.addEventListener("click", function (evento) {
    const menu = evento.target.closest("details.desplegable");
    cerrarDesplegables(menu);
    if (menu && evento.target.closest(".desplegable__opcion")) {
      // Se deja pasar el clic (un enlace o un botón de envío) y después se cierra.
      window.setTimeout(function () { menu.open = false; }, 0);
    }
  });

  document.addEventListener("keydown", function (evento) {
    if (evento.key !== "Escape") return;
    const abierto = document.querySelector("details.desplegable[open]");
    if (!abierto) return;
    abierto.open = false;
    const boton = abierto.querySelector("summary");
    if (boton) boton.focus();
  });

  // Un botón (o enlace) con data-mostrar="id" muestra u oculta esa parte y deja el cursor en
  // su primer campo (el buscador de Pedidos detrás de la lupa). Sin JavaScript, el enlace lleva
  // a la misma página con la parte ya a la vista.
  document.addEventListener("click", function (evento) {
    const boton = evento.target.closest("[data-mostrar]");
    if (!boton) return;
    const parte = document.getElementById(boton.dataset.mostrar);
    if (!parte) return;
    evento.preventDefault();
    parte.hidden = !parte.hidden;
    boton.setAttribute("aria-expanded", String(!parte.hidden));
    if (!parte.hidden) {
      const campo = parte.querySelector("input:not([type=hidden]), select, textarea");
      if (campo) campo.focus();
    }
  });

  /* 14. Asistente ------------------------------------------------------------ */

  // El panel del asistente (docs/10-asistente.md, docs/11-plan-tanda-7.md, sección 1.5).
  // base.html deja <aside id="asistente"> solo si la dueña lo tiene; HTMX lo llena la primera
  // vez que se abre (evento "asistente-abrir"). Lo que hay adentro lo dibuja el servidor:
  //   [data-asistente-abrir]       el botón del encabezado: abre y cierra;
  //   [data-asistente-cerrar]      la equis del panel;
  //   [data-asistente-form]        el formulario de la pregunta (hx-post, con hx-target
  //                                "#asistente-pendiente" y hx-swap "outerHTML");
  //   [data-asistente-sugerencia]  una sugerencia: la escribe y la envía;
  //   #asistente-mensajes          la conversación, que se desplaza por dentro;
  //   [data-asistente-bienvenida]  el saludo de la conversación vacía (se va con la primera
  //                                pregunta);
  //   [data-asistente-caja]        la caja grande de Hoy: abre el panel y pregunta desde allá.
  // Ctrl J (o Cmd J) abre y cierra. Esc cierra si no hay una ventana ni un menú abierto.
  // Enter envía y Shift+Enter hace un salto de línea.

  // En computador el panel va al lado de la hoja y se recuerda abierto al cambiar de
  // pantalla. En celular y en pantallas medianas tapa la hoja: no se recuerda.
  const PANEL_AL_LADO = "(min-width: 1024px)";
  const SIN_RESPUESTA = "No pude contestar ahora. Intenta de nuevo en un rato.";
  let asistenteQuiereFoco = false;
  let preguntaEnEspera = "";

  function panelAsistente() {
    return document.getElementById("asistente");
  }

  function marcarBotonesAsistente(abierto) {
    document.querySelectorAll("[data-asistente-abrir]").forEach(function (boton) {
      boton.classList.toggle("es-presionado", abierto);
      boton.setAttribute("aria-expanded", String(abierto));
    });
  }

  function listaAsistente(panel) {
    return panel.querySelector("#asistente-mensajes");
  }

  function bajarAlFinal(panel) {
    const lista = listaAsistente(panel);
    if (lista) lista.scrollTop = lista.scrollHeight;
  }

  function enfocarAsistente(panel) {
    bajarAlFinal(panel);
    const caja = panel.querySelector("[data-asistente-form] textarea");
    if (caja && !caja.disabled) caja.focus();
  }

  // Entrar y salir con movimiento (app.css, sección 8, "El panel del asistente entra y
  // sale"). Solo cuando la persona lo abre o lo cierra: si ya viene abierto de otra pantalla,
  // no se anima; con menos movimiento pedido, abre y cierra de una vez.
  //   Computador: el navegador toma una foto antes y otra después (View Transitions) y pasa
  //   de una a otra: el panel entra desde la derecha y la orilla de la hoja se corre con él.
  //   La hoja se acomoda a su nuevo ancho una sola vez; si se animara su ancho, lo de adentro
  //   (textos, tarjetas, el saludo) se reacomodaría en cada cuadro y se vería temblar.
  //   Pantallas medianas y celular: el panel va encima de la hoja; solo se desliza (.entra y
  //   .se-cierra) y la hoja no cambia.
  // Mientras se mueve, `asistenteVaAbierto` dice cómo va a quedar, y cada movimiento lleva
  // su número: si se toca otra vez a mitad de camino, cambia de dirección sin trabarse.
  let movimientoAsistente = 0;
  let asistenteVaAbierto = null;

  function estaAbierto(panel) {
    return asistenteVaAbierto === null ? !panel.hidden : asistenteVaAbierto;
  }

  function mostrarAsistente(panel, abrir, despues) {
    const numero = ++movimientoAsistente;
    const marco = panel.closest("[data-marco]") || panel.parentElement;
    asistenteVaAbierto = abrir;
    panel.classList.remove("entra", "se-cierra");
    function terminar() {
      if (numero !== movimientoAsistente) return;
      asistenteVaAbierto = null;
      panel.classList.remove("entra", "se-cierra");
      marco.classList.remove("asistente-cambia");
    }
    function cambiar() {
      panel.hidden = !abrir;
      if (despues) despues();
    }

    if (!hayMovimiento()) {
      cambiar();
      terminar();
    } else if (window.matchMedia(PANEL_AL_LADO).matches) {
      if (!document.startViewTransition) {
        cambiar();  // un navegador sin fotos: cambia de una vez, sin temblar
        terminar();
        return;
      }
      // .asistente-cambia les da nombre a la hoja y al panel solo durante el cambio.
      marco.classList.add("asistente-cambia");
      document.startViewTransition(cambiar).finished.finally(terminar);
    } else {
      if (abrir) panel.hidden = false;
      void panel.offsetWidth;  // así la clase, puesta otra vez, anima desde el principio
      panel.classList.add(abrir ? "entra" : "se-cierra");
      alTerminar(panel, milisegundos(abrir ? "--duracion-larga" : "--duracion"), function () {
        if (numero !== movimientoAsistente) return;
        if (!abrir) panel.hidden = true;
        terminar();
      });
      if (abrir && despues) despues();
    }
  }

  function abrirAsistente() {
    const panel = panelAsistente();
    if (!panel) return false;
    marcarBotonesAsistente(true);
    if (window.matchMedia(PANEL_AL_LADO).matches) {
      document.cookie = "asistente=abierto; path=/; max-age=" + UN_ANO + "; SameSite=Lax";
    }
    function listo() {
      if (panel.childElementCount) {
        enfocarAsistente(panel);
      } else if (window.htmx) {
        // Primera vez: se pide el panel. Al llegar, el cursor queda en la caja.
        asistenteQuiereFoco = true;
        window.htmx.trigger(panel, "asistente-abrir");
      }
    }
    if (estaAbierto(panel)) {
      listo();
    } else {
      mostrarAsistente(panel, true, listo);
    }
    return true;
  }

  function cerrarAsistente() {
    const panel = panelAsistente();
    if (!panel || !estaAbierto(panel)) return false;
    mostrarAsistente(panel, false);
    marcarBotonesAsistente(false);
    document.cookie = "asistente=; path=/; max-age=0; SameSite=Lax";
    // El cursor vuelve al botón que se ve (el del computador o el redondo del celular).
    const boton = Array.prototype.find.call(
      document.querySelectorAll("[data-asistente-abrir]"),
      function (b) { return b.offsetParent !== null; }
    );
    if (boton) boton.focus();
    return true;
  }

  function alternarAsistente() {
    const panel = panelAsistente();
    if (!panel) return false;
    return estaAbierto(panel) ? cerrarAsistente() : abrirAsistente();
  }

  document.addEventListener("click", function (evento) {
    if (evento.target.closest("[data-asistente-abrir]") && panelAsistente()) {
      evento.preventDefault();
      alternarAsistente();
      return;
    }
    if (evento.target.closest("[data-asistente-cerrar]")) {
      evento.preventDefault();
      cerrarAsistente();
      return;
    }
    const sugerencia = evento.target.closest("[data-asistente-sugerencia]");
    if (sugerencia) {
      const panel = sugerencia.closest("#asistente") || panelAsistente();
      const formulario = panel && panel.querySelector("[data-asistente-form]");
      const caja = formulario && formulario.querySelector("textarea");
      if (!caja || caja.disabled) return;
      evento.preventDefault();
      caja.value = sugerencia.dataset.asistenteSugerencia || sugerencia.textContent.trim();
      formulario.requestSubmit();
    }
  });

  // Se escucha antes que los demás (captura): así, si hay una ventana o un menú abierto, Esc
  // los cierra a ellos primero y el panel se queda.
  document.addEventListener("keydown", function (evento) {
    const panel = panelAsistente();
    if (!panel) return;
    if ((evento.ctrlKey || evento.metaKey) && !evento.altKey && !evento.shiftKey &&
        evento.key.toLowerCase() === "j") {
      evento.preventDefault();
      alternarAsistente();
    } else if (evento.key === "Escape" && estaAbierto(panel) &&
               !document.querySelector("dialog[open], details.desplegable[open]")) {
      cerrarAsistente();
    }
  }, true);

  // Enter envía; Shift+Enter (o mientras se escribe una tilde) hace salto de línea. La caja
  // crece con el texto hasta 120 px (el máximo lo pone app.css).
  const CAJAS_ASISTENTE = "[data-asistente-form] textarea, [data-asistente-caja] textarea";

  document.addEventListener("keydown", function (evento) {
    const caja = evento.target.closest && evento.target.closest(CAJAS_ASISTENTE);
    if (!caja || evento.key !== "Enter" || evento.shiftKey || evento.isComposing) return;
    evento.preventDefault();
    caja.closest("form").requestSubmit();
  });

  document.addEventListener("input", function (evento) {
    const caja = evento.target.closest && evento.target.closest(CAJAS_ASISTENTE);
    if (!caja) return;
    caja.style.height = "auto";
    caja.style.height = caja.scrollHeight + "px";
  });

  // Antes de que HTMX envíe la pregunta (captura, para ir antes que él): si está vacía o ya
  // hay una en camino, no se envía. Si no, la burbuja sale de una vez con los tres puntos, en
  // #asistente-pendiente, que es donde HTMX pondrá la respuesta.
  document.addEventListener("submit", function (evento) {
    const formulario = evento.target.closest("[data-asistente-form]");
    if (!formulario || !window.htmx) return;
    const panel = formulario.closest("#asistente") || document;
    const caja = formulario.querySelector("textarea");
    const pregunta = caja ? caja.value.trim() : "";
    if (!pregunta || panel.querySelector("#asistente-pendiente")) {
      evento.preventDefault();
      evento.stopImmediatePropagation();
      return;
    }
    const pagina = formulario.querySelector("input[name=pagina]");
    if (pagina) pagina.value = window.location.pathname + window.location.search;
    const lista = panel.querySelector("#asistente-mensajes");
    if (!lista) return;
    const bienvenida = lista.querySelector("[data-asistente-bienvenida]");
    if (bienvenida) bienvenida.remove();

    const pendiente = document.createElement("div");
    pendiente.id = "asistente-pendiente";
    pendiente.className = "asistente__turno";
    const burbuja = document.createElement("div");
    burbuja.className = "mensaje mensaje--usuaria";
    const texto = document.createElement("p");
    texto.textContent = pregunta;
    burbuja.appendChild(texto);
    const respuesta = document.createElement("div");
    respuesta.className = "mensaje mensaje--asistente";
    const pensando = document.createElement("p");
    pensando.className = "mensaje__pensando";
    const puntos = document.createElement("span");
    puntos.className = "mensaje__puntos";
    puntos.setAttribute("aria-hidden", "true");
    for (let i = 0; i < 3; i++) puntos.appendChild(document.createElement("span"));
    pensando.appendChild(puntos);
    pensando.appendChild(document.createTextNode("Revisando tus datos…"));
    respuesta.appendChild(pensando);
    pendiente.appendChild(burbuja);
    pendiente.appendChild(respuesta);
    lista.appendChild(pendiente);
    bajarAlFinal(panel);
    asistenteQuiereFoco = true;
  }, true);

  // La caja grande de Hoy: la pregunta se pasa al panel y se envía desde allá. Si el panel
  // todavía no ha llegado, espera a que llegue (htmx:afterSettle, abajo).
  function enviarPreguntaEnEspera() {
    const panel = panelAsistente();
    const formulario = panel && panel.querySelector("[data-asistente-form]");
    const caja = formulario && formulario.querySelector("textarea");
    if (!preguntaEnEspera || !caja) return;
    const pregunta = preguntaEnEspera;
    preguntaEnEspera = "";
    if (caja.disabled) return;  // sin preguntas: el panel ya dice cuándo vuelve
    caja.value = pregunta;
    formulario.requestSubmit();
  }

  document.addEventListener("submit", function (evento) {
    const formulario = evento.target.closest("[data-asistente-caja]");
    // Sin el panel o sin HTMX, el formulario lleva a la página del asistente.
    if (!formulario || !panelAsistente() || !window.htmx) return;
    evento.preventDefault();
    const campo = formulario.querySelector("textarea");
    const pregunta = campo ? campo.value.trim() : "";
    if (!pregunta) return;
    campo.value = "";
    campo.style.height = "";
    preguntaEnEspera = pregunta;
    abrirAsistente();
    enviarPreguntaEnEspera();
  }, true);

  // HTMX ya tomó la pregunta: se vacía la caja.
  document.addEventListener("htmx:beforeRequest", function (evento) {
    const formulario = evento.target.closest && evento.target.closest("[data-asistente-form]");
    if (!formulario) return;
    const caja = formulario.querySelector("textarea");
    if (caja) {
      caja.value = "";
      caja.style.height = "";
    }
  });

  // Llegó el panel o una respuesta: abajo del todo y el cursor en la caja (solo si la dueña
  // lo abrió o preguntó; al cargar una pantalla con el panel abierto, el cursor no se mueve).
  document.addEventListener("htmx:afterSettle", function (evento) {
    const panel = panelAsistente();
    if (!panel || !panel.contains(evento.target) && evento.target !== panel) return;
    bajarAlFinal(panel);
    if (asistenteQuiereFoco && !panel.hidden) {
      asistenteQuiereFoco = false;
      enfocarAsistente(panel);
    }
    if (preguntaEnEspera && !panel.hidden) enviarPreguntaEnEspera();
  });

  // Si la pregunta no llegó (sin internet, servidor caído), los tres puntos cambian por el
  // aviso, y se puede volver a preguntar.
  function sinRespuesta(evento) {
    const formulario = evento.target.closest && evento.target.closest("[data-asistente-form]");
    if (!formulario) return;
    const pendiente = document.getElementById("asistente-pendiente");
    if (!pendiente) return;
    pendiente.removeAttribute("id");
    const pensando = pendiente.querySelector(".mensaje__pensando");
    if (pensando) {
      const aviso = document.createElement("p");
      aviso.textContent = SIN_RESPUESTA;
      pensando.replaceWith(aviso);
    }
  }

  document.addEventListener("htmx:sendError", sinRespuesta);
  document.addEventListener("htmx:responseError", sinRespuesta);

})();
