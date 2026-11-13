/* JavaScript propio de la aplicación.
   1. Menú que se contrae (y se recuerda en este navegador).
   2. Panel "Más" de la barra de abajo en celular.
   3. Fotos que pasan ("Trabajos del taller").
   4. HTMX envía la protección CSRF en cada petición, y dibuja los formularios con errores.
   5. Ventana (para "Nuevo pedido" y otros formularios cortos).
   6. Botones "Copiar".
   7. Elegir un archivo (en celular).
   8. El cursor no se pierde cuando HTMX cambia una parte de la página.
   9. Un enlace a algo que está dentro de una fila plegada (<details>) la abre.
   10. Botones que esperan: "cargando" si la acción tarda.
   11. Lo que entra y sale sin recargar (HTMX): se desvanece, y una fila que se va se cierra.
   12. Aviso corto de confirmación ("Abono registrado.").

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
      contraerMenu(false);
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

  /* 3. Fotos que pasan ----------------------------------------------------- */

  const CADA_FOTO_MS = 4000;

  function iniciarFotos(contenedor) {
    if (contenedor.dataset.iniciado) return;
    contenedor.dataset.iniciado = "si";
    const fotos = contenedor.querySelectorAll("[data-foto]");
    const tarjeta = contenedor.closest(".tarjeta") || contenedor;
    const puntos = tarjeta.querySelectorAll("[data-punto]");
    const menosMovimiento = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    // Con una sola foto, o si la persona pidió menos movimiento, se queda en la primera.
    if (fotos.length < 2 || menosMovimiento) return;
    let actual = 0;
    window.setInterval(function () {
      fotos[actual].classList.remove("es-visible");
      if (puntos[actual]) puntos[actual].classList.remove("es-visible");
      actual = (actual + 1) % fotos.length;
      fotos[actual].classList.add("es-visible");
      if (puntos[actual]) puntos[actual].classList.add("es-visible");
    }, CADA_FOTO_MS);
  }

  function iniciarTodasLasFotos(raiz) {
    raiz.querySelectorAll("[data-fotos]").forEach(iniciarFotos);
  }

  document.addEventListener("DOMContentLoaded", function () {
    iniciarTodasLasFotos(document);
  });

  // Si HTMX trae una parte nueva de la página con fotos, también pasan.
  document.addEventListener("htmx:load", function (evento) {
    iniciarTodasLasFotos(evento.target);
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
})();
