"""Testes de caminhos e conectividade: BFS, DFS, componentes conexas e Dijkstra.

Casos pequenos de resposta conhecida, as bases reais (Karate Club, Twitch PT e
Network of Thrones, lidas pelos leitores da Frente 1) e invariantes com Hypothesis.
Os valores de referência das bases foram calculados com o NetworkX 3.7.
"""

# pytest.raises confere que uma função lança o erro esperado; pytest.approx compara com tolerância.
import pytest

# Hypothesis sorteia grafos aleatórios para testar propriedades gerais.
from hypothesis import given
from hypothesis import strategies as st

# Leitores do Brunno (Frente 1): cada um devolve a base já como Grafo.
from redes.leitores import RAIZ, carregar_karate, carregar_thrones, carregar_twitch_ptbr

# As funções que estão sendo testadas.
from redes.metricas.caminhos import bfs, componentes_conexas, dijkstra, ordem_dfs
from redes.nucleo import Grafo


# Funções auxiliares (não começam com "test_", então o pytest não as roda como teste).

def precisa(caminho):
    """Pula o teste quando a base não foi baixada (dados/brutos/ fica fora do Git)."""
    return pytest.mark.skipif(not (RAIZ / caminho).exists(), reason=f"baixe {caminho} (veja dados/README.md)")


# Arquivos que precisam existir para os testes da Twitch PT e da Network of Thrones rodarem.
TWITCH = "dados/brutos/twitch/PTBR/musae_PTBR_edges.csv"
THRONES = "dados/brutos/asoiaf-book3-edges.csv"


def caminho(n):
    """Fila de n nós: 0 - 1 - 2 - ... - (n-1)."""
    return Grafo.de_arestas((i, i + 1) for i in range(n - 1))


def ciclo(n):
    """Roda de n nós: 0 - 1 - ... - (n-1) - 0. O % n liga o último de volta ao 0."""
    return Grafo.de_arestas((i, (i + 1) % n) for i in range(n))


def estrela(n):
    """Nó 0 no centro, ligado aos outros n - 1 nós."""
    return Grafo.de_arestas((0, i) for i in range(1, n))


def contar_por_distancia(distancia):
    """Transforma {nó: distância} em {distância: quantidade de nós}."""
    contagem = {}
    for d in distancia.values():
        contagem[d] = contagem.get(d, 0) + 1
    return contagem


# ---------------------------------------------------------------------------
# BFS: casos pequenos, de resposta conhecida
# ---------------------------------------------------------------------------

def test_bfs_no_isolado():
    # Um nó sozinho só alcança ele mesmo, a distância 0.
    g = Grafo()
    g.adicionar_no("a")
    assert bfs(g, "a") == {"a": 0}


def test_bfs_caminho():
    # Fila 0 - 1 - 2 - 3 - 4.
    g = caminho(5)

    # Saindo da ponta, a distância até o nó i é o próprio i.
    assert bfs(g, 0) == {0: 0, 1: 1, 2: 2, 3: 3, 4: 4}

    # Saindo do meio, as distâncias crescem para os dois lados.
    assert bfs(g, 2) == {2: 0, 1: 1, 3: 1, 0: 2, 4: 2}


def test_bfs_estrela():
    # Estrela com centro 0 e pontas 1 a 5.
    g = estrela(6)

    # Do centro, todas as pontas estão a 1 passo.
    assert bfs(g, 0) == {0: 0, 1: 1, 2: 1, 3: 1, 4: 1, 5: 1}

    # De uma ponta, o centro está a 1 passo e as outras pontas a 2 (passando pelo centro).
    assert bfs(g, 1) == {1: 0, 0: 1, 2: 2, 3: 2, 4: 2, 5: 2}


def test_bfs_ciclo():
    # Roda de 6 nós: dá para ir pelos dois lados, e a BFS tem que pegar o lado mais curto.
    g = ciclo(6)

    # O nó 5 é vizinho do 0 (distância 1, não 5); o mais longe é o 3, do lado oposto.
    assert bfs(g, 0) == {0: 0, 1: 1, 5: 1, 2: 2, 4: 2, 3: 3}


def test_bfs_desconexo():
    # Dois pedaços separados: 0 - 1 e 2 - 3.
    g = Grafo.de_arestas([(0, 1), (2, 3)])

    # Saindo do 0, só o pedaço dele aparece; os nós 2 e 3 ficam fora do resultado.
    assert bfs(g, 0) == {0: 0, 1: 1}


def test_bfs_direcionado():
    # Arestas com sentido: 1 -> 2 -> 3.
    g = Grafo.de_arestas([(1, 2), (2, 3)], direcionado=True)

    # Do 1 dá para chegar em todos, seguindo as setas.
    assert bfs(g, 1) == {1: 0, 2: 1, 3: 2}

    # Do 3 não sai nenhuma seta: ele só alcança ele mesmo.
    assert bfs(g, 3) == {3: 0}


def test_bfs_ignora_pesos():
    # A aresta direta 0 - 2 tem peso alto, mas a BFS conta arestas, não pesos.
    g = Grafo.de_arestas([(0, 1, 1.0), (1, 2, 1.0), (0, 2, 99.0)])

    # O nó 2 está a 1 aresta do 0, mesmo com o peso 99.
    assert bfs(g, 0)[2] == 1


def test_bfs_origem_inexistente():
    g = caminho(3)

    # O "with pytest.raises(KeyError)" passa se o código de dentro lançar KeyError
    # e falha se não lançar: o nó 99 não existe, então a função tem que reclamar.
    with pytest.raises(KeyError):
        bfs(g, 99)


def test_bfs_nao_altera_o_grafo():
    # Regra do grupo: o algoritmo não pode modificar o grafo que recebe.
    g = ciclo(5)
    bfs(g, 0)
    assert g.numero_de_nos() == 5
    assert g.numero_de_arestas() == 5


# ---------------------------------------------------------------------------
# DFS: casos pequenos, de resposta conhecida
# ---------------------------------------------------------------------------

def test_dfs_no_isolado():
    g = Grafo()
    g.adicionar_no("a")
    assert ordem_dfs(g, "a") == ["a"]


def test_dfs_caminho():
    # Numa fila só existe um jeito de andar: sempre em frente.
    g = caminho(5)
    assert ordem_dfs(g, 0) == [0, 1, 2, 3, 4]


def test_dfs_vai_fundo_antes_de_voltar():
    # Árvore:      0
    #            /   \
    #           1     2
    #          / \
    #         3   4
    g = Grafo.de_arestas([(0, 1), (0, 2), (1, 3), (1, 4)])

    # A DFS desce pelo ramo do 1 inteiro (1, 3, 4) antes de visitar o 2.
    assert ordem_dfs(g, 0) == [0, 1, 3, 4, 2]

    # A BFS faria por camadas (0, depois 1 e 2, depois 3 e 4): é a diferença entre as duas.
    assert list(bfs(g, 0)) == [0, 1, 2, 3, 4]


def test_dfs_ciclo_nao_repete_no():
    # Na roda, a busca volta ao ponto de partida; não pode visitar ninguém duas vezes.
    g = ciclo(5)
    assert ordem_dfs(g, 0) == [0, 1, 2, 3, 4]


def test_dfs_desconexo():
    # Dois pedaços separados: saindo do 2, só o pedaço dele é visitado.
    g = Grafo.de_arestas([(0, 1), (2, 3)])
    assert ordem_dfs(g, 2) == [2, 3]


def test_dfs_direcionado():
    # 1 -> 2 -> 3: do 2 só dá para seguir até o 3; o 1 fica para trás.
    g = Grafo.de_arestas([(1, 2), (2, 3)], direcionado=True)
    assert ordem_dfs(g, 2) == [2, 3]


def test_dfs_caminho_longo_sem_estourar_recursao():
    # Uma DFS recursiva quebraria aqui (RecursionError), porque o Python
    # limita a recursão a cerca de 1.000 níveis. A versão com pilha aguenta.
    g = caminho(5000)
    assert len(ordem_dfs(g, 0)) == 5000


def test_dfs_origem_inexistente():
    g = caminho(3)
    with pytest.raises(KeyError):
        ordem_dfs(g, 99)


# ---------------------------------------------------------------------------
# Componentes conexas: casos pequenos, de resposta conhecida
# ---------------------------------------------------------------------------

def test_componentes_grafo_vazio():
    # Sem nós, não há nenhuma componente.
    assert componentes_conexas(Grafo()) == []


def test_componentes_no_isolado():
    # Um nó sem arestas é uma componente sozinho.
    g = Grafo()
    g.adicionar_no("a")
    assert componentes_conexas(g) == [{"a"}]


def test_componentes_grafo_conexo():
    # Na roda todo mundo alcança todo mundo: uma componente só, com os 6 nós.
    assert componentes_conexas(ciclo(6)) == [{0, 1, 2, 3, 4, 5}]


def test_componentes_desconexo():
    # Três pedaços: 0 - 1, 2 - 3 - 4 e o nó 9 isolado.
    g = Grafo.de_arestas([(0, 1), (2, 3), (3, 4)])
    g.adicionar_no(9)

    # Saem na ordem em que o primeiro nó de cada pedaço foi inserido no grafo.
    assert componentes_conexas(g) == [{0, 1}, {2, 3, 4}, {9}]


def test_componentes_direcionado_ignora_o_sentido():
    # 1 -> 2 <- 3: do 1 não dá para chegar no 3 seguindo as setas,
    # mas os três estão ligados, então formam uma componente (fracamente conexa).
    g = Grafo.de_arestas([(1, 2), (3, 2)], direcionado=True)
    assert componentes_conexas(g) == [{1, 2, 3}]


def test_componentes_nao_altera_o_grafo():
    g = Grafo.de_arestas([(0, 1), (2, 3)])
    componentes_conexas(g)
    assert g.numero_de_nos() == 4
    assert g.numero_de_arestas() == 2


# ---------------------------------------------------------------------------
# Dijkstra: casos pequenos, de resposta conhecida
# ---------------------------------------------------------------------------

def test_dijkstra_no_isolado():
    g = Grafo()
    g.adicionar_no("a")
    assert dijkstra(g, "a") == {"a": 0.0}


def test_dijkstra_soma_os_pesos():
    # Fila com pesos: 0 -(2)- 1 -(3)- 2 -(4)- 3.
    g = Grafo.de_arestas([(0, 1, 2.0), (1, 2, 3.0), (2, 3, 4.0)])

    # A distância é a soma dos pesos no caminho: 2, 2 + 3 = 5 e 2 + 3 + 4 = 9.
    assert dijkstra(g, 0) == {0: 0.0, 1: 2.0, 2: 5.0, 3: 9.0}


def test_dijkstra_prefere_o_desvio_mais_barato():
    # Triângulo: a aresta direta 0 - 2 custa 5, mas o desvio 0 - 1 - 2 custa 1 + 1 = 2.
    g = Grafo.de_arestas([(0, 1, 1.0), (1, 2, 1.0), (0, 2, 5.0)])

    # É aqui que o Dijkstra difere da BFS: ele escolhe o caminho mais barato, não o de menos arestas.
    assert dijkstra(g, 0)[2] == 2.0
    assert bfs(g, 0)[2] == 1


def test_dijkstra_sem_pesos_e_igual_a_bfs():
    # Sem peso, toda aresta vale 1.0, então a soma dos pesos é o número de arestas.
    g = ciclo(6)
    assert dijkstra(g, 0) == bfs(g, 0)


def test_dijkstra_desconexo():
    # Os nós do outro pedaço (2 e 3) não aparecem no resultado.
    g = Grafo.de_arestas([(0, 1, 2.5), (2, 3, 1.0)])
    assert dijkstra(g, 0) == {0: 0.0, 1: 2.5}


def test_dijkstra_direcionado():
    # 1 -> 2 custa 1 e 2 -> 3 custa 2; não existe caminho de volta para o 1.
    g = Grafo.de_arestas([(1, 2, 1.0), (2, 3, 2.0)], direcionado=True)
    assert dijkstra(g, 1) == {1: 0.0, 2: 1.0, 3: 3.0}
    assert dijkstra(g, 3) == {3: 0.0}


def test_dijkstra_com_funcao_de_distancia():
    # Pesos como "número de interações": a - b interagem 4 vezes, b - c 2 vezes e a - c 1 vez.
    g = Grafo.de_arestas([("a", "b", 4.0), ("b", "c", 2.0), ("a", "c", 1.0)])

    # Com distancia = 1 / peso, quem interage mais fica mais perto.
    d = dijkstra(g, "a", distancia=lambda peso: 1 / peso)

    # a - b: 1/4 = 0,25.
    assert d["b"] == pytest.approx(0.25)

    # a - c direto custaria 1/1 = 1,0; passando por b custa 1/4 + 1/2 = 0,75, que é menor.
    assert d["c"] == pytest.approx(0.75)


def test_dijkstra_resultado_em_ordem_crescente():
    g = Grafo.de_arestas([(0, 1, 7.0), (0, 2, 1.0), (2, 3, 2.0), (3, 1, 1.0)])

    # Os nós entram no resultado do mais próximo para o mais distante.
    assert list(dijkstra(g, 0).items()) == [(0, 0.0), (2, 1.0), (3, 3.0), (1, 4.0)]


def test_dijkstra_nos_de_tipos_diferentes():
    # Um nó inteiro e um nó texto à mesma distância: o heap não pode tentar comparar 1 com "x".
    g = Grafo.de_arestas([(0, 1, 1.0), (0, "x", 1.0)])
    assert dijkstra(g, 0) == {0: 0.0, 1: 1.0, "x": 1.0}


def test_dijkstra_peso_negativo():
    # O Dijkstra só é correto sem comprimentos negativos; a função avisa em vez de errar calada.
    g = Grafo.de_arestas([(0, 1, -1.0)])
    with pytest.raises(ValueError):
        dijkstra(g, 0)


def test_dijkstra_origem_inexistente():
    g = caminho(3)
    with pytest.raises(KeyError):
        dijkstra(g, 99)


def test_dijkstra_nao_altera_o_grafo():
    g = Grafo.de_arestas([(0, 1, 2.0), (1, 2, 3.0)])
    dijkstra(g, 0)
    assert g.numero_de_arestas() == 2
    assert g.peso(0, 1) == 2.0


# ---------------------------------------------------------------------------
# Karate Club (34 nós, 78 arestas, sem peso): já vem no repositório
# ---------------------------------------------------------------------------

def test_karate_bfs_a_partir_do_no_0():
    g = carregar_karate()
    distancia = bfs(g, 0)

    # O Karate é conexo: a BFS alcança os 34 nós.
    assert len(distancia) == 34

    # 1 nó a distância 0 (o próprio instrutor), 16 vizinhos diretos, 9 a dois passos e 8 a três.
    assert contar_por_distancia(distancia) == {0: 1, 1: 16, 2: 9, 3: 8}

    # O instrutor (0) e o administrador (33) não são amigos diretos: estão a 2 passos.
    assert distancia[33] == 2


def test_karate_maior_distancia():
    g = carregar_karate()

    # O nó 16 é um dos mais afastados da rede: o mais longe dele está a 5 passos,
    # que é o diâmetro do Karate (valor do documento de tarefas).
    assert max(bfs(g, 16).values()) == 5


def test_karate_dfs():
    g = carregar_karate()
    ordem = ordem_dfs(g, 0)

    # Começa pela origem, visita os 34 nós e não repete nenhum.
    assert ordem[0] == 0
    assert len(ordem) == 34
    assert len(set(ordem)) == 34


def test_karate_uma_componente():
    g = carregar_karate()
    componentes = componentes_conexas(g)

    # O clube inteiro é um pedaço só, com os 34 membros.
    assert len(componentes) == 1
    assert componentes[0] == set(g.nos())


def test_karate_dijkstra_igual_a_bfs_de_qualquer_origem():
    g = carregar_karate()

    # O Karate não tem pesos (todos valem 1.0), então os dois algoritmos têm que concordar
    # saindo de cada um dos 34 nós.
    for origem in g.nos():
        assert dijkstra(g, origem) == bfs(g, origem)


# ---------------------------------------------------------------------------
# Twitch PT (1.912 nós, 31.299 arestas, sem peso): base principal do TP.
# Os testes pulam se a base não estiver em dados/brutos/.
# ---------------------------------------------------------------------------

@precisa(TWITCH)
def test_twitch_uma_componente():
    # O leitor devolve o grafo e os atributos dos streamers; aqui só o grafo interessa.
    g, _ = carregar_twitch_ptbr()
    componentes = componentes_conexas(g)

    # Referência do documento de tarefas: a rede inteira é uma componente só.
    assert len(componentes) == 1
    assert len(componentes[0]) == 1912


@precisa(TWITCH)
def test_twitch_bfs_a_partir_do_no_mais_conectado():
    g, _ = carregar_twitch_ptbr()

    # O nó 127 é o streamer de maior grau (767 vizinhos).
    distancia = bfs(g, 127)

    # Ele alcança os 1.912 nós, e ninguém está a mais de 4 passos dele.
    assert len(distancia) == 1912
    assert contar_por_distancia(distancia) == {0: 1, 1: 767, 2: 1020, 3: 123, 4: 1}


@precisa(TWITCH)
def test_twitch_bfs_a_partir_de_um_no_periferico():
    g, _ = carregar_twitch_ptbr()

    # O nó 0 tem só 2 vizinhos; mesmo assim, chega em toda a rede em até 5 passos.
    assert contar_por_distancia(bfs(g, 0)) == {0: 1, 1: 2, 2: 368, 3: 1428, 4: 110, 5: 3}


@precisa(TWITCH)
def test_twitch_dfs_visita_todos_sem_repetir():
    g, _ = carregar_twitch_ptbr()
    ordem = ordem_dfs(g, 127)
    assert len(ordem) == 1912
    assert len(set(ordem)) == 1912


@precisa(TWITCH)
def test_twitch_dijkstra_igual_a_bfs():
    g, _ = carregar_twitch_ptbr()

    # A Twitch PT não tem pesos, então o Dijkstra tem que dar as mesmas distâncias da BFS.
    assert dijkstra(g, 127) == bfs(g, 127)


# ---------------------------------------------------------------------------
# Network of Thrones, livro 3 (303 personagens, 1.008 arestas com peso).
# O peso é o número de interações entre dois personagens.
# Os testes pulam se a base não estiver em dados/brutos/.
# ---------------------------------------------------------------------------

@precisa(THRONES)
def test_thrones_uma_componente():
    g = carregar_thrones()
    componentes = componentes_conexas(g)
    assert len(componentes) == 1
    assert len(componentes[0]) == 303


@precisa(THRONES)
def test_thrones_dijkstra_com_o_inverso_das_interacoes():
    g = carregar_thrones()

    # Mais interações = mais perto, por isso a distância de cada aresta é 1 / peso.
    d = dijkstra(g, "Tyrion-Lannister", distancia=lambda peso: 1 / peso)

    # Tyrion alcança os 303 personagens.
    assert len(d) == 303

    # Tyrion e Sansa interagem 78 vezes: distância 1/78.
    assert d["Sansa-Stark"] == pytest.approx(1 / 78)

    # Tyrion e Jaime interagem 33 vezes: distância 1/33.
    assert d["Jaime-Lannister"] == pytest.approx(1 / 33)

    # Tyrion e Arya têm aresta direta, mas fraca (7 interações, distância 1/7 = 0,143).
    # Passando por Sansa (78 interações com Tyrion e 23 com Arya) a distância cai para 0,056.
    assert g.peso("Tyrion-Lannister", "Arya-Stark") == 7.0
    assert d["Arya-Stark"] == pytest.approx(1 / 78 + 1 / 23)
    assert d["Arya-Stark"] < 1 / 7

    # Referência do NetworkX 3.7: o personagem mais distante de Tyrion.
    mais_distante = max(d, key=d.get)
    assert mais_distante == "Galbart-Glover"
    assert d[mais_distante] == pytest.approx(0.9601, abs=1e-4)


@precisa(THRONES)
def test_thrones_bfs_conta_arestas_e_dijkstra_soma_pesos():
    g = carregar_thrones()

    # Em número de arestas, Jon Snow está a 2 passos de Tyrion...
    assert bfs(g, "Tyrion-Lannister")["Jon-Snow"] == 2

    # ...e, somando os pesos como estão (sem função de distância), o menor total é 7.
    assert dijkstra(g, "Tyrion-Lannister")["Jon-Snow"] == 7.0


# ---------------------------------------------------------------------------
# Invariantes, em grafos aleatórios (Hypothesis)
# ---------------------------------------------------------------------------

# Receita do sorteio: lista de até 200 arestas entre nós de 0 a 30.
listas_de_arestas = st.lists(st.tuples(st.integers(0, 30), st.integers(0, 30)), max_size=200)


@given(listas_de_arestas)
def test_bfs_vizinhos_diferem_no_maximo_1(lista):
    g = Grafo.de_arestas(lista)

    # Lista vazia gera grafo sem nós: não há origem para testar.
    if g.numero_de_nos() == 0:
        return

    # Usa o primeiro nó do grafo como origem.
    origem = next(iter(g.nos()))
    distancia = bfs(g, origem)

    # A origem está sempre a distância 0.
    assert distancia[origem] == 0

    # Em grafo não direcionado, dois vizinhos nunca podem estar a mais de 1 passo
    # de diferença da origem: se v está a distância d, w está no máximo a d + 1.
    for v, w, _ in g.arestas():
        if v in distancia:
            assert w in distancia
            assert abs(distancia[v] - distancia[w]) <= 1


@given(listas_de_arestas)
def test_dfs_e_bfs_alcancam_os_mesmos_nos(lista):
    g = Grafo.de_arestas(lista)
    if g.numero_de_nos() == 0:
        return
    origem = next(iter(g.nos()))
    ordem = ordem_dfs(g, origem)

    # A DFS não visita nenhum nó duas vezes.
    assert len(ordem) == len(set(ordem))

    # As duas buscas andam em ordens diferentes, mas chegam exatamente aos mesmos nós.
    assert set(ordem) == set(bfs(g, origem))


@given(listas_de_arestas)
def test_componentes_repartem_os_nos(lista):
    g = Grafo.de_arestas(lista)
    componentes = componentes_conexas(g)

    # Todo nó está em exatamente uma componente: os tamanhos somam n...
    assert sum(len(c) for c in componentes) == g.numero_de_nos()

    # ...e juntando todas as componentes aparecem todos os nós, sem faltar nenhum.
    todos = set()
    for c in componentes:
        todos |= c
    assert todos == set(g.nos())


@given(listas_de_arestas)
def test_componente_e_o_que_a_bfs_alcanca(lista):
    g = Grafo.de_arestas(lista)

    # A componente de um nó é exatamente o conjunto que a BFS alcança saindo dele.
    for componente in componentes_conexas(g):
        qualquer_no = next(iter(componente))
        assert componente == set(bfs(g, qualquer_no))


@given(listas_de_arestas)
def test_dijkstra_sem_pesos_coincide_com_bfs(lista):
    g = Grafo.de_arestas(lista)
    if g.numero_de_nos() == 0:
        return
    origem = next(iter(g.nos()))

    # Com todos os pesos iguais a 1.0, somar pesos é o mesmo que contar arestas.
    assert dijkstra(g, origem) == bfs(g, origem)