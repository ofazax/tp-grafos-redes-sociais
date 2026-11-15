"""Decomposição em k-núcleos (k-core). Frente 3."""

from __future__ import annotations

from redes.nucleo.grafo import Grafo, No
from redes.nucleo.indexador import IndexadorDeNos


def numero_de_nucleo(g: Grafo) -> dict[No, int]:
    """Número de núcleo (core number) de cada nó, pelo algoritmo de Batagelj e Zaversnik.

    O k-núcleo é o maior subgrafo em que todo nó tem grau >= k. O número de núcleo de v é o
    maior k tal que v está no k-núcleo. O algoritmo remove sempre o nó de menor grau que
    sobrou; o grau dele no momento da remoção é o seu número de núcleo. Os nós ficam
    ordenados por grau em "baldes" (bucket sort), e cada remoção só baixa em 1 o grau dos
    vizinhos, o que dá tempo linear.

    Laços (v, v) são ignorados. No grafo direcionado, o grau é entrada + saída, e os vizinhos
    são os predecessores e os sucessores (como no NetworkX).

    Tempo: O(n + m). Espaço: O(n + m).
    Referência: Batagelj e Zaversnik (2003), "An O(m) algorithm for cores decomposition of networks".
    """
    indexador = IndexadorDeNos(g)
    n = len(indexador)
    if n == 0:
        return {}

    indice = indexador.para_indice

    # Vizinhos de cada nó como inteiros, sem laços. No direcionado, entram as duas direções
    # (um par com arestas nos dois sentidos conta duas vezes, igual ao grau entrada + saída).
    vizinhos: list[list[int]] = []
    for v in indexador.para_no:
        lista = [indice[w] for w in g.vizinhos(v) if w != v]
        if g.direcionado:
            lista += [indice[w] for w in g.predecessores(v) if w != v]
        vizinhos.append(lista)

    grau = [len(lista) for lista in vizinhos]
    maior_grau = max(grau)

    # Bucket sort dos nós pelo grau: inicio[k] é onde começam os nós de grau k em `ordem`.
    contagem = [0] * (maior_grau + 1)
    for k in grau:
        contagem[k] += 1
    inicio = [0] * (maior_grau + 1)
    soma = 0
    for k in range(maior_grau + 1):
        inicio[k] = soma
        soma += contagem[k]

    # ordem: nós em ordem crescente de grau; posicao[v]: onde v está em `ordem`.
    ordem = [0] * n
    posicao = [0] * n
    proximo = inicio[:]
    for v in range(n):
        posicao[v] = proximo[grau[v]]
        ordem[posicao[v]] = v
        proximo[grau[v]] += 1

    # Percorre os nós em ordem de grau. Ao "remover" v, o grau atual dele é o número de
    # núcleo. Cada vizinho w com grau maior perde 1 de grau e desce um balde: troca de
    # lugar com o primeiro nó do seu balde e o balde começa uma posição depois.
    for i in range(n):
        v = ordem[i]
        for w in vizinhos[v]:
            if grau[w] > grau[v]:
                gw = grau[w]
                primeiro = ordem[inicio[gw]]
                if primeiro != w:
                    pw = posicao[w]
                    pp = inicio[gw]
                    ordem[pw], ordem[pp] = primeiro, w
                    posicao[primeiro], posicao[w] = pw, pp
                inicio[gw] += 1
                grau[w] -= 1

    return {indexador.para_no[i]: grau[i] for i in range(n)}


def k_nucleo(g: Grafo, k: int) -> Grafo:
    """Subgrafo induzido pelos nós com número de núcleo >= k (o k-núcleo).

    Todo nó do resultado tem grau >= k dentro dele. As arestas mantêm o peso e o grafo
    mantém a direção do original. O grafo de entrada não é alterado. Com k maior que o
    núcleo máximo, devolve um grafo vazio.

    Tempo: O(n + m). Espaço: O(n + m).
    Referência: Seidman (1983), "Network structure and minimum degree";
    Batagelj e Zaversnik (2003).
    """
    nucleo = numero_de_nucleo(g)
    dentro = {v for v, c in nucleo.items() if c >= k}

    sub = Grafo(direcionado=g.direcionado)
    for v in g.nos():
        if v in dentro:
            sub.adicionar_no(v)
    for v, w, peso in g.arestas():
        if v in dentro and w in dentro:
            sub.adicionar_aresta(v, w, peso)
    return sub
