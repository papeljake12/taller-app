"""Pruebas del lector del archivo .env (config/entorno.py)."""

import pytest
from django.core.exceptions import ImproperlyConfigured

from config import entorno


@pytest.fixture
def archivo(tmp_path, monkeypatch):
    """Devuelve una función que escribe un .env de prueba y lo carga."""
    for nombre in ("PRUEBA_A", "PRUEBA_B", "PRUEBA_C", "PRUEBA_VACIA", "PRUEBA_SISTEMA"):
        # setenv y luego delenv: así pytest recuerda que no existían y las borra al final.
        monkeypatch.setenv(nombre, "x")
        monkeypatch.delenv(nombre)

    def escribir_y_cargar(contenido):
        ruta = tmp_path / ".env"
        ruta.write_text(contenido, encoding="utf-8")
        entorno.cargar(ruta)

    return escribir_y_cargar


def test_lee_variables_y_salta_comentarios_y_lineas_vacias(archivo):
    archivo("# un comentario\n\nPRUEBA_A=uno\n  PRUEBA_B = dos  \n")

    assert entorno.texto("PRUEBA_A") == "uno"
    assert entorno.texto("PRUEBA_B") == "dos"


def test_quita_comillas_y_respeta_el_signo_igual_dentro_del_valor(archivo):
    archivo("PRUEBA_A=\"con espacios\"\nPRUEBA_B=abc=def\n")

    assert entorno.texto("PRUEBA_A") == "con espacios"
    assert entorno.texto("PRUEBA_B") == "abc=def"


def test_la_variable_del_sistema_gana_sobre_la_del_archivo(archivo, monkeypatch):
    monkeypatch.setenv("PRUEBA_SISTEMA", "del sistema")
    archivo("PRUEBA_SISTEMA=del archivo\n")

    assert entorno.texto("PRUEBA_SISTEMA") == "del sistema"


def test_una_variable_obligatoria_vacia_avisa_cual_falta(archivo):
    archivo("PRUEBA_VACIA=\n")

    with pytest.raises(ImproperlyConfigured, match="PRUEBA_VACIA"):
        entorno.texto("PRUEBA_VACIA")
    assert entorno.texto("PRUEBA_VACIA", "por defecto") == "por defecto"


def test_una_linea_sin_signo_igual_es_un_error(archivo):
    with pytest.raises(ImproperlyConfigured, match="línea 2"):
        archivo("PRUEBA_A=uno\nesto no vale\n")


def test_booleanos_y_listas(archivo):
    archivo("PRUEBA_A=True\nPRUEBA_B=no\nPRUEBA_C=localhost, 127.0.0.1,\n")

    assert entorno.booleano("PRUEBA_A", False) is True
    assert entorno.booleano("PRUEBA_B", True) is False
    assert entorno.booleano("PRUEBA_VACIA", True) is True
    assert entorno.lista("PRUEBA_C") == ["localhost", "127.0.0.1"]


def test_sin_archivo_no_pasa_nada(tmp_path):
    entorno.cargar(tmp_path / "no-existe.env")
