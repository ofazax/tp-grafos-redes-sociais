"""Serviço de integração entre a interface e o backend real (pacote redes).

Este módulo não utiliza dados mockados: todas as métricas, caminhos, layouts,
comunidades e simulações SIR são calculados sobre instâncias reais de `redes.nucleo.Grafo`.
"""

from __future__ import annotations

import csv
import gzip
import io
import json
import math
import random
import threading
from collections import defaultdict, deque
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any

from interface.tema import (
    CORES_COMUNIDADES,
    PALETA,
)
from redes.aplicacao.influencia import (
    beta_recomendado,
    evolucao_sir,
    limiar_epidemico,
    poder_de_espalhamento,
    tau_de_kendall,
)
from redes.geradores.modelos import barabasi_albert, erdos_renyi, watts_strogatz
from redes.leitores.bases import (
    RAIZ,
    carregar_clubes_karate,
    carregar_facebook,
    carregar_karate,
    carregar_thrones,
    carregar_twitch_ptbr,
)
from redes.metricas.caminhos import (
    bfs,
    componentes_conexas,
    diametro,
    dijkstra,
    distancia_media,
    ordem_dfs,
)
from redes.metricas.centralidade import intermediacao, pagerank
from redes.metricas.grau import (
    centralidade_de_grau,
    densidade,
    distribuicao_de_graus,
    grau_medio,
)
from redes.metricas.nucleo_k import numero_de_nucleo
from redes.metricas.proximidade import harmonica, proximidade
from redes.nucleo.grafo import Grafo, No
from redes.visualizacao.posicionamento import fruchterman_reingold

# ---------------------------------------------------------------------------
# Importações opcionais das Frentes 4 e 5 (caso já mescladas na branch atual)
# ---------------------------------------------------------------------------
try:
    from redes.metricas.agrupamento import (  # type: ignore[import-not-found]
        agrupamento_medio as _agrupamento_medio_backend,
        transitividade as _transitividade_backend,
        triangulos as _triangulos_backend,
    )
except ImportError:
    _agrupamento_medio_backend = None
    _transitividade_backend = None
    _triangulos_backend = None

try:
    from redes.comunidades.louvain import louvain as _louvain_backend  # type: ignore[import-not-found]
    from redes.comunidades.modularidade import (  # type: ignore[import-not-found]
        modularidade as _modularidade_backend,
    )
except ImportError:
    _louvain_backend = None
    _modularidade_backend = None

try:
    from redes.comunidades.avaliacao import ari as _ari_backend  # type: ignore[import-not-found]
    from redes.comunidades.avaliacao import nmi as _nmi_backend  # type: ignore[import-not-found]
    from redes.comunidades.rotulos import (  # type: ignore[import-not-found]
        propagacao_de_rotulos as _propagacao_backend,
    )
except ImportError:
    _ari_backend = None
    _nmi_backend = None
    _propagacao_backend = None


# ---------------------------------------------------------------------------
# Caches em memória de execução para evitar releitura de disco repetida
# ---------------------------------------------------------------------------
_CACHE_BASES_BRUTAS: dict[str, tuple[Grafo, dict[str, Any]]] = {}
_CACHE_ANALISES: dict[tuple[Any, ...], dict[str, Any]] = {}
_CACHE_SIR: dict[tuple[Any, ...], dict[str, Any]] = {}
_CACHE_LAYOUTS: dict[tuple[Any, ...], dict[No, tuple[float, float]]] = {}


def formatar_int_br(valor: int) -> str:
    """Formata um inteiro com separador de milhar brasileiro (ex.: 4039 -> '4.039')."""
    return f"{int(valor):,}".replace(",", ".")


def formatar_float_br(valor: float, casas: int = 4) -> str:
    """Formata um float com vírgula decimal (ex.: 0.6055 -> '0,6055')."""
    return f"{valor:.{casas}f}".replace(".", ",")


def formatar_rotulo_no(no: No) -> str:
    """Formata o identificador de um nó para exibição na interface."""
    if isinstance(no, int):
        return f"#{no}"
    return str(no)


# ---------------------------------------------------------------------------
# 1. Cálculos complementares sobre Grafo (quando módulo de outra frente não está na main)
# ---------------------------------------------------------------------------
def calcular_agrupamento_e_triangulos(g: Grafo) -> tuple[float, float, int]:
    """Calcula (clustering_medio, transitividade_global, total_triangulos) sobre o Grafo g."""
    n = g.numero_de_nos()
    if n == 0:
        return 0.0, 0.0, 0

    if (
        _agrupamento_medio_backend is not None
        and _transitividade_backend is not None
        and _triangulos_backend is not None
    ):
        tri_por_no = _triangulos_backend(g)
        total_tri = sum(tri_por_no.values()) // 3
        clust_med = float(_agrupamento_medio_backend(g))
        trans = float(_transitividade_backend(g))
        return clust_med, trans, total_tri

    vizinhos = {v: set(g.vizinhos(v)) - {v} for v in g.nos()}
    contagem_dupla: dict[No, int] = {v: 0 for v in g.nos()}

    for u, v, _ in g.arestas():
        if u == v:
            continue
        comuns = len(vizinhos[u] & vizinhos[v])
        if comuns > 0:
            contagem_dupla[u] += comuns
            contagem_dupla[v] += comuns

    triangulos_no = {v: total // 2 for v, total in contagem_dupla.items()}
    soma_triangulos_nos = sum(triangulos_no.values())
    total_triangulos = soma_triangulos_nos // 3

    soma_clustering = 0.0
    total_triades = 0
    for v in g.nos():
        k = len(vizinhos[v])
        if k >= 2:
            triades_v = k * (k - 1) // 2
            total_triades += triades_v
            soma_clustering += triangulos_no[v] / triades_v

    clustering_medio = soma_clustering / n if n > 0 else 0.0
    transitividade_global = (
        soma_triangulos_nos / total_triades if total_triades > 0 else 0.0
    )
    return clustering_medio, transitividade_global, total_triangulos


def calcular_modularidade_particao(g: Grafo, particao: dict[No, int]) -> float:
    """Calcula a modularidade de Newman–Girvan Q de uma partição sobre o Grafo g."""
    if _modularidade_backend is not None:
        return float(_modularidade_backend(g, particao))

    if g.numero_de_arestas() == 0 or g.numero_de_nos() == 0:
        return 0.0

    sigma_in: dict[int, float] = defaultdict(float)
    sigma_tot: dict[int, float] = defaultdict(float)
    dois_m = 0.0

    for v in g.nos():
        c = particao[v]
        for w in g.vizinhos(v):
            sigma_tot[c] += g.peso(v, w)

    for u, v, peso in g.arestas():
        if u == v:
            dois_m += peso
            if particao[u] == particao[v]:
                sigma_in[particao[u]] += peso
        else:
            dois_m += 2.0 * peso
            if particao[u] == particao[v]:
                sigma_in[particao[u]] += 2.0 * peso

    if dois_m == 0.0:
        return 0.0

    q = 0.0
    for c in sigma_tot:
        q += (sigma_in[c] / dois_m) - ((sigma_tot[c] / dois_m) ** 2)
    return q


def executar_propagacao_rotulos(
    g: Grafo, semente: int = 42, max_iteracoes: int = 30
) -> tuple[dict[No, int], float]:
    """Executa detecção de comunidades por Propagação de Rótulos (Raghavan et al., 2007)."""
    nos = list(g.nos())
    if not nos:
        return {}, 0.0

    # Usa a implementação da Frente 4 (redes/comunidades/rotulos.py) quando ela existe.
    if _propagacao_backend is not None and not g.direcionado:
        particao = _propagacao_backend(g, semente=semente)
        return particao, calcular_modularidade_particao(g, particao)

    gerador = random.Random(semente)
    rotulo: dict[No, int] = {v: i for i, v in enumerate(nos)}

    for _ in range(max_iteracoes):
        ordem = nos[:]
        gerador.shuffle(ordem)
        mudou = False
        for v in ordem:
            pesos_por_rotulo: dict[int, float] = defaultdict(float)
            for w in g.vizinhos(v):
                if w != v:
                    pesos_por_rotulo[rotulo[w]] += g.peso(v, w)
            if not pesos_por_rotulo:
                continue
            maior_peso = max(pesos_por_rotulo.values())
            candidatos = sorted(
                r for r, p in pesos_por_rotulo.items() if abs(p - maior_peso) < 1e-9
            )
            escolhido = rotulo[v] if rotulo[v] in candidatos else gerador.choice(candidatos)
            if escolhido != rotulo[v]:
                rotulo[v] = escolhido
                mudou = True
        if not mudou:
            break

    unicos = sorted(set(rotulo.values()))
    mapa = {antigo: novo for novo, antigo in enumerate(unicos)}
    particao = {v: mapa[c] for v, c in rotulo.items()}
    return particao, calcular_modularidade_particao(g, particao)


def executar_louvain(
    g: Grafo, semente: int = 42, max_passadas: int = 15
) -> tuple[dict[No, int], float]:
    """Executa otimização de modularidade de Louvain (Blondel et al., 2008) sobre o Grafo g."""
    if _louvain_backend is not None and not g.direcionado:
        try:
            return _louvain_backend(g, semente=semente)
        except TypeError:
            return _louvain_backend(g)

    nos = list(g.nos())
    if not nos or g.numero_de_arestas() == 0:
        return {v: i for i, v in enumerate(nos)}, 0.0

    gerador = random.Random(semente)
    comunidade: dict[No, int] = {v: i for i, v in enumerate(nos)}

    kv: dict[No, float] = {}
    dois_m = 0.0
    for v in nos:
        soma_pesos = sum(g.peso(v, w) for w in g.vizinhos(v))
        kv[v] = soma_pesos
        dois_m += soma_pesos

    if dois_m == 0.0:
        return comunidade, 0.0

    sigma_tot: dict[int, float] = {comunidade[v]: kv[v] for v in nos}

    for _ in range(max_passadas):
        ordem = nos[:]
        gerador.shuffle(ordem)
        melhorou = False

        for v in ordem:
            c_atual = comunidade[v]
            k_v = kv[v]
            pesos_com: dict[int, float] = defaultdict(float)
            for w in g.vizinhos(v):
                if w != v:
                    pesos_com[comunidade[w]] += g.peso(v, w)

            sigma_tot[c_atual] -= k_v
            ganho_base = pesos_com.get(c_atual, 0.0) - (sigma_tot[c_atual] * k_v / dois_m)
            melhor_c = c_atual
            melhor_ganho = ganho_base

            for c_viz, k_v_in in pesos_com.items():
                ganho = k_v_in - (sigma_tot[c_viz] * k_v / dois_m)
                if ganho > melhor_ganho + 1e-9:
                    melhor_ganho = ganho
                    melhor_c = c_viz

            comunidade[v] = melhor_c
            sigma_tot[melhor_c] = sigma_tot.get(melhor_c, 0.0) + k_v
            if melhor_c != c_atual:
                melhorou = True

        if not melhorou:
            break

    unicos = sorted(set(comunidade.values()))
    mapa = {antigo: novo for novo, antigo in enumerate(unicos)}
    particao = {v: mapa[c] for v, c in comunidade.items()}
    return particao, calcular_modularidade_particao(g, particao)


def calcular_nmi_e_ari(
    particao_a: dict[No, int], particao_b: dict[No, int]
) -> tuple[float, float]:
    """Calcula a Informação Mútua Normalizada (NMI) e o Índice Rand Ajustado (ARI) entre duas partições."""
    chaves = [v for v in particao_a if v in particao_b]
    n = len(chaves)
    if n < 2:
        return 0.0, 0.0

    # Usa as funções da Frente 4 (redes/comunidades/avaliacao.py) quando elas existem.
    if _nmi_backend is not None and _ari_backend is not None:
        a = {v: particao_a[v] for v in chaves}
        b = {v: particao_b[v] for v in chaves}
        return (
            max(0.0, min(1.0, float(_nmi_backend(a, b)))),
            max(0.0, min(1.0, float(_ari_backend(a, b)))),
        )

    cont_a: dict[int, int] = defaultdict(int)
    cont_b: dict[int, int] = defaultdict(int)
    contingencia: dict[tuple[int, int], int] = defaultdict(int)

    for v in chaves:
        ca = particao_a[v]
        cb = particao_b[v]
        cont_a[ca] += 1
        cont_b[cb] += 1
        contingencia[(ca, cb)] += 1

    # NMI
    mi = 0.0
    for (ca, cb), nij in contingencia.items():
        if nij > 0:
            mi += (nij / n) * math.log((nij * n) / (cont_a[ca] * cont_b[cb]))

    ha = -sum((na / n) * math.log(na / n) for na in cont_a.values() if na > 0)
    hb = -sum((nb / n) * math.log(nb / n) for nb in cont_b.values() if nb > 0)
    nmi = (2.0 * mi / (ha + hb)) if (ha + hb) > 0 else 1.0

    # ARI (Hubert & Arabie, 1985)
    def comb2(k: int) -> float:
        return float(k * (k - 1) // 2)

    soma_nij = sum(comb2(nij) for nij in contingencia.values())
    soma_a = sum(comb2(na) for na in cont_a.values())
    soma_b = sum(comb2(nb) for nb in cont_b.values())
    total_pares = comb2(n)

    if total_pares == 0:
        return max(0.0, min(1.0, nmi)), 0.0

    esperado = (soma_a * soma_b) / total_pares
    max_indice = 0.5 * (soma_a + soma_b)
    denom = max_indice - esperado
    ari = (soma_nij - esperado) / denom if abs(denom) > 1e-12 else 1.0
    return max(0.0, min(1.0, nmi)), max(0.0, min(1.0, ari))


def simular_sir_monte_carlo(
    g: Grafo,
    semente_no: No,
    beta: float,
    gamma: float = 1.0,
    simulacoes: int = 100,
    semente_aleatoria: int = 42,
) -> dict[str, Any]:
    """SIR da tela de influenciadores, pelo `evolucao_sir` da Frente 5 (`redes.aplicacao`).

    Devolve o alcance médio, as curvas S(t), I(t) e R(t) na média das rodadas e o estado de
    cada nó no pico da primeira rodada, com a semente marcada como "SEED". As rodadas vão até
    não sobrar infectado, como na descrição do problema.
    """
    n = g.numero_de_nos()
    if n == 0 or semente_no not in g:
        return {
            "alcance_medio": 0.0,
            "curva_s": [1.0],
            "curva_i": [0.0],
            "curva_r": [0.0],
            "estados_snapshot": {},
        }

    chave_sir = (id(g), n, g.numero_de_arestas(), semente_no, beta, gamma, int(simulacoes), int(semente_aleatoria))
    if chave_sir in _CACHE_SIR:
        return _CACHE_SIR[chave_sir]

    evolucao = evolucao_sir(
        g, semente_no, beta, gamma=gamma, rodadas=max(1, int(simulacoes)), semente=semente_aleatoria
    )
    estados = dict(evolucao["estados"])
    estado_semente = estados.get(semente_no, "S")
    estados[semente_no] = "SEED"
    res = {
        "alcance_medio": evolucao["alcance"],
        "curva_s": evolucao["curva_s"],
        "curva_i": evolucao["curva_i"],
        "curva_r": evolucao["curva_r"],
        "estados_snapshot": estados,
        "estado_semente": estado_semente,
    }
    _CACHE_SIR[chave_sir] = res
    return res


# Concordância exibida na tela: tau-b de Kendall (Frente 5) entre o alcance no SIR e as
# centralidades que a análise calcula para todos os nós (grau, núcleo e PageRank). As 6
# centralidades completas estão no experimento da Frente 5 (python -m redes.aplicacao.experimento).
# O alcance usa as mesmas rodadas da tela (100 por padrão, como no experimento): com poucas
# rodadas, o sorteio deixa o alcance ruidoso e o tau sai menor do que é.
MAX_ORIGENS_CONCORDANCIA = 2000
AMOSTRA_ORIGENS_CONCORDANCIA = 300
# Nas redes amostradas, os candidatos ao ranking por alcance incluem os primeiros de cada centralidade.
CANDIDATOS_POR_CENTRALIDADE = 30


def alcance_da_tela(
    g: Grafo, beta: float, gamma: float, semente: int, rodadas: int
) -> tuple[dict[No, float], bool]:
    """Alcance no SIR (`poder_de_espalhamento`) de todos os nós, ou de uma amostra nas redes grandes.

    Devolve (alcance, amostrado). Com mais de MAX_ORIGENS_CONCORDANCIA nós, só
    AMOSTRA_ORIGENS_CONCORDANCIA origens sorteadas (com a semente) são simuladas. Fica em cache
    por rede e parâmetros, e serve ao tau do rodapé e ao ranking da tela.
    """
    n = g.numero_de_nos()
    chave = (id(g), n, g.numero_de_arestas(), beta, gamma, semente, rodadas, "alcance")
    if chave in _CACHE_SIR:
        return _CACHE_SIR[chave]

    amostrado = n > MAX_ORIGENS_CONCORDANCIA
    origens = None
    if amostrado:
        origens = random.Random(semente).sample(list(g.nos()), AMOSTRA_ORIGENS_CONCORDANCIA)
    alcance = poder_de_espalhamento(
        g, beta, gamma=gamma, rodadas=max(1, rodadas), semente=semente, origens=origens
    )
    _CACHE_SIR[chave] = (alcance, amostrado)
    return alcance, amostrado


def ranking_por_alcance(
    g: Grafo,
    analise: dict[str, Any],
    beta: float,
    gamma: float,
    semente: int,
    rodadas: int,
    k: int = 5,
) -> tuple[list[No], dict[No, float]]:
    """Os k nós de maior alcance no SIR, com empates desfeitos pelo grau e depois pelo nó.

    É a mesma regra do experimento da Frente 5. Nas redes amostradas, os candidatos são a
    amostra mais os CANDIDATOS_POR_CENTRALIDADE primeiros do grau, do núcleo e do PageRank; os
    que ainda não têm alcance são simulados com os mesmos parâmetros. Devolve (top k, alcance).
    """
    if g.numero_de_nos() == 0:
        return [], {}
    alcance, amostrado = alcance_da_tela(g, beta, gamma, semente, rodadas)
    if amostrado:
        alcance = dict(alcance)
        candidatos: set[No] = set()
        for valores in (analise["centralidade_grau"], analise["kcore"], analise["pagerank"]):
            candidatos.update(sorted(valores, key=valores.get, reverse=True)[:CANDIDATOS_POR_CENTRALIDADE])
        faltantes = [v for v in candidatos if v not in alcance]
        if faltantes:
            alcance.update(
                poder_de_espalhamento(
                    g, beta, gamma=gamma, rodadas=max(1, rodadas), semente=semente, origens=faltantes
                )
            )
    # Desempate pelo nó: números em ordem numérica, como no experimento (nomes depois, em ordem alfabética).
    def chave(v: No) -> tuple:
        no = (0, v, "") if isinstance(v, (int, float)) else (1, 0, str(v))
        return (-alcance[v], -g.grau(v), no)

    ordem = sorted(alcance, key=chave)
    return ordem[:k], alcance


def concordancia_sir_da_tela(
    g: Grafo,
    analise: dict[str, Any],
    beta: float,
    gamma: float,
    semente: int,
    rodadas: int,
    atributos: dict[No, dict] | None = None,
) -> str:
    """Texto com o tau-b do grau, do núcleo e do PageRank contra o alcance (e, na Twitch PT,
    contra as visualizações reais).

    O alcance vem de `alcance_da_tela`: em redes com mais de MAX_ORIGENS_CONCORDANCIA nós, é o de
    uma amostra de origens, e os valores aparecem com "≈". Fica em cache por rede e parâmetros.
    """
    n = g.numero_de_nos()
    if n < 2:
        return "Concordância (τ de Kendall): rede pequena demais"

    chave = (id(g), n, g.numero_de_arestas(), beta, gamma, semente, rodadas, "concordancia")
    if chave in _CACHE_SIR:
        return _CACHE_SIR[chave]

    alcance, amostrado = alcance_da_tela(g, beta, gamma, semente, rodadas)

    centralidades = [
        ("Grau", analise["centralidade_grau"]),
        ("k-Core", analise["kcore"]),
        ("PageRank", analise["pagerank"]),
    ]
    aprox = "≈" if amostrado else "="

    def formatar(tau: float) -> str:
        return "—" if math.isnan(tau) else formatar_float_br(tau, 2)

    partes = [f"{nome} τ{aprox}{formatar(tau_de_kendall(valores, alcance))}" for nome, valores in centralidades]
    texto = "τ de Kendall com o alcance SIR: " + " • ".join(partes)

    if atributos:
        visualizacoes = {v: dados["visualizacoes"] for v, dados in atributos.items() if "visualizacoes" in dados}
        if visualizacoes:
            partes_w = [f"{nome} τ={formatar(tau_de_kendall(valores, visualizacoes))}" for nome, valores in centralidades]
            texto += " | com as visualizações reais: " + " • ".join(partes_w)

    _CACHE_SIR[chave] = texto
    return texto


# ---------------------------------------------------------------------------
# 2. Leitura das 4 bases reais homologadas e de arquivos importados
# ---------------------------------------------------------------------------
def _contar_lacos_lista_arestas(caminho_arquivo: Any, compactado_gz: bool = False) -> int:
    """Conta quantos laços (v, v) existiam no arquivo bruto antes da filtragem do leitor."""
    try:
        lacos = 0
        abridor = (
            gzip.open(caminho_arquivo, "rt", encoding="utf-8")
            if compactado_gz
            else open(caminho_arquivo, encoding="utf-8")
        )
        with abridor as arq:
            for linha in arq:
                linha = linha.strip()
                if not linha or linha.startswith("#"):
                    continue
                partes = linha.split()
                if len(partes) >= 2 and partes[0] == partes[1]:
                    lacos += 1
        return lacos
    except OSError:
        return 0


def _contar_lacos_csv(caminho_arquivo: Any, col_u: str, col_v: str) -> int:
    """Conta quantos laços (v, v) existiam num arquivo CSV bruto."""
    try:
        lacos = 0
        with open(caminho_arquivo, newline="", encoding="utf-8") as arq:
            for linha in csv.DictReader(arq):
                if linha.get(col_u) == linha.get(col_v):
                    lacos += 1
        return lacos
    except OSError:
        return 0


def carregar_base_homologada(chave: str) -> tuple[Grafo, dict[str, Any]]:
    """Carrega uma das 4 bases reais usando `redes.leitores.bases` e devolve (grafo, metadados)."""
    if chave in _CACHE_BASES_BRUTAS:
        return _CACHE_BASES_BRUTAS[chave]

    if chave == "karate":
        caminho = RAIZ / "tests/dados/karate_arestas.txt"
        g = carregar_karate(caminho)
        clubes = carregar_clubes_karate()
        lacos = _contar_lacos_lista_arestas(caminho)
        meta = {
            "chave": "karate",
            "nome": "Karate Club",
            "tag": "Real",
            "vertices": g.numero_de_nos(),
            "arestas": g.numero_de_arestas(),
            "vertices_str": formatar_int_br(g.numero_de_nos()),
            "arestas_str": formatar_int_br(g.numero_de_arestas()),
            "lacos": str(lacos),
            "comunidades_reais": f"{len(set(clubes.values()))} Facções Reais (Ativo)",
            "gabarito_comunidades": clubes,
            "origem": "Origem: tests/dados/karate_arestas.txt",
            "ponderado_padrao": False,
            "direcionado_padrao": False,
            "resumo_curto": f"{formatar_int_br(g.numero_de_nos())} nós • {formatar_int_br(g.numero_de_arestas())} arestas",
            "disponivel": True,
        }
        _CACHE_BASES_BRUTAS[chave] = (g, meta)
        return g, meta

    if chave == "thrones":
        caminho = RAIZ / "dados/brutos/asoiaf-book3-edges.csv"
        if not caminho.exists():
            raise FileNotFoundError(f"Arquivo não encontrado: {caminho}")
        g = carregar_thrones(caminho)
        lacos = _contar_lacos_csv(caminho, "Source", "Target")
        meta = {
            "chave": "thrones",
            "nome": "Network of Thrones",
            "tag": "CSV",
            "vertices": g.numero_de_nos(),
            "arestas": g.numero_de_arestas(),
            "vertices_str": formatar_int_br(g.numero_de_nos()),
            "arestas_str": formatar_int_br(g.numero_de_arestas()),
            "lacos": str(lacos),
            "comunidades_reais": "Não Disponível",
            "gabarito_comunidades": None,
            "origem": "Origem: dados/brutos/asoiaf-book3-edges.csv",
            "ponderado_padrao": True,
            "direcionado_padrao": False,
            "resumo_curto": f"{formatar_int_br(g.numero_de_nos())} nós • {formatar_int_br(g.numero_de_arestas())} arestas",
            "disponivel": True,
        }
        _CACHE_BASES_BRUTAS[chave] = (g, meta)
        return g, meta

    if chave == "twitch":
        pasta = RAIZ / "dados/brutos/twitch/PTBR"
        caminho_arestas = pasta / "musae_PTBR_edges.csv"
        if not caminho_arestas.exists():
            raise FileNotFoundError(f"Arquivo não encontrado: {caminho_arestas}")
        g, atributos = carregar_twitch_ptbr(pasta)
        lacos = _contar_lacos_csv(caminho_arestas, "from", "to")
        meta = {
            "chave": "twitch",
            "nome": "Twitch PT",
            "tag": "SNAP",
            "vertices": g.numero_de_nos(),
            "arestas": g.numero_de_arestas(),
            "vertices_str": formatar_int_br(g.numero_de_nos()),
            "arestas_str": formatar_int_br(g.numero_de_arestas()),
            "lacos": str(lacos),
            "comunidades_reais": "Não Disponível",
            "gabarito_comunidades": None,
            "atributos_nos": atributos,
            "origem": "Origem: dados/brutos/twitch/PTBR/musae_PTBR_edges.csv",
            "ponderado_padrao": False,
            "direcionado_padrao": False,
            "resumo_curto": f"{formatar_int_br(g.numero_de_nos())} nós • {formatar_int_br(g.numero_de_arestas())} arestas",
            "disponivel": True,
        }
        _CACHE_BASES_BRUTAS[chave] = (g, meta)
        return g, meta

    if chave == "facebook":
        caminho = RAIZ / "dados/brutos/facebook_combined.txt.gz"
        if not caminho.exists():
            raise FileNotFoundError(f"Arquivo não encontrado: {caminho}")
        g = carregar_facebook(caminho)
        lacos = _contar_lacos_lista_arestas(caminho, compactado_gz=True)
        meta = {
            "chave": "facebook",
            "nome": "ego-Facebook",
            "tag": "SNAP",
            "vertices": g.numero_de_nos(),
            "arestas": g.numero_de_arestas(),
            "vertices_str": formatar_int_br(g.numero_de_nos()),
            "arestas_str": formatar_int_br(g.numero_de_arestas()),
            "lacos": str(lacos),
            "comunidades_reais": "Não Disponível",
            "gabarito_comunidades": None,
            "origem": "Origem: dados/brutos/facebook_combined.txt.gz",
            "ponderado_padrao": False,
            "direcionado_padrao": False,
            "resumo_curto": f"{formatar_int_br(g.numero_de_nos())} nós • {formatar_int_br(g.numero_de_arestas())} arestas",
            "disponivel": True,
        }
        _CACHE_BASES_BRUTAS[chave] = (g, meta)
        return g, meta

    raise KeyError(f"Base desconhecida: {chave}")


def obter_catalogo_bases_reais() -> dict[str, dict[str, Any]]:
    """Inspeciona as 4 bases reais e devolve seus metadados reais de leitura."""
    catalogo: dict[str, dict[str, Any]] = {}
    for chave in ("facebook", "twitch", "thrones", "karate"):
        try:
            _, meta = carregar_base_homologada(chave)
            catalogo[chave] = {
                k: v
                for k, v in meta.items()
                if k not in ("gabarito_comunidades", "atributos_nos")
            }
        except FileNotFoundError:
            # Caso alguma base externa de dados/brutos/ não esteja presente no disco
            catalogo[chave] = {
                "chave": chave,
                "nome": chave,
                "tag": "SNAP",
                "vertices": 0,
                "arestas": 0,
                "vertices_str": "0",
                "arestas_str": "0",
                "lacos": "0",
                "comunidades_reais": "Arquivo ausente em dados/brutos/",
                "origem": f"Baixe em dados/brutos/ ({chave})",
                "ponderado_padrao": chave == "thrones",
                "direcionado_padrao": False,
                "resumo_curto": "Baixar em dados/brutos/",
                "disponivel": False,
            }
    return catalogo


def construir_grafo_com_opcoes(
    g_base: Grafo, direcionado: bool, ponderado: bool
) -> Grafo:
    """Reconstrói um Grafo respeitando as opções de direcionamento e ponderação escolhidas."""
    if not direcionado and g_base.direcionado is False:
        if ponderado:
            return g_base
        # Se a base já possui todas as arestas com peso 1.0, retorna sem copiar
        amostra = next(g_base.arestas(), None)
        if amostra is None or amostra[2] == 1.0:
            return g_base

    g_novo = Grafo(direcionado=direcionado)
    for v in g_base.nos():
        g_novo.adicionar_no(v)
    for u, v, peso in g_base.arestas():
        g_novo.adicionar_aresta(u, v, float(peso) if ponderado else 1.0)
    return g_novo


def _converter_id_no(texto: str) -> int | str:
    """Converte string numérica para int, ou mantém como string (ex.: 'Tyrion-Lannister')."""
    limpo = texto.strip()
    try:
        return int(limpo)
    except ValueError:
        return limpo


def ler_grafo_de_texto_importado(
    nome_arquivo: str,
    conteudo: str,
    direcionado: bool = False,
    ponderado: bool = False,
) -> tuple[Grafo, int]:
    """Lê um Grafo real a partir do conteúdo textual de um arquivo (.txt ou .csv) e conta laços descartados."""
    g = Grafo(direcionado=direcionado)
    lacos_ignorados = 0
    linhas_brutas = [
        ln.strip()
        for ln in conteudo.splitlines()
        if ln.strip() and not ln.strip().startswith("#")
    ]
    if not linhas_brutas:
        raise ValueError("O arquivo selecionado está vazio ou não contém arestas válidas.")

    eh_csv = nome_arquivo.lower().endswith(".csv") or ("," in linhas_brutas[0])
    if eh_csv:
        leitor = csv.reader(io.StringIO("\n".join(linhas_brutas)))
        linhas_csv = [row for row in leitor if len(row) >= 2]
        if not linhas_csv:
            raise ValueError("Nenhuma linha com ao menos duas colunas encontrada no CSV.")

        # Detecta cabeçalho textual
        primeira = [c.strip().lower() for c in linhas_csv[0]]
        tem_cabecalho = any(
            col in ("source", "target", "from", "to", "origem", "destino", "u", "v", "id1", "id2")
            for col in primeira
        )
        idx_u, idx_v, idx_peso = 0, 1, 2
        inicio = 0
        if tem_cabecalho:
            inicio = 1
            for i, col in enumerate(primeira):
                if col in ("source", "from", "origem", "u", "id1"):
                    idx_u = i
                elif col in ("target", "to", "destino", "v", "id2"):
                    idx_v = i
                elif col in ("weight", "peso", "w"):
                    idx_peso = i

        for row in linhas_csv[inicio:]:
            if len(row) <= max(idx_u, idx_v):
                continue
            u = _converter_id_no(row[idx_u])
            v = _converter_id_no(row[idx_v])
            if u == v:
                lacos_ignorados += 1
                continue
            peso = 1.0
            if ponderado and len(row) > idx_peso:
                try:
                    peso = float(row[idx_peso])
                except ValueError:
                    peso = 1.0
            g.adicionar_aresta(u, v, peso)
    else:
        for linha in linhas_brutas:
            partes = linha.split()
            if len(partes) < 2:
                continue
            u = _converter_id_no(partes[0])
            v = _converter_id_no(partes[1])
            if u == v:
                lacos_ignorados += 1
                continue
            peso = 1.0
            if ponderado and len(partes) >= 3:
                try:
                    peso = float(partes[2])
                except ValueError:
                    peso = 1.0
            g.adicionar_aresta(u, v, peso)

    if g.numero_de_nos() == 0 or g.numero_de_arestas() == 0:
        raise ValueError("Nenhuma aresta válida pôde ser extraída do arquivo informado.")

    return g, lacos_ignorados


# ---------------------------------------------------------------------------
# 3. Reconstrução de Caminhos Reais (Dijkstra, BFS, DFS) sobre o Grafo
# ---------------------------------------------------------------------------
def resolver_no_no_grafo(g: Grafo, entrada: Any) -> No | None:
    """Localiza o identificador real de um nó no Grafo a partir do texto informado pelo usuário."""
    if entrada is None:
        return None
    if entrada in g:
        return entrada

    texto = str(entrada).strip()
    if texto.startswith("#"):
        texto = texto[1:].strip()

    if texto in g:
        return texto

    try:
        como_int = int(texto)
        if como_int in g:
            return como_int
    except ValueError:
        pass

    # Busca case-insensitive para grafos com nomes (ex.: Network of Thrones)
    texto_lower = texto.lower()
    for v in g.nos():
        if str(v).lower() == texto_lower:
            return v
    return None


def calcular_caminho_real(
    g: Grafo,
    algoritmo: str,
    origem_input: Any,
    destino_input: Any,
    inverter_peso_interacao: bool = False,
) -> dict[str, Any]:
    """Calcula o caminho entre dois nós usando `bfs`, `ordem_dfs` ou `dijkstra` de `redes.metricas.caminhos`."""
    u = resolver_no_no_grafo(g, origem_input)
    v = resolver_no_no_grafo(g, destino_input)

    if u is None or v is None:
        exemplos = ", ".join(formatar_rotulo_no(x) for x in list(g.nos())[:5])
        return {
            "encontrado": False,
            "algoritmo": algoritmo,
            "erro_titulo": "Vértice Inexistente no Grafo Ativo",
            "erro_mensagem": f"Informe vértices válidos pertencentes ao grafo ativo (ex.: {exemplos}).",
            "rota": [],
            "rota_rotulos": [],
            "saltos": 0,
            "custo_total": 0.0,
        }

    if u == v:
        return {
            "encontrado": False,
            "algoritmo": algoritmo,
            "erro_titulo": "Origem e Destino Idênticos",
            "erro_mensagem": "Selecione dois vértices distintos para calcular o caminho na rede.",
            "rota": [],
            "rota_rotulos": [],
            "saltos": 0,
            "custo_total": 0.0,
        }

    if algoritmo == "BFS":
        distancias = bfs(g, u)
        if v not in distancias:
            return _resposta_sem_caminho(algoritmo, u, v)

        # Reconstrói um caminho mínimo em número de arestas voltando de v até u pelas camadas da BFS
        fontes_bfs = g.predecessores if g.direcionado else g.vizinhos
        caminho_rev: list[No] = [v]
        atual = v
        while atual != u:
            d_atual = distancias[atual]
            anterior = next(
                w for w in fontes_bfs(atual) if distancias.get(w) == d_atual - 1
            )
            caminho_rev.append(anterior)
            atual = anterior

        caminho = list(reversed(caminho_rev))
        custo = float(len(caminho) - 1)
        return _formatar_resposta_caminho(algoritmo, caminho, custo)

    if algoritmo == "DFS":
        ordem = ordem_dfs(g, u)
        if v not in set(ordem):
            return _resposta_sem_caminho(algoritmo, u, v)

        # Reconstrói o caminho percorrido na árvore de busca em profundidade
        visitados: set[No] = set()
        pai: dict[No, No] = {}
        pilha: list[No] = [u]
        while pilha:
            atual = pilha.pop()
            if atual in visitados:
                continue
            visitados.add(atual)
            if atual == v:
                break
            for w in reversed(list(g.vizinhos(atual))):
                if w not in visitados:
                    pai[w] = atual
                    pilha.append(w)

        caminho_dfs: list[No] = [v]
        while caminho_dfs[-1] != u:
            caminho_dfs.append(pai[caminho_dfs[-1]])
        caminho_dfs.reverse()
        custo = sum(
            g.peso(caminho_dfs[i], caminho_dfs[i + 1])
            for i in range(len(caminho_dfs) - 1)
        )
        return _formatar_resposta_caminho(algoritmo, caminho_dfs, custo)

    # Algoritmo padrão: Dijkstra (redes.metricas.caminhos.dijkstra)
    fn_dist = (lambda p: 1.0 / p) if inverter_peso_interacao else None
    distancias_dijk = dijkstra(g, u, distancia=fn_dist)
    if v not in distancias_dijk:
        return _resposta_sem_caminho("Dijkstra", u, v)

    # Reconstrói o caminho mínimo a partir das distâncias exatas de Dijkstra
    caminho_reverso: list[No] = [v]
    atual = v
    visitados_rec: set[No] = {v}
    fontes = g.predecessores if g.direcionado else g.vizinhos

    while atual != u:
        d_atual = distancias_dijk[atual]
        melhor_ant: No | None = None
        menor_erro = float("inf")
        for ant in fontes(atual):
            if ant in distancias_dijk and ant not in visitados_rec:
                peso = g.peso(ant, atual)
                comp = fn_dist(peso) if fn_dist is not None else peso
                erro = abs((distancias_dijk[ant] + comp) - d_atual)
                if erro < menor_erro:
                    menor_erro = erro
                    melhor_ant = ant
        if melhor_ant is None:
            break
        caminho_reverso.append(melhor_ant)
        visitados_rec.add(melhor_ant)
        atual = melhor_ant

    caminho_dijk = list(reversed(caminho_reverso))
    return _formatar_resposta_caminho("Dijkstra", caminho_dijk, distancias_dijk[v])


def _resposta_sem_caminho(algoritmo: str, u: No, v: No) -> dict[str, Any]:
    return {
        "encontrado": False,
        "algoritmo": algoritmo,
        "erro_titulo": "Caminho Inexistente entre os Vértices",
        "erro_mensagem": (
            f"Não existe rota conectando {formatar_rotulo_no(u)} até "
            f"{formatar_rotulo_no(v)} (componentes conexas distintas)."
        ),
        "rota": [],
        "rota_rotulos": [],
        "saltos": 0,
        "custo_total": 0.0,
    }


def _formatar_resposta_caminho(
    algoritmo: str, caminho: list[No], custo_total: float
) -> dict[str, Any]:
    saltos = max(0, len(caminho) - 1)
    return {
        "encontrado": True,
        "algoritmo": algoritmo,
        "rota": [str(x) for x in caminho],
        "rota_rotulos": [formatar_rotulo_no(x) for x in caminho],
        "saltos": saltos,
        "custo_total": round(float(custo_total), 4),
        "resumo_header": f"{algoritmo}: {saltos} {'salto' if saltos == 1 else 'saltos'} (Custo Total = {custo_total:.2f})",
    }


# ---------------------------------------------------------------------------
# 4. Análise Estrutural, Comunidades, SIR e Subgrafo Visual (Fruchterman–Reingold)
# ---------------------------------------------------------------------------
def construir_histograma_grau(g: Grafo) -> list[dict[str, Any]]:
    """Constrói as 6 faixas do histograma P(k) a partir de `distribuicao_de_graus(g)`."""
    dist = distribuicao_de_graus(g)
    n = g.numero_de_nos()
    if n == 0 or not dist:
        return []

    max_k = max(dist.keys())
    cores = [
        PALETA["deepnavy"],
        PALETA["deepnavy"],
        PALETA["petrol"],
        PALETA["petrol"],
        PALETA["mutedgreen"],
        PALETA["mutedgreen"],
    ]

    if max_k > 60:
        faixas = [
            ("1-15", 0, 15),
            ("16-30", 16, 30),
            ("31-60", 31, 60),
            ("61-120", 61, 120),
            ("121-250", 121, 250),
            (">250", 251, max_k + 1),
        ]
    elif max_k > 18:
        passo = max(2, math.ceil(max_k / 6))
        faixas = []
        ini = 0
        for i in range(6):
            fim = ini + passo - 1 if i < 5 else max_k
            rot = f">{ini - 1}" if i == 5 else f"{max(1, ini)}-{fim}"
            faixas.append((rot, ini, fim))
            ini = fim + 1
    else:
        faixas = [
            ("1-2", 0, 2),
            ("3-4", 3, 4),
            ("5-6", 5, 6),
            ("7-9", 7, 9),
            ("10-12", 10, 12),
            (">12", 13, max(14, max_k)),
        ]

    contagens: list[int] = []
    for _, k_min, k_max in faixas:
        soma_faixa = sum(qtd for k, qtd in dist.items() if k_min <= k <= k_max)
        contagens.append(soma_faixa)

    maior_contagem = max(max(contagens), 1)
    resultado: list[dict[str, Any]] = []
    for idx, ((rot_faixa, _, _), qtd) in enumerate(zip(faixas, contagens)):
        pct_real = round((qtd / n) * 100.0, 1)
        altura_barra = max(6, round((qtd / maior_contagem) * 92)) if qtd > 0 else 3
        pct_txt = f"{pct_real:.0f}%" if pct_real >= 10 else f"{pct_real:.1f}%".replace(".", ",")
        resultado.append(
            {
                "faixa": rot_faixa,
                "qtd": qtd,
                "percentual_real": pct_real,
                "altura_barra": altura_barra,
                "rotulo": f"{rot_faixa} ({qtd} • {pct_txt})",
                "cor": cores[idx],
            }
        )
    return resultado


def _closeness_e_harmonica_no(g: Grafo, v: No) -> tuple[float, float]:
    """Calcula (closeness, harmonica) de um único nó v via `bfs(g, v)`."""
    n = g.numero_de_nos()
    if n < 2:
        return 0.0, 0.0
    dist = bfs(g, v)
    alcancados = len(dist) - 1
    soma = sum(dist.values())
    clos = ((alcancados / (n - 1)) * (alcancados / soma)) if alcancados > 0 and soma > 0 else 0.0
    harm = sum(1.0 / d for d in dist.values() if d > 0)
    return clos, harm


def obter_analise_base_cacheada(
    g: Grafo,
    chave_cache: tuple[Any, ...],
    gabarito_comunidades: dict[No, int] | None = None,
    semente: int = 42,
) -> dict[str, Any]:
    """Executa e armazena em cache as métricas estruturais e partições do Grafo g."""
    if chave_cache in _CACHE_ANALISES:
        return _CACHE_ANALISES[chave_cache]

    n = g.numero_de_nos()
    m = g.numero_de_arestas()
    amostra_caminhos = None if n <= 400 else 15
    amostra_brandes = None if n <= 350 else 15

    gm = grau_medio(g)
    den = densidade(g)
    comps = componentes_conexas(g)
    maior_comp = max((len(c) for c in comps), default=0)
    pct_maior_comp = (100.0 * maior_comp / n) if n > 0 else 0.0

    dm = distancia_media(g, amostra=amostra_caminhos, semente=semente) if m > 0 else 0.0
    diam = diametro(g, amostra=amostra_caminhos, semente=semente) if m > 0 else 0

    pr_map = pagerank(g) if n > 0 else {}
    kcore_map = numero_de_nucleo(g) if n > 0 else {}
    bet_map = intermediacao(g, k=amostra_brandes, semente=semente) if n > 0 else {}
    deg_cent_map = centralidade_de_grau(g) if n > 0 else {}

    # Ordena os nós por grau e PageRank para identificar os principais hubs da rede
    nos_ordenados = sorted(
        g.nos(),
        key=lambda v: (g.grau(v), pr_map.get(v, 0.0), kcore_map.get(v, 0)),
        reverse=True,
    )

    # Closeness e Harmônica: grafo inteiro quando n <= 350, ou exato via BFS para os top 8 nós
    if n <= 350:
        clos_map = proximidade(g)
        harm_map = harmonica(g)
    else:
        clos_map = {}
        harm_map = {}
        for v in nos_ordenados[:8]:
            c_val, h_val = _closeness_e_harmonica_no(g, v)
            clos_map[v] = c_val
            harm_map[v] = h_val

    # Agrupamento e Triângulos
    clust_medio, trans_global, total_tri = calcular_agrupamento_e_triangulos(g)

    # Comunidades (Louvain e Propagação de Rótulos)
    part_louvain, q_louvain = executar_louvain(g, semente=semente)
    part_lpa, q_lpa = executar_propagacao_rotulos(g, semente=semente)

    if gabarito_comunidades:
        nmi_louvain, ari_louvain = calcular_nmi_e_ari(part_louvain, gabarito_comunidades)
        nmi_lpa, ari_lpa = calcular_nmi_e_ari(part_lpa, gabarito_comunidades)
        rotulo_comparacao_gt = "Gabarito Real (Karate Club)"
    else:
        # Quando a base não possui gabarito externo, compara concordância entre Louvain e LPA
        nmi_louvain, ari_louvain = calcular_nmi_e_ari(part_louvain, part_lpa)
        nmi_lpa, ari_lpa = nmi_louvain, ari_louvain
        rotulo_comparacao_gt = "Concordância Louvain × LPA"

    histograma = construir_histograma_grau(g)

    analise = {
        "grau_medio": gm,
        "densidade": den,
        "distancia_media": dm,
        "diametro": diam,
        "maior_componente_qtd": maior_comp,
        "maior_componente_pct": pct_maior_comp,
        "num_componentes": len(comps),
        "pagerank": pr_map,
        "kcore": kcore_map,
        "betweenness": bet_map,
        "centralidade_grau": deg_cent_map,
        "closeness": clos_map,
        "harmonica": harm_map,
        "nos_ordenados": nos_ordenados,
        "clustering_medio": clust_medio,
        "transitividade_global": trans_global,
        "total_triangulos": total_tri,
        "particao_louvain": part_louvain,
        "q_louvain": q_louvain,
        "nmi_louvain": nmi_louvain,
        "ari_louvain": ari_louvain,
        "particao_lpa": part_lpa,
        "q_lpa": q_lpa,
        "nmi_lpa": nmi_lpa,
        "ari_lpa": ari_lpa,
        "rotulo_comparacao_gt": rotulo_comparacao_gt,
        "histograma_grau": histograma,
    }
    _CACHE_ANALISES[chave_cache] = analise
    return analise


def resumir_comunidades_reais(
    g: Grafo, particao: dict[No, int], max_clusters_legenda: int = 5
) -> tuple[list[dict[str, Any]], int, dict[No, int]]:
    """Agrupa os nós por comunidade, calcula hub central e densidade interna real de cada cluster."""
    membros_por_com: dict[int, list[No]] = defaultdict(list)
    for v, cid in particao.items():
        membros_por_com[cid].append(v)

    clusters_ordenados = sorted(
        membros_por_com.values(), key=lambda lista: len(lista), reverse=True
    )
    total_clusters = len(clusters_ordenados)

    nomes_cores = ["Ciano", "Esmeralda", "Âmbar", "Violeta", "Coral"]
    lista_resumo: list[dict[str, Any]] = []
    mapa_cluster_visual: dict[No, int] = {}

    for idx, membros in enumerate(clusters_ordenados):
        cor_idx = min(idx, max_clusters_legenda - 1)
        for v in membros:
            mapa_cluster_visual[v] = cor_idx

        if idx < max_clusters_legenda:
            hub = max(membros, key=lambda v: g.grau(v))
            conj = set(membros)
            n_c = len(membros)
            arestas_internas = 0
            for u in membros:
                for w in g.vizinhos(u):
                    if w in conj and u != w:
                        arestas_internas += 1
            if not g.direcionado:
                arestas_internas //= 2
            pares_possiveis = n_c * (n_c - 1) if g.direcionado else (n_c * (n_c - 1)) // 2
            dens_interna = (arestas_internas / pares_possiveis) if pares_possiveis > 0 else 0.0

            lista_resumo.append(
                {
                    "indice": idx,
                    "nome": f"Comunidade {idx + 1} ({nomes_cores[idx]})",
                    "hub": str(hub),
                    "hub_rotulo": formatar_rotulo_no(hub),
                    "densidade": formatar_float_br(dens_interna, 2),
                    "qtd_nos": n_c,
                    "cor": CORES_COMUNIDADES[idx],
                    "meta": f"Hub Central: {formatar_rotulo_no(hub)} • Densidade: {formatar_float_br(dens_interna, 2)}",
                }
            )

    return lista_resumo, total_clusters, mapa_cluster_visual


def construir_subgrafo_visual_e_posicoes(
    g: Grafo,
    analise: dict[str, Any],
    mapa_cluster_visual: dict[No, int],
    comunidades_resumo: list[dict[str, Any]],
    iteracoes_fr: int = 35,
    semente_fr: int = 42,
) -> tuple[list[dict[str, Any]], list[list[int]]]:
    """Posiciona TODOS os nós e arestas do Grafo g via Fruchterman–Reingold para o mapa interativo."""
    n = g.numero_de_nos()
    if n == 0:
        return [], []

    chave_layout = (id(g), n, g.numero_de_arestas(), int(iteracoes_fr), int(semente_fr))
    if chave_layout in _CACHE_LAYOUTS:
        posicoes = _CACHE_LAYOUTS[chave_layout]
    else:
        iters = min(int(iteracoes_fr), 25 if n > 500 else 45)
        posicoes = fruchterman_reingold(g, iteracoes=iters, semente=semente_fr)
        _CACHE_LAYOUTS[chave_layout] = posicoes

    paleta_nos = [PALETA["deepnavy"], PALETA["petrol"], PALETA["mutedgreen"], PALETA["sage"]]
    pr_map = analise["pagerank"]
    bet_map = analise["betweenness"]
    kcore_map = analise["kcore"]

    # Centros espaciais dos clusters para a visualização particionada de comunidades
    centros_clusters = [
        (-0.52, -0.42),
        (0.52, -0.44),
        (0.0, 0.04),
        (-0.50, 0.48),
        (0.52, 0.46),
    ]
    hubs_set = {str(c["hub"]) for c in comunidades_resumo}

    nos_ordenados = analise["nos_ordenados"]
    indice_visual: dict[No, int] = {v: idx for idx, v in enumerate(nos_ordenados)}

    nos_payload: list[dict[str, Any]] = []
    for idx, v in enumerate(nos_ordenados):
        px, py = posicoes.get(v, (0.0, 0.0))
        c_vis = int(mapa_cluster_visual.get(v, idx % 5))
        ccx, ccy = centros_clusters[c_vis % len(centros_clusters)]
        eh_hub = str(v) in hubs_set

        # Coordenada agrupada por comunidade mantendo a vizinhança relativa do Fruchterman–Reingold
        if eh_hub:
            cx_com, cy_com = ccx, ccy
        else:
            cx_com = ccx + px * 0.28
            cy_com = ccy + py * 0.28

        nos_payload.append(
            {
                "id": str(v),
                "rotulo": formatar_rotulo_no(v),
                "subtitulo": f"Nó {v}" if isinstance(v, str) else f"User_{v}",
                "x": round(float(px), 4),
                "y": round(float(py), 4),
                "cx": round(float(cx_com), 4),
                "cy": round(float(cy_com), 4),
                "is_hub": eh_hub,
                "degree": g.grau(v),
                "pagerank": f"{pr_map.get(v, 0.0):.4f}",
                "betweenness": f"{bet_map.get(v, 0.0):.4f}",
                "kcore": int(kcore_map.get(v, 0)),
                "comm": c_vis,
                "color": paleta_nos[c_vis % len(paleta_nos)],
                "comm_color": CORES_COMUNIDADES[c_vis % len(CORES_COMUNIDADES)],
            }
        )

    # Todas as arestas do grafo representadas por pares de índices [u_idx, v_idx] em nos_payload
    arestas_payload: list[list[int]] = []
    for u, w, _ in g.arestas():
        if u != w and u in indice_visual and w in indice_visual:
            arestas_payload.append([indice_visual[u], indice_visual[w]])

    return nos_payload, arestas_payload


# ---------------------------------------------------------------------------
# 5. Gerenciador de Sessão do Backend e Servidor HTTP Local para a UI
# ---------------------------------------------------------------------------
class GerenciadorSessaoBackend:
    """Mantém o Grafo ativo e processa todas as ações da interface sobre o pacote `redes`."""

    def __init__(self) -> None:
        self.lock = threading.Lock()
        self.chave_base_selecionada = "facebook"
        self.direcionado = False
        self.ponderado = False
        self.semente_layout = 42
        self.iteracoes_layout = 50
        self.algoritmo_comunidade = "Louvain"
        self.semente_comunidade = 42
        # Parâmetros do SIR da Frente 5: gamma = 1 (cada infectado tenta transmitir uma vez),
        # 100 rodadas e beta = 1,5 x limiar epidêmico da rede ativa (0,012 na Twitch PT),
        # recalculado a cada troca de rede em _ajustar_beta_sir.
        self.sir_beta = 0.012
        self.sir_beta_c: float | None = None
        self.sir_gamma = 1.0
        self.sir_simulacoes = 100
        self.sir_seed = 2026  # a mesma semente do experimento: na Twitch PT, o ranking é o do relatório
        self.sir_semente_no: No | None = None
        # True enquanto o usuário não escolheu a semente: aí ela é o nó de maior alcance.
        self.sir_semente_automatica = True
        self.caminho_algoritmo = "Dijkstra"
        self.caminho_origem: No | None = None
        self.caminho_destino: No | None = None
        self.arquivo_importado_nome: str | None = None
        self.arquivo_importado_meta: str | None = None

        self.grafo_ativo: Grafo = Grafo()
        self.meta_ativa: dict[str, Any] = {}
        self.ultimo_caminho: dict[str, Any] = {}

        # Inicializa carregando ego-Facebook (se baixado em dados/brutos/) ou Karate Club
        try:
            self.ativar_base_homologada("facebook", direcionado=False, ponderado=False)
        except FileNotFoundError:
            self.ativar_base_homologada("karate", direcionado=False, ponderado=False)

    def _ajustar_beta_sir(self, g: Grafo) -> None:
        """Põe o beta do SIR em 1,5 x limiar epidêmico da rede nova, com 3 casas (0,012 na Twitch PT).

        No grafo direcionado o limiar não está definido; ele é calculado sobre a mesma rede sem
        a direção das arestas.
        """
        if g.direcionado:
            # O limiar só está definido sem direção: usa a mesma rede, sem a direção das arestas.
            nao_direcionado = Grafo.de_arestas((v, w) for v, w, _ in g.arestas())
            for v in g.nos():
                nao_direcionado.adicionar_no(v)
            g = nao_direcionado
        try:
            self.sir_beta_c = limiar_epidemico(g)
            self.sir_beta = round(beta_recomendado(g), 3)
        except ValueError:
            self.sir_beta_c = None

    def _definir_endpoints_padrao(self, g: Grafo, nos_ordenados: list[No]) -> None:
        """Escolhe dois nós reais conectados a pelo menos 2 saltos de distância como rota inicial."""
        self._ajustar_beta_sir(g)
        self.sir_semente_automatica = True
        if not nos_ordenados:
            self.caminho_origem = None
            self.caminho_destino = None
            self.sir_semente_no = None
            return

        origem = nos_ordenados[0]
        self.sir_semente_no = origem
        self.caminho_origem = origem

        dist = bfs(g, origem)
        candidatos_dist3 = [w for w, d in dist.items() if d == 3]
        candidatos_dist2 = [w for w, d in dist.items() if d == 2]
        if candidatos_dist3:
            self.caminho_destino = candidatos_dist3[0]
        elif candidatos_dist2:
            self.caminho_destino = candidatos_dist2[0]
        elif len(nos_ordenados) > 1:
            self.caminho_destino = nos_ordenados[1]
        else:
            self.caminho_destino = origem

    def ativar_base_homologada(
        self, chave: str, direcionado: bool = False, ponderado: bool = False
    ) -> dict[str, Any]:
        """Carrega uma das 4 bases reais homologadas via `redes.leitores.bases`."""
        g_bruto, meta = carregar_base_homologada(chave)
        self.chave_base_selecionada = chave
        self.direcionado = direcionado
        self.ponderado = ponderado
        self.arquivo_importado_nome = None
        self.grafo_ativo = construir_grafo_com_opcoes(g_bruto, direcionado, ponderado)
        self.meta_ativa = dict(meta)

        analise = self._obter_analise_atual()
        self._definir_endpoints_padrao(self.grafo_ativo, analise["nos_ordenados"])
        self.ultimo_caminho = calcular_caminho_real(
            self.grafo_ativo,
            self.caminho_algoritmo,
            self.caminho_origem,
            self.caminho_destino,
            inverter_peso_interacao=(chave == "thrones" and ponderado),
        )
        return self.obter_payload_completo()

    def importar_arquivo_real(
        self,
        nome_arquivo: str,
        conteudo: str,
        direcionado: bool = False,
        ponderado: bool = False,
    ) -> dict[str, Any]:
        """Constrói um Grafo real a partir de um arquivo (.txt ou .csv) enviado pelo usuário."""
        g_imp, lacos = ler_grafo_de_texto_importado(
            nome_arquivo, conteudo, direcionado=direcionado, ponderado=ponderado
        )
        nome_limpo = nome_arquivo.rsplit(".", 1)[0]
        self.direcionado = direcionado
        self.ponderado = ponderado
        self.arquivo_importado_nome = nome_arquivo
        self.arquivo_importado_meta = (
            f"{formatar_int_br(g_imp.numero_de_nos())} vértices • "
            f"{formatar_int_br(g_imp.numero_de_arestas())} arestas • "
            f"{lacos} laços ignorados"
        )
        self.grafo_ativo = g_imp
        self.meta_ativa = {
            "chave": "importado",
            "nome": nome_limpo,
            "tag": "Importado",
            "vertices": g_imp.numero_de_nos(),
            "arestas": g_imp.numero_de_arestas(),
            "vertices_str": formatar_int_br(g_imp.numero_de_nos()),
            "arestas_str": formatar_int_br(g_imp.numero_de_arestas()),
            "lacos": str(lacos),
            "comunidades_reais": "Arquivo Importado",
            "gabarito_comunidades": None,
            "origem": f"Arquivo importado: {nome_arquivo}",
            "ponderado_padrao": ponderado,
            "direcionado_padrao": direcionado,
            "resumo_curto": f"{formatar_int_br(g_imp.numero_de_nos())} nós • {formatar_int_br(g_imp.numero_de_arestas())} arestas",
        }

        analise = self._obter_analise_atual()
        self._definir_endpoints_padrao(self.grafo_ativo, analise["nos_ordenados"])
        self.ultimo_caminho = calcular_caminho_real(
            self.grafo_ativo,
            self.caminho_algoritmo,
            self.caminho_origem,
            self.caminho_destino,
        )
        return self.obter_payload_completo()

    def gerar_rede_sintetica_real(
        self, modelo: str, n: int, param: float, semente: int
    ) -> dict[str, Any]:
        """Gera um Grafo sintético usando `barabasi_albert`, `erdos_renyi` ou `watts_strogatz`."""
        n_int = int(n)
        seed_int = int(semente)
        if n_int < 10:
            raise ValueError("O número de nós (n) deve ser pelo menos 10.")

        if modelo == "ba":
            m_int = int(param)
            if not (1 <= m_int < n_int):
                raise ValueError("No modelo Barabási–Albert, use 1 <= m < n.")
            g_sint = barabasi_albert(n_int, m_int, semente=seed_int)
            nome_mod = f"Sintético Barabási–Albert (n={n_int}, m={m_int})"
            origem_txt = f"Gerador: barabasi_albert(n={n_int}, m={m_int}, semente={seed_int})"
        elif modelo == "er":
            p_flt = float(param)
            if not (0.0 <= p_flt <= 1.0):
                raise ValueError("No modelo Erdős–Rényi, use 0 <= p <= 1.")
            g_sint = erdos_renyi(n_int, p_flt, semente=seed_int)
            nome_mod = f"Sintético Erdős–Rényi (n={n_int}, p={p_flt})"
            origem_txt = f"Gerador: erdos_renyi(n={n_int}, p={p_flt}, semente={seed_int})"
        else:
            k_int = int(param)
            if k_int % 2 != 0:
                k_int += 1
            if not (2 <= k_int < n_int):
                raise ValueError("No modelo Watts–Strogatz, use k par com 2 <= k < n.")
            g_sint = watts_strogatz(n_int, k_int, 0.15, semente=seed_int)
            nome_mod = f"Sintético Watts–Strogatz (n={n_int}, k={k_int})"
            origem_txt = f"Gerador: watts_strogatz(n={n_int}, k={k_int}, p=0.15, semente={seed_int})"

        self.direcionado = False
        self.ponderado = False
        self.semente_layout = seed_int
        self.semente_comunidade = seed_int
        self.sir_seed = seed_int
        self.arquivo_importado_nome = None
        self.grafo_ativo = g_sint
        self.meta_ativa = {
            "chave": f"sint_{modelo}",
            "nome": nome_mod,
            "tag": "Sintético",
            "vertices": g_sint.numero_de_nos(),
            "arestas": g_sint.numero_de_arestas(),
            "vertices_str": formatar_int_br(g_sint.numero_de_nos()),
            "arestas_str": formatar_int_br(g_sint.numero_de_arestas()),
            "lacos": "0",
            "comunidades_reais": "Modelo Sintético",
            "gabarito_comunidades": None,
            "origem": origem_txt,
            "ponderado_padrao": False,
            "direcionado_padrao": False,
            "resumo_curto": f"{formatar_int_br(g_sint.numero_de_nos())} nós • {formatar_int_br(g_sint.numero_de_arestas())} arestas",
        }

        analise = self._obter_analise_atual()
        self._definir_endpoints_padrao(self.grafo_ativo, analise["nos_ordenados"])
        self.ultimo_caminho = calcular_caminho_real(
            self.grafo_ativo,
            self.caminho_algoritmo,
            self.caminho_origem,
            self.caminho_destino,
        )
        return self.obter_payload_completo()

    def _obter_analise_atual(self) -> dict[str, Any]:
        chave_cache = (
            self.meta_ativa.get("nome", ""),
            self.grafo_ativo.numero_de_nos(),
            self.grafo_ativo.numero_de_arestas(),
            self.grafo_ativo.direcionado,
            self.ponderado,
            self.semente_comunidade,
        )
        return obter_analise_base_cacheada(
            self.grafo_ativo,
            chave_cache=chave_cache,
            gabarito_comunidades=self.meta_ativa.get("gabarito_comunidades"),
            semente=self.semente_comunidade,
        )

    def obter_payload_completo(self) -> dict[str, Any]:
        """Monta o payload completo de dados reais calculados pelo backend para a interface."""
        g = self.grafo_ativo
        analise = self._obter_analise_atual()

        # 1. Comunidades ativas (Louvain ou LPA)
        if self.algoritmo_comunidade == "LPA":
            particao_ativa = analise["particao_lpa"]
            q_ativo = analise["q_lpa"]
            nmi_ativo = analise["nmi_lpa"]
            ari_ativo = analise["ari_lpa"]
        else:
            particao_ativa = analise["particao_louvain"]
            q_ativo = analise["q_louvain"]
            nmi_ativo = analise["nmi_louvain"]
            ari_ativo = analise["ari_louvain"]

        comunidades_resumo, total_clusters, mapa_cluster_visual = resumir_comunidades_reais(
            g, particao_ativa
        )

        # 2. Grafo completo posicionado via Fruchterman–Reingold
        nos_visuais, arestas_visuais = construir_subgrafo_visual_e_posicoes(
            g,
            analise,
            mapa_cluster_visual,
            comunidades_resumo=comunidades_resumo,
            iteracoes_fr=self.iteracoes_layout,
            semente_fr=self.semente_layout,
        )

        # 3. Tabela de Centralidades (Top 5 vértices da rede)
        top_nos = analise["nos_ordenados"][:5]
        tabela_centralidades: list[dict[str, str]] = []
        for v in top_nos:
            tabela_centralidades.append(
                {
                    "vertice": formatar_rotulo_no(v),
                    "closeness": f"{analise['closeness'].get(v, 0.0):.4f}",
                    "harmonica": f"{analise['harmonica'].get(v, 0.0):.4f}",
                    "betweenness": f"{analise['betweenness'].get(v, 0.0):.4f}",
                    "pagerank": f"{analise['pagerank'].get(v, 0.0):.4f}",
                    "kcore": str(analise["kcore"].get(v, 0)),
                }
            )

        # 4. Top 5 Influenciadores: os de maior alcance no SIR (poder_de_espalhamento, Frente 5)
        top_influenciadores: list[dict[str, Any]] = []
        top_sir, alcance_top = ranking_por_alcance(
            g, analise, self.sir_beta, self.sir_gamma, self.sir_seed, self.sir_simulacoes
        )

        for idx, v in enumerate(top_sir):
            alc_pct = alcance_top[v] * 100.0
            rot_v = formatar_rotulo_no(v)
            top_influenciadores.append(
                {
                    "rank": f"#{idx + 1}",
                    "id": str(v),
                    "rotulo_curto": rot_v,
                    "vertice": rot_v,
                    "grau": g.grau(v),
                    "pagerank": f"{analise['pagerank'].get(v, 0.0):.4f}",
                    "kcore": int(analise["kcore"].get(v, 0)),
                    "alcance": f"{alc_pct:.1f}%".replace(".", ","),
                    "alcance_num": round(alcance_top[v], 4),
                }
            )

        # Simulação SIR detalhada para a semente ativa. Ao abrir uma rede, a semente é o nó de
        # maior alcance (o 1º do ranking); depois, vale a que o usuário escolher.
        semente_sir = resolver_no_no_grafo(g, self.sir_semente_no)
        if (semente_sir is None or self.sir_semente_automatica) and top_sir:
            semente_sir = top_sir[0]
        self.sir_semente_no = semente_sir

        sir_detalhe = (
            simular_sir_monte_carlo(
                g,
                semente_no=semente_sir,
                beta=self.sir_beta,
                gamma=self.sir_gamma,
                simulacoes=self.sir_simulacoes,
                semente_aleatoria=self.sir_seed,
            )
            if semente_sir is not None
            else {
                "alcance_medio": 0.0,
                "curva_s": [1.0],
                "curva_i": [0.0],
                "curva_r": [0.0],
                "estados_snapshot": {},
            }
        )

        # Estados SIR projetados sobre todos os nós do grafo
        estados_snap = sir_detalhe.get("estados_snapshot", {})
        for n_vis, no_real_vis in zip(nos_visuais, analise["nos_ordenados"]):
            n_vis["sir_state"] = (
                "SEED"
                if no_real_vis == semente_sir
                else estados_snap.get(no_real_vis, "S")
            )
        estado_semente = sir_detalhe.get("estado_semente")
        cont_inf = sum(1 for v in g.nos() if estados_snap.get(v) == "I") + (estado_semente == "I")
        cont_rec = sum(1 for v in g.nos() if estados_snap.get(v) == "R") + (estado_semente == "R")
        cont_sus = max(0, g.numero_de_nos() - cont_inf - cont_rec)

        concordancia_str = concordancia_sir_da_tela(
            g,
            analise,
            self.sir_beta,
            self.sir_gamma,
            self.sir_seed,
            self.sir_simulacoes,
            atributos=self.meta_ativa.get("atributos_nos"),
        )

        # 5. Tabela Ranking Consolidado (Página 6)
        ranking_consolidado: list[dict[str, str]] = []
        for idx, item_inf in enumerate(top_influenciadores[:5]):
            no_real = top_sir[idx]
            c_idx = mapa_cluster_visual.get(no_real, 0)
            ranking_consolidado.append(
                {
                    "vertice": item_inf["rotulo_curto"],
                    "grau": str(item_inf["grau"]),
                    "pagerank": item_inf["pagerank"],
                    "comunidade": f"Grupo {c_idx + 1}",
                    "alcance_sir": item_inf["alcance"].replace(",", "."),
                }
            )

        # 6. Estrutura de Exportação JSON Consolidada
        json_exportacao = {
            "metadados_grafo": {
                "nome": self.meta_ativa.get("nome", "Grafo"),
                "vertices": g.numero_de_nos(),
                "arestas": g.numero_de_arestas(),
                "direcionado": g.direcionado,
                "ponderado": self.ponderado,
            },
            "metricas_globais": {
                "densidade": round(analise["densidade"], 6),
                "grau_medio": round(analise["grau_medio"], 4),
                "distancia_media": round(analise["distancia_media"], 4),
                "diametro": int(analise["diametro"]),
                "maior_componente_conexa": int(analise["maior_componente_qtd"]),
                "clustering_medio": round(analise["clustering_medio"], 4),
                "transitividade_global": round(analise["transitividade_global"], 4),
                "total_triangulos": int(analise["total_triangulos"]),
                "modularidade_louvain": round(analise["q_louvain"], 4),
                "modularidade_lpa": round(analise["q_lpa"], 4),
            },
            "ultimo_caminho_calculado": {
                "algoritmo": self.ultimo_caminho.get("algoritmo", self.caminho_algoritmo),
                "rota": self.ultimo_caminho.get("rota", []),
                "custo_total": self.ultimo_caminho.get("custo_total", 0.0),
            },
            "top_influenciadores_sir": [
                {
                    "id": item["id"],
                    "grau": item["grau"],
                    "pagerank": float(item["pagerank"]),
                    "kcore": item["kcore"],
                    "alcance_medio": item["alcance_num"],
                }
                for item in top_influenciadores
            ],
        }

        return {
            "paleta": PALETA,
            "cores_comunidades": CORES_COMUNIDADES,
            "catalogo_bases": obter_catalogo_bases_reais(),
            "sessao": {
                "chave_base": self.chave_base_selecionada,
                "nome_grafo": self.meta_ativa.get("nome", "Grafo"),
                "vertices": g.numero_de_nos(),
                "arestas": g.numero_de_arestas(),
                "vertices_str": formatar_int_br(g.numero_de_nos()),
                "arestas_str": formatar_int_br(g.numero_de_arestas()),
                "lacos_str": str(self.meta_ativa.get("lacos", "0")),
                "direcionado": g.direcionado,
                "ponderado": self.ponderado,
                "config_curta": f"{'Dir' if g.direcionado else 'Não-Dir'} / {'Com Peso' if self.ponderado else 'Sem Peso'}",
                "badge_header": f"{'Direcionado' if g.direcionado else 'Não-Direcionado'} • {'Com Peso' if self.ponderado else 'Sem Peso'}",
                "comunidades_reais": self.meta_ativa.get("comunidades_reais", "Não Disponível"),
                "origem": self.meta_ativa.get("origem", ""),
                "arquivo_importado_nome": self.arquivo_importado_nome,
                "arquivo_importado_meta": self.arquivo_importado_meta,
                "semente_ativa": self.semente_layout,
            },
            "visualizacao": {
                "nos": nos_visuais,
                "arestas": arestas_visuais,
                "caminho": self.ultimo_caminho,
                "origem_padrao": str(self.caminho_origem) if self.caminho_origem is not None else "",
                "destino_padrao": str(self.caminho_destino) if self.caminho_destino is not None else "",
            },
            "metricas": {
                "grau_medio_str": formatar_float_br(analise["grau_medio"], 2),
                "densidade_str": formatar_float_br(analise["densidade"], 4),
                "dist_diam_str": f"{formatar_float_br(analise['distancia_media'], 2)} / {analise['diametro']}",
                "maior_comp_str": f"{analise['maior_componente_pct']:.0f}% ({formatar_int_br(analise['maior_componente_qtd'])})",
                "clustering_medio_str": formatar_float_br(analise["clustering_medio"], 4),
                "transitividade_str": formatar_float_br(analise["transitividade_global"], 4),
                "total_triangulos_str": formatar_int_br(analise["total_triangulos"]),
                "histograma_grau": analise["histograma_grau"],
                "tabela_centralidades": tabela_centralidades,
            },
            "comunidades": {
                "algoritmo_ativo": self.algoritmo_comunidade,
                "modularidade_str": f"Q = {formatar_float_br(q_ativo, 3)}",
                "subtitulo_q": f"Louvain: Q = {formatar_float_br(analise['q_louvain'], 3)} • LPA: Q = {formatar_float_br(analise['q_lpa'], 3)}",
                "total_clusters": total_clusters,
                "total_clusters_str": f"{total_clusters} {'Cluster' if total_clusters == 1 else 'Clusters'}",
                "nmi_str": formatar_float_br(nmi_ativo, 3),
                "nmi_pct": round(nmi_ativo * 100.0, 1),
                "ari_str": formatar_float_br(ari_ativo, 3),
                "ari_pct": round(ari_ativo * 100.0, 1),
                "rotulo_comparacao": analise["rotulo_comparacao_gt"],
                "lista": comunidades_resumo,
            },
            "sir": {
                "beta": self.sir_beta,
                "gamma": self.sir_gamma,
                "simulacoes": self.sir_simulacoes,
                "semente": self.sir_seed,
                "no_semente": str(semente_sir) if semente_sir is not None else "",
                "no_semente_rotulo": formatar_rotulo_no(semente_sir) if semente_sir is not None else "",
                "alcance_str": f"{alcance_top.get(semente_sir, sir_detalhe['alcance_medio']) * 100.0:.1f}%".replace(".", ","),
                "infectados_str": f"{formatar_int_br(cont_inf)} nós",
                "recuperados_str": f"{formatar_int_br(cont_rec)} nós",
                "suscetiveis_str": f"{formatar_int_br(cont_sus)} nós",
                "curva_s": [round(x, 4) for x in sir_detalhe["curva_s"]],
                "curva_i": [round(x, 4) for x in sir_detalhe["curva_i"]],
                "curva_r": [round(x, 4) for x in sir_detalhe["curva_r"]],
                "correlacao_str": concordancia_str,
                "limiar": self.sir_beta_c,
                "limiar_str": (
                    f"β_c = {formatar_float_br(self.sir_beta_c, 4)}"
                    + (" (sem a direção das arestas)" if g.direcionado else "")
                    if self.sir_beta_c is not None and math.isfinite(self.sir_beta_c)
                    else "β_c infinito: nenhum nó tem 2 ou mais vizinhos, e o surto não cresce"
                ),
                "top_influenciadores": top_influenciadores,
            },
            "resultados": {
                "ranking_consolidado": ranking_consolidado,
                "json_exportacao": json_exportacao,
            },
        }


# Singleton de sessão e servidor HTTP local em background
_SESSAO_GLOBAL: GerenciadorSessaoBackend | None = None
_PORTA_API_LOCAL: int | None = None
_LOCK_SERVIDOR = threading.Lock()


def obter_sessao_backend() -> GerenciadorSessaoBackend:
    """Retorna a instância única do gerenciador de sessão conectado ao pacote `redes`."""
    global _SESSAO_GLOBAL
    with _LOCK_SERVIDOR:
        if _SESSAO_GLOBAL is None:
            _SESSAO_GLOBAL = GerenciadorSessaoBackend()
        return _SESSAO_GLOBAL


class _ManipuladorRequisicoesBackend(BaseHTTPRequestHandler):
    """Manipulador HTTP local que expõe os algoritmos do pacote `redes` para a UI."""

    def log_message(self, format: str, *args: Any) -> None:
        return  # Silencia logs de console a cada chamada

    def _enviar_json(self, status: int, dados: dict[str, Any]) -> None:
        corpo = json.dumps(dados, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(corpo)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()
        self.wfile.write(corpo)

    def do_OPTIONS(self) -> None:
        self._enviar_json(200, {"ok": True})

    def do_GET(self) -> None:
        sessao = obter_sessao_backend()
        with sessao.lock:
            self._enviar_json(200, {"ok": True, "dados": sessao.obter_payload_completo()})

    def do_POST(self) -> None:
        sessao = obter_sessao_backend()
        tamanho = int(self.headers.get("Content-Length", "0"))
        corpo_raw = self.rfile.read(tamanho).decode("utf-8") if tamanho > 0 else "{}"

        try:
            req = json.loads(corpo_raw) if corpo_raw else {}
            acao = req.get("acao", "")

            with sessao.lock:
                if acao == "carregar_base":
                    chave = str(req.get("chave", "facebook"))
                    direcionado = bool(req.get("direcionado", False))
                    ponderado = bool(req.get("ponderado", False))
                    dados = sessao.ativar_base_homologada(chave, direcionado, ponderado)
                    self._enviar_json(200, {"ok": True, "dados": dados})
                    return

                if acao == "importar_arquivo":
                    nome = str(req.get("nome", "arestas_importadas.txt"))
                    conteudo = str(req.get("conteudo", ""))
                    direcionado = bool(req.get("direcionado", False))
                    ponderado = bool(req.get("ponderado", False))
                    dados = sessao.importar_arquivo_real(nome, conteudo, direcionado, ponderado)
                    self._enviar_json(200, {"ok": True, "dados": dados})
                    return

                if acao == "gerar_sintetico":
                    modelo = str(req.get("modelo", "ba"))
                    n = int(req.get("n", 200))
                    param = float(req.get("param", 4.0))
                    semente = int(req.get("semente", 42))
                    dados = sessao.gerar_rede_sintetica_real(modelo, n, param, semente)
                    self._enviar_json(200, {"ok": True, "dados": dados})
                    return

                if acao == "calcular_caminho":
                    algoritmo = str(req.get("algoritmo", "Dijkstra"))
                    origem = req.get("origem")
                    destino = req.get("destino")
                    sessao.caminho_algoritmo = algoritmo
                    sessao.caminho_origem = resolver_no_no_grafo(sessao.grafo_ativo, origem)
                    sessao.caminho_destino = resolver_no_no_grafo(sessao.grafo_ativo, destino)
                    sessao.ultimo_caminho = calcular_caminho_real(
                        sessao.grafo_ativo,
                        algoritmo,
                        origem,
                        destino,
                        inverter_peso_interacao=(
                            sessao.chave_base_selecionada == "thrones" and sessao.ponderado
                        ),
                    )
                    dados = sessao.obter_payload_completo()
                    self._enviar_json(
                        200,
                        {
                            "ok": sessao.ultimo_caminho.get("encontrado", False),
                            "caminho": sessao.ultimo_caminho,
                            "dados": dados,
                        },
                    )
                    return

                if acao == "recalcular_layout":
                    sessao.semente_layout = int(req.get("semente", sessao.semente_layout + 7))
                    sessao.iteracoes_layout = int(req.get("iteracoes", 50))
                    dados = sessao.obter_payload_completo()
                    self._enviar_json(200, {"ok": True, "dados": dados})
                    return

                if acao == "detectar_comunidades":
                    sessao.algoritmo_comunidade = str(req.get("algoritmo", "Louvain"))
                    sessao.semente_comunidade = int(req.get("semente", 42))
                    dados = sessao.obter_payload_completo()
                    self._enviar_json(200, {"ok": True, "dados": dados})
                    return

                if acao == "simular_sir":
                    beta = float(req.get("beta", sessao.sir_beta))
                    gamma = float(req.get("gamma", sessao.sir_gamma))
                    simulacoes = int(req.get("simulacoes", sessao.sir_simulacoes))
                    # Valida antes de gravar: um valor inválido na sessão quebraria os próximos pedidos.
                    if not 0.0 <= beta <= 1.0 or not 0.0 < gamma <= 1.0 or simulacoes < 1:
                        self._enviar_json(
                            400,
                            {"ok": False, "erro": "Use 0 ≤ β ≤ 1, 0 < γ ≤ 1 e pelo menos 1 simulação."},
                        )
                        return
                    sessao.sir_beta = beta
                    sessao.sir_gamma = gamma
                    sessao.sir_simulacoes = simulacoes
                    sessao.sir_seed = int(req.get("semente", sessao.sir_seed))
                    if "no_semente" in req and req["no_semente"] is not None:
                        sessao.sir_semente_no = resolver_no_no_grafo(
                            sessao.grafo_ativo, req["no_semente"]
                        )
                        sessao.sir_semente_automatica = False
                    dados = sessao.obter_payload_completo()
                    self._enviar_json(200, {"ok": True, "dados": dados})
                    return

                self._enviar_json(400, {"ok": False, "erro": f"Ação desconhecida: {acao}"})
        except Exception as exc:  # noqa: BLE001
            self._enviar_json(400, {"ok": False, "erro": str(exc)})


def iniciar_servidor_api_local() -> str:
    """Inicia o servidor HTTP local em thread daemon (uma única vez por processo) e devolve a URL."""
    global _PORTA_API_LOCAL
    with _LOCK_SERVIDOR:
        if _PORTA_API_LOCAL is not None:
            return f"http://127.0.0.1:{_PORTA_API_LOCAL}"

        servidor = ThreadingHTTPServer(("127.0.0.1", 0), _ManipuladorRequisicoesBackend)
        _PORTA_API_LOCAL = int(servidor.server_port)
        thread = threading.Thread(target=servidor.serve_forever, daemon=True)
        thread.start()
        return f"http://127.0.0.1:{_PORTA_API_LOCAL}"
