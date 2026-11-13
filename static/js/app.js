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

   Este archivo es compartido: después de la tanda 2 solo lo cambia el coordinador. */

(function () {
  "use strict";

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

  function contraerMenu(contraido) {
    const marco = document.querySelector("[data-marco]");
    if (!marco) return;
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
    panel.hidden = !abierto;
    boton.setAttribute("aria-expanded", String(abierto));
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

  document.addEventListener("htmx:afterSwap", function (evento) {
    const dialogo = ventana();
    if (!dialogo || evento.detail.target !== dialogo) return;
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
      dialogo.close();
    }
  });

  // El servidor puede cerrarla después de guardar con la cabecera "HX-Trigger: cerrar-ventana".
  document.body.addEventListener("cerrar-ventana", function () {
    const dialogo = ventana();
    if (dialogo && dialogo.open) dialogo.close();
  });

  document.addEventListener("close", function (evento) {
    if (evento.target === ventana()) evento.target.replaceChildren();
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
      // Los lectores de pantalla oyen qué sigue (el texto de la demo).
      avisar("Copiado. Ya lo puedes pegar en WhatsApp.");
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
})();
