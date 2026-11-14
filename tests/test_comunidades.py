"""Testes de detecção de comunidades e cálculo de modularidade."""

from pathlib import Path
import pytest

from redes.comunidades.modularidade import modularidade
from redes.nucleo.grafo import Grafo

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
# Testes com casos teóricos de resposta conhecida
# -------------------------------------------------------------

def test_modularidade_grafo_vazio():
    g = Grafo()
    assert modularidade(g, {}) == 0.0


def test_modularidade_comunidade_unica():
    # Em qualquer grafo, colocar todos os nós na mesma comunidade resulta em Q = 0.0
    g = Grafo.de_arestas([(0, 1), (1, 2), (2, 0), (2, 3)])
    particao = {0: 0, 1: 0, 2: 0, 3: 0}
    assert modularidade(g, particao) == pytest.approx(0.0)


def test_modularidade_dois_componentes_isolados():
    # Dois triângulos totalmente desconexos: {0,1,2} e {3,4,5}
    # Resposta teórica exata: Q = 0.5
    g = Grafo.de_arestas([
        (0, 1), (1, 2), (2, 0),
        (3, 4), (4, 5), (5, 3)
    ])
    particao = {0: 0, 1: 0, 2: 0, 3: 1, 4: 1, 5: 1}
    assert modularidade(g, particao) == pytest.approx(0.5)


# -------------------------------------------------------------
# Teste de Corretude: Gabarito da Divisão Real do Karate Club
# -------------------------------------------------------------

def test_modularidade_divisao_real_karate():
    g, particao_real = carregar_karate_e_clubes()
    q = modularidade(g, particao_real)

    # A divisão histórica em duas facções tem modularidade canônica de 0.3582
    assert q == pytest.approx(0.3582, abs=1e-3)