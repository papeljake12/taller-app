/* La esfera del asistente (templates/piezas/esfera.html, los estilos en static/css/app.css,
   sección 7, "La esfera"): la misma de Lucy, el producto de David. Tinta azul que se mueve en
   agua, dibujada en un lienzo.

   Cómo se dibuja: un lienzo invisible de 64 × 64 puntos guarda un ruido que se deforma a sí
   mismo (tres capas giradas, para que no se note la cuadrícula). Ese ruido se calcula una sola
   vez por cuadro para todas las esferas de la página; se colorea con los tonos de la esfera
   (--esfera-tonos) y cada esfera lo copia agrandado y un poco difuminado. Pocos puntos
   agrandados: de ahí lo borroso.

   Qué se mueve: solo las esferas vivas (data-esfera-viva: la de arriba del panel y la de la
   caja de Hoy), unas 30 veces por segundo. Las del botón del encabezado se dibujan una vez y
   quedan quietas. El reloj se detiene si la pestaña no se ve, si ninguna viva está a la vista
   o si la persona pidió menos movimiento. Mientras el asistente revisa los datos
   (static/js/app.js pone #asistente-pendiente), la de arriba del panel lleva
   esfera--atendiendo: late (CSS) y la tinta corre más rápido.

   Las esferas nuevas (HTMX llena el panel sin recargar) las encuentra un MutationObserver, y
   un ResizeObserver ajusta cada lienzo a su esfera: una que estaba oculta se dibuja cuando
   aparece. Sin JavaScript se ve el azul de fondo de la esfera. */

(function () {
  "use strict";

  if (window.esferaDelAsistente) return;  // un solo motor por página
  window.esferaDelAsistente = true;

  const PUNTOS = 64;        // el lado del lienzo donde se calcula la tinta
  const CUADROS = 30;       // cuántas veces por segundo se redibuja la viva
  const DESENFOQUE = 0.012; // el difuminado al copiarla, en partes del lado
  const MARGEN = 0.04;      // cuánto se sale el dibujo por cada lado, para que el borde no se aclare
  const RAPIDEZ = 2.6;      // cuánto más rápido corre la tinta mientras el asistente revisa

  // ---------- El ruido: tinta que se deforma a sí misma ----------
  function hash(x, y) {
    let h = (Math.imul(x, 374761393) + Math.imul(y, 668265263)) | 0;
    h = Math.imul(h ^ (h >>> 13), 1274126177);
    return ((h ^ (h >>> 16)) >>> 0) / 4294967296;
  }

  function ruido(x, y) {
    const xi = Math.floor(x);
    const yi = Math.floor(y);
    const xf = x - xi;
    const yf = y - yi;
    const u = xf * xf * (3 - 2 * xf);
    const v = yf * yf * (3 - 2 * yf);
    const a = hash(xi, yi);
    const b = hash(xi + 1, yi);
    const c = hash(xi, yi + 1);
    const d = hash(xi + 1, yi + 1);
    return a + (b - a) * u + (c - a) * v + (a - b - c + d) * u * v;
  }

  function capas(x, y) {
    return ruido(x, y) * 0.6
      + ruido((0.8 * x - 0.6 * y) * 2.03 + 3.1, (0.6 * x + 0.8 * y) * 2.03 + 7.7) * 0.3
      + ruido((0.28 * x + 0.96 * y) * 4.1 + 11.3, (-0.96 * x + 0.28 * y) * 4.1 + 2.9) * 0.1;
  }

  // ---------- El cálculo compartido ----------
  const valores = new Uint8Array(PUNTOS * PUNTOS);  // el ruido de este cuadro, de 0 a 255
  let cuadro = 0;  // cuántas veces se ha calculado: cada escala sabe si está al día
  let reloj = 7;   // dónde va la tinta; arranca en un punto bonito

  function calcular() {
    const paso = 2 / PUNTOS;
    const t = reloj;
    let i = 0;
    for (let y = 0; y < PUNTOS; y++) {
      for (let x = 0; x < PUNTOS; x++) {
        const px = x * paso;
        const py = y * paso;
        const qx = capas(px + t * 0.11, py + t * 0.07);
        const qy = capas(px + 5.2 - t * 0.08, py + 1.3 + t * 0.09);
        let v = capas(px + 2.1 * qx + t * 0.04, py + 2.1 * qy - t * 0.05);
        v = (v - 0.3) / 0.42 + ((x - y) / PUNTOS) * 0.18;  // más luz arriba a la derecha
        valores[i++] = (v < 0 ? 0 : v > 1 ? 1 : v) * 255;
      }
    }
    cuadro += 1;
  }

  // Una escala de tonos ("#0b2a9a #0e48de …") convertida en 256 colores.
  function tabla(tonos) {
    const rgb = tonos.split(/\s+/)
      .filter(function (tono) { return /^#[0-9a-f]{6}$/i.test(tono); })
      .map(function (tono) { return [1, 3, 5].map(function (k) { return parseInt(tono.slice(k, k + 2), 16); }); });
    if (rgb.length < 2) return null;
    const colores = new Uint8ClampedArray(256 * 3);
    for (let i = 0; i < 256; i++) {
      const p = (i / 255) * (rgb.length - 1);
      const k = Math.min(Math.floor(p), rgb.length - 2);
      const f = p - k;
      for (let c = 0; c < 3; c++) colores[i * 3 + c] = rgb[k][c] + (rgb[k + 1][c] - rgb[k][c]) * f;
    }
    return colores;
  }

  // Cada escala de tonos en uso, con su lienzo chico coloreado desde el ruido compartido.
  const escalas = new Map();
  function fuente(tonos) {
    if (!escalas.has(tonos)) {
      const colores = tabla(tonos);
      if (!colores) return null;
      const lienzo = document.createElement("canvas");
      lienzo.width = PUNTOS;
      lienzo.height = PUNTOS;
      const ctx = lienzo.getContext("2d");
      escalas.set(tonos, { colores: colores, lienzo: lienzo, ctx: ctx, imagen: ctx.createImageData(PUNTOS, PUNTOS), cuadro: -1 });
    }
    const escala = escalas.get(tonos);
    if (escala.cuadro !== cuadro) {
      const datos = escala.imagen.data;
      const colores = escala.colores;
      for (let i = 0, j = 0; i < valores.length; i++, j += 4) {
        const c = valores[i] * 3;
        datos[j] = colores[c];
        datos[j + 1] = colores[c + 1];
        datos[j + 2] = colores[c + 2];
        datos[j + 3] = 255;
      }
      escala.ctx.putImageData(escala.imagen, 0, 0);
      escala.cuadro = cuadro;
    }
    return escala.lienzo;
  }

  // ---------- Las esferas de la página ----------
  const esferas = new Map();  // el elemento → su lienzo y su tamaño
  calcular();

  function dibujar(esfera) {
    if (!esfera.lado) return;
    const tonos = getComputedStyle(esfera.el).getPropertyValue("--esfera-tonos").trim();
    const origen = fuente(tonos);
    if (!origen) return;  // sin los estilos todavía: queda el azul de fondo
    const ctx = esfera.ctx;
    const lado = esfera.lado;
    const m = lado * MARGEN;
    ctx.clearRect(0, 0, lado, lado);
    ctx.filter = "blur(" + (lado * DESENFOQUE).toFixed(2) + "px)";
    ctx.imageSmoothingEnabled = true;
    ctx.imageSmoothingQuality = "high";
    ctx.drawImage(origen, -m, -m, lado + 2 * m, lado + 2 * m);
  }

  // ---------- El reloj ----------
  const menosMovimiento = window.matchMedia("(prefers-reduced-motion: reduce)");
  let pendiente = 0;
  let previo = 0;
  let ultimo = null;

  function vivas() {
    return Array.from(esferas.values()).filter(function (e) { return e.viva && e.lado; });
  }

  function bucle(ahora) {
    pendiente = requestAnimationFrame(bucle);
    if (ahora - previo < 1000 / CUADROS - 1) return;
    previo = ahora;
    const lista = vivas();
    const atiende = lista.some(function (e) { return e.el.classList.contains("esfera--atendiendo"); });
    if (ultimo !== null) reloj += Math.min(0.1, (ahora - ultimo) / 1000) * (atiende ? RAPIDEZ : 1);
    ultimo = ahora;
    calcular();
    lista.forEach(dibujar);
  }

  function revisarReloj() {
    const mover = !menosMovimiento.matches && !document.hidden && vivas().length > 0;
    if (mover && !pendiente) {
      ultimo = null;
      pendiente = requestAnimationFrame(bucle);
    } else if (!mover && pendiente) {
      cancelAnimationFrame(pendiente);
      pendiente = 0;
    }
  }

  // ---------- Encontrar las esferas ----------
  // El lienzo mide lo que la esfera por la densidad de la pantalla.
  function medir(esfera, ancho) {
    const lado = Math.round(ancho * (window.devicePixelRatio || 1));
    if (lado === esfera.lado) return;
    esfera.lado = lado;
    if (!lado) return;  // oculta: se dibuja cuando aparezca
    esfera.lienzo.width = lado;
    esfera.lienzo.height = lado;
    dibujar(esfera);
  }

  const tamanos = new ResizeObserver(function (entradas) {
    entradas.forEach(function (entrada) {
      const esfera = esferas.get(entrada.target);
      if (esfera) medir(esfera, entrada.contentRect.width);
    });
    revisarReloj();
  });

  // Cambiar el zoom o pasar la ventana a otra pantalla cambia la densidad sin cambiar el
  // tamaño: el ResizeObserver no se entera, esto sí.
  function vigilarDensidad() {
    matchMedia("(resolution: " + (window.devicePixelRatio || 1) + "dppx)").addEventListener("change", function () {
      esferas.forEach(function (esfera) { medir(esfera, esfera.el.getBoundingClientRect().width); });
      vigilarDensidad();
    }, { once: true });
  }

  // Mientras el asistente revisa los datos (app.js pone #asistente-pendiente), late la de
  // arriba del panel: la que responde. La de Hoy sigue moviéndose sin latir.
  function revisarAtendiendo() {
    const atiende = document.getElementById("asistente-pendiente") !== null;
    esferas.forEach(function (esfera) {
      if (esfera.panel) esfera.el.classList.toggle("esfera--atendiendo", atiende);
    });
  }

  function registrar(el) {
    if (esferas.has(el)) return;
    let lienzo = el.querySelector("canvas");
    if (!lienzo) {
      lienzo = document.createElement("canvas");
      lienzo.className = "esfera__lienzo";
      el.prepend(lienzo);
    }
    esferas.set(el, { el: el, lienzo: lienzo, ctx: lienzo.getContext("2d"), lado: 0, viva: el.hasAttribute("data-esfera-viva"),
      panel: el.closest(".asistente__titulo") !== null });
    tamanos.observe(el);
  }

  function buscar(nodo) {
    if (nodo.nodeType !== Node.ELEMENT_NODE) return;
    if (nodo.matches("[data-esfera]")) registrar(nodo);
    nodo.querySelectorAll("[data-esfera]").forEach(registrar);
  }

  function olvidarLasQueSalieron() {
    esferas.forEach(function (esfera, el) {
      if (el.isConnected) return;
      esferas.delete(el);
      tamanos.unobserve(el);
    });
  }

  new MutationObserver(function (cambios) {
    let salieron = false;
    cambios.forEach(function (cambio) {
      cambio.addedNodes.forEach(buscar);
      if (cambio.removedNodes.length) salieron = true;
    });
    if (salieron) olvidarLasQueSalieron();
    revisarAtendiendo();
    revisarReloj();
  }).observe(document.documentElement, { childList: true, subtree: true });

  document.querySelectorAll("[data-esfera]").forEach(registrar);
  vigilarDensidad();
  // Si los estilos llegaron después del primer dibujo, se vuelven a dibujar al cargar.
  window.addEventListener("load", function () { esferas.forEach(dibujar); }, { once: true });
  document.addEventListener("visibilitychange", revisarReloj);
  menosMovimiento.addEventListener("change", revisarReloj);
})();
