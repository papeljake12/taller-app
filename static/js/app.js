/* JavaScript propio de la aplicación.
   1. Menú que se contrae (y se recuerda en este navegador).
   2. Panel "Más" de la barra de abajo en celular.
   3. Fotos que pasan ("Trabajos del taller").
   4. HTMX envía la protección CSRF en cada petición.

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
})();
