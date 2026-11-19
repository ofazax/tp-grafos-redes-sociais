"""Os mesmos testes de medir.py, com o NetworkX. Frente 3.

Uso, da raiz do projeto:
    python -m desempenho.comparar_networkx            # tudo
    python -m desempenho.comparar_networkx --rapido   # só 1.000 e 2.000 nós

Salva desempenho/resultados/medicoes_networkx.csv. Cada grafo é construído pelo nosso código
e copiado para um networkx.Graph com os mesmos nós, arestas e pesos (a cópia não entra no
tempo). Além do tempo, a coluna diferenca_max mostra a maior diferença, entre todos os nós,
entre o resultado do NetworkX e o nosso. Ela fica vazia na intermediação amostrada, porque
os dois sorteiam origens diferentes.

Equivalentes no NetworkX 3.7:
    bfs                    -> single_source_shortest_path_length
    intermediacao_exata    -> betweenness_centrality
    intermediacao_k100     -> betweenness_centrality(k=100, seed=42)
    pagerank               -> _pagerank_python (a versão em Python puro; o nx.pagerank
                              padrão exige o SciPy, que não está nas dependências)
    numero_de_nucleo       -> core_number
"""

from __future__ import annotations

import argparse
import statistics

import networkx as nx
from networkx.algorithms.link_analysis.pagerank_alg import _pagerank_python

from desempenho.casos import (
    ALGORITMOS,
    K_AMOSTRA,
    MAX_N_EXATA,
    PASTA_RESULTADOS,
    REPETICOES,
    SEMENTE,
    EscritorCsv,
    arestas_alcancadas,
    casos,
    deve_medir,
    linha_de_resultado,
    medir_memoria,
    medir_tempo,
    mostrar,
    origem_da_bfs,
)
from desempenho.medir import funcoes as funcoes_redes
from redes.nucleo.grafo import Grafo


def para_networkx(g: Grafo) -> nx.Graph:
    """Copia o Grafo para o NetworkX, com os nós na mesma ordem e os mesmos pesos. Tempo: O(n + m)."""
    G = nx.DiGraph() if g.direcionado else nx.Graph()
    G.add_nodes_from(g.nos())
    G.add_weighted_edges_from(g.arestas())
    return G


def funcoes(G: nx.Graph, g: Grafo) -> dict:
    """Os mesmos algoritmos de medir.funcoes, com os mesmos parâmetros, no NetworkX."""
    origem = origem_da_bfs(g)
    return {
        "bfs": lambda: nx.single_source_shortest_path_length(G, origem),
        "intermediacao_exata": lambda: nx.betweenness_centrality(G),
        f"intermediacao_k{K_AMOSTRA}": lambda: nx.betweenness_centrality(G, k=K_AMOSTRA, seed=SEMENTE),
        "pagerank": lambda: _pagerank_python(G, alpha=0.85, max_iter=100, tol=1e-8, weight="weight"),
        "numero_de_nucleo": lambda: nx.core_number(G),
    }


def diferenca_maxima(nosso: dict, deles: dict) -> float:
    """Maior |nosso[v] - deles[v]| entre todos os nós (um nó que falta num dos dois é erro). Tempo: O(n)."""
    if nosso.keys() != deles.keys():
        raise AssertionError("os dois resultados não têm os mesmos nós")
    return max((abs(nosso[v] - deles[v]) for v in nosso), default=0.0)


def principal() -> None:
    """Lê as opções da linha de comando, mede o NetworkX em cada grafo e grava o CSV."""
    analisador = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    analisador.add_argument("--rapido", action="store_true", help="só os dois menores tamanhos")
    analisador.add_argument("--sem-bases", action="store_true", help="não mede as 4 bases")
    analisador.add_argument("--repeticoes", type=int, default=REPETICOES)
    analisador.add_argument("--max-n-exata", type=int, default=MAX_N_EXATA)
    opcoes = analisador.parse_args()

    caminho = PASTA_RESULTADOS / ("medicoes_networkx_rapido.csv" if opcoes.rapido else "medicoes_networkx.csv")
    escritor = EscritorCsv(caminho)
    try:
        for caso in casos(rapido=opcoes.rapido, com_bases=not opcoes.sem_bases):
            g = caso.construir()
            G = para_networkx(g)
            deles, nossas = funcoes(G, g), funcoes_redes(g)
            for algoritmo in ALGORITMOS:
                if not deve_medir(algoritmo, g.numero_de_nos(), opcoes.max_n_exata):
                    continue
                funcao = deles[algoritmo]
                tempos = medir_tempo(funcao, opcoes.repeticoes)
                memoria = medir_memoria(funcao)
                resultado = funcao()
                teps = None
                if algoritmo == "bfs":
                    teps = arestas_alcancadas(g, resultado) / statistics.median(tempos)
                # A amostrada sorteia origens diferentes nos dois: os valores não são comparáveis.
                diferenca = None
                if algoritmo != f"intermediacao_k{K_AMOSTRA}":
                    diferenca = diferenca_maxima(nossas[algoritmo](), resultado)
                linha = linha_de_resultado("networkx", algoritmo, caso, g, tempos, memoria, teps, diferenca)
                escritor.escrever(linha)
                mostrar(linha)
    finally:
        escritor.fechar()
    print(f"\nResultados em {caminho}")


if __name__ == "__main__":
    principal()
