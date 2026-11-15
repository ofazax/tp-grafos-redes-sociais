"""Centralidades de proximidade: closeness e harmônica. Frente 2."""

from __future__ import annotations

# As duas centralidades são calculadas com as distâncias da BFS.
from redes.metricas.caminhos import bfs
from redes.nucleo.grafo import Grafo, No


def proximidade(g: Grafo) -> dict[No, float]:
    """Centralidade de proximidade (closeness) de cada nó: (n - 1) / soma das distâncias.

    É o inverso da distância média de v até os outros nós: quanto mais perto v
    está de todo mundo, maior o valor. Vale 1.0 quando v é vizinho de todos.
    As distâncias contam arestas (BFS), então o peso das arestas é ignorado.

    Em grafo desconexo, v não alcança todos os nós, e a fórmula simples
    favoreceria quem está numa componente pequena. Por isso o valor é
    multiplicado pela fração dos nós que v alcança (correção de Wasserman e
    Faust, a mesma do NetworkX): com r nós alcançados,
    proximidade(v) = (r / (n - 1)) * (r / soma das distâncias).
    Em grafo conexo, r = n - 1 e sobra a fórmula do título. Nó que não alcança
    ninguém recebe 0.0. No direcionado, usa as distâncias de v até os outros.

    Tempo: O(n(n + m)), uma BFS por nó. Espaço: O(n).
    Referência: Bavelas (1950); Sabidussi (1966); Wasserman e Faust, Social Network Analysis (1994), cap. 5.
    """
    n = g.numero_de_nos()

    resultado: dict[No, float] = {}

    for v in g.nos():

        # Distância de v até cada nó que ele alcança (v incluído, com distância 0).
        distancia = bfs(g, v)

        # Quantos outros nós v alcança, e a soma das distâncias até eles.
        alcancados = len(distancia) - 1
        soma = sum(distancia.values())

        # Nó isolado (ou sem saída, no direcionado): não está perto de ninguém.
        if alcancados == 0:
            resultado[v] = 0.0
            continue

        # alcancados / soma é o inverso da distância média até quem v alcança;
        # alcancados / (n - 1) é a fração da rede que v alcança (1.0 em grafo conexo).
        resultado[v] = (alcancados / (n - 1)) * (alcancados / soma)

    return resultado


def harmonica(g: Grafo) -> dict[No, float]:
    """Centralidade harmônica de cada nó: soma de 1 / distância até cada outro nó.

    Vizinho direto soma 1, nó a dois passos soma 1/2, a três passos soma 1/3,
    e assim por diante. Nó que v não alcança soma 0 (como se estivesse a
    distância infinita), por isso a harmônica funciona em grafo desconexo sem
    nenhuma correção. O valor vai de 0 (nó isolado) a n - 1 (vizinho de todos).
    As distâncias contam arestas (BFS). No direcionado, usa as distâncias de v
    até os outros.

    Tempo: O(n(n + m)), uma BFS por nó. Espaço: O(n).
    Referência: Marchiori e Latora (2000); Boldi e Vigna (2014), Axioms for Centrality,
    Internet Mathematics 10(3-4):222-262.
    """
    resultado: dict[No, float] = {}

    for v in g.nos():

        # Distância de v até cada nó que ele alcança.
        distancia = bfs(g, v)

        # Soma 1 / d para cada nó alcançado; o "if d > 0" pula o próprio v, que está a distância 0.
        resultado[v] = sum(1 / d for d in distancia.values() if d > 0)

    return resultado