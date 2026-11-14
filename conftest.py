"""Piezas comunes para todas las pruebas (pytest las encuentra solas)."""

import pytest

from cuentas.models import Usuario
from tests import fabricas


@pytest.fixture(autouse=True)
def sin_internet_para_claude(monkeypatch):
    """Ninguna prueba llega a la API de Claude (docs/06-pruebas.md, "Asistente").

    Se corta dentro de la librería `anthropic`, justo antes de enviar: así falla cualquier
    camino, aunque alguien arme el cliente a mano o ponga una clave. Las pruebas que necesitan
    respuestas de Claude usan asistente.falso.instalar() con un guion.
    """

    def prohibido(*args, **kwargs):
        raise AssertionError("Las pruebas no llaman a la API de Claude: usa asistente.falso.")

    monkeypatch.setattr("anthropic._base_client.SyncAPIClient.request", prohibido)
    monkeypatch.setattr("anthropic._base_client.AsyncAPIClient.request", prohibido)


@pytest.fixture
def taller(db):
    return fabricas.crear_taller()


@pytest.fixture
def duena(taller):
    return fabricas.crear_usuaria(taller, rol=Usuario.Rol.DUENA)


@pytest.fixture
def costurera(taller):
    return fabricas.crear_usuaria(taller, rol=Usuario.Rol.COSTURERA)


@pytest.fixture
def administrador(db):
    return fabricas.crear_administrador()


@pytest.fixture
def sesion_duena(client, duena):
    """Un navegador de prueba con la sesión de la dueña ya abierta."""
    client.force_login(duena)
    return client


@pytest.fixture
def sesion_administrador(client, administrador):
    client.force_login(administrador)
    return client
