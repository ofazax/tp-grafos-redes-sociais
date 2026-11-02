"""Teste inicial: confere que o pacote redes e seus módulos podem ser importados."""
import importlib

import pytest

MODULOS = [
    "redes",
    "redes.core",
    "redes.loaders",
    "redes.generators",
    "redes.metrics",
    "redes.community",
    "redes.applied",
    "redes.viz",
]


@pytest.mark.parametrize("nome", MODULOS)
def test_modulo_importa(nome):
    assert importlib.import_module(nome) is not None
