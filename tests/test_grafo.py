"""Testes da classe Grafo: casos de resposta conhecida e invariantes."""
from hypothesis import given
from hypothesis import strategies as st

from redes.nucleo import Grafo, para_listas_indexadas


def completo(n):
    return Grafo.de_arestas((i, j) for i in range(n) for j in range(i + 1, n))


def test_grafo_vazio():
    g = Grafo()
    assert g.numero_de_nos() == 0
    assert g.numero_de_arestas() == 0
    assert list(g.arestas()) == []


def test_no_isolado():
    g = Grafo()
    g.adicionar_no("a")
    assert "a" in g
    assert g.grau("a") == 0
    assert list(g.vizinhos("a")) == []


def test_completo_k5():
    g = completo(5)
    assert g.numero_de_nos() == 5
    assert g.numero_de_arestas() == 10  # n(n-1)/2
    assert all(g.grau(v) == 4 for v in g.nos())


def test_estrela():
    g = Grafo.de_arestas((0, i) for i in range(1, 6))
    assert g.grau(0) == 5
    assert all(g.grau(i) == 1 for i in range(1, 6))


def test_nao_direcionado_e_simetrico():
    g = Grafo.de_arestas([(1, 2)])
    assert g.tem_aresta(1, 2) and g.tem_aresta(2, 1)


def test_aresta_repetida_nao_conta_duas_vezes():
    g = Grafo()
    g.adicionar_aresta(1, 2, 1.0)
    g.adicionar_aresta(2, 1, 3.0)
    assert g.numero_de_arestas() == 1
    assert g.peso(1, 2) == 3.0


def test_laco_conta_dois_no_grau():
    g = Grafo()
    g.adicionar_aresta("x", "x")
    assert g.numero_de_arestas() == 1
    assert g.grau("x") == 2


def test_direcionado():
    g = Grafo.de_arestas([(1, 2), (1, 3), (3, 1)], direcionado=True)
    assert g.tem_aresta(1, 2) and not g.tem_aresta(2, 1)
    assert g.grau_saida(1) == 2
    assert g.grau_entrada(1) == 1
    assert g.grau(1) == 3
    assert sorted(g.predecessores(1)) == [3]
    assert g.numero_de_arestas() == 3


def test_arestas_lista_cada_aresta_uma_vez():
    g = completo(4)
    pares = {frozenset((v, w)) for v, w, _ in g.arestas()}
    assert len(pares) == len(list(g.arestas())) == 6


def test_reindexacao():
    g = Grafo.de_arestas([("ana", "bia"), ("bia", "caio")])
    indexador, adj = para_listas_indexadas(g)
    assert indexador.para_no == ["ana", "bia", "caio"]
    assert sorted(adj[indexador.para_indice["bia"]]) == [0, 2]


listas_de_arestas = st.lists(st.tuples(st.integers(0, 30), st.integers(0, 30)), max_size=200)


@given(listas_de_arestas)
def test_soma_dos_graus_e_2m(lista):
    g = Grafo.de_arestas(lista)
    assert sum(g.grau(v) for v in g.nos()) == 2 * g.numero_de_arestas()


@given(listas_de_arestas)
def test_arestas_bate_com_numero_de_arestas(lista):
    g = Grafo.de_arestas(lista)
    assert len(list(g.arestas())) == g.numero_de_arestas()


@given(listas_de_arestas)
def test_direcionado_entrada_igual_saida(lista):
    g = Grafo.de_arestas(lista, direcionado=True)
    total_saida = sum(g.grau_saida(v) for v in g.nos())
    total_entrada = sum(g.grau_entrada(v) for v in g.nos())
    assert total_saida == total_entrada == g.numero_de_arestas()
