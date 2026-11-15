"""Testes das centralidades de proximidade: closeness e harmônica.

Casos pequenos de resposta conhecida, as bases reais (Karate Club, Twitch PT e
Network of Thrones, lidas pelos leitores da Frente 1) e invariantes com Hypothesis.
Os valores de referência vêm do documento de tarefas e do NetworkX 3.7.
"""

# pytest.approx compara números decimais com tolerância.
import pytest

# Hypothesis sorteia grafos aleatórios para testar propriedades gerais.
from hypothesis import given
from hypothesis import strategies as st

# Leitores do Brunno (Frente 1): cada um devolve a base já como Grafo.
from redes.leitores import RAIZ, carregar_karate, carregar_thrones, carregar_twitch_ptbr

# A centralidade de grau entra para comparar os rankings no Karate.
from redes.metricas.grau import centralidade_de_grau

# As funções que estão sendo testadas.
from redes.metricas.proximidade import harmonica, proximidade
from redes.nucleo import Grafo


# Funções auxiliares (não começam com "test_", então o pytest não as roda como teste).

def precisa(caminho):
    """Pula o teste quando a base não foi baixada (dados/brutos/ fica fora do Git)."""
    return pytest.mark.skipif(not (RAIZ / caminho).exists(), reason=f"baixe {caminho} (veja dados/README.md)")


TWITCH = "dados/brutos/twitch/PTBR/musae_PTBR_edges.csv"
THRONES = "dados/brutos/asoiaf-book3-edges.csv"


def caminho(n):
    """Fila de n nós: 0 - 1 - 2 - ... - (n-1)."""
    return Grafo.de_arestas((i, i + 1) for i in range(n - 1))


def estrela(n):
    """Nó 0 no centro, ligado aos outros n - 1 nós."""
    return Grafo.de_arestas((0, i) for i in range(1, n))


def completo(n):
    """Grafo completo: todo nó ligado a todos os outros."""
    return Grafo.de_arestas((i, j) for i in range(n) for j in range(i + 1, n))


def mais_central(valores):
    """Nó com o maior valor num dicionário {nó: valor}."""
    return max(valores, key=valores.get)


# ---------------------------------------------------------------------------
# Closeness: casos pequenos, de resposta conhecida
# ---------------------------------------------------------------------------

def test_proximidade_grafo_vazio():
    # Sem nós, não há valor para devolver.
    assert proximidade(Grafo()) == {}


def test_proximidade_no_isolado():
    # Um nó sozinho não está perto de ninguém: 0.0, sem divisão por zero.
    g = Grafo()
    g.adicionar_no("a")
    assert proximidade(g) == {"a": 0.0}


def test_proximidade_completo():
    # Todo nó é vizinho dos outros 4: soma das distâncias = 4, então (5 - 1) / 4 = 1.0, o valor máximo.
    assert proximidade(completo(5)) == {v: 1.0 for v in range(5)}


def test_proximidade_estrela():
    # Centro 0 e 4 pontas.
    c = proximidade(estrela(5))

    # O centro está a 1 passo de todos: 4 / 4 = 1.0.
    assert c[0] == 1.0

    # Uma ponta está a 1 passo do centro e a 2 das outras 3 pontas: soma = 1 + 2 + 2 + 2 = 7, então 4 / 7.
    assert all(c[i] == pytest.approx(4 / 7) for i in range(1, 5))


def test_proximidade_caminho():
    # Fila 0 - 1 - 2.
    c = proximidade(caminho(3))

    # O do meio está a 1 passo dos dois: 2 / 2 = 1.0.
    assert c[1] == 1.0

    # Cada ponta está a 1 passo do meio e a 2 da outra ponta: 2 / 3.
    assert c[0] == pytest.approx(2 / 3)
    assert c[2] == pytest.approx(2 / 3)


def test_proximidade_desconexo_usa_a_correcao():
    # Dois pedaços: 0 - 1 - 2 e 3 - 4. São 5 nós, então n - 1 = 4.
    g = Grafo.de_arestas([(0, 1), (1, 2), (3, 4)])
    c = proximidade(g)

    # O nó 1 alcança 2 nós, os dois a distância 1: (2 / 4) * (2 / 2) = 0,5.
    assert c[1] == pytest.approx(0.5)

    # O nó 0 alcança 2 nós, com distâncias 1 e 2: (2 / 4) * (2 / 3) = 1/3.
    assert c[0] == pytest.approx(1 / 3)

    # O nó 3 alcança só 1 nó, a distância 1: (1 / 4) * (1 / 1) = 0,25.
    # Sem a correção ele teria 1.0, o máximo, mesmo estando num pedaço de dois nós.
    assert c[3] == pytest.approx(0.25)


def test_proximidade_direcionado():
    # 1 -> 2 -> 3: usa as distâncias de cada nó até os outros, no sentido das setas.
    c = proximidade(Grafo.de_arestas([(1, 2), (2, 3)], direcionado=True))

    # O 1 alcança 2 nós, com distâncias 1 e 2: (2 / 2) * (2 / 3) = 2/3.
    assert c[1] == pytest.approx(2 / 3)

    # O 2 alcança só o 3: (1 / 2) * (1 / 1) = 0,5.
    assert c[2] == pytest.approx(0.5)

    # Do 3 não sai nenhuma seta: 0.0.
    assert c[3] == 0.0


# ---------------------------------------------------------------------------
# Harmônica: casos pequenos, de resposta conhecida
# ---------------------------------------------------------------------------

def test_harmonica_grafo_vazio():
    assert harmonica(Grafo()) == {}


def test_harmonica_no_isolado():
    g = Grafo()
    g.adicionar_no("a")
    assert harmonica(g) == {"a": 0.0}


def test_harmonica_completo():
    # Cada um dos outros 4 nós é vizinho e soma 1: total 4.0, que é o máximo (n - 1).
    assert harmonica(completo(5)) == {v: 4.0 for v in range(5)}


def test_harmonica_estrela():
    h = harmonica(estrela(5))

    # O centro tem 4 vizinhos: 4 * 1 = 4.0.
    assert h[0] == 4.0

    # Uma ponta tem 1 vizinho (soma 1) e 3 nós a dois passos (cada um soma 1/2): 1 + 1,5 = 2,5.
    assert all(h[i] == pytest.approx(2.5) for i in range(1, 5))


def test_harmonica_caminho():
    h = harmonica(caminho(3))

    # O do meio tem 2 vizinhos: 2.0. Cada ponta tem 1 vizinho e 1 nó a dois passos: 1 + 1/2 = 1,5.
    assert h[1] == 2.0
    assert h[0] == pytest.approx(1.5)
    assert h[2] == pytest.approx(1.5)


def test_harmonica_desconexo_sem_correcao():
    # Dois pedaços: 0 - 1 - 2 e 3 - 4. Nó não alcançado soma 0, sem tratamento especial.
    h = harmonica(Grafo.de_arestas([(0, 1), (1, 2), (3, 4)]))

    # O nó 1 tem 2 vizinhos: 2.0. O nó 0 tem 1 vizinho e 1 nó a dois passos: 1,5.
    assert h[1] == 2.0
    assert h[0] == pytest.approx(1.5)

    # Os nós 3 e 4 só alcançam um ao outro: 1.0.
    assert h[3] == 1.0
    assert h[4] == 1.0


def test_harmonica_direcionado():
    # 1 -> 2 -> 3: o 1 alcança o 2 (soma 1) e o 3 (soma 1/2); do 3 não sai nada.
    h = harmonica(Grafo.de_arestas([(1, 2), (2, 3)], direcionado=True))
    assert h == {1: 1.5, 2: 1.0, 3: 0.0}


def test_nao_alteram_o_grafo():
    # Regra do grupo: o algoritmo não pode modificar o grafo que recebe.
    g = estrela(6)
    proximidade(g)
    harmonica(g)
    assert g.numero_de_nos() == 6
    assert g.numero_de_arestas() == 5


# ---------------------------------------------------------------------------
# Karate Club (referências do documento de tarefas)
# ---------------------------------------------------------------------------

def test_karate_proximidade():
    c = proximidade(carregar_karate())

    # Um valor para cada um dos 34 membros.
    assert len(c) == 34

    # Valores de referência dos três nós mais centrais.
    assert c[0] == pytest.approx(0.569, abs=1e-3)
    assert c[2] == pytest.approx(0.5593, abs=1e-4)
    assert c[33] == pytest.approx(0.55, abs=1e-4)


def test_karate_harmonica():
    h = harmonica(carregar_karate())
    assert h[33] == pytest.approx(23.25)
    assert h[0] == pytest.approx(23.167, abs=1e-3)


def test_karate_cada_metrica_aponta_um_lider():
    g = carregar_karate()

    # Pelo grau e pela harmônica, o mais central é o administrador (33), que tem mais amigos diretos.
    assert mais_central(centralidade_de_grau(g)) == 33
    assert mais_central(harmonica(g)) == 33

    # Pela closeness é o instrutor (0): tem um amigo a menos, mas está mais perto do resto do clube.
    assert mais_central(proximidade(g)) == 0


# ---------------------------------------------------------------------------
# Network of Thrones e Twitch PT (os testes pulam se a base não estiver em dados/brutos/)
# ---------------------------------------------------------------------------

@precisa(THRONES)
def test_thrones_proximidade_e_harmonica():
    g = carregar_thrones()

    # Referência do NetworkX 3.7. As distâncias contam arestas; os pesos não entram.
    c = proximidade(g)
    assert mais_central(c) == "Joffrey-Baratheon"
    assert c["Joffrey-Baratheon"] == pytest.approx(0.4741, abs=1e-4)
    assert c["Tyrion-Lannister"] == pytest.approx(0.4576, abs=1e-4)

    h = harmonica(g)
    assert mais_central(h) == "Joffrey-Baratheon"
    assert h["Joffrey-Baratheon"] == pytest.approx(163.083, abs=1e-3)


# Este teste faz uma BFS a partir de cada um dos 1.912 nós da Twitch PT: leva alguns segundos.

@precisa(TWITCH)
def test_twitch_proximidade():
    g, _ = carregar_twitch_ptbr()
    c = proximidade(g)
    assert len(c) == 1912

    # Referência do documento de tarefas: a closeness máxima é a do nó 127, 0,6009.
    assert mais_central(c) == 127
    assert c[127] == pytest.approx(0.6009, abs=1e-4)

    # Referência do NetworkX 3.7: o segundo colocado e o menor valor da rede.
    assert c[1297] == pytest.approx(0.5684, abs=1e-4)
    assert min(c.values()) == pytest.approx(0.2048, abs=1e-4)


# ---------------------------------------------------------------------------
# Invariantes, em grafos aleatórios (Hypothesis)
# ---------------------------------------------------------------------------

# Receita do sorteio: lista de até 100 arestas entre nós de 0 a 20.
listas_de_arestas = st.lists(st.tuples(st.integers(0, 20), st.integers(0, 20)), max_size=100)


@given(listas_de_arestas)
def test_um_valor_por_no(lista):
    g = Grafo.de_arestas(lista)

    # Regra do grupo: toda métrica devolve um valor para cada nó, sem faltar nem sobrar.
    assert set(proximidade(g)) == set(g.nos())
    assert set(harmonica(g)) == set(g.nos())


@given(listas_de_arestas)
def test_proximidade_fica_entre_0_e_1(lista):
    g = Grafo.de_arestas(lista)

    # 0 é o nó que não alcança ninguém; 1 é o nó vizinho de todos. O 1e-12 cobre o arredondamento.
    assert all(0.0 <= valor <= 1.0 + 1e-12 for valor in proximidade(g).values())


@given(listas_de_arestas)
def test_harmonica_fica_entre_os_vizinhos_e_n_menos_1(lista):
    g = Grafo.de_arestas(lista)
    n = g.numero_de_nos()
    h = harmonica(g)

    for v in g.nos():
        # Cada vizinho soma exatamente 1 (o set tira um eventual laço do nó com ele mesmo).
        vizinhos = len(set(g.vizinhos(v)) - {v})
        assert h[v] >= vizinhos

        # Cada um dos outros n - 1 nós soma no máximo 1.
        assert h[v] <= n - 1 + 1e-12


@given(listas_de_arestas)
def test_vizinho_de_todos_tem_valor_maximo(lista):
    g = Grafo.de_arestas(lista)
    n = g.numero_de_nos()
    c = proximidade(g)
    h = harmonica(g)

    for v in g.nos():
        # Se v é vizinho de todos os outros, as duas centralidades batem no máximo.
        if len(set(g.vizinhos(v)) - {v}) == n - 1 and n > 1:
            assert c[v] == pytest.approx(1.0)
            assert h[v] == pytest.approx(n - 1)