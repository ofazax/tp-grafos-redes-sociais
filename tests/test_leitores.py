"""Testes dos leitores: tamanhos conferidos das quatro bases e os cuidados de cada formato."""

import pytest

from redes.leitores import (
    RAIZ,
    carregar_clubes_karate,
    carregar_facebook,
    carregar_karate,
    carregar_thrones,
    carregar_twitch_ptbr,
)


def precisa(caminho):
    """Pula o teste quando a base não foi baixada (dados/brutos/ fica fora do Git)."""
    return pytest.mark.skipif(not (RAIZ / caminho).exists(), reason=f"baixe {caminho} (veja dados/README.md)")


# Karate Club: já vem no repositório, em tests/dados/


def test_karate():
    g = carregar_karate()
    assert (g.numero_de_nos(), g.numero_de_arestas()) == (34, 78)
    assert not g.direcionado
    assert set(g.nos()) == set(range(34))
    assert g.grau(0) == 16  # Mr. Hi
    assert g.grau(33) == 17  # Officer (John A.)


def test_karate_funciona_de_qualquer_pasta(tmp_path, monkeypatch):
    # O caminho padrão parte de RAIZ, e não da pasta atual do terminal.
    monkeypatch.chdir(tmp_path)
    assert carregar_karate().numero_de_arestas() == 78


def test_clubes_karate():
    clubes = carregar_clubes_karate()
    assert len(clubes) == 34
    assert set(clubes) == set(carregar_karate().nos())
    assert sorted(clubes.values()).count(0) == 17  # Mr. Hi
    assert sorted(clubes.values()).count(1) == 17  # Officer


def test_lista_de_arestas_pula_comentarios_vazias_e_lacos(tmp_path):
    arquivo = tmp_path / "arestas.txt"
    arquivo.write_text("# comentário\n\n0 1\n1 2\n2 2\n  3 0  \n", encoding="utf-8")
    g = carregar_karate(arquivo)
    assert sorted(g.nos()) == [0, 1, 2, 3]
    assert g.numero_de_arestas() == 3  # o laço (2, 2) foi descartado
    assert not g.tem_aresta(2, 2)


def test_csv_com_quebra_de_linha_antiga(tmp_path):
    # O CSV da Network of Thrones separa as linhas só com \r.
    arquivo = tmp_path / "thrones.csv"
    arquivo.write_bytes(b"Source,Target,Type,weight,book\rA,B,Undirected,3,3\rB,C,Undirected,5,3")
    g = carregar_thrones(arquivo)
    assert g.numero_de_arestas() == 2
    assert g.peso("A", "B") == 3.0
    assert g.peso("C", "B") == 5.0  # não direcionado: vale nos dois sentidos


# Bases baixadas: os testes pulam se o arquivo não existir


@precisa("dados/brutos/twitch/PTBR/musae_PTBR_edges.csv")
def test_twitch():
    g, atributos = carregar_twitch_ptbr()
    assert (g.numero_de_nos(), g.numero_de_arestas()) == (1912, 31299)
    assert set(atributos) == set(g.nos())  # todo nó tem atributos (ligados pelo new_id)
    assert sum(a["parceiro"] for a in atributos.values()) == 279
    exemplo = atributos[1706]  # primeira linha do musae_PTBR_target.csv
    assert exemplo == {"visualizacoes": 929459, "parceiro": True, "adulto": False, "dias": 1943}


@precisa("dados/brutos/facebook_combined.txt.gz")
def test_facebook():
    g = carregar_facebook()
    assert (g.numero_de_nos(), g.numero_de_arestas()) == (4039, 88234)


@precisa("dados/brutos/asoiaf-book3-edges.csv")
def test_thrones():
    g = carregar_thrones()
    assert (g.numero_de_nos(), g.numero_de_arestas()) == (303, 1008)
    assert max(g.nos(), key=g.grau) == "Tyrion-Lannister"
    assert g.grau("Tyrion-Lannister") == 59
    assert g.peso("Addam-Marbrand", "Gyles-Rosby") == 3.0  # primeira linha do arquivo
    assert all(peso > 0 for _, _, peso in g.arestas())
