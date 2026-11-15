"""La cotización con los precios guardados del Cotizador (carril C, T32).

Claude entiende "¿cuánto cobro por 15 vestidos de comparsa?" y pide esta herramienta con el
nombre de la prenda y la cantidad. La cuenta no la hace Claude: se busca la prenda en
"Mis prendas" del taller y se usa la misma fórmula del Cotizador (calculos.cotizar), con los
mismos valores por defecto de su formulario (ganancia y abono de FormularioCotizacion).

- Un nombre exacto (sin importar tildes ni mayúsculas) gana.
- Si no, se buscan las que contienen lo escrito (calculos.coincide). Si son varias, se
  devuelven sus nombres para que Claude pregunte cuál; si no hay ninguna, el error dice cuáles
  hay guardadas.
- La tarjeta trae el botón "Abrir en el Cotizador", que abre la pantalla con esa prenda y esas
  cifras: GET a cotizador:calcular con guardada, cantidad, ganancia, abono y tipo.
"""

from urllib.parse import urlencode

from django.urls import reverse

from asistente.contratos import Contexto, ErrorDeHerramienta, Resultado, Tarjeta
from cotizador.formularios import CAMPOS_DEL_PRECIO, FormularioCotizacion
from cotizador.models import PrendaGuardada
from pedidos import calculos
from pedidos.models import Cliente

# Cuántos nombres se le dicen a Claude como mucho (opciones o prendas guardadas).
TOPE_DE_NOMBRES = 30


def _por_defecto(campo):
    """El valor inicial del campo en el formulario del Cotizador (ganancia 30, abono 50)."""
    return FormularioCotizacion.base_fields[campo].initial


def _igual(a, b):
    return " ".join(calculos.sin_tildes(a).split()) == " ".join(calculos.sin_tildes(b).split())


def _buscar(ctx, prenda):
    """La prenda guardada que se pidió, o la lista de nombres si coinciden varias."""
    guardadas = list(PrendaGuardada.objects.del_taller(ctx.taller).order_by("nombre", "pk"))
    exactas = [p for p in guardadas if _igual(p.nombre, prenda)]
    if exactas:
        return exactas[0], None
    buscado = " ".join(prenda.split())
    parecidas = [p for p in guardadas if calculos.coincide(buscado, p.nombre)]
    if len(parecidas) == 1:
        return parecidas[0], None
    if parecidas:
        return None, [p.nombre for p in parecidas[:TOPE_DE_NOMBRES]]
    if not guardadas:
        raise ErrorDeHerramienta(
            "No hay prendas guardadas en el Cotizador. La dueña tiene que guardar la prenda "
            "con sus costos en el Cotizador para poder cotizarla."
        )
    nombres = ", ".join(p.nombre for p in guardadas[:TOPE_DE_NOMBRES])
    raise ErrorDeHerramienta(
        f"No hay una prenda guardada que se llame «{buscado}». Las guardadas son: {nombres}."
    )


# --- El título de la tarjeta ----------------------------------------------------------------

_VOCALES = "aeiouáéíóú"
_SIN_TILDE = str.maketrans("áéíóú", "aeiou")


def _plural(palabra):
    """'vestido' -> 'vestidos', 'pantalón' -> 'pantalones', 'overol' -> 'overoles'.

    Reglas sencillas del español; lo raro (palabras en inglés, por ejemplo) se queda bien o
    con una s de más o de menos, nunca se pierde el nombre.
    """
    final = palabra[-1:].lower()
    if not final.isalpha() or final in "sx":
        return palabra
    if final in _VOCALES or final == "y":
        return palabra + "s"
    if final == "z":
        return palabra[:-1] + "ces"
    if final in "lrndj":
        if final == "n":
            # pantalón -> pantalones: la tilde de la última sílaba se va.
            return palabra.translate(_SIN_TILDE) + "es"
        return palabra + "es"
    return palabra + "s"


def nombre_para_titulo(nombre, cantidad):
    """'Vestido de comparsa' y 15 -> 'vestidos de comparsa' (como en diseno/asistente.html).

    Solo la primera palabra pasa a plural y a minúscula; el resto queda como está guardado.
    """
    palabras = nombre.split()
    if not palabras:
        return nombre
    primera = palabras[0]
    if not (len(primera) > 1 and primera.isupper()):  # una sigla ("JEAN") se deja igual
        primera = primera[:1].lower() + primera[1:]
        if cantidad != 1:
            primera = _plural(primera)
    return " ".join([primera, *palabras[1:]])


# --- La herramienta ---------------------------------------------------------------------------


def cotizar(ctx: Contexto, *, prenda, cantidad, ganancia_pct, abono_pct) -> Resultado:
    guardada, opciones = _buscar(ctx, prenda)
    if opciones:
        return Resultado(
            datos={"opciones": opciones},
            revisado="Busqué en tus prendas guardadas",
        )

    ganancia = _por_defecto("ganancia") if ganancia_pct is None else ganancia_pct
    abono = _por_defecto("abono") if abono_pct is None else abono_pct
    valores = {
        "metros": guardada.metros,
        "precio_metro": guardada.precio_metro,
        "insumos": guardada.insumos,
        "mano_obra": guardada.mano_obra,
        "extra": guardada.extra,
        "ganancia": ganancia,
        "cantidad": cantidad,
        "abono": abono,
    }
    # En el mismo orden que FormularioCotizacion.cotizacion().
    cotizacion = calculos.cotizar(*(valores[campo] for campo in CAMPOS_DEL_PRECIO))
    if cotizacion.total <= 0:
        raise ErrorDeHerramienta(
            f"La prenda guardada «{guardada.nombre}» no tiene costos: hay que escribirlos en el "
            "Cotizador para poder cotizarla."
        )

    datos = {
        "prenda": guardada.nombre,
        "cantidad": cantidad,
        "costo": cotizacion.costo,
        "precio_unidad": cotizacion.precio_unidad,
        "total": cotizacion.total,
        "abono": cotizacion.abono,
        "ganancia": cotizacion.ganancia,
        "metros_totales": str(cotizacion.metros_totales),
    }
    url = reverse("cotizador:calcular") + "?" + urlencode({
        "guardada": guardada.pk,
        "cantidad": cantidad,
        "ganancia": ganancia,
        "abono": abono,
        "tipo": Cliente.Tipo.EMPRESA.value,  # el tipo con que empieza el Cotizador
    })
    return Resultado(
        datos=datos,
        revisado=f"Usé tu prenda guardada «{guardada.nombre}»",
        tarjeta=Tarjeta(
            "cotizacion",
            f"Total de {cantidad} {nombre_para_titulo(guardada.nombre, cantidad)}",
            {**datos, "url_cotizador": url},
        ),
    )
