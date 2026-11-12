"""Leitura das quatro bases de dados do TP para a classe Grafo. Frente 1.

Bases (tamanhos conferidos nos testes de tests/test_leitores.py):
    Karate Club     34 nós e 78 arestas, sem peso        tests/dados/karate_arestas.txt
    Twitch PT       1.912 nós e 31.299 arestas           dados/brutos/twitch/PTBR/
    ego-Facebook    4.039 nós e 88.234 arestas           dados/brutos/facebook_combined.txt.gz
    Thrones (livro 3) 303 nós e 1.008 arestas, com peso   dados/brutos/asoiaf-book3-edges.csv

Todas as redes são não direcionadas. Os leitores descartam laços (v, v), que são ruído nas
bases reais. Os nomes das colunas (from, views, Source...) vêm das fontes e ficam como estão.
"""

from __future__ import annotations

import csv
import gzip
from collections.abc import Iterable, Iterator
from pathlib import Path

from redes.nucleo import Grafo

# Raiz do repositório: bases.py -> leitores -> redes -> raiz.
# Com ela os caminhos padrão funcionam de qualquer pasta (pytest, Streamlit, terminal).
RAIZ = Path(__file__).resolve().parents[2]


def _linhas_uteis(arquivo: Iterable[str]) -> Iterator[str]:
    """Devolve as linhas do arquivo sem espaços nas pontas, pulando vazias e comentários (#).

    Tempo: O(tamanho do arquivo). Espaço(1), porque é um gerador (lê uma linha por vez).
    """

    # Remove espaços e quebra de linha
    for linha in arquivo:
        linha = linha.strip()

        # Linha vazia e comentario não se torna uma aresta
        if linha and not linha.startswith("#"):
            yield linha


def _ler_lista_de_arestas(arquivo: Iterable[str]) -> Grafo:
    """Monta um grafo não direcionado a partir de linhas 'v w' (lista de arestas do SNAP).

    Usado pelo Karate e pelo ego-Facebook, quem tem o mesmo formato.
    Tempo: O(m). Espaço: O(n + m).
    """

    g = Grafo()
    for linha in _linhas_uteis(arquivo):

        v, w = map(int, linha.split())

        if v != w:
            g.adicionar_aresta(v, w)
    return g


def carregar_karate(caminho: str | Path = RAIZ / "tests/dados/karate_arestas.txt") -> Grafo:
    """Zachary's Karate Club: 34 nós (0 a 33) e 78 arestas, sem peso.

    Tempo: O(m). Espaço: O(n + m).
    Referência: Zachary (1977), Journal of Anthropological Research 33(4):452-473.
    """
    with open(caminho, encoding="utf-8") as arquivo:
        return _ler_lista_de_arestas(arquivo)


def carregar_clubes_karate(caminho: str | Path = RAIZ / "tests/dados/karate_clubes.txt") -> dict[int, int]:
    """Facção real de cada membro do Karate: 0 = Mr. Hi, 1 = Officer (17 membros em cada).

    É o gabarito das comunidades: o Arthur compara o Louvain com ele (NMI e ARI).
    Tempo: O(n). Espaço: O(n).
    Referência: Zachary (1977).
    """
    clubes: dict[int, int] = {}
    with open(caminho, encoding="utf-8") as arquivo:
        # Cada linha é "nó facção"
        for linha in _linhas_uteis(arquivo):
            no, faccao = map(int, linha.split())
            clubes[no] = faccao
    return clubes


def carregar_twitch_ptbr(pasta: str | RAIZ / "dados/brutos/twitch/PTBR") -> tuple[Grafo, dict[int, dict]]:
    """Rede de streamers da Twitch em português e os atributos de cada streamer.

    Devolve (grafo, atributos). O grafo tem 1.912 nós e 31.299 arestas (amizade mútua, sem peso).
    atributos[no] = {"visualizacoes": int, "parceiro": bool, "adulto": bool, "dias": int},
    com 279 parceiros. Os atributos se ligam aos nós pela coluna new_id, que é a usada nas arestas.

    Tempo: O(n + m). Espaço: O(n + m).
    Referência: Rozemberczki, Allen e Sarkar (2021), Multi-Scale Attributed Node Embedding,
    Journal of Complex Networks; dados do SNAP (Leskovec e Krevl, 2014).
    """
    pasta = Path(pasta)
    g = Grafo()

    with open(pasta / "musae_PTBR_edges.csv", newline="", encoding="utf-8") as arquivo:
        for linha in csv.DictReader(arquivo):
            v, w = int(linha["from"]), int(linha["to"])
            if v != w:
                g.adicionar_aresta(v, w)

    atributos: dict[int, dict] = {}

    with open(pasta / "musae_PTBR_target.csv", newline="", encoding="utf-8") as arquivo:
        for linha in csv.DictReader(arquivo):
            no = int(linha["new_id"])
            atributos[no] = {
                "visualizacoes": linha["partner"] == "True",
                "adulto": linha["mature"] == "True",
                "dias": int(linha["days"]),
            }
            g.adicionar_no(no)
    return g, atributos


def carregar_facebook(caminho: str | Path = RAIZ / "dados/brutos/facebook_combined.txt.gz") -> Grafo:
    """ego-Facebook do SNAP: 4.039 nós e 88.234 arestas, sem peso.

    O arquivo é texto compactado em gzip, com uma aresta 'v w' por linha.
    Tempo: O(m). Espaço: O(n + m).
    Referência: McAuley e Leskovec (2012), Learning to Discover Social Circles in Ego Networks, NIPS.
    """
    with gzip.open(caminho, "rt", encoding="utf-8") as arquivo:
        return _ler_lista_de_arestas(arquivo)


def carregar_thrones(caminho: str | Path = RAIZ / "dados/brutos/asoiaf-book3-edges.csv") -> Grafo:
    """Network of Thrones, livro 3: 303 personagens e 1.008 arestas com peso.

    Os nós são nomes (ex.: "Tyrion-Lannister") e o peso é o número de vezes em que os dois
    personagens aparecem a até 15 palavras um do outro.
    Tempo: O(m). Espaço: O(n + m).
    Referência: Beveridge e Shan (2016), Network of Thrones, Math Horizons 23(4):18-22.
    """
    g = Grafo()

    with open(caminho, newline="", encoding="utf-8") as arquivo:
        for linha in csv.DictReader(arquivo):
            v, w = linha["Source"], linha["Target"]
            if v != w:
                g.adicionar_aresta(v, w, float(linha["weight"]))
    return g
