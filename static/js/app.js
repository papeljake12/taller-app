/* JavaScript propio de la aplicación.
   1. Menú que se contrae (y se recuerda en este navegador).
   2. Panel "Más" de la barra de abajo en celular.
   3. Fotos que pasan ("Trabajos del taller").
   4. HTMX envía la protección CSRF en cada petición, y dibuja los formularios con errores.
   5. Ventana (para "Nuevo pedido" y otros formularios cortos).
   6. Botones "Copiar".

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
    const primero = dialogo.querySelector("[autofocus], input, select, textarea, button");
    if (primero) primero.focus();
  });

  document.addEventListener("click", function (evento) {
    // Abierta como página (sin la ventana): "Cancelar" vuelve a la página anterior.
    if (evento.target.closest(".ventana--pagina [data-cerrar-ventana]")) {
      window.history.back();
      return;
    }
    const dialogo = ventana();
    if (!dialogo || !dialogo.open) return;
    // Tocar el fondo oscuro (fuera de la ventana) también la cierra.
    if (evento.target.closest("[data-cerrar-ventana]") || evento.target === dialogo) {
      dialogo.close();
    }
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
      if (boton.dataset.textoOriginal) return;
      boton.dataset.textoOriginal = boton.textContent;
      boton.textContent = "Copiado";
      window.setTimeout(function () {
        boton.textContent = boton.dataset.textoOriginal;
        delete boton.dataset.textoOriginal;
      }, COPIADO_MS);
    });
  });
})();
