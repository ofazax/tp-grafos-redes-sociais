"""Poder de espalhamento na Twitch PT: roda o SIR a partir de cada streamer e grava o alcance. Frente 5.

Uso, da raiz do projeto (com a Twitch PT em dados/brutos/, veja dados/README.md):
    python -m redes.aplicacao.experimento              # beta = 0,012, 100 rodadas (cerca de 25 s)
    python -m redes.aplicacao.experimento --rodadas 10 # rápido, para conferir

Salva redes/aplicacao/resultados/alcance_twitch.csv, com uma linha por streamer: o alcance
médio no SIR, o grau, o número de núcleo e os atributos reais (visualizações e parceria).
É a entrada da comparação dos rankings (tau de Kendall).
"""

from __future__ import annotations

import argparse
import csv
import time
from pathlib import Path

from redes.aplicacao.influencia import limiar_epidemico, poder_de_espalhamento
from redes.leitores.bases import carregar_twitch_ptbr
from redes.metricas.nucleo_k import numero_de_nucleo
from redes.nucleo.grafo import Grafo, No

# Valores da descrição do problema (Etapa 1): beta pouco acima do limiar (0,0079), gamma = 1.
BETA = 0.012
RODADAS = 100
SEMENTE = 2026

PASTA_RESULTADOS = Path(__file__).parent / "resultados"
COLUNAS = ["posicao", "no", "alcance", "atingidos_medios", "grau", "nucleo", "visualizacoes", "parceiro"]


def tabela_de_alcance(
    g: Grafo,
    atributos: dict[No, dict],
    beta: float = BETA,
    rodadas: int = RODADAS,
    semente: int | None = SEMENTE,
) -> list[dict]:
    """Uma linha por nó, do maior para o menor alcance no SIR.

    Cada linha tem a posição no ranking (1 = maior alcance), o nó, o alcance rho(v) (fração
    da rede atingida, na média das rodadas), os atingidos médios (rho(v) * n), o grau, o
    número de núcleo e, quando o nó tem atributos, as visualizações e se é parceiro. Empates
    no alcance são desfeitos pelo grau e depois pelo identificador do nó, como na descrição
    do problema.

    Tempo: o do poder_de_espalhamento, O(rodadas * n * (n + m)) no pior caso, mais
    O(n log n) para ordenar. Espaço: O(n + m).
    """
    n = g.numero_de_nos()
    alcance = poder_de_espalhamento(g, beta, rodadas=rodadas, semente=semente)
    nucleo = numero_de_nucleo(g)
    ordem = sorted(g.nos(), key=lambda v: (-alcance[v], -g.grau(v), v))

    linhas = []
    for posicao, v in enumerate(ordem, start=1):
        dados = atributos.get(v, {})
        linhas.append(
            {
                "posicao": posicao,
                "no": v,
                "alcance": alcance[v],
                "atingidos_medios": alcance[v] * n,
                "grau": g.grau(v),
                "nucleo": nucleo[v],
                "visualizacoes": dados.get("visualizacoes", ""),
                "parceiro": dados.get("parceiro", ""),
            }
        )
    return linhas


def salvar_csv(linhas: list[dict], caminho: Path) -> None:
    """Grava as linhas no CSV (cria a pasta, se preciso), com o alcance em 6 casas decimais."""
    caminho.parent.mkdir(parents=True, exist_ok=True)
    with open(caminho, "w", newline="", encoding="utf-8") as arquivo:
        escritor = csv.DictWriter(arquivo, fieldnames=COLUNAS)
        escritor.writeheader()
        for linha in linhas:
            escritor.writerow(
                {**linha, "alcance": f"{linha['alcance']:.6f}", "atingidos_medios": f"{linha['atingidos_medios']:.2f}"}
            )


def principal() -> None:
    """Lê as opções, roda o SIR a partir de cada streamer da Twitch PT, mostra o resumo e grava o CSV."""
    analisador = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    analisador.add_argument("--beta", type=float, default=BETA, help=f"chance de cada aresta transmitir (padrão {BETA})")
    analisador.add_argument("--rodadas", type=int, default=RODADAS, help=f"rodadas por nó (padrão {RODADAS})")
    analisador.add_argument("--semente", type=int, default=SEMENTE, help=f"semente do sorteio (padrão {SEMENTE})")
    analisador.add_argument("--saida", type=Path, default=PASTA_RESULTADOS / "alcance_twitch.csv")
    opcoes = analisador.parse_args()

    g, atributos = carregar_twitch_ptbr()
    beta_c = limiar_epidemico(g)
    print(f"Twitch PT: n = {g.numero_de_nos()}, m = {g.numero_de_arestas()}")
    print(f"Limiar epidêmico beta_c = {beta_c:.5f}; beta = {opcoes.beta} ({opcoes.beta / beta_c:.2f} x beta_c)")
    print(f"Rodando {opcoes.rodadas} rodadas a partir de cada nó (semente {opcoes.semente})...", flush=True)

    inicio = time.perf_counter()
    linhas = tabela_de_alcance(g, atributos, opcoes.beta, opcoes.rodadas, opcoes.semente)
    duracao = time.perf_counter() - inicio

    atingidos = sorted(linha["atingidos_medios"] for linha in linhas)
    print(f"Pronto em {duracao:.1f} s. Atingidos por rodada: mínimo {atingidos[0]:.1f}, "
          f"mediana {atingidos[len(atingidos) // 2]:.1f}, máximo {atingidos[-1]:.1f}")
    print("\n  #     nó   alcance   grau  núcleo  visualizações")
    for linha in linhas[:10]:
        print(f"{linha['posicao']:>3} {linha['no']:>6}  {linha['alcance'] * 100:6.2f}%  {linha['grau']:>5}  "
              f"{linha['nucleo']:>6}  {linha['visualizacoes']:>13}")

    salvar_csv(linhas, opcoes.saida)
    print(f"\nSalvo em {opcoes.saida}")


if __name__ == "__main__":
    principal()
