"""Testes de detecção de comunidades e cálculo de modularidade."""

from pathlib import Path
import pytest

from redes.comunidades.modularidade import modularidade
from redes.comunidades.louvain import louvain
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


# -------------------------------------------------------------
# Testes do algoritmo de Louvain
# -------------------------------------------------------------

def test_louvain_grafo_vazio():
    g = Grafo()
    particao, q = louvain(g)
    assert particao == {}
    assert q == 0.0


def test_louvain_particao_valida():
    # Todos os nós do grafo devem estar na partição com IDs inteiros
    g, _ = carregar_karate_e_clubes()
    particao, q = louvain(g)
    assert set(particao.keys()) == set(g.nos())
    assert all(isinstance(c, int) for c in particao.values())


def test_louvain_determinismo():
    # Mesma semente → mesmo resultado
    g, _ = carregar_karate_e_clubes()
    p1, q1 = louvain(g, semente=42)
    p2, q2 = louvain(g, semente=42)
    assert p1 == p2
    assert q1 == pytest.approx(q2)


def test_louvain_q_karate():
    # Louvain deve encontrar partição com Q entre 0.39 e 0.42 no Karate Club
    # (valor canônico máximo reportado: ~0.4198)
    g, _ = carregar_karate_e_clubes()
    _, q = louvain(g)
    assert 0.39 <= q <= 0.42, f"Q={q:.4f} fora do intervalo esperado [0.39, 0.42]"


def test_louvain_q_maior_que_divisao_real():
    # Louvain otimiza Q, logo deve encontrar partição melhor que a divisão manual
    g, particao_real = carregar_karate_e_clubes()
    q_real = modularidade(g, particao_real)   # 0.3582
    _, q_louvain = louvain(g)
    assert q_louvain > q_real, (
        f"Louvain (Q={q_louvain:.4f}) não superou a divisão real (Q={q_real:.4f})"
    )