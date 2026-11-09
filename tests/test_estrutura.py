"""Teste inicial: confere que o pacote redes e seus módulos podem ser importados."""
import importlib

import pytest

MODULOS = [
    "redes",
    "redes.nucleo",
    "redes.leitores",
    "redes.geradores",
    "redes.metricas",
    "redes.comunidades",
    "redes.aplicacao",
    "redes.visualizacao",
]


@pytest.mark.parametrize("nome", MODULOS)
def test_modulo_importa(nome):
    assert importlib.import_module(nome) is not None
