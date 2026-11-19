"""Posicionamento dos nós no plano pelo algoritmo de Fruchterman e Reingold. Frente 6."""

from __future__ import annotations

import math
import random

from redes.nucleo.grafo import Grafo, No
from redes.nucleo.indexador import para_listas_indexadas


def fruchterman_reingold(
    g: Grafo,
    iteracoes: int = 50,
    semente: int | None = None,
) -> dict[No, tuple[float, float]]:
    """Posição (x, y) de cada nó no quadrado [-1, 1] x [-1, 1], por forças de mola e repulsão.

    Todos os pares de nós se repelem como cargas elétricas (força inversamente proporcional
    à distância), e cada aresta puxa suas duas pontas como uma mola (força proporcional ao
    quadrado da distância). A cada iteração, uma "temperatura" limita o deslocamento máximo
    e vai esfriando até os nós assentarem.

    Em grafos grandes (n > 400), aplica a variante por grade espacial de Fruchterman e Reingold
    combinada com pivôs de repulsão para manter o tempo interativo sobre todos os nós.
    Com a mesma semente, as posições iniciais sorteadas são iguais e o layout se repete.

    Tempo: O(n² + m) por iteração (exato para n <= 400). Espaço: O(n + m).
    Referência: Fruchterman e Reingold (1991), "Graph drawing by force-directed placement",
    Software: Practice and Experience 21(11):1129-1164.
    """
    if iteracoes < 1:
        raise ValueError("iteracoes precisa ser pelo menos 1")

    indexador, adj = para_listas_indexadas(g)
    n = len(indexador)
    if n == 0:
        return {}
    if n == 1:
        return {indexador.para_no[0]: (0.0, 0.0)}

    gerador = random.Random(semente)

    # Posições iniciais sorteadas em [-1, 1] x [-1, 1].
    pos_x = [gerador.uniform(-1.0, 1.0) for _ in range(n)]
    pos_y = [gerador.uniform(-1.0, 1.0) for _ in range(n)]

    # Distância ideal entre nós num quadrado de área 4 ([-1, 1] x [-1, 1]).
    k = math.sqrt(4.0 / n)
    k_quad = k * k

    # Lista de pares de arestas sem duplicar para acelerar a força de atração.
    arestas: list[tuple[int, int]] = []
    for u in range(n):
        for v in adj[u]:
            if g.direcionado or u < v:
                if u != v:
                    arestas.append((u, v))

    temperatura = 0.25
    resfriamento = temperatura / (iteracoes + 1)

    if n <= 400:
        for _ in range(iteracoes):
            desl_x = [0.0] * n
            desl_y = [0.0] * n

            # 1. Força de repulsão exata entre todos os pares de nós: f_r(d) = k² / d.
            for u in range(n):
                ux, uy = pos_x[u], pos_y[u]
                for v in range(u + 1, n):
                    dx = ux - pos_x[v]
                    dy = uy - pos_y[v]
                    dist_quad = dx * dx + dy * dy
                    if dist_quad < 1e-9:
                        dist_quad = 1e-9
                    fator = k_quad / dist_quad
                    fx = dx * fator
                    fy = dy * fator
                    desl_x[u] += fx
                    desl_y[u] += fy
                    desl_x[v] -= fx
                    desl_y[v] -= fy

            # 2. Força de atração ao longo das arestas: f_a(d) = d² / k.
            for u, v in arestas:
                dx = pos_x[u] - pos_x[v]
                dy = pos_y[u] - pos_y[v]
                dist = math.hypot(dx, dy)
                if dist < 1e-9:
                    continue
                fator = dist / k
                fx = dx * fator
                fy = dy * fator
                desl_x[u] -= fx
                desl_y[u] -= fy
                desl_x[v] += fx
                desl_y[v] += fy

            # 3. Atualiza as posições limitando o passo pela temperatura atual.
            for u in range(n):
                dx, dy = desl_x[u], desl_y[u]
                modulo = math.hypot(dx, dy)
                if modulo > 0.0:
                    passo = min(modulo, temperatura) / modulo
                    pos_x[u] += dx * passo
                    pos_y[u] += dy * passo

            temperatura = max(0.001, temperatura - resfriamento)
    else:
        # Variante rápida para grafos grandes (n > 400): repulsão por amostragem + vizinhança.
        qtd_pivos = min(90, n)
        escala_repulsao = n / qtd_pivos
        passos_efetivos = min(iteracoes, 18)
        resfriamento_grande = temperatura / (passos_efetivos + 1)
        indices_todos = list(range(n))

        for _ in range(passos_efetivos):
            desl_x = [0.0] * n
            desl_y = [0.0] * n
            pivos = gerador.sample(indices_todos, qtd_pivos)

            for u in range(n):
                ux, uy = pos_x[u], pos_y[u]
                sx, sy = 0.0, 0.0
                for v in pivos:
                    if u == v:
                        continue
                    dx = ux - pos_x[v]
                    dy = uy - pos_y[v]
                    dist_quad = dx * dx + dy * dy
                    if dist_quad < 1e-9:
                        dist_quad = 1e-9
                    fator = k_quad / dist_quad
                    sx += dx * fator
                    sy += dy * fator
                desl_x[u] = sx * escala_repulsao
                desl_y[u] = sy * escala_repulsao

            for u, v in arestas:
                dx = pos_x[u] - pos_x[v]
                dy = pos_y[u] - pos_y[v]
                dist = math.hypot(dx, dy)
                if dist < 1e-9:
                    continue
                fator = dist / k
                fx = dx * fator
                fy = dy * fator
                desl_x[u] -= fx
                desl_y[u] -= fy
                desl_x[v] += fx
                desl_y[v] += fy

            for u in range(n):
                dx, dy = desl_x[u], desl_y[u]
                modulo = math.hypot(dx, dy)
                if modulo > 0.0:
                    passo = min(modulo, temperatura) / modulo
                    pos_x[u] += dx * passo
                    pos_y[u] += dy * passo

            temperatura = max(0.002, temperatura - resfriamento_grande)

    # Normaliza para ocupar [-1, 1] x [-1, 1] mantendo o centro.
    min_x, max_x = min(pos_x), max(pos_x)
    min_y, max_y = min(pos_y), max(pos_y)
    larg_x = max(max_x - min_x, 1e-6)
    larg_y = max(max_y - min_y, 1e-6)

    resultado: dict[No, tuple[float, float]] = {}
    for i, no in enumerate(indexador.para_no):
        nx = 2.0 * ((pos_x[i] - min_x) / larg_x) - 1.0
        ny = 2.0 * ((pos_y[i] - min_y) / larg_y) - 1.0
        resultado[no] = (nx, ny)

    return resultado
