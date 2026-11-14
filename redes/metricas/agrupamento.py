"""Métricas de agrupamento: contagem de triângulos, clustering local e transitividade. Frente 4."""

from __future__ import annotations

from redes.nucleo.grafo import Grafo, No

def triangulos(g: Grafo) -> dict[No, int]:
    """Número de triângulos dos quais cada nó participa.
    
    Tempo: O(m^1.5). Espaço: O(n + m).

    Referência: Schank & Wagner (2005), Latapy (2008).
    Justificativa: Itera sobre as m arestas e faz intersecção de conjuntos
    de vizinhos em O(min(k_u, k_v)), cujo somatório total é O(m^1.5).
    """

    # 1. Dicionário acumulador iniciado com 0 para todos os nós
    contagem: dict[No, int] = {v: 0 for v in g.nos()}

    # 2. Guarda os vizinhos como conjuntos (set) para intersecção rápida O(min(k_u, k_v))
    vizinhos = {v: set(g.vizinhos(v)) for v in g.nos()}

    # 3. Percorre cada aresta (u, v) do grafo
    for u, v, _ in g.arestas():
        if u == v:
            continue  # Ignora laços (self-loops)

        # Vizinhos que estão ligados tanto a 'u' quanto a 'v' fecham triângulos com a aresta (u, v)
        comuns = len(vizinhos[u] & vizinhos[v])
        if comuns > 0:
            contagem[u] += comuns
            contagem[v] += comuns

    # 4. Cada triângulo que toca o nó foi contado 2 vezes (uma por cada aresta incidente do triângulo)
    return {v: total // 2 for v, total in contagem.items()}

def agrupamento_local(g: Grafo) -> dict[No, float]:
    """Coeficiente de agrupamento local de cada nó (Watts & Strogatz, 1998).
    
    Tempo: O(m^1.5). Espaço: O(n).

    Para nós com grau < 2, o agrupamento é 0.0.
    Para grau >= 2: 2 * T_v / (k * (k - 1)).
    """
    # 1. Obtém a contagem de triângulos de cada nó 
    triangulos_por_no = triangulos(g)
    resultado: dict[No, float] = {}

    # 2. Calcula o coeficiente para cada nó
    for v in g.nos():
        k = g.grau(v)
        if k < 2:
            resultado[v] = 0.0
        else:
            possiveis = k * (k - 1)
            resultado[v] = (2 * triangulos_por_no[v]) / possiveis

    return resultado

def agrupamento_medio(g: Grafo) -> float:
    """Média aritmética dos coeficientes de agrupamento local de todos os nós.
    
    Tempo: O(m^1.5). Espaço: O(n).

    Em grafo sem nós, retorna 0.0.
    """
    n = g.numero_de_nos()
    if n == 0:
        return 0.0

    valores = agrupamento_local(g)
    return sum(valores.values()) / n

def transitividade(g: Grafo) -> float:
    """Fração global de tríades abertas que se fecham em triângulos na rede inteira.

    Tempo: O(m^1.5). Espaço: O(n + m).
    
    Transitividade = (3 * total_triângulos) / total_tríades.
    Em grafos sem tríades (ex.: vazios ou sem caminhos de tamanho 2), retorna 0.0.
    """
    # 1. Soma dos triângulos de todos os nós (= 3 * total de triângulos do grafo)
    triangulos_por_no = triangulos(g)
    tres_vezes_triangulos = sum(triangulos_por_no.values())

    # 2. Total de tríades na rede: soma de k * (k - 1) / 2 para todos os nós
    total_triades = sum(g.grau(v) * (g.grau(v) - 1) // 2 for v in g.nos())

    if total_triades == 0:
        return 0.0

    return tres_vezes_triangulos / total_triades