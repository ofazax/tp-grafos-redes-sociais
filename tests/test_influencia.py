"""Testes do limiar epidêmico, da simulação SIR, do tau de Kendall e das tabelas do experimento:
casos de resposta conhecida, valores esperados calculados à mão, Karate Club, invariantes e Twitch PT."""

import csv
import itertools
import math
from pathlib import Path

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from redes.aplicacao.experimento import (
    CENTRALIDADES,
    COLUNAS,
    COLUNAS_CONCORDANCIA,
    centralidades_da_rede,
    salvar_concordancia_csv,
    salvar_csv,
    tabela_de_alcance,
    tabela_de_concordancia,
)
from redes.aplicacao.influencia import (
    comparar_rankings,
    limiar_epidemico,
    poder_de_espalhamento,
    simular_sir,
    tau_de_kendall,
)
from redes.leitores import RAIZ, carregar_twitch_ptbr
from redes.metricas.caminhos import componentes_conexas
from redes.metricas.grau import centralidade_de_grau
from redes.metricas.nucleo_k import numero_de_nucleo
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


def valores(*lista):
    # Dicionário nó -> valor, com os nós 0, 1, 2, ... na ordem da lista.
    return dict(enumerate(lista))


def tau_b_ingenuo(x, y):
    # Definição direta, comparando os n(n-1)/2 pares: serve de referência para o tau_de_kendall.
    concordantes = discordantes = so_em_x = so_em_y = 0
    for a, b in itertools.combinations([v for v in x if v in y], 2):
        dx = (x[a] > x[b]) - (x[a] < x[b])
        dy = (y[a] > y[b]) - (y[a] < y[b])
        if dx == 0 and dy == 0:
            continue
        if dx == 0:
            so_em_x += 1
        elif dy == 0:
            so_em_y += 1
        elif dx == dy:
            concordantes += 1
        else:
            discordantes += 1
    total = concordantes + discordantes
    denominador = math.sqrt((total + so_em_x) * (total + so_em_y))
    return (concordantes - discordantes) / denominador if denominador else math.nan


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


# Tau-b de Kendall


def test_tau_rankings_iguais():
    assert tau_de_kendall(valores(1, 2, 3, 4, 5), valores(10, 20, 30, 40, 50)) == pytest.approx(1.0)


def test_tau_rankings_invertidos():
    assert tau_de_kendall(valores(1, 2, 3, 4, 5), valores(50, 40, 30, 20, 10)) == pytest.approx(-1.0)


def test_tau_com_empate():
    # Pares: 5 concordantes, nenhum discordante e 1 empatado só em x (nós 1 e 2).
    # tau_b = 5 / sqrt((5 + 1) * (5 + 0)) = 5 / sqrt(30).
    assert tau_de_kendall(valores(1, 2, 2, 3), valores(1, 2, 3, 4)) == pytest.approx(5 / math.sqrt(30))


def test_tau_empate_dos_dois_lados_nao_conta():
    # Os nós 0 e 1 empatam em x e em y: o par sai das contas, e o resto está na mesma ordem.
    assert tau_de_kendall(valores(1, 1, 2), valores(5, 5, 9)) == pytest.approx(1.0)


def test_tau_exemplo_da_documentacao_do_scipy():
    # Exemplo de scipy.stats.kendalltau (tau-b), com empates nos dois lados.
    assert tau_de_kendall(valores(12, 2, 1, 12, 2), valores(1, 4, 7, 1, 0)) == pytest.approx(-0.47140452079103173)


def test_tau_so_olha_a_ordem():
    # Trocar os valores por outros na mesma ordem (aqui, ao cubo) não muda o tau.
    x, y = valores(3, 1, 4, 1, 5, 9, 2), valores(2, 7, 1, 8, 2, 8, 1)
    assert tau_de_kendall(x, y) == pytest.approx(tau_de_kendall({v: c**3 for v, c in x.items()}, y))


def test_tau_usa_so_os_nos_em_comum():
    assert tau_de_kendall({0: 1, 1: 2, 2: 3, 9: 100}, {0: 1, 1: 2, 2: 3, 8: -5}) == pytest.approx(1.0)


def test_tau_sem_ordem_e_nan():
    # Todos iguais em x: não há ordem para comparar.
    assert math.isnan(tau_de_kendall(valores(7, 7, 7), valores(1, 2, 3)))


def test_tau_menos_de_dois_nos_e_nan():
    assert math.isnan(tau_de_kendall({0: 1}, {0: 1}))
    assert math.isnan(tau_de_kendall({}, {}))


@settings(max_examples=200, deadline=None)
@given(
    st.lists(st.tuples(st.integers(0, 4), st.integers(0, 4)), min_size=2, max_size=30)
)
def test_tau_igual_a_definicao_direta(pares):
    # Valores de 0 a 4 em até 30 nós: muitos empates, o caso difícil do tau-b.
    x = {i: a for i, (a, _) in enumerate(pares)}
    y = {i: b for i, (_, b) in enumerate(pares)}
    esperado = tau_b_ingenuo(x, y)
    obtido = tau_de_kendall(x, y)
    if math.isnan(esperado):
        assert math.isnan(obtido)
    else:
        assert obtido == pytest.approx(esperado)
        assert obtido == pytest.approx(tau_de_kendall(y, x))  # simétrico
        assert -1.0 <= obtido <= 1.0


def test_comparar_rankings():
    x = valores(1, 2, 3, 4)
    tabela = comparar_rankings({"a": x, "b": valores(4, 3, 2, 1)}, {"r": x, "s": valores(1, 2, 2, 3)})
    assert set(tabela) == {"a", "b"}
    assert tabela["a"]["r"] == pytest.approx(1.0)
    assert tabela["b"]["r"] == pytest.approx(-1.0)
    assert tabela["a"]["s"] == pytest.approx(5 / math.sqrt(30))
    assert tabela["b"]["s"] == pytest.approx(-5 / math.sqrt(30))


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


# Tabela de alcance (experimento.py)


def test_tabela_ordenada_pelo_alcance():
    # Com beta = 1, cada nó atinge a própria componente: os 3 nós do triângulo vêm antes
    # dos 2 da aresta solta, e o nó isolado fica por último.
    g = Grafo.de_arestas([(0, 1), (1, 2), (2, 0), (3, 4)])
    g.adicionar_no(5)
    linhas = tabela_de_alcance(g, {}, beta=1.0, rodadas=2, semente=1)
    assert [linha["no"] for linha in linhas] == [0, 1, 2, 3, 4, 5]
    assert [linha["posicao"] for linha in linhas] == [1, 2, 3, 4, 5, 6]
    assert linhas[0]["alcance"] == pytest.approx(3 / 6)
    assert linhas[0]["atingidos_medios"] == pytest.approx(3)
    assert linhas[-1]["alcance"] == pytest.approx(1 / 6)


def test_tabela_desempata_pelo_grau_e_depois_pelo_no():
    # Com beta = 0, todos têm alcance 1/n: vale o grau (centro 0 primeiro) e depois o nó,
    # em ordem numérica (2 antes de 10).
    g = Grafo.de_arestas([(0, 10), (0, 2), (0, 1)])
    linhas = tabela_de_alcance(g, {}, beta=0.0, rodadas=1, semente=1)
    assert [linha["no"] for linha in linhas] == [0, 1, 2, 10]


def test_tabela_traz_grau_nucleo_e_atributos():
    g = completo(4)
    g.adicionar_aresta(3, 4)
    atributos = {0: {"visualizacoes": 100, "parceiro": True}}
    linhas = {linha["no"]: linha for linha in tabela_de_alcance(g, atributos, beta=0.5, rodadas=5, semente=1)}
    assert linhas[0]["grau"] == 3 and linhas[0]["nucleo"] == 3
    assert linhas[4]["grau"] == 1 and linhas[4]["nucleo"] == 1
    assert linhas[0]["visualizacoes"] == 100 and linhas[0]["parceiro"] is True
    assert linhas[4]["visualizacoes"] == "" and linhas[4]["parceiro"] == ""


def test_tabela_usa_o_mesmo_alcance_do_poder_de_espalhamento():
    g = carregar_karate()
    linhas = tabela_de_alcance(g, {}, beta=0.2, rodadas=20, semente=5)
    rho = poder_de_espalhamento(g, 0.2, rodadas=20, semente=5)
    assert {linha["no"]: linha["alcance"] for linha in linhas} == rho


def test_salvar_csv(tmp_path):
    g = estrela(4)
    linhas = tabela_de_alcance(g, {0: {"visualizacoes": 7, "parceiro": False}}, beta=1.0, rodadas=1, semente=1)
    caminho = tmp_path / "sub" / "alcance.csv"
    salvar_csv(linhas, caminho)
    with open(caminho, encoding="utf-8", newline="") as arquivo:
        lidas = list(csv.DictReader(arquivo))
    assert list(lidas[0]) == COLUNAS
    assert len(lidas) == 4
    assert lidas[0]["no"] == "0" and lidas[0]["alcance"] == "1.000000" and lidas[0]["visualizacoes"] == "7"


# Tabela de concordância (experimento.py)


def test_centralidades_da_rede_tem_as_seis():
    c = centralidades_da_rede(carregar_karate())
    assert list(c) == ["grau", "proximidade", "harmonica", "intermediacao", "pagerank", "nucleo"]
    assert list(c) == list(CENTRALIDADES)
    assert all(len(valores_por_no) == 34 for valores_por_no in c.values())


def test_tabela_de_concordancia():
    x = valores(1, 2, 3, 4)
    linhas = tabela_de_concordancia({"a": x, "b": valores(4, 3, 2, 1)}, alcance=x, visualizacoes=valores(1, 2, 2, 3))
    assert [linha["centralidade"] for linha in linhas] == ["a", "b"]
    assert linhas[0]["tau_alcance"] == pytest.approx(1.0)
    assert linhas[1]["tau_alcance"] == pytest.approx(-1.0)
    assert linhas[0]["tau_visualizacoes"] == pytest.approx(5 / math.sqrt(30))


def test_salvar_concordancia_csv(tmp_path):
    linhas = [{"centralidade": "grau", "tau_alcance": 0.70331, "tau_visualizacoes": 0.43256}]
    caminho = tmp_path / "concordancia.csv"
    salvar_concordancia_csv(linhas, caminho)
    with open(caminho, encoding="utf-8", newline="") as arquivo:
        lidas = list(csv.DictReader(arquivo))
    assert list(lidas[0]) == COLUNAS_CONCORDANCIA
    assert lidas == [{"centralidade": "grau", "tau_alcance": "0.7033", "tau_visualizacoes": "0.4326"}]


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


@precisa_twitch
def test_twitch_tabela_de_alcance():
    # Uma rodada por nó, só para conferir a tabela inteira (a de 100 rodadas leva ~20 s).
    g, atributos = carregar_twitch_ptbr()
    linhas = tabela_de_alcance(g, atributos, beta=0.012, rodadas=1, semente=1)
    assert len(linhas) == 1912
    assert all(linha["visualizacoes"] != "" for linha in linhas)
    assert max(linha["nucleo"] for linha in linhas) == 37


@precisa_twitch
def test_twitch_tau_com_as_visualizacoes():
    # Valores de referência das notas da Frente 5 (calculados com o NetworkX): grau ≈ 0,43 e núcleo ≈ 0,40.
    g, atributos = carregar_twitch_ptbr()
    visualizacoes = {v: dados["visualizacoes"] for v, dados in atributos.items()}
    assert tau_de_kendall(centralidade_de_grau(g), visualizacoes) == pytest.approx(0.4326, abs=1e-4)
    assert tau_de_kendall(numero_de_nucleo(g), visualizacoes) == pytest.approx(0.4034, abs=1e-4)
