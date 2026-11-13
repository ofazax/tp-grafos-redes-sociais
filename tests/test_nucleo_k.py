"""Testes do k-núcleo (k-core): casos de resposta conhecida, Karate Club e invariantes."""

from pathlib import Path

from hypothesis import given, settings
from hypothesis import strategies as st

from redes.metricas.nucleo_k import k_nucleo, numero_de_nucleo
from redes.nucleo import Grafo

ARQUIVO_KARATE = Path(__file__).parent / "dados" / "karate_arestas.txt"


def carregar_karate():
    # Lê o Karate Club de tests/dados (uma aresta 'v w' por linha).
    g = Grafo()
    with open(ARQUIVO_KARATE, encoding="utf-8") as arquivo:
        for linha in arquivo:
            linha = linha.strip()
            if not linha or linha.startswith("#"):
                continue
            v, w = linha.split()
            g.adicionar_aresta(int(v), int(w))
    return g


def completo(n):
    return Grafo.de_arestas((i, j) for i in range(n) for j in range(i + 1, n))


# Casos pequenos, de resposta conhecida


def test_grafo_vazio():
    assert numero_de_nucleo(Grafo()) == {}
    assert k_nucleo(Grafo(), 1).numero_de_nos() == 0


def test_no_isolado():
    g = Grafo()
    g.adicionar_no("a")
    assert numero_de_nucleo(g) == {"a": 0}


def test_completo():
    # No K5 todo nó tem grau 4 e nenhum sai antes dos outros: núcleo 4 para todos.
    assert numero_de_nucleo(completo(5)) == {v: 4 for v in range(5)}


def test_arvore():
    # Em uma árvore sempre existe folha para remover: todos os nós têm núcleo 1.
    g = Grafo.de_arestas([(0, 1), (0, 2), (1, 3), (1, 4), (2, 5)])
    assert numero_de_nucleo(g) == {v: 1 for v in range(6)}


def test_triangulo_com_cauda():
    # Triângulo 0-1-2 com a cauda 2-3-4: o triângulo é o 2-núcleo e a cauda fica com 1.
    g = Grafo.de_arestas([(0, 1), (1, 2), (2, 0), (2, 3), (3, 4)])
    assert numero_de_nucleo(g) == {0: 2, 1: 2, 2: 2, 3: 1, 4: 1}
    sub = k_nucleo(g, 2)
    assert set(sub.nos()) == {0, 1, 2}
    assert sub.numero_de_arestas() == 3


def test_k4_com_pendentes():
    # Um K4 (núcleo 3) com um nó de grau 3 que só se liga a pendentes não entra no 3-núcleo.
    g = completo(4)
    g.adicionar_aresta(0, "x")
    g.adicionar_aresta("x", "y")
    g.adicionar_aresta("x", "z")
    nucleo = numero_de_nucleo(g)
    assert all(nucleo[v] == 3 for v in range(4))
    assert nucleo["x"] == 1 and nucleo["y"] == 1 and nucleo["z"] == 1


def test_laco_ignorado():
    g = Grafo.de_arestas([(0, 1), (0, 0)])
    assert numero_de_nucleo(g) == {0: 1, 1: 1}


def test_direcionado_grau_total():
    # Ciclo dirigido 0 -> 1 -> 2 -> 0: cada nó tem grau total 2, então núcleo 2.
    g = Grafo.de_arestas([(0, 1), (1, 2), (2, 0)], direcionado=True)
    assert numero_de_nucleo(g) == {0: 2, 1: 2, 2: 2}
    assert k_nucleo(g, 2).direcionado


def test_k_nucleo_acima_do_maximo():
    assert k_nucleo(completo(4), 4).numero_de_nos() == 0


def test_k_nucleo_mantem_peso_e_nao_altera_o_grafo():
    g = Grafo.de_arestas([(0, 1, 2.5), (1, 2, 1.0), (2, 0, 4.0), (2, 3, 1.0)])
    antes = sorted(g.arestas())
    sub = k_nucleo(g, 2)
    assert sub.peso(0, 1) == 2.5 and sub.peso(2, 0) == 4.0
    assert sorted(g.arestas()) == antes


# Karate Club: valores de referência do guia (NetworkX 3.7)


def test_karate():
    g = carregar_karate()
    nucleo = numero_de_nucleo(g)
    assert max(nucleo.values()) == 4
    assert {v for v, c in nucleo.items() if c == 4} == {0, 1, 2, 3, 7, 8, 13, 30, 32, 33}
    assert set(k_nucleo(g, 4).nos()) == {0, 1, 2, 3, 7, 8, 13, 30, 32, 33}


# Invariantes em grafos aleatórios

arestas_aleatorias = st.lists(
    st.tuples(st.integers(0, 14), st.integers(0, 14)).filter(lambda a: a[0] != a[1]),
    max_size=50,
)


def nucleo_por_definicao(g, k):
    # Remove repetidamente quem tem grau < k; o que sobra é o k-núcleo.
    vivos = set(g.nos())
    mudou = True
    while mudou:
        mudou = False
        for v in list(vivos):
            if sum(1 for w in g.vizinhos(v) if w in vivos) < k:
                vivos.remove(v)
                mudou = True
    return vivos


@settings(max_examples=60)
@given(arestas_aleatorias)
def test_invariantes(arestas):
    g = Grafo.de_arestas(arestas)
    nucleo = numero_de_nucleo(g)
    assert set(nucleo) == set(g.nos())
    # O número de núcleo nunca passa do grau.
    assert all(0 <= nucleo[v] <= g.grau(v) for v in g.nos())
    # Para cada k, os nós com núcleo >= k são exatamente o k-núcleo pela definição,
    # e dentro do k-núcleo todo nó tem grau >= k.
    for k in range(max(nucleo.values(), default=0) + 2):
        sub = k_nucleo(g, k)
        assert set(sub.nos()) == nucleo_por_definicao(g, k)
        assert all(sub.grau(v) >= k for v in sub.nos())
