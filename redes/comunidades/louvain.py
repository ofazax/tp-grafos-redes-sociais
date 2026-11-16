"""Algoritmo de Louvain para detecção de comunidades. Frente 4."""

from __future__ import annotations

import random
from collections import defaultdict

from redes.nucleo.grafo import Grafo, No
from redes.comunidades.modularidade import modularidade as _modularidade_real


def louvain(g: Grafo, seed: int | None = 42) -> tuple[dict[No, int], float]:
    """Detecta comunidades pelo método de Louvain (Blondel et al., 2008).

    Executa iterações de duas fases até a modularidade Q convergir:
      Fase 1 (otimização local): move cada nó para a comunidade vizinha que
        maximize o ganho ΔQ. Repete até nenhum nó se mover.
      Fase 2 (agregação): colapsa cada comunidade num super-nó; arestas
        internas viram self-loops e arestas entre comunidades viram arestas
        pesadas entre super-nós.

    Tempo: ~O(m) por passada. Espaço: O(n + m).
    Referência: Blondel et al. (2008), Journal of Statistical Mechanics.

    Args:
        g: Grafo não direcionado (ponderado ou não).
        seed: semente para embaralhamento da ordem de visita dos nós.

    Returns:
        Tupla (partição, Q) onde partição é um dict {nó_original: id_comunidade}
        e Q é a modularidade final.
    """
    if g.numero_de_nos() == 0:
        return {}, 0.0

    # guarda o grafo original para calcular Q real no final
    g_original = g
    rng = random.Random(seed)

    # --- pré-computa o grau ponderado de cada nó e 2m ---
    kv: dict[No, float] = {}
    dois_m = 0.0
    for v in g.nos():
        grau_v = sum(g.peso(v, w) for w in g.vizinhos(v))
        kv[v] = grau_v
        dois_m += grau_v
    # dois_m = soma de todos os graus = 2 * (soma dos pesos das arestas)

    if dois_m == 0.0:
        return {v: i for i, v in enumerate(g.nos())}, 0.0

    # --- inicialização: cada nó na sua própria comunidade ---
    comunidade_de: dict[No, int] = {v: i for i, v in enumerate(g.nos())}
    sigma_tot: dict[int, float] = {comunidade_de[v]: kv[v] for v in g.nos()}
    sigma_in: dict[int, float] = defaultdict(float)

    # Hierarquia: v_super → lista de nós originais que ele representa
    hierarquia: dict[No, list[No]] = {v: [v] for v in g.nos()}

    q_atual = _modularidade_louvain(sigma_in, sigma_tot, dois_m)

    # --- loop externo: repete Fase1 + Fase2 enquanto Q melhora ---
    while True:
        # == FASE 1: otimização local ==
        melhorou = True
        while melhorou:
            melhorou = False
            nos_embaralhados = list(g.nos())
            rng.shuffle(nos_embaralhados)

            for v in nos_embaralhados:
                c_atual = comunidade_de[v]

                # soma dos pesos de v para cada comunidade vizinha
                k_v_para: dict[int, float] = defaultdict(float)
                for w in g.vizinhos(v):
                    if w != v:
                        k_v_para[comunidade_de[w]] += g.peso(v, w)

                # remove v da sua comunidade atual
                sigma_tot[c_atual] -= kv[v]
                sigma_in[c_atual] -= 2.0 * k_v_para.get(c_atual, 0.0)

                melhor_c = c_atual
                melhor_dq = 0.0  # só move se ganho for positivo

                for c, k_v_in in k_v_para.items():
                    # ΔQ de mover v para a comunidade c
                    # (fórmula simplificada de Blondel et al. eq. 4 e 5)
                    dq = (k_v_in / dois_m
                          - sigma_tot[c] * kv[v] / (dois_m ** 2))
                    if dq > melhor_dq:
                        melhor_dq = dq
                        melhor_c = c

                # reinsere v na melhor comunidade (pode ser a mesma)
                comunidade_de[v] = melhor_c
                sigma_tot[melhor_c] += kv[v]
                sigma_in[melhor_c] += 2.0 * k_v_para.get(melhor_c, 0.0)

                if melhor_c != c_atual:
                    melhorou = True

        # == FASE 2: agregação ==
        q_novo = _modularidade_louvain(sigma_in, sigma_tot, dois_m)
        if q_novo <= q_atual + 1e-10:
            break
        q_atual = q_novo

        g, hierarquia, comunidade_de, kv, sigma_in, sigma_tot, dois_m = (
            _agregar(g, comunidade_de, hierarquia)
        )

    # --- desempacota hierarquia para obter partição nos nós originais ---
    particao_final: dict[No, int] = {}
    for v_super, nos_originais in hierarquia.items():
        id_com = comunidade_de[v_super]
        for no_orig in nos_originais:
            particao_final[no_orig] = id_com

    # renumera os ids de comunidade de 0 a k-1
    ids_unicos = sorted(set(particao_final.values()))
    remapeia = {antigo: novo for novo, antigo in enumerate(ids_unicos)}
    particao_final = {v: remapeia[c] for v, c in particao_final.items()}

    # calcula Q final usando a função correta sobre o grafo original
    q_final = _modularidade_real(g_original, particao_final)

    return particao_final, q_final


# ---------------------------------------------------------------------------
# Funções auxiliares (não fazem parte da API pública do módulo)
# ---------------------------------------------------------------------------

def _modularidade_louvain(
    sigma_in: dict[int, float],
    sigma_tot: dict[int, float],
    dois_m: float,
) -> float:
    """Calcula Q a partir dos acumuladores da Fase 1. O(c), c = nº comunidades."""
    if dois_m == 0.0:
        return 0.0
    q = 0.0
    for c in sigma_tot:
        q += sigma_in[c] / dois_m - (sigma_tot[c] / dois_m) ** 2
    return q


def _agregar(
    g: Grafo,
    comunidade_de: dict[No, int],
    hierarquia: dict[No, list[No]],
) -> tuple[Grafo, dict[No, list[No]], dict[No, int], dict[No, float],
           dict[int, float], dict[int, float], float]:
    """Fase 2: colapsa cada comunidade num super-nó e constrói novo grafo."""

    # identifica quais comunidades existem e cria IDs de super-nós
    ids_comunidades = sorted(set(comunidade_de.values()))
    super_no_de: dict[int, int] = {c: i for i, c in enumerate(ids_comunidades)}

    g_novo = Grafo()

    # garante que todos os super-nós existem (mesmo comunidades sem arestas externas)
    for sn in super_no_de.values():
        g_novo.adicionar_no(sn)

    # percorre as arestas do grafo atual e as adiciona no super-grafo
    for u, v, peso in g.arestas():
        sn_u = super_no_de[comunidade_de[u]]
        sn_v = super_no_de[comunidade_de[v]]
        # arestas internas viram self-loops; externas viram arestas entre super-nós
        p_atual = g_novo._adj[sn_u].get(sn_v, 0.0)
        g_novo._adj[sn_u][sn_v] = p_atual + peso
        if sn_u != sn_v:
            p_inv = g_novo._adj[sn_v].get(sn_u, 0.0)
            g_novo._adj[sn_v][sn_u] = p_inv + peso
        # atualiza o contador interno de arestas
    # reconstrói _m manualmente (self-loops também contam 1)
    g_novo._m = sum(
        1 for sn_u in g_novo._adj for sn_v in g_novo._adj[sn_u] if sn_v >= sn_u
    )

    # nova hierarquia: super-nó → lista de nós ORIGINAIS
    nova_hierarquia: dict[No, list[No]] = defaultdict(list)
    for v_super, nos_orig in hierarquia.items():
        sn = super_no_de[comunidade_de[v_super]]
        nova_hierarquia[sn].extend(nos_orig)

    # cada super-nó começa na sua própria comunidade
    nova_com_de: dict[No, int] = {sn: sn for sn in g_novo.nos()}

    # recalcula kv, sigma_tot e sigma_in para o novo grafo
    novo_kv: dict[No, float] = {}
    novo_dois_m = 0.0
    for sn in g_novo.nos():
        grau = sum(g_novo.peso(sn, w) for w in g_novo.vizinhos(sn))
        novo_kv[sn] = grau
        novo_dois_m += grau

    novo_sigma_tot: dict[int, float] = {sn: novo_kv[sn] for sn in g_novo.nos()}
    novo_sigma_in: dict[int, float] = defaultdict(float)
    for sn in g_novo.nos():
        if g_novo.tem_aresta(sn, sn):
            novo_sigma_in[sn] += 2.0 * g_novo.peso(sn, sn)

    return (g_novo, dict(nova_hierarquia), nova_com_de,
            novo_kv, novo_sigma_in, novo_sigma_tot, novo_dois_m)
