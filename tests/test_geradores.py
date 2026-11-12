"""Testes dos geradores: tamanhos esperados, semente e propriedades de cada modelo."""

import random

import pytest

from redes.geradores import barabasi_albert, erdos_renyi, watts_strogatz


def arestas_ordenadas(g):
    """Lista de arestas comparável entre dois grafos: cada par em ordem (menor, maior)."""
    return sorted((min(v, w), max(v, w)) for v, w, _ in g.arestas())


def conexo(g):
    """True se dá para chegar de qualquer nó a qualquer outro (busca simples, só para o teste)."""
    nos = list(g.nos())
    if not nos:
        return True
    vistos, pilha = {nos[0]}, [nos[0]]
    while pilha:
        v = pilha.pop()
        for w in g.vizinhos(v):
            if w not in vistos:
                vistos.add(w)
                pilha.append(w)
    return len(vistos) == len(nos)


# Regra comum: a mesma semente gera o mesmo grafo


@pytest.mark.parametrize(
    "gerar",
    [
        lambda s: erdos_renyi(300, 0.05, semente=s),
        lambda s: barabasi_albert(300, 3, semente=s),
        lambda s: watts_strogatz(300, 6, 0.2, semente=s),
    ],
    ids=["erdos_renyi", "barabasi_albert", "watts_strogatz"],
)
def test_mesma_semente_mesmo_grafo(gerar):
    assert arestas_ordenadas(gerar(7)) == arestas_ordenadas(gerar(7))
    assert arestas_ordenadas(gerar(7)) != arestas_ordenadas(gerar(8))


def test_nao_usa_o_random_global():
    random.seed(0)
    g1 = erdos_renyi(200, 0.05, semente=3)
    random.seed(12345)
    g2 = erdos_renyi(200, 0.05, semente=3)
    assert arestas_ordenadas(g1) == arestas_ordenadas(g2)


# Erdős-Rényi


def test_erdos_renyi_extremos():
    assert erdos_renyi(10, 0.0).numero_de_arestas() == 0
    assert erdos_renyi(10, 0.0).numero_de_nos() == 10  # nós isolados também existem
    assert erdos_renyi(10, 1.0).numero_de_arestas() == 45  # completo: n(n-1)/2
    assert erdos_renyi(0, 0.5).numero_de_nos() == 0


def test_erdos_renyi_numero_de_arestas():
    # Esperado: p · n(n-1)/2 = 0,01 · 499.500 = 4.995. Com semente=1, sai 4.963.
    assert erdos_renyi(1000, 0.01, semente=1).numero_de_arestas() == 4963
    for semente in range(5):
        m = erdos_renyi(1000, 0.01, semente=semente).numero_de_arestas()
        assert abs(m - 4995) <= 0.05 * 4995


def test_erdos_renyi_sem_lacos():
    g = erdos_renyi(500, 0.02, semente=2)
    assert all(v != w for v, w, _ in g.arestas())
    assert set(g.nos()) == set(range(500))


def test_erdos_renyi_parametros_invalidos():
    with pytest.raises(ValueError):
        erdos_renyi(10, 1.5)


# Barabási-Albert


def test_barabasi_albert():
    g = barabasi_albert(1000, 3, semente=1)
    assert g.numero_de_nos() == 1000
    assert g.numero_de_arestas() == 3 * (1000 - 3)  # m(n - m) = 2.991
    assert all(v != w for v, w, _ in g.arestas())  # sem laços
    assert all(g.grau(v) >= 3 for v in range(3, 1000))  # todo nó novo chega com m arestas
    assert conexo(g)
    assert max(g.grau(v) for v in g.nos()) > 30  # surgem hubs


def test_barabasi_albert_parametros_invalidos():
    with pytest.raises(ValueError):
        barabasi_albert(5, 5)


# Watts-Strogatz


def test_watts_strogatz_sem_religacao_e_um_anel():
    g = watts_strogatz(20, 4, 0.0)
    assert g.numero_de_arestas() == 20 * 4 // 2
    assert all(g.grau(v) == 4 for v in g.nos())
    assert g.tem_aresta(19, 0) and g.tem_aresta(19, 1)  # o % n fecha o anel


@pytest.mark.parametrize("p", [0.1, 0.5, 1.0])
def test_watts_strogatz_mantem_n_k_sobre_2_arestas(p):
    g = watts_strogatz(1000, 4, p, semente=1)
    assert g.numero_de_arestas() == 2000  # n·k/2
    assert all(v != w for v, w, _ in g.arestas())
    assert sum(g.grau(v) for v in g.nos()) == 4000


def test_watts_strogatz_parametros_invalidos():
    with pytest.raises(ValueError):
        watts_strogatz(10, 3, 0.1)  # k ímpar
