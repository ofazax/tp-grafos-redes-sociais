"""Centralidades de intermediação (Brandes) e PageRank. Frente 3."""

from __future__ import annotations

import random
import warnings
from collections import deque

from redes.nucleo.grafo import Grafo, No
from redes.nucleo.indexador import IndexadorDeNos, para_listas_indexadas


def intermediacao(
    g: Grafo,
    k: int | None = None,
    semente: int | None = None,
    normalizada: bool = True,
) -> dict[No, float]:
    """Centralidade de intermediação (betweenness) de cada nó, pelo algoritmo de Brandes.

    A intermediação de v é a soma, sobre os pares (s, t) com s != v != t, da fração dos
    caminhos mínimos de s a t que passam por v. As distâncias contam arestas (BFS), então o
    peso das arestas é ignorado.

    Com k = None o cálculo é exato: uma BFS a partir de cada nó. Com k inteiro, só k origens
    sorteadas com random.Random(semente) entram na conta, e o resultado é escalado por n / k,
    o que dá uma estimativa sem viés da versão exata (Brandes e Pich, 2007). Se k >= n, o
    cálculo é exato.

    Normalização (a mesma do NetworkX): com normalizada=True, divide por (n - 1)(n - 2), e o
    resultado fica entre 0 e 1. Com normalizada=False, o não direcionado é dividido por 2,
    porque cada par (s, t) aparece duas vezes, uma vez a partir de s e outra a partir de t.
    Assim, o centro de uma estrela com n nós dá (n - 1)(n - 2) / 2.

    Tempo: O(nm) na versão exata e O(km) na amostrada. Espaço: O(n + m).
    Referência: Brandes (2001), "A faster algorithm for betweenness centrality";
    Brandes e Pich (2007), "Centrality estimation in large networks".
    """
    # Listas indexadas por inteiro (0..n-1) são mais rápidas que os dicionários do Grafo.
    indexador, adj = para_listas_indexadas(g)
    n = len(indexador)

    # Origens das BFS: todos os nós (exata) ou k nós sorteados (amostragem).
    if k is None or k >= n:
        origens = range(n)
        amostrada = False
    else:
        if k < 1:
            raise ValueError("k precisa ser pelo menos 1")
        origens = random.Random(semente).sample(range(n), k)
        amostrada = True

    # Acumulador da intermediação de cada nó.
    cb = [0.0] * n

    for s in origens:
        _acumular_dependencias(adj, s, cb)

    # Escala final: normalização, ou o fator 1/2 do não direcionado, e o n / k da amostragem.
    escala = 1.0
    if normalizada:
        # Com n <= 2 nenhum nó fica entre outros dois, então todos os valores já são 0.
        if n > 2:
            escala = 1.0 / ((n - 1) * (n - 2))
    elif not g.direcionado:
        escala = 0.5
    if amostrada:
        escala *= n / k

    return {indexador.para_no[i]: cb[i] * escala for i in range(n)}


def _acumular_dependencias(adj: list[list[int]], s: int, cb: list[float]) -> None:
    """Uma rodada de Brandes: BFS a partir de s e soma das dependências em cb. O(n + m)."""
    n = len(adj)

    # sigma[w]: número de caminhos mínimos de s até w.
    sigma = [0] * n
    sigma[s] = 1

    # dist[w]: distância (em arestas) de s até w; -1 quer dizer que w ainda não foi visitado.
    dist = [-1] * n
    dist[s] = 0

    # pred[w]: nós logo antes de w em algum caminho mínimo de s até w.
    pred: list[list[int]] = [[] for _ in range(n)]

    # Pilha com os nós na ordem da BFS: desempilhar dá a ordem decrescente de distância.
    pilha: list[int] = []
    fila = deque([s])

    # Fase 1: BFS contando os caminhos mínimos.
    while fila:
        v = fila.popleft()
        pilha.append(v)
        for w in adj[v]:
            # Primeira vez que w é alcançado: entra na fila com distância d(v) + 1.
            if dist[w] < 0:
                dist[w] = dist[v] + 1
                fila.append(w)
            # w está um nível abaixo de v: todo caminho mínimo até v continua até w.
            if dist[w] == dist[v] + 1:
                sigma[w] += sigma[v]
                pred[w].append(v)

    # Fase 2: dependências, dos nós mais distantes para os mais próximos de s.
    # delta[v] = soma, sobre os w que têm v como predecessor, de (sigma[v] / sigma[w]) * (1 + delta[w]).
    delta = [0.0] * n
    while pilha:
        w = pilha.pop()
        coeficiente = (1.0 + delta[w]) / sigma[w]
        for v in pred[w]:
            delta[v] += sigma[v] * coeficiente
        # A origem não conta na própria intermediação.
        if w != s:
            cb[w] += delta[w]


def pagerank(
    g: Grafo,
    amortecimento: float = 0.85,
    tolerancia: float = 1e-8,
    max_iteracoes: int = 100,
) -> dict[No, float]:
    """PageRank de cada nó, por iteração de potência. A soma de todos os valores é 1.

    Um navegador aleatório, a cada passo, segue uma aresta de saída com probabilidade
    `amortecimento` (escolhendo a aresta em proporção ao peso) ou salta para um nó qualquer
    com probabilidade 1 - amortecimento. O PageRank de v é a fração do tempo que ele passa
    em v. Nós sem arestas de saída repartem o valor igualmente entre todos os nós. No grafo
    não direcionado, cada aresta vale nos dois sentidos.

    Para quando a soma das diferenças entre duas iterações fica abaixo de n * tolerancia
    (o mesmo critério do NetworkX). Se não convergir em max_iteracoes, emite um
    RuntimeWarning e devolve a última iteração: o erro cai por um fator `amortecimento` a
    cada passo, então depois de 100 iterações ele já é da ordem de 0,85^100 ~ 1e-7. Isso
    acontece em grafos bipartidos (estrela, árvores), em que a iteração oscila entre os
    dois lados antes de assentar.

    Tempo: O(n + m) por iteração. Espaço: O(n + m).
    Referência: Brin e Page (1998), "The anatomy of a large-scale hypertextual Web search engine".
    """
    indexador = IndexadorDeNos(g)
    n = len(indexador)
    if n == 0:
        return {}

    indice = indexador.para_indice

    # Para cada nó i: lista de (j, fração do peso de saída de i que vai para j).
    transicoes: list[list[tuple[int, float]]] = []
    # Nós sem saída ("pendurados"): o valor deles é repartido entre todos os nós.
    pendurados: list[int] = []

    for i, v in enumerate(indexador.para_no):
        saida = g.adj[v]
        total = sum(saida.values())
        if total == 0:
            pendurados.append(i)
            transicoes.append([])
        else:
            transicoes.append([(indice[w], peso / total) for w, peso in saida.items()])

    d = amortecimento
    # Começa com o valor espalhado igualmente: 1/n para cada nó.
    x = [1.0 / n] * n

    for _ in range(max_iteracoes):
        anterior = x
        x = [0.0] * n

        # Cada nó passa d * (seu valor) adiante, dividido entre os vizinhos pelo peso.
        for i, saidas in enumerate(transicoes):
            parcela = d * anterior[i]
            for j, fracao in saidas:
                x[j] += parcela * fracao

        # Salto aleatório (1 - d) e o valor dos pendurados, repartidos igualmente.
        soma_pendurados = sum(anterior[i] for i in pendurados)
        base = (1.0 - d) / n + d * soma_pendurados / n
        for j in range(n):
            x[j] += base

        # Convergiu: a mudança total entre duas iterações ficou pequena.
        erro = sum(abs(x[j] - anterior[j]) for j in range(n))
        if erro < n * tolerancia:
            break
    else:
        # O for terminou sem break: não convergiu dentro do limite de iterações.
        warnings.warn(
            f"o PageRank não convergiu em {max_iteracoes} iterações (erro {erro:.1e})",
            RuntimeWarning,
            stacklevel=2,
        )

    return {indexador.para_no[i]: x[i] for i in range(n)}
