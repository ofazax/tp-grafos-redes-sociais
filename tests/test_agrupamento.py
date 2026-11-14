"""Testes das métricas de agrupamento: casos conhecidos, Karate Club e invariantes."""

from pathlib import Path
import pytest
from hypothesis import given
from hypothesis import strategies as st

from redes.metricas.agrupamento import (
    triangulos,
    agrupamento_local,
    agrupamento_medio,
    transitividade,
)
from redes.nucleo.grafo import Grafo

ARQUIVO_KARATE = Path(__file__).parent / "dados" / "karate_arestas.txt"


def carregar_karate() -> Grafo:
    """Lê o grafo do Karate Club a partir dos dados de teste."""
    g = Grafo()
    with open(ARQUIVO_KARATE, encoding="utf-8") as f:
        for linha in f:
            linha = linha.strip()
            if not linha or linha.startswith("#"):
                continue
            u, v = linha.split()
            g.adicionar_aresta(int(u), int(v))
    return g


# -------------------------------------------------------------
# Casos de resposta conhecida matematicamente
# -------------------------------------------------------------

def test_grafo_vazio():
    g = Grafo()
    assert triangulos(g) == {}
    assert agrupamento_local(g) == {}
    assert agrupamento_medio(g) == 0.0
    assert transitividade(g) == 0.0


def test_triangulo_unico():
    # Triângulo simples com 3 nós (0, 1, 2)
    g = Grafo.de_arestas([(0, 1), (1, 2), (2, 0)])
    assert triangulos(g) == {0: 1, 1: 1, 2: 1}
    assert agrupamento_local(g) == {0: 1.0, 1: 1.0, 2: 1.0}
    assert agrupamento_medio(g) == 1.0
    assert transitividade(g) == 1.0


def test_estrela_sem_triangulos():
    # Nó 0 no centro, ligado a 4 folhas (sem triângulos)
    g = Grafo.de_arestas([(0, 1), (0, 2), (0, 3), (0, 4)])
    t = triangulos(g)
    assert all(qtd == 0 for qtd in t.values())
    assert agrupamento_medio(g) == 0.0
    assert transitividade(g) == 0.0


def test_grafo_completo_k5():
    # Em um grafo completo, todo par de vizinhos é conectado (clustering = 1.0)
    g = Grafo.de_arestas((i, j) for i in range(5) for j in range(i + 1, 5))
    # Em K_5 cada nó participa de C(4, 2) = 6 triângulos
    t = triangulos(g)
    assert all(qtd == 6 for qtd in t.values())
    assert agrupamento_medio(g) == 1.0
    assert transitividade(g) == 1.0


# -------------------------------------------------------------
# Teste de Corretude Oficial: Zachary's Karate Club
# -------------------------------------------------------------

def test_karate_club_gabarito():
    g = carregar_karate()
    t = triangulos(g)

    # 1. Total de triângulos no Karate Club deve ser rigorosamente 45
    total_triangulos = sum(t.values()) // 3
    assert total_triangulos == 45

    # 2. Agrupamento médio canônico da literatura: ~0.5706
    c_medio = agrupamento_medio(g)
    assert pytest.approx(0.5706, abs=1e-3) == c_medio

    # 3. Transitividade global canônica da literatura: ~0.2557
    trans = transitividade(g)
    assert pytest.approx(0.2557, abs=1e-3) == trans


# -------------------------------------------------------------
# Invariantes com Hypothesis
# -------------------------------------------------------------

@given(st.integers(min_value=2, max_value=15))
def test_invariante_intervalo_clustering(n):
    # Em qualquer grafo gerado, o agrupamento deve estar em [0.0, 1.0]
    g = Grafo.de_arestas((i, (i + 1) % n) for i in range(n))
    c_medio = agrupamento_medio(g)
    trans = transitividade(g)
    assert 0.0 <= c_medio <= 1.0
    assert 0.0 <= trans <= 1.0