"""Cálculo da modularidade de uma partição de comunidades. Frente 4."""

from __future__ import annotations

from collections import defaultdict
from redes.nucleo.grafo import Grafo, No


def modularidade(g: Grafo, particao: dict[No, int]) -> float:
    """Calcula a modularidade Q de uma dada partição em comunidades.
    
    A modularidade mede a densidade de arestas internas das comunidades comparada
    à esperada em um grafo aleatório nulo com os mesmos graus dos nós.
    
    Tempo: O(m). Espaço: O(n + c), onde c é o número de comunidades.
    Referência: Newman & Girvan (2004), Physical Review E.
    """
    if g.numero_de_arestas() == 0 or g.numero_de_nos() == 0:
        return 0.0

    # Acumuladores de peso por comunidade
    sigma_in: dict[int, float] = defaultdict(float)
    sigma_tot: dict[int, float] = defaultdict(float)
    dois_m = 0.0

    # 1. Acumula os graus (pesos incidentes) de cada nó na sua respectiva comunidade
    for v in g.nos():
        c = particao[v]
        for w in g.vizinhos(v):
            sigma_tot[c] += g.peso(v, w)

    # 2. Percorre as arestas para computar o peso total 2m e as arestas internas
    for u, v, peso in g.arestas():
        if u == v:
            dois_m += peso
            if particao[u] == particao[v]:
                sigma_in[particao[u]] += peso
        else:
            dois_m += 2 * peso
            # Se as duas pontas da aresta estão na mesma comunidade, ela é interna
            if particao[u] == particao[v]:
                c = particao[u]
                sigma_in[c] += 2 * peso

    if dois_m == 0.0:
        return 0.0

    # 3. Calcula a soma da modularidade sobre todas as comunidades da partição
    q = 0.0
    comunidades = set(particao.values())
    for c in comunidades:
        fracao_interna = sigma_in[c] / dois_m
        fracao_esperada = (sigma_tot[c] / dois_m) ** 2
        q += fracao_interna - fracao_esperada

    return q