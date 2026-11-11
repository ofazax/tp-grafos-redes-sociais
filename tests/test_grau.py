"""Testes das métricas de grau: casos de resposta conhecida, Karate Club e invariantes."""

from pathlib import Path

import pytest

#Entradas aleatórias
from hypothesis import given
from hypothesis import strategies as st

from redes.metricas.grau import (
    centralidade_de_grau,
    densidade,
    distribuicao_de_graus,
    grau_medio,
)
from redes.nucleo import Grafo #Montar os grafos de teste

ARQUIVO_KARATE = Path(__file__).parent / "dados" / "karate_arestas.txt"


def carregar_karate():
    #Lê o Karate Club de tests/dados (uma aresta 'u v' por linha).
    g = Grafo()
    with open(ARQUIVO_KARATE, encoding="utf-8") as arquivo:
        for linha in arquivo:
            linha = linha.strip()
            if not linha or linha.startswith("#"):
                continue
            v, w = linha.split()
            g.adicionar_aresta(int(v), int(w))
    return g


#Grafo completo
def completo(n):
    return Grafo.de_arestas((i, j) for i in range(n) for j in range(i + 1, n))


def estrela(n):
    #Nó 0 no centro, ligado aos outros n - 1 nós.
    return Grafo.de_arestas((0, i) for i in range(1, n))


# Casos pequenos, de resposta conhecida

#Grafo sem nenhum nó: caso extremo
def test_grafo_vazio():
    g = Grafo()
    assert centralidade_de_grau(g) == {}    #Sem nós não há valor para devolver: dicionário vazio
    assert distribuicao_de_graus(g) == {}   #Sem nós nenhum grau aparece
    assert densidade(g) == 0.0              #Com menos de 2 não existe par possível
    assert grau_medio(g) == 0.0             #Sem nós o grau médio é 0.0


#Grafo com um único nó e nenhuma aresta
def test_no_isolado():
    g = Grafo()
    g.adicionar_no("a")
    assert centralidade_de_grau(g) == {"a": 0.0}    #A função precisa devolver zero (n - 1 = 0)
    assert distribuicao_de_graus(g) == {0: 1}       #Um nó com grau 0 {grau 0: 1 nó}
    assert densidade(g) == 0.0                      #Um nó não forma par
    assert grau_medio(g) == 0.0                     #O único nó tem grau 0, média = 0


#K5: 5 nós, cada um ligado aos outros 4             
def test_completo_k5():
    g = completo(5)
    assert centralidade_de_grau(g) == {v: 1.0 for v in range(5)}    #Cada nó é vizinha de todos os outros: [4 / (5 - 1)] = 1
    assert distribuicao_de_graus(g) == {4: 5}                       #Os 5 nós tem grau 4 {grau 4: 5 nos} ... {4: 5}
    assert densidade(g) == 1.0                                      #Todas as arestas possíveis existem, densidade máxima = 1
    assert grau_medio(g) == 4.0                                     #Todos tem grau 4, média = 4


#Estrela com 6 nós
def test_estrela():
    g = estrela(6)
    centralidade = centralidade_de_grau(g)
    assert centralidade[0] == 1.0           #O centro é vizinho dos outros 5
    assert all(centralidade[i] == pytest.approx(1 / 5) for i in range(1, 6))
    assert distribuicao_de_graus(g) == {1: 5, 5: 1}         #Ordem crescente de graus
    assert densidade(g) == pytest.approx(2 * 5 / (6 * 5))   #(10/30)
    assert grau_medio(g) == pytest.approx(10 / 6)


def test_caminho():
    g = Grafo.de_arestas([(0, 1), (1, 2), (2, 3)])
    assert distribuicao_de_graus(g) == {1: 2, 2: 2}     #Pontas (0 e 3) têm grau 1; Meios (1 e 2) tem grau 2
    assert densidade(g) == pytest.approx(0.5)           #2m / (n(n - 1)) = 2 * 3 / (4 * 3) = 0,5
    assert grau_medio(g) == 1.5                         #2m / n = 6 / 4 = 1,5.


def test_direcionado():
    g = Grafo.de_arestas([(1, 2), (2, 3), (3, 1)], direcionado=True)
    assert densidade(g) == pytest.approx(3 / 6)                     #Se esquecer de tratar daria 1 e o teste falharia
    assert grau_medio(g) == 2.0                                     #Cada nó tem 1 aresta entradando e 1 saindo, grau 2 para todos
    assert centralidade_de_grau(g) == {1: 1.0, 2: 1.0, 3: 1.0}      #Grau 2 dividido por n - 1 = 2


#Não altera o grafo que recebe
def test_nao_altera_o_grafo():
    g = completo(4)
    centralidade_de_grau(g)
    distribuicao_de_graus(g)
    densidade(g)
    grau_medio(g)
    assert g.numero_de_nos() == 4
    assert g.numero_de_arestas() == 6


# Karate Club: valores de referência do documento de divisão de tarefas

def test_karate_tamanho():
    g = carregar_karate()
    assert g.numero_de_nos() == 34
    assert g.numero_de_arestas() == 78


def test_karate_densidade_e_grau_medio():
    g = carregar_karate()

    #Arredonda valor
    assert densidade(g) == pytest.approx(0.139, abs=1e-3)
    assert grau_medio(g) == pytest.approx(4.588, abs=1e-3)


def test_karate_grau_maximo():
    g = carregar_karate()
    distribuicao = distribuicao_de_graus(g)
    assert max(distribuicao) == 17
    centralidade = centralidade_de_grau(g)                  #Descobre quem tem o maior grau
    assert max(centralidade, key=centralidade.get) == 33    #Nó mais central = 33
    assert centralidade[33] == pytest.approx(17 / 33)       #n - 1 = 33 


# Invariantes, em grafos aleatórios

listas_de_arestas = st.lists(st.tuples(st.integers(0, 30), st.integers(0, 30)), max_size=200)


@given(listas_de_arestas)
def test_distribuicao_soma_n(lista):
    g = Grafo.de_arestas(lista)

    #Cada nó entra em exatamente um grau de distribuição, então a soma de quantidades precisa dar o número de nós
    assert sum(distribuicao_de_graus(g).values()) == g.numero_de_nos()


@given(listas_de_arestas)
def test_grau_medio_e_a_media_dos_graus(lista):
    g = Grafo.de_arestas(lista)

    #Se a lista sorteada estiver vazia, o grafo não tem nós e a média não existe
    if g.numero_de_nos() > 0:
        media = sum(g.grau(v) for v in g.nos()) / g.numero_de_nos()     #Soma o grau de cada nó e divide por n
        assert grau_medio(g) == pytest.approx(media)                    #Atalho da função, precisa dar o mesmo resultado da linha de cima


@given(listas_de_arestas)
def test_centralidade_tem_um_valor_por_no(lista):
    g = Grafo.de_arestas(lista)

    #Elas precisam ser exatamente os nós
    assert set(centralidade_de_grau(g)) == set(g.nos())