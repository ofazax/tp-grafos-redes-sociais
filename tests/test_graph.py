"""Testes da classe Graph: casos de resposta conhecida e invariantes."""
from hypothesis import given
from hypothesis import strategies as st

from redes.core import Graph, to_index_lists


def completo(n):
    return Graph.from_edges((i, j) for i in range(n) for j in range(i + 1, n))


def test_grafo_vazio():
    g = Graph()
    assert g.number_of_nodes() == 0
    assert g.number_of_edges() == 0
    assert list(g.edges()) == []


def test_no_isolado():
    g = Graph()
    g.add_node("a")
    assert "a" in g
    assert g.degree("a") == 0
    assert list(g.neighbors("a")) == []


def test_completo_k5():
    g = completo(5)
    assert g.number_of_nodes() == 5
    assert g.number_of_edges() == 10  # n(n-1)/2
    assert all(g.degree(u) == 4 for u in g.nodes())


def test_estrela():
    g = Graph.from_edges((0, i) for i in range(1, 6))
    assert g.degree(0) == 5
    assert all(g.degree(i) == 1 for i in range(1, 6))


def test_nao_direcionado_e_simetrico():
    g = Graph.from_edges([(1, 2)])
    assert g.has_edge(1, 2) and g.has_edge(2, 1)


def test_aresta_repetida_nao_conta_duas_vezes():
    g = Graph()
    g.add_edge(1, 2, 1.0)
    g.add_edge(2, 1, 3.0)
    assert g.number_of_edges() == 1
    assert g.weight(1, 2) == 3.0


def test_laco_conta_dois_no_grau():
    g = Graph()
    g.add_edge("x", "x")
    assert g.number_of_edges() == 1
    assert g.degree("x") == 2


def test_direcionado():
    g = Graph.from_edges([(1, 2), (1, 3), (3, 1)], directed=True)
    assert g.has_edge(1, 2) and not g.has_edge(2, 1)
    assert g.out_degree(1) == 2
    assert g.in_degree(1) == 1
    assert g.degree(1) == 3
    assert sorted(g.predecessors(1)) == [3]
    assert g.number_of_edges() == 3


def test_edges_lista_cada_aresta_uma_vez():
    g = completo(4)
    pares = {frozenset((u, v)) for u, v, _ in g.edges()}
    assert len(pares) == len(list(g.edges())) == 6


def test_reindexacao():
    g = Graph.from_edges([("ana", "bia"), ("bia", "caio")])
    idx, adj = to_index_lists(g)
    assert idx.to_node == ["ana", "bia", "caio"]
    assert sorted(adj[idx.to_index["bia"]]) == [0, 2]


arestas = st.lists(st.tuples(st.integers(0, 30), st.integers(0, 30)), max_size=200)


@given(arestas)
def test_soma_dos_graus_e_2m(lista):
    g = Graph.from_edges(lista)
    assert sum(g.degree(u) for u in g.nodes()) == 2 * g.number_of_edges()


@given(arestas)
def test_edges_bate_com_number_of_edges(lista):
    g = Graph.from_edges(lista)
    assert len(list(g.edges())) == g.number_of_edges()


@given(arestas)
def test_direcionado_entrada_igual_saida(lista):
    g = Graph.from_edges(lista, directed=True)
    total_saida = sum(g.out_degree(u) for u in g.nodes())
    total_entrada = sum(g.in_degree(u) for u in g.nodes())
    assert total_saida == total_entrada == g.number_of_edges()
