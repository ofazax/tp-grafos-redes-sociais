"""Testes da intermediação (Brandes) e do PageRank: casos de resposta conhecida, Karate Club e invariantes."""

from pathlib import Path

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from redes.metricas.centralidade import intermediacao, pagerank
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


def estrela(n):
    # Nó 0 no centro, ligado aos outros n - 1 nós.
    return Grafo.de_arestas((0, i) for i in range(1, n))


def caminho(n):
    return Grafo.de_arestas((i, i + 1) for i in range(n - 1))


# Casos pequenos, de resposta conhecida


def test_grafo_vazio():
    assert intermediacao(Grafo()) == {}


def test_no_isolado():
    g = Grafo()
    g.adicionar_no("a")
    assert intermediacao(g) == {"a": 0.0}


@pytest.mark.parametrize("n", [3, 5, 10])
def test_estrela_centro(n):
    # O centro fica no único caminho mínimo entre cada par de folhas: (n - 1)(n - 2)/2 pares.
    g = estrela(n)
    b = intermediacao(g, normalizada=False)
    assert b[0] == pytest.approx((n - 1) * (n - 2) / 2)
    assert all(b[i] == 0.0 for i in range(1, n))
    # Normalizada, o centro de uma estrela é o máximo possível: 1.
    assert intermediacao(g)[0] == pytest.approx(1.0)


def test_completo_zero():
    # No grafo completo todo par é vizinho: ninguém fica no meio de um caminho mínimo.
    assert all(valor == 0.0 for valor in intermediacao(completo(6)).values())


def test_caminho():
    # No caminho 0-1-2-3-4, o nó i separa i * (4 - i) pares.
    b = intermediacao(caminho(5), normalizada=False)
    assert b == pytest.approx({0: 0.0, 1: 3.0, 2: 4.0, 3: 3.0, 4: 0.0})


def test_ciclo_quatro_caminhos_divididos():
    # No ciclo 0-1-2-3-0, o par (0, 2) tem dois caminhos mínimos (por 1 e por 3): cada um leva 1/2.
    g = Grafo.de_arestas([(0, 1), (1, 2), (2, 3), (3, 0)])
    assert intermediacao(g, normalizada=False) == pytest.approx({v: 0.5 for v in range(4)})


def test_desconexo():
    # Dois caminhos de 3 nós separados: só os meios têm intermediação.
    g = Grafo.de_arestas([(0, 1), (1, 2), ("a", "b"), ("b", "c")])
    b = intermediacao(g, normalizada=False)
    assert b[1] == pytest.approx(1.0)
    assert b["b"] == pytest.approx(1.0)
    assert b[0] == b[2] == b["a"] == b["c"] == 0.0


def test_direcionado():
    # 0 -> 1 -> 2: só o par ordenado (0, 2) passa pelo 1, e o direcionado não divide por 2.
    g = Grafo.de_arestas([(0, 1), (1, 2)], direcionado=True)
    assert intermediacao(g, normalizada=False) == pytest.approx({0: 0.0, 1: 1.0, 2: 0.0})


def test_nao_altera_o_grafo():
    g = carregar_karate()
    antes = sorted(g.arestas())
    intermediacao(g)
    intermediacao(g, k=5, semente=1)
    assert sorted(g.arestas()) == antes


# Karate Club: valores de referência do guia (NetworkX 3.7)


def test_karate_exata():
    b = intermediacao(carregar_karate())
    assert b[0] == pytest.approx(0.4376, abs=1e-4)
    assert b[33] == pytest.approx(0.3041, abs=1e-4)
    assert b[32] == pytest.approx(0.1452, abs=1e-4)
    assert max(b, key=b.get) == 0


# Amostragem


def test_amostragem_k_igual_a_n_e_exata():
    g = carregar_karate()
    assert intermediacao(g, k=34, semente=7) == pytest.approx(intermediacao(g))
    assert intermediacao(g, k=1000, semente=7) == pytest.approx(intermediacao(g))


def test_amostragem_repete_com_a_mesma_semente():
    g = carregar_karate()
    assert intermediacao(g, k=10, semente=42) == intermediacao(g, k=10, semente=42)


def test_amostragem_estima_a_exata():
    # Com metade das origens, os dois nós mais centrais (0 e 33) continuam no topo,
    # e a média de várias sementes fica perto do valor exato.
    g = carregar_karate()
    exata = intermediacao(g)
    medias = {v: 0.0 for v in g.nos()}
    rodadas = 30
    for semente in range(rodadas):
        for v, valor in intermediacao(g, k=17, semente=semente).items():
            medias[v] += valor / rodadas
    assert medias[0] == pytest.approx(exata[0], rel=0.15)
    assert medias[33] == pytest.approx(exata[33], rel=0.15)


def test_k_invalido():
    with pytest.raises(ValueError):
        intermediacao(carregar_karate(), k=0)


# Invariantes em grafos aleatórios

arestas_aleatorias = st.lists(
    st.tuples(st.integers(0, 14), st.integers(0, 14)).filter(lambda a: a[0] != a[1]),
    max_size=40,
)


@settings(max_examples=60)
@given(arestas_aleatorias)
def test_invariantes(arestas):
    g = Grafo.de_arestas(arestas)
    n = g.numero_de_nos()
    b = intermediacao(g)
    # Um valor por nó, todos entre 0 e 1.
    assert set(b) == set(g.nos())
    assert all(-1e-12 <= valor <= 1 + 1e-12 for valor in b.values())
    # Folhas (grau 1) e nós isolados nunca ficam entre dois outros nós.
    assert all(b[v] == 0.0 for v in g.nos() if g.grau(v) <= 1)
    # Sem normalizar, a soma das intermediações é a soma, sobre os pares alcançáveis,
    # de (distância - 1). Conferimos com uma BFS simples.
    bruta = intermediacao(g, normalizada=False)
    total = 0
    for s in g.nos():
        dist = {s: 0}
        fila = [s]
        for v in fila:
            for w in g.vizinhos(v):
                if w not in dist:
                    dist[w] = dist[v] + 1
                    fila.append(w)
        total += sum(d - 1 for d in dist.values() if d > 0)
    assert sum(bruta.values()) == pytest.approx(total / 2)
    assert n == len(b)


# PageRank


def test_pagerank_grafo_vazio():
    assert pagerank(Grafo()) == {}


def test_pagerank_simetrico():
    # Ciclo e grafo completo: todos os nós são iguais, então todos valem 1/n.
    ciclo = Grafo.de_arestas((i, (i + 1) % 5) for i in range(5))
    assert pagerank(ciclo) == pytest.approx({v: 1 / 5 for v in range(5)})
    assert pagerank(completo(6)) == pytest.approx({v: 1 / 6 for v in range(6)})


def test_pagerank_estrela():
    # Na estrela, o centro recebe de todas as folhas e cada folha só do centro:
    # x_c = (1 - d)/n + d(n - 1)x_f  e  x_f = (1 - d)/n + d x_c / (n - 1).
    n, d = 6, 0.85
    x_f = (1 - d) / n * (1 + d / (n - 1)) / (1 - d * d)
    x_c = 1 - (n - 1) * x_f
    # A estrela é bipartida e oscila: com mais iterações, converge na tolerância do guia.
    pr = pagerank(estrela(n), amortecimento=d, max_iteracoes=200)
    assert pr[0] == pytest.approx(x_c)
    assert all(pr[i] == pytest.approx(x_f) for i in range(1, n))


def test_pagerank_no_pendurado():
    # 0 -> 1 e o 1 não tem saída: o valor do 1 é repartido entre todos, e a soma continua 1.
    g = Grafo.de_arestas([(0, 1)], direcionado=True)
    pr = pagerank(g)
    assert sum(pr.values()) == pytest.approx(1.0)
    assert pr[1] > pr[0]
    # Nó isolado num grafo não direcionado também é pendurado.
    g = Grafo.de_arestas([(0, 1)])
    g.adicionar_no(2)
    pr = pagerank(g)
    assert sum(pr.values()) == pytest.approx(1.0)
    assert pr[0] == pytest.approx(pr[1])
    assert pr[2] < pr[0]


def test_pagerank_sem_amortecimento_de_salto():
    # Com amortecimento 0 só há salto aleatório: todos valem 1/n.
    assert pagerank(carregar_karate(), amortecimento=0.0) == pytest.approx({v: 1 / 34 for v in range(34)})


def test_pagerank_usa_o_peso():
    # 0 -> 1 com peso 3 e 0 -> 2 com peso 1: o 1 recebe três vezes mais do 0 que o 2.
    g = Grafo.de_arestas([(0, 1, 3.0), (0, 2, 1.0), (1, 0), (2, 0)], direcionado=True)
    pr = pagerank(g, max_iteracoes=200)
    assert pr[1] > pr[2]


def test_pagerank_nao_convergiu_avisa():
    # Com poucas iterações não dá para convergir: avisa e devolve a última iteração.
    with pytest.warns(RuntimeWarning):
        pr = pagerank(carregar_karate(), max_iteracoes=2)
    assert sum(pr.values()) == pytest.approx(1.0)


def test_pagerank_nao_altera_o_grafo():
    g = carregar_karate()
    antes = sorted(g.arestas())
    pagerank(g)
    assert sorted(g.arestas()) == antes


def test_pagerank_karate():
    pr = pagerank(carregar_karate())
    assert pr[33] == pytest.approx(0.1009, abs=1e-4)
    assert pr[0] == pytest.approx(0.0970, abs=1e-4)
    assert pr[32] == pytest.approx(0.0717, abs=1e-4)
    assert sum(pr.values()) == pytest.approx(1.0)
    assert max(pr, key=pr.get) == 33


@settings(max_examples=60)
@given(arestas_aleatorias, st.booleans())
def test_pagerank_invariantes(arestas, direcionado):
    g = Grafo.de_arestas(arestas, direcionado=direcionado)
    pr = pagerank(g, max_iteracoes=300)
    assert set(pr) == set(g.nos())
    if pr:
        # Uma distribuição de probabilidade: soma 1 e todo nó recebe pelo menos o salto (1 - d)/n.
        n = g.numero_de_nos()
        assert sum(pr.values()) == pytest.approx(1.0)
        assert all(valor >= 0.15 / n - 1e-9 for valor in pr.values())
