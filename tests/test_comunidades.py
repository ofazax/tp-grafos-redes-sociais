"""Testes de detecção de comunidades por propagação de rótulos e avaliação (NMI, ARI)."""

from pathlib import Path
import pytest

from redes.nucleo.grafo import Grafo
from redes.comunidades.rotulos import propagacao_de_rotulos
from redes.comunidades.avaliacao import nmi, ari

ARQUIVO_ARESTAS = Path(__file__).parent / "dados" / "karate_arestas.txt"
ARQUIVO_CLUBES = Path(__file__).parent / "dados" / "karate_clubes.txt"


def carregar_karate_e_clubes() -> tuple[Grafo, dict[int, int]]:
    """Carrega o grafo do Karate Club e a partição real da cisão em dois grupos."""
    g = Grafo()
    with open(ARQUIVO_ARESTAS, encoding="utf-8") as f:
        for linha in f:
            linha = linha.strip()
            if not linha or linha.startswith("#"):
                continue
            u, v = linha.split()
            g.adicionar_aresta(int(u), int(v))

    particao_real: dict[int, int] = {}
    with open(ARQUIVO_CLUBES, encoding="utf-8") as f:
        for linha in f:
            linha = linha.strip()
            if not linha or linha.startswith("#"):
                continue
            no, faccao = linha.split()
            particao_real[int(no)] = int(faccao)

    return g, particao_real

# -------------------------------------------------------------
# Testes de Propagação de Rótulos e Avaliação (NMI, ARI)
# -------------------------------------------------------------

def test_rotulos_grafo_vazio():
    g = Grafo()
    assert propagacao_de_rotulos(g) == {}


def test_rotulos_particao_valida():
    # Todos os nós devem estar na partição com IDs inteiros
    g, _ = carregar_karate_e_clubes()
    particao = propagacao_de_rotulos(g)
    assert set(particao.keys()) == set(g.nos())
    assert all(isinstance(c, int) for c in particao.values())


def test_rotulos_determinismo():
    g, _ = carregar_karate_e_clubes()
    p1 = propagacao_de_rotulos(g, seed=7)
    p2 = propagacao_de_rotulos(g, seed=7)
    assert p1 == p2


def test_nmi_particoes_identicas():
    # Partições idênticas → NMI = 1.0
    p = {0: 0, 1: 0, 2: 1, 3: 1}
    assert nmi(p, p) == pytest.approx(1.0)


def test_nmi_particoes_independentes():
    # Partições completamente opostas em blocos equilibrados → NMI ≈ 0.0
    p1 = {0: 0, 1: 0, 2: 1, 3: 1}
    p2 = {0: 0, 1: 1, 2: 0, 3: 1}
    assert nmi(p1, p2) == pytest.approx(0.0, abs=1e-9)


def test_ari_particoes_identicas():
    # Partições idênticas → ARI = 1.0
    p = {0: 0, 1: 0, 2: 1, 3: 1}
    assert ari(p, p) == pytest.approx(1.0)


def test_ari_particoes_independentes():
    # Em partições aleatórias independentes com tamanho suficiente, ARI converge para ~0.0
    import random
    rng = random.Random(42)
    n_nos = 500
    p1 = {i: rng.randint(0, 3) for i in range(n_nos)}
    p2 = {i: rng.randint(0, 3) for i in range(n_nos)}
    assert ari(p1, p2) == pytest.approx(0.0, abs=0.05)


def test_ari_particoes_opostas_negativo():
    # Partições diametralmente opostas (pior que o acaso) resultam em ARI negativo
    p1 = {0: 0, 1: 0, 2: 1, 3: 1}
    p2 = {0: 0, 1: 1, 2: 0, 3: 1}
    assert ari(p1, p2) == pytest.approx(-0.5)