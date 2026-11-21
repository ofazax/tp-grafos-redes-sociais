"""Influenciadores na Twitch PT: alcance no SIR e comparação das 6 centralidades. Frente 5.

Uso, da raiz do projeto (com a Twitch PT em dados/brutos/, veja dados/README.md):
    python -m redes.aplicacao.experimento              # beta = 0,012, 100 rodadas (cerca de 40 s)
    python -m redes.aplicacao.experimento --rodadas 10 # rápido, para conferir

Roda o SIR a partir de cada streamer, calcula as 6 centralidades e compara o ranking de cada uma
com o alcance (pergunta P1) e com as visualizações reais (pergunta P2) pelo tau-b de Kendall.
Salva em redes/aplicacao/resultados/:
    alcance_twitch.csv       uma linha por streamer: alcance, grau, núcleo, visualizações e parceria
    concordancia_twitch.csv  uma linha por centralidade: tau-b contra o alcance e contra as visualizações
"""

from __future__ import annotations

import argparse
import csv
import time
from pathlib import Path

from redes.aplicacao.influencia import comparar_rankings, limiar_epidemico, poder_de_espalhamento, tau_de_kendall
from redes.leitores.bases import carregar_twitch_ptbr
from redes.metricas.centralidade import intermediacao, pagerank
from redes.metricas.grau import centralidade_de_grau
from redes.metricas.nucleo_k import numero_de_nucleo
from redes.metricas.proximidade import harmonica, proximidade
from redes.nucleo.grafo import Grafo, No

# Valores da descrição do problema (Etapa 1): beta pouco acima do limiar (0,0079), gamma = 1.
BETA = 0.012
RODADAS = 100
SEMENTE = 2026

PASTA_RESULTADOS = Path(__file__).parent / "resultados"
COLUNAS = ["posicao", "no", "alcance", "atingidos_medios", "grau", "nucleo", "visualizacoes", "parceiro"]
COLUNAS_CONCORDANCIA = ["centralidade", "tau_alcance", "tau_visualizacoes"]

# As 6 centralidades da descrição do problema, na ordem das tabelas do relatório.
CENTRALIDADES = {
    "grau": centralidade_de_grau,
    "proximidade": proximidade,
    "harmonica": harmonica,
    "intermediacao": intermediacao,
    "pagerank": pagerank,
    "nucleo": numero_de_nucleo,
}


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


def centralidades_da_rede(g: Grafo) -> dict[str, dict[No, float]]:
    """As 6 centralidades de cada nó: grau, proximidade, harmônica, intermediação, PageRank e núcleo.

    A intermediação é a exata (Brandes). Tempo: O(nm), dominado pela intermediação.
    Espaço: O(n + m).
    """
    return {nome: funcao(g) for nome, funcao in CENTRALIDADES.items()}


def tabela_de_concordancia(
    centralidades: dict[str, dict[No, float]],
    alcance: dict[No, float],
    visualizacoes: dict[No, float],
) -> list[dict]:
    """Uma linha por centralidade, com o tau-b do ranking dela contra o alcance e contra as visualizações.

    A ordem das linhas é a das centralidades recebidas. Tempo: O(c * n log n). Espaço: O(n).
    """
    taus = comparar_rankings(centralidades, {"alcance": alcance, "visualizacoes": visualizacoes})
    return [
        {"centralidade": nome, "tau_alcance": tau["alcance"], "tau_visualizacoes": tau["visualizacoes"]}
        for nome, tau in taus.items()
    ]


def salvar_concordancia_csv(linhas: list[dict], caminho: Path) -> None:
    """Grava a tabela de concordância no CSV (cria a pasta, se preciso), com o tau em 4 casas decimais."""
    caminho.parent.mkdir(parents=True, exist_ok=True)
    with open(caminho, "w", newline="", encoding="utf-8") as arquivo:
        escritor = csv.DictWriter(arquivo, fieldnames=COLUNAS_CONCORDANCIA)
        escritor.writeheader()
        for linha in linhas:
            escritor.writerow(
                {
                    "centralidade": linha["centralidade"],
                    "tau_alcance": f"{linha['tau_alcance']:.4f}",
                    "tau_visualizacoes": f"{linha['tau_visualizacoes']:.4f}",
                }
            )


def principal() -> None:
    """Lê as opções, roda o SIR e as centralidades na Twitch PT, mostra os resultados e grava os CSVs."""
    analisador = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    analisador.add_argument("--beta", type=float, default=BETA, help=f"chance de cada aresta transmitir (padrão {BETA})")
    analisador.add_argument("--rodadas", type=int, default=RODADAS, help=f"rodadas por nó (padrão {RODADAS})")
    analisador.add_argument("--semente", type=int, default=SEMENTE, help=f"semente do sorteio (padrão {SEMENTE})")
    analisador.add_argument("--pasta", type=Path, default=PASTA_RESULTADOS, help="onde gravar os CSVs")
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

    print("\nCalculando as 6 centralidades...", flush=True)
    inicio = time.perf_counter()
    centralidades = centralidades_da_rede(g)
    print(f"Pronto em {time.perf_counter() - inicio:.1f} s.")

    alcance = {linha["no"]: linha["alcance"] for linha in linhas}
    visualizacoes = {v: dados["visualizacoes"] for v, dados in atributos.items()}
    concordancia = tabela_de_concordancia(centralidades, alcance, visualizacoes)

    print("\nTau-b de Kendall de cada centralidade")
    print("centralidade     x alcance  x visualizações")
    for linha in concordancia:
        print(f"{linha['centralidade']:<15} {linha['tau_alcance']:>10.4f} {linha['tau_visualizacoes']:>16.4f}")
    print(f"(referência: o próprio alcance x visualizações = {tau_de_kendall(alcance, visualizacoes):.4f})")

    melhor_p1 = max(concordancia, key=lambda linha: linha["tau_alcance"])
    melhor_p2 = max(concordancia, key=lambda linha: linha["tau_visualizacoes"])
    tau = {linha["centralidade"]: linha for linha in concordancia}
    h1 = tau["nucleo"]["tau_alcance"] > tau["grau"]["tau_alcance"]
    h2 = all(0 < linha["tau_visualizacoes"] < linha["tau_alcance"] for linha in concordancia)
    print(f"\nP1 (prevê o alcance): {melhor_p1['centralidade']} (tau = {melhor_p1['tau_alcance']:.4f})")
    print(f"P2 (prevê as visualizações): {melhor_p2['centralidade']} (tau = {melhor_p2['tau_visualizacoes']:.4f})")
    print(f"H1 (núcleo supera o grau na P1): {'confirmada' if h1 else 'refutada'}")
    print(f"H2 (0 < tau com visualizações < tau com alcance, para todas): {'confirmada' if h2 else 'refutada'}")

    salvar_csv(linhas, opcoes.pasta / "alcance_twitch.csv")
    salvar_concordancia_csv(concordancia, opcoes.pasta / "concordancia_twitch.csv")
    print(f"\nSalvo em {opcoes.pasta}")


if __name__ == "__main__":
    principal()
