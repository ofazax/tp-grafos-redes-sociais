"""Testes do posicionamento Fruchterman–Reingold: validade das coordenadas e reprodutibilidade."""

import math

import pytest

from redes.geradores import barabasi_albert, erdos_renyi
from redes.leitores import carregar_karate
from redes.nucleo import Grafo
from redes.visualizacao import fruchterman_reingold


def test_grafo_vazio_e_no_unico():
    assert fruchterman_reingold(Grafo()) == {}
    g = Grafo()
    g.adicionar_no("unico")
    assert fruchterman_reingold(g) == {"unico": (0.0, 0.0)}


def test_iteracoes_invalidas():
    with pytest.raises(ValueError):
        fruchterman_reingold(carregar_karate(), iteracoes=0)


def test_posicao_para_todos_os_nos_sem_valores_invalidos():
    g = barabasi_albert(40, 3, semente=42)
    pos = fruchterman_reingold(g, iteracoes=30, semente=42)
    assert set(pos) == set(g.nos())
    for x, y in pos.values():
        assert math.isfinite(x) and math.isfinite(y)
        assert -1.0 <= x <= 1.0
        assert -1.0 <= y <= 1.0


def test_mesma_semente_repete_o_layout():
    g = erdos_renyi(30, 0.15, semente=7)
    pos1 = fruchterman_reingold(g, iteracoes=25, semente=99)
    pos2 = fruchterman_reingold(g, iteracoes=25, semente=99)
    assert pos1 == pos2
