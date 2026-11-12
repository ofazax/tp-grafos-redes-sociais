"""Métricas de grau: centralidade de grau, distribuição, densidade e grau médio. Frente 2."""

from __future__ import annotations

from redes.nucleo.grafo import Grafo, No


def centralidade_de_grau(g: Grafo) -> dict[No, float]:
    #Centralidade de grau de cada nó: grau(v) / (n - 1).

    #É a fração dos outros nós com quem v está ligado: 1.0 significa que v é vizinho de todos. 
    #Em grafo com menos de 2 nós não há "outros nós", então o valor é 0.0.
    n = g.numero_de_nos()

    # Evita a divisão por zero (n - 1 = 0) no grafo com um único nó.
    if n < 2:
        return {v: 0.0 for v in g.nos()}

    # O maior grau possível de um nó é n - 1 (ligado a todos os outros).
    return {v: g.grau(v) / (n - 1) for v in g.nos()}


def distribuicao_de_graus(g: Grafo) -> dict[int, int]:
    #Quantos nós têm cada grau: {grau: quantidade de nós}, em ordem crescente de grau.

    #Só aparecem os graus que existem no grafo. 
    contagem: dict[int, int] = {}

    for v in g.nos():
        k = g.grau(v)
        # get(k, 0) devolve 0 na primeira vez que o grau k aparece.
        contagem[k] = contagem.get(k, 0) + 1

    # Devolve em ordem crescente de grau, para a interface não precisar ordenar.
    return dict(sorted(contagem.items()))


def densidade(g: Grafo) -> float:
    #Fração das arestas possíveis que existem no grafo, entre 0 e 1.

    #Não direcionado: 2m / (n(n - 1)). 
    # Direcionado: m / (n(n - 1)), porque (v, w) e (w, v) são arestas diferentes. Com menos de 2 nós, é 0.0.
    n = g.numero_de_nos()
    m = g.numero_de_arestas()

    if n < 2:
        return 0.0

    # Número de pares ordenados de nós diferentes.
    pares = n * (n - 1)

    if g.direcionado:
        return m / pares

    # No não direcionado, cada aresta ocupa dois pares ordenados: (v, w) e (w, v).
    return 2 * m / pares


def grau_medio(g: Grafo) -> float:
    #Grau médio do grafo: soma dos graus / n = 2m / n.

    #Cada aresta soma 2 ao total dos graus (1 em cada ponta), por isso a soma dos graus é sempre 2m. 
    #No direcionado, grau = entrada + saída. No grafo vazio, é 0.0.
    n = g.numero_de_nos()

    if n == 0:
        return 0.0

    return 2 * g.numero_de_arestas() / n