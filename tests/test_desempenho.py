"""Testes das funções de medição de desempenho (desempenho/casos.py e o ajuste dos gráficos).

Não importam o NetworkX: só comparar_networkx.py usa o NetworkX, e ele fica fora dos testes.
"""

import gc

import pytest

from desempenho.casos import (
    ALGORITMOS,
    COLUNAS,
    K_AMOSTRA,
    MAX_N_EXATA,
    arestas_alcancadas,
    casos,
    deve_medir,
    linha_de_resultado,
    medir_memoria,
    medir_tempo,
    origem_da_bfs,
)
from desempenho.graficos import inclinacao
from desempenho.medir import funcoes
from redes.metricas.caminhos import bfs
from redes.nucleo.grafo import Grafo


def caminho_mais_par_solto() -> Grafo:
    """0 - 1 - 2 e, separado, 3 - 4."""
    return Grafo.de_arestas([(0, 1), (1, 2), (3, 4)])


def test_intermediacao_exata_so_ate_o_limite():
    assert deve_medir("intermediacao_exata", MAX_N_EXATA)
    assert not deve_medir("intermediacao_exata", MAX_N_EXATA + 1)
    assert deve_medir("intermediacao_exata", 10_000, max_n_exata=10_000)


def test_amostrada_so_quando_n_maior_que_k():
    amostrada = f"intermediacao_k{K_AMOSTRA}"
    assert not deve_medir(amostrada, K_AMOSTRA)
    assert deve_medir(amostrada, K_AMOSTRA + 1)


def test_outros_algoritmos_sempre():
    for algoritmo in ("bfs", "pagerank", "numero_de_nucleo"):
        assert deve_medir(algoritmo, 10**6)


def test_arestas_alcancadas_conta_so_a_componente_da_origem():
    g = caminho_mais_par_solto()
    assert arestas_alcancadas(g, bfs(g, 0)) == 2
    assert arestas_alcancadas(g, bfs(g, 3)) == 1


def test_arestas_alcancadas_no_direcionado():
    g = Grafo.de_arestas([(0, 1), (1, 2), (2, 0)], direcionado=True)
    assert arestas_alcancadas(g, bfs(g, 0)) == 3


def test_origem_da_bfs_e_sempre_a_mesma():
    g = caminho_mais_par_solto()
    assert origem_da_bfs(g) == origem_da_bfs(g)
    assert origem_da_bfs(g) in g


def test_medir_tempo_devolve_uma_medida_por_repeticao():
    tempos = medir_tempo(lambda: sum(range(1000)), repeticoes=3)
    assert len(tempos) == 3
    assert all(t >= 0 for t in tempos)


def test_medir_tempo_religa_o_coletor_de_lixo():
    medir_tempo(lambda: None, repeticoes=1)
    assert gc.isenabled()
    with pytest.raises(ZeroDivisionError):
        medir_tempo(lambda: 1 / 0, repeticoes=1)
    assert gc.isenabled()


def test_medir_memoria_ve_uma_lista_grande():
    # Uma lista com 10^6 referências ocupa uns 7,6 MiB (8 bytes por posição).
    assert medir_memoria(lambda: [0] * 10**6) > 7


def test_casos_rapidos_tem_os_tres_modelos_em_cada_tamanho():
    lista = list(casos(rapido=True, com_bases=False))
    assert [c.nome for c in lista] == ["ER", "BA", "WS", "ER", "BA", "WS"]
    assert {c.tipo for c in lista} == {"sintetico"}
    assert [c.construir().numero_de_nos() for c in lista] == [1000] * 3 + [2000] * 3


def test_casos_saem_iguais_com_a_mesma_semente():
    primeiro = next(casos(rapido=True, com_bases=False))
    assert sorted(primeiro.construir().arestas()) == sorted(primeiro.construir().arestas())


def test_linha_de_resultado_tem_todas_as_colunas():
    g = caminho_mais_par_solto()
    caso = next(casos(rapido=True, com_bases=False))
    linha = linha_de_resultado("redes", "bfs", caso, g, [0.3, 0.1, 0.2], 1.5, teps=10.0)
    assert tuple(linha) == COLUNAS
    assert linha["n_mais_m"] == 8
    assert float(linha["tempo_mediana_s"]) == 0.2
    assert linha["diferenca_max"] == ""


def test_medir_tem_uma_funcao_para_cada_algoritmo():
    g = caminho_mais_par_solto()
    assert tuple(funcoes(g)) == ALGORITMOS


def test_inclinacao_de_potencias():
    assert inclinacao([(x, 3 * x**2) for x in (10, 100, 1000)]) == pytest.approx(2.0)
    assert inclinacao([(x, 5 * x) for x in (10, 100, 1000, 10_000)]) == pytest.approx(1.0)
    assert inclinacao([(10, 1), (100, 2)]) is None
