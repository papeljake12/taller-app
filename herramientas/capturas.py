"""Capturas de las pantallas de una tanda, en computador (1280 px) y en celular (390 px).

Levanta el servidor de desarrollo, entra con una usuaria, abre cada pantalla con Chrome
(sin ventana, manejado por Playwright) y guarda una captura de la página completa en
docs/capturas/tanda-N/. Además avisa si algo se sale del ancho, si un archivo no cargó o
si el navegador mostró un error.

Con --formatos completo toma cada pantalla en 1366 x 768, en 1920 x 1080 y en celular (390 px).
En computador comprueba que la página misma no se desplace (docs/08-diseno.md,
"Desplazamiento": lo que se desplaza es el contenido de la hoja) y guarda la hoja completa,
con todo su contenido a la vista, para poder compararla con diseno/.

Uso:
    uv run python herramientas/capturas.py --tanda 1
    uv run python herramientas/capturas.py --tanda 1 --usuario david
    uv run python herramientas/capturas.py --tanda 1 --referencias carpeta/   (también las de diseno/)
    uv run python herramientas/capturas.py --tanda 3 --solo pedidos pedido --salida carpeta/
    uv run python herramientas/capturas.py --tanda 6 --formatos completo --salida docs/capturas/rediseno/

Solo se usa en el computador de desarrollo. Necesita Google Chrome instalado.
"""

import argparse
import os
import socket
import subprocess
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from urllib.request import urlopen

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.local")

COMPUTADOR = {"viewport": {"width": 1280, "height": 900}}
CELULAR = {"viewport": {"width": 390, "height": 844}, "is_mobile": True, "has_touch": True}

# Los tamaños de cada juego de capturas: (nombre en el archivo, formato).
FORMATOS = {
    "normal": [("computador", COMPUTADOR), ("celular", CELULAR)],
    "completo": [
        ("1366x768", {"viewport": {"width": 1366, "height": 768}}),
        ("1920x1080", {"viewport": {"width": 1920, "height": 1080}}),
        ("celular", CELULAR),
    ],
}


@dataclass
class Pantalla:
    nombre: str
    url: str
    referencia: str | None = None  # página de diseno/ en computador
    referencia_celular: str | None = None  # página de diseno/ en celular, si es otra
    menu: str | None = None  # "contraido" para el menú contraído
    sin_sesion: bool = False
    solo_computador: bool = False


# Cada tanda agrega aquí sus pantallas.
PANTALLAS = {
    1: [
        Pantalla("entrar", "/entrar/", "entrar.html", sin_sesion=True),
        Pantalla("hoy", "/", "hoy.html"),
        Pantalla("hoy-menu-contraido", "/", "hoy-menu-contraido.html", menu="contraido",
                 solo_computador=True),
        Pantalla("piezas", "/piezas/"),
    ],
    2: [
        Pantalla("pedidos", "/pedidos/", "pedidos.html"),
        Pantalla("pedido", "/pedidos/{pedido}/", "pedido.html"),
        Pantalla("nuevo-pedido", "/pedidos/nuevo/", "nuevo-pedido.html"),
        Pantalla("calendario", "/calendario/", "calendario.html"),
        Pantalla("clientes", "/clientes/", "clientes.html"),
        Pantalla("cotizador", "/cotizador/", "cotizador.html"),
        Pantalla("telas", "/telas/", "telas.html"),
        Pantalla("resumen", "/resumen/", "resumen.html"),
        Pantalla("mi-taller", "/mi-taller/", "mi-taller.html"),
        Pantalla("tallas-publico", "/tallas/{token}/", "tallas-publico.html", sin_sesion=True),
    ],
    3: [
        Pantalla("pedidos-atrasados", "/pedidos/?filtro=atrasados"),
        Pantalla("buscar", "/buscar/?q=esquina"),
    ],
    4: [
        Pantalla("resumen-octubre", "/resumen/?mes={mes_anterior}"),
    ],
}

DESBORDE = """(ancho) => {
  const fuera = [];
  for (const e of document.querySelectorAll('body *')) {
    const r = e.getBoundingClientRect();
    if (!r.width || r.right <= ancho + 0.5) continue;
    let p = e.parentElement, dentro = false;
    while (p && p !== document.body) {
      const o = getComputedStyle(p).overflowX;
      if (o === 'auto' || o === 'scroll' || o === 'hidden') { dentro = true; break; }
      p = p.parentElement;
    }
    if (!dentro) fuera.push(e.tagName.toLowerCase() + '.' + [...e.classList].join('.'));
  }
  return { ancho: document.documentElement.scrollWidth, fuera: fuera.slice(0, 5) };
}"""


# Computador: la página misma no se desplaza (lo hace el contenido de la hoja).
PAGINA_QUIETA = """() => {
  const pagina = document.scrollingElement || document.documentElement;
  return { pagina: pagina.scrollHeight, ventana: window.innerHeight };
}"""

# Para la captura de computador: el marco y la hoja crecen hasta mostrar todo el contenido.
HOJA_COMPLETA = (
    "html{overflow:visible!important}"
    ".marco{height:auto!important;min-height:100vh;overflow:visible!important}"
    ".hoja{overflow:visible!important}.hoja__contenido{overflow:visible!important}"
)


def puerto_libre():
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def levantar_servidor(puerto):
    proceso = subprocess.Popen(
        [sys.executable, "manage.py", "runserver", f"127.0.0.1:{puerto}", "--noreload"],
        cwd=RAIZ, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
    )
    for _ in range(100):
        try:
            urlopen(f"http://127.0.0.1:{puerto}/entrar/", timeout=1)
            return proceso
        except OSError:
            time.sleep(0.2)
    proceso.terminate()
    raise SystemExit("El servidor no arrancó.")


def abrir_sesion(usuario):
    """Crea una sesión para la usuaria, sin pedir su contraseña. Devuelve la clave."""
    import django

    django.setup()
    from django.contrib.auth import get_user_model
    from django.test import Client

    Usuario = get_user_model()
    if usuario:
        persona = Usuario.objects.get(username=usuario)
    else:
        persona = Usuario.objects.filter(rol="duena", is_active=True).order_by("pk").first()
        if persona is None:
            raise SystemExit("No hay ninguna dueña. Usa --usuario o carga los ejemplos.")
    cliente = Client()
    cliente.force_login(persona)
    return cliente.cookies["sessionid"].value, persona.username


def datos_para_direcciones(usuario):
    """Lo que va en las direcciones con número: el pedido del diseño (el del Restaurante)."""
    from pedidos.models import Pedido

    pedidos = Pedido.objects.filter(taller__usuarias__username=usuario)
    pedido = pedidos.filter(detalle__startswith="18 camisas").first() or pedidos.first()
    if pedido is None:
        return {}
    from django.utils import timezone

    from pedidos.calculos import sumar_meses

    anterior = sumar_meses(timezone.localdate(), -1)
    return {
        "pedido": pedido.pk,
        "token": pedido.token_tallas,
        "mes_anterior": f"{anterior.year}-{anterior.month:02d}",
    }


def cerrar_sesion(clave):
    from django.contrib.sessions.models import Session

    Session.objects.filter(session_key=clave).delete()


def capturar(navegador, url, archivo, formato, cookies, ancho, avisos=None, completa=False):
    contexto = navegador.new_context(device_scale_factor=1, **formato)
    if cookies:
        contexto.add_cookies(cookies)
    pagina = contexto.new_page()
    problemas = []
    pagina.on("console", lambda m: m.type == "error" and problemas.append("consola: " + m.text))
    pagina.on("pageerror", lambda e: problemas.append(f"error de JavaScript: {e}"))
    pagina.on("response", lambda r: r.status >= 400 and problemas.append(f"{r.status} {r.url}"))
    pagina.goto(url, wait_until="networkidle")
    pagina.evaluate("document.fonts.ready")
    pagina.wait_for_timeout(300)
    medida = pagina.evaluate(DESBORDE, ancho)
    if medida["ancho"] > ancho:
        problemas.append(f"la página mide {medida['ancho']} px de ancho: {medida['fuera']}")
    if avisos is not None and not formato.get("is_mobile"):
        quieta = pagina.evaluate(PAGINA_QUIETA)
        if quieta["pagina"] > quieta["ventana"] + 1:
            problemas.append(f"la página se desplaza: mide {quieta['pagina']} px de alto en una "
                             f"ventana de {quieta['ventana']} px")
        completa = True
    if completa and not formato.get("is_mobile"):
        pagina.add_style_tag(content=HOJA_COMPLETA)
        pagina.wait_for_timeout(100)
    archivo.parent.mkdir(parents=True, exist_ok=True)
    pagina.screenshot(path=str(archivo), full_page=True)
    contexto.close()
    return problemas


def main():
    argumentos = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    argumentos.add_argument("--tanda", type=int, required=True)
    argumentos.add_argument("--usuario", help="usuario con el que se entra (por defecto, la primera dueña)")
    argumentos.add_argument("--referencias", type=Path,
                            help="carpeta donde guardar también las capturas de diseno/")
    argumentos.add_argument("--solo", nargs="+", metavar="PANTALLA",
                            help="capturar solo estas pantallas (por su nombre)")
    argumentos.add_argument("--salida", type=Path,
                            help="carpeta de las capturas (por defecto, docs/capturas/tanda-N/)")
    argumentos.add_argument("--formatos", choices=sorted(FORMATOS), default="normal",
                            help="normal: 1280 px y celular. completo: 1366 x 768, 1920 x 1080 "
                                 "y celular, con la hoja completa a la vista")
    opciones = argumentos.parse_args()

    pantallas = [p for n in sorted(PANTALLAS) if n <= opciones.tanda for p in PANTALLAS[n]]
    if opciones.solo:
        pantallas = [p for p in pantallas if p.nombre in opciones.solo]
    salida = opciones.salida or RAIZ / "docs" / "capturas" / f"tanda-{opciones.tanda}"

    from playwright.sync_api import sync_playwright

    clave, usuario = abrir_sesion(opciones.usuario)
    datos = datos_para_direcciones(usuario)
    faltan = [p.nombre for p in pantallas if "{" in p.url and not datos]
    if faltan:
        raise SystemExit(f"Faltan pedidos para {faltan}: carga los ejemplos (cargar_ejemplos).")
    puerto = puerto_libre()
    servidor = levantar_servidor(puerto)
    base = f"http://127.0.0.1:{puerto}"
    print(f"Servidor en {base}, sesión de {usuario}. Capturas en {salida}")
    total = 0
    completo = opciones.formatos == "completo"
    try:
        with sync_playwright() as p:
            navegador = p.chromium.launch(channel="chrome")
            for pantalla in pantallas:
                cookies = [] if pantalla.sin_sesion else [
                    {"name": "sessionid", "value": clave, "url": base}]
                if pantalla.menu:
                    cookies.append({"name": "menu", "value": pantalla.menu, "url": base})
                formatos = []
                for nombre_formato, formato in FORMATOS[opciones.formatos]:
                    celular = formato.get("is_mobile", False)
                    if celular and pantalla.solo_computador:
                        continue
                    referencia = (pantalla.referencia_celular or pantalla.referencia) if celular                         else pantalla.referencia
                    formatos.append((nombre_formato, formato, referencia))
                for nombre_formato, formato, referencia in formatos:
                    ancho = formato["viewport"]["width"]
                    archivo = salida / f"{pantalla.nombre}-{nombre_formato}.png"
                    avisos = [] if completo else None
                    problemas = capturar(navegador, base + pantalla.url.format(**datos), archivo,
                                         formato, cookies, ancho, avisos)
                    total += len(problemas)
                    estado = "bien" if not problemas else "REVISAR"
                    print(f"  {pantalla.nombre} ({nombre_formato}): {estado}")
                    for problema in problemas:
                        print(f"      - {problema}")
                    if opciones.referencias and referencia:
                        destino = opciones.referencias / f"{pantalla.nombre}-{nombre_formato}-diseno.png"
                        capturar(navegador, (RAIZ / "diseno" / referencia).as_uri(), destino,
                                 formato, [], ancho, completa=completo)
            navegador.close()
    finally:
        servidor.terminate()
        cerrar_sesion(clave)
    print("Sin problemas." if total == 0 else f"{total} problema(s) para revisar.")
    return 1 if total else 0


if __name__ == "__main__":
    sys.exit(main())
