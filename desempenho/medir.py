"""Mede tempo, pico de memória e TEPS dos algoritmos do pacote redes. Frente 3.

Uso, da raiz do projeto:
    python -m desempenho.medir            # tudo (leva cerca de 1 hora)
    python -m desempenho.medir --rapido   # só 1.000 e 2.000 nós, para conferir

Salva desempenho/resultados/medicoes_redes.csv. Os grafos, os algoritmos e as regras de
medição estão em casos.py; comparar_networkx.py faz o mesmo com o NetworkX.
"""

from __future__ import annotations

import argparse
import statistics

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
    salvar_ambiente,
)
from redes.metricas.caminhos import bfs
from redes.metricas.centralidade import intermediacao, pagerank
from redes.metricas.nucleo_k import numero_de_nucleo
from redes.nucleo.grafo import Grafo


def funcoes(g: Grafo) -> dict:
    """Cada algoritmo de ALGORITMOS como uma função sem argumentos, pronta para medir."""
    origem = origem_da_bfs(g)
    return {
        "bfs": lambda: bfs(g, origem),
        "intermediacao_exata": lambda: intermediacao(g),
        f"intermediacao_k{K_AMOSTRA}": lambda: intermediacao(g, k=K_AMOSTRA, semente=SEMENTE),
        "pagerank": lambda: pagerank(g),
        "numero_de_nucleo": lambda: numero_de_nucleo(g),
    }


def principal() -> None:
    """Lê as opções da linha de comando, mede cada algoritmo em cada grafo e grava o CSV."""
    analisador = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    analisador.add_argument("--rapido", action="store_true", help="só os dois menores tamanhos")
    analisador.add_argument("--sem-bases", action="store_true", help="não mede as 4 bases")
    analisador.add_argument("--repeticoes", type=int, default=REPETICOES)
    analisador.add_argument("--max-n-exata", type=int, default=MAX_N_EXATA)
    opcoes = analisador.parse_args()

    caminho = PASTA_RESULTADOS / ("medicoes_redes_rapido.csv" if opcoes.rapido else "medicoes_redes.csv")
    if not opcoes.rapido:
        salvar_ambiente()
    escritor = EscritorCsv(caminho)
    try:
        for caso in casos(rapido=opcoes.rapido, com_bases=not opcoes.sem_bases):
            g = caso.construir()
            a_medir = funcoes(g)
            for algoritmo in ALGORITMOS:
                if not deve_medir(algoritmo, g.numero_de_nos(), opcoes.max_n_exata):
                    continue
                funcao = a_medir[algoritmo]
                tempos = medir_tempo(funcao, opcoes.repeticoes)
                memoria = medir_memoria(funcao)
                teps = None
                if algoritmo == "bfs":
                    # TEPS: arestas percorridas por segundo (a métrica do Graph500).
                    teps = arestas_alcancadas(g, funcao()) / statistics.median(tempos)
                linha = linha_de_resultado("redes", algoritmo, caso, g, tempos, memoria, teps)
                escritor.escrever(linha)
                mostrar(linha)
    finally:
        escritor.fechar()
    print(f"\nResultados em {caminho}")


if __name__ == "__main__":
    principal()
