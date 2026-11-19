"""Testes do limiar epidêmico e da simulação SIR: casos de resposta conhecida, valores
esperados calculados à mão, Karate Club, invariantes e Twitch PT."""

import math
from pathlib import Path

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from redes.aplicacao.influencia import limiar_epidemico, poder_de_espalhamento, simular_sir
from redes.leitores import RAIZ, carregar_twitch_ptbr
from redes.metricas.caminhos import componentes_conexas
from redes.nucleo import Grafo

ARQUIVO_KARATE = Path(__file__).parent / "dados" / "karate_arestas.txt"
TWITCH = "dados/brutos/twitch/PTBR/musae_PTBR_edges.csv"

precisa_twitch = pytest.mark.skipif(not (RAIZ / TWITCH).exists(), reason=f"baixe {TWITCH} (veja dados/README.md)")


def carregar_karate():
    g = Grafo()
    with open(ARQUIVO_KARATE, encoding="utf-8") as arquivo:
        for linha in arquivo:
            linha = linha.strip()
            if not linha or linha.startswith("#"):
                continue
            v, w = linha.split()
            g.adicionar_aresta(int(v), int(w))
    return g


def completo(n):
    return Grafo.de_arestas((i, j) for i in range(n) for j in range(i + 1, n))


def estrela(n):
    # Nó 0 no centro, ligado aos outros n - 1 nós.
    return Grafo.de_arestas((0, i) for i in range(1, n))


def caminho(n):
    return Grafo.de_arestas((i, i + 1) for i in range(n - 1))


def ciclo(n):
    return Grafo.de_arestas((i, (i + 1) % n) for i in range(n))


# Limiar epidêmico: beta_c = <k> / (<k²> - <k>)


def test_limiar_completo():
    # Todos com grau n - 1: (n - 1) / ((n - 1)² - (n - 1)) = 1 / (n - 2).
    assert limiar_epidemico(completo(10)) == pytest.approx(1 / 8)


def test_limiar_estrela():
    # <k> = 2(n - 1)/n e <k²> = n - 1, então beta_c = 2 / (n - 2).
    assert limiar_epidemico(estrela(12)) == pytest.approx(2 / 10)


def test_limiar_ciclo():
    # Todos com grau 2: 2 / (4 - 2) = 1. No ciclo, só beta = 1 garante um surto grande.
    assert limiar_epidemico(ciclo(7)) == pytest.approx(1.0)


def test_limiar_sem_no_de_grau_2_e_infinito():
    # Só arestas soltas e um nó isolado: nenhum surto passa de 2 nós.
    g = Grafo.de_arestas([(0, 1), (2, 3)])
    g.adicionar_no(4)
    assert limiar_epidemico(g) == math.inf


def test_limiar_ignora_laco():
    g = completo(5)
    g.adicionar_aresta(0, 0)
    assert limiar_epidemico(g) == pytest.approx(limiar_epidemico(completo(5)))


def test_limiar_grafo_vazio():
    with pytest.raises(ValueError):
        limiar_epidemico(Grafo())


def test_limiar_direcionado():
    with pytest.raises(ValueError):
        limiar_epidemico(Grafo.de_arestas([(0, 1)], direcionado=True))


# SIR: uma rodada


def test_sir_beta_zero_so_atinge_a_origem():
    assert simular_sir(completo(8), 3, beta=0.0, semente=1) == {3}


def test_sir_beta_um_atinge_a_componente_inteira():
    g = caminho(10)
    assert simular_sir(g, 0, beta=1.0, semente=1) == set(g.nos())


def test_sir_nao_passa_da_componente():
    g = Grafo.de_arestas([(0, 1), (1, 2), (10, 11)])
    assert simular_sir(g, 0, beta=1.0, semente=1) == {0, 1, 2}


def test_sir_gamma_menor_que_um_ainda_atinge_tudo_com_beta_um():
    assert simular_sir(caminho(6), 0, beta=1.0, gamma=0.3, semente=5) == set(range(6))


def test_sir_varias_origens():
    g = Grafo.de_arestas([(0, 1), (2, 3), (4, 5)])
    assert simular_sir(g, [0, 4], beta=1.0, semente=1) == {0, 1, 4, 5}


def test_sir_origem_que_e_uma_tupla():
    # Uma tupla que é nó do grafo vale como origem única, e não como lista de origens.
    g = Grafo.de_arestas([(("a", 1), ("b", 2))])
    assert simular_sir(g, ("a", 1), beta=1.0, semente=1) == {("a", 1), ("b", 2)}


def test_sir_direcionado_segue_o_sentido():
    g = Grafo.de_arestas([(0, 1), (1, 2)], direcionado=True)
    assert simular_sir(g, 2, beta=1.0, semente=1) == {2}
    assert simular_sir(g, 0, beta=1.0, semente=1) == {0, 1, 2}


def test_sir_mesma_semente_mesmo_resultado():
    g = completo(20)
    assert simular_sir(g, 0, beta=0.1, semente=42) == simular_sir(g, 0, beta=0.1, semente=42)


def test_sir_nao_altera_o_grafo():
    g = estrela(6)
    antes = sorted(g.arestas())
    simular_sir(g, 0, beta=0.5, semente=1)
    poder_de_espalhamento(g, beta=0.5, rodadas=5, semente=1)
    assert sorted(g.arestas()) == antes


@pytest.mark.parametrize("beta, gamma", [(-0.1, 1.0), (1.5, 1.0), (0.5, 0.0), (0.5, 1.2)])
def test_sir_parametros_invalidos(beta, gamma):
    with pytest.raises(ValueError):
        simular_sir(completo(4), 0, beta=beta, gamma=gamma)


def test_sir_origem_fora_do_grafo():
    with pytest.raises(ValueError):
        simular_sir(completo(4), 99, beta=0.5)


def test_sir_sem_origens():
    with pytest.raises(ValueError):
        simular_sir(completo(4), [], beta=0.5)


# Alcance médio rho(v) por Monte Carlo: valores esperados calculados à mão


def test_alcance_beta_zero():
    # Só a origem é atingida: rho = 1/n para todo nó.
    assert poder_de_espalhamento(completo(5), beta=0.0, rodadas=3, semente=1) == pytest.approx(
        {v: 1 / 5 for v in range(5)}
    )


def test_alcance_beta_um():
    # Cada nó atinge a própria componente inteira.
    g = Grafo.de_arestas([(0, 1), (1, 2), (3, 4)])
    esperado = {0: 3 / 5, 1: 3 / 5, 2: 3 / 5, 3: 2 / 5, 4: 2 / 5}
    assert poder_de_espalhamento(g, beta=1.0, rodadas=3, semente=1) == pytest.approx(esperado)


def test_alcance_aresta_unica():
    # A origem atinge o vizinho com chance beta: rho = (1 + beta) / 2 = 0,65 com beta = 0,3.
    g = Grafo.de_arestas([(0, 1)])
    rho = poder_de_espalhamento(g, beta=0.3, rodadas=20_000, semente=7)
    assert rho[0] == pytest.approx(0.65, abs=0.01)
    assert rho[1] == pytest.approx(0.65, abs=0.01)


def test_alcance_estrela():
    # Do centro: 1 + beta(n - 1) atingidos. De uma folha: 1 + beta(1 + beta(n - 2)).
    n, beta = 10, 0.4
    rho = poder_de_espalhamento(estrela(n), beta=beta, rodadas=20_000, semente=3, origens=[0, 1])
    assert rho[0] == pytest.approx((1 + beta * (n - 1)) / n, abs=0.01)
    assert rho[1] == pytest.approx((1 + beta * (1 + beta * (n - 2))) / n, abs=0.01)


def test_alcance_gamma_menor_que_um():
    # Aresta única: a cada passo a origem falha com chance 1 - beta e se recupera com gamma.
    # P(nunca transmitir) = (1 - beta)gamma / (1 - (1 - beta)(1 - gamma)) = 0,4/0,6 = 2/3,
    # com beta = 0,2 e gamma = 0,5. Logo rho = (1 + 1/3) / 2.
    g = Grafo.de_arestas([(0, 1)])
    rho = poder_de_espalhamento(g, beta=0.2, gamma=0.5, rodadas=20_000, semente=11, origens=[0])
    assert rho[0] == pytest.approx((1 + 1 / 3) / 2, abs=0.01)


def test_alcance_so_das_origens_pedidas():
    rho = poder_de_espalhamento(completo(6), beta=0.2, rodadas=5, semente=1, origens=[0, 3])
    assert set(rho) == {0, 3}


def test_alcance_repete_com_a_mesma_semente():
    g = completo(12)
    assert poder_de_espalhamento(g, 0.2, rodadas=10, semente=9) == poder_de_espalhamento(g, 0.2, rodadas=10, semente=9)


def test_alcance_rodadas_invalidas():
    with pytest.raises(ValueError):
        poder_de_espalhamento(completo(3), 0.5, rodadas=0)


def test_alcance_origem_fora_do_grafo():
    with pytest.raises(ValueError):
        poder_de_espalhamento(completo(3), 0.5, origens=[99])


# Karate Club


def test_karate_beta_um_atinge_todos():
    g = carregar_karate()
    assert simular_sir(g, 0, beta=1.0, semente=1) == set(g.nos())


def test_karate_lideres_espalham_mais():
    # Os dois líderes (0 e 33) têm os maiores graus e, com beta perto do limiar, devem
    # alcançar mais que o nó 11, que tem grau 1.
    g = carregar_karate()
    beta = 1.5 * limiar_epidemico(g)
    rho = poder_de_espalhamento(g, beta, rodadas=2_000, semente=1, origens=[0, 33, 11])
    assert rho[0] > rho[11]
    assert rho[33] > rho[11]


# Invariantes em grafos aleatórios


@st.composite
def grafos(draw):
    n = draw(st.integers(min_value=1, max_value=12))
    pares = [(i, j) for i in range(n) for j in range(i + 1, n)]
    arestas = draw(st.lists(st.sampled_from(pares), unique=True) if pares else st.just([]))
    g = Grafo.de_arestas(arestas)
    for v in range(n):
        g.adicionar_no(v)
    return g


@settings(max_examples=60, deadline=None)
@given(grafos())
def test_beta_um_atinge_a_componente(g):
    n = g.numero_de_nos()
    componente = {v: c for c in componentes_conexas(g) for v in c}
    rho = poder_de_espalhamento(g, beta=1.0, rodadas=2, semente=0)
    assert rho == pytest.approx({v: len(componente[v]) / n for v in g.nos()})


@settings(max_examples=60, deadline=None)
@given(grafos(), st.floats(min_value=0.0, max_value=1.0), st.integers(min_value=0, max_value=10**6))
def test_atingidos_ficam_na_componente_da_origem(g, beta, semente):
    componente = {v: c for c in componentes_conexas(g) for v in c}
    atingidos = simular_sir(g, 0, beta=beta, semente=semente)
    assert 0 in atingidos
    assert atingidos <= componente[0]


# Twitch PT: valor da descrição do problema (Etapa 1)


@precisa_twitch
def test_twitch_limiar():
    # <k> ≈ 32,74 e <k²> ≈ 4.189,7.
    g, _ = carregar_twitch_ptbr()
    assert limiar_epidemico(g) == pytest.approx(0.007876, abs=1e-6)


@precisa_twitch
def test_twitch_hub_espalha_mais_que_folha():
    # O nó 127 tem o maior grau (767); o 13 tem grau 1. Com beta = 0,012 (≈ 1,5 beta_c),
    # o surto que começa no hub atinge mais. Só duas origens, para o teste ser rápido.
    g, _ = carregar_twitch_ptbr()
    rho = poder_de_espalhamento(g, beta=0.012, rodadas=200, semente=1, origens=[127, 13])
    assert rho[127] > rho[13]
