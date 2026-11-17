"""Métricas de avaliação de partições de comunidades. Frente 4."""

from __future__ import annotations

import math
from collections import Counter

from redes.nucleo.grafo import No


def nmi(p1: dict[No, int], p2: dict[No, int]) -> float:
    """Informação Mútua Normalizada entre duas partições (NMI).

    Mede o quanto uma partição prevê a outra. NMI = 1.0 quando as partições
    são idênticas (módulo renomeação), NMI = 0.0 quando são independentes.

    Tempo: O(n). Espaço: O(k1 * k2).
    Referência: Danon et al. (2005), Journal of Statistical Mechanics.

    Args:
        p1: partição 1 — dict {nó: id_comunidade}.
        p2: partição 2 — dict {nó: id_comunidade}.

    Returns:
        Valor NMI em [0.0, 1.0].
    """
    nos = list(p1.keys())
    n = len(nos)
    if n == 0:
        return 0.0

    # contagem conjunta: (c1, c2) -> quantidade de nós
    conjunta: Counter = Counter((p1[v], p2[v]) for v in nos)

    # contagens marginais
    marginal1: Counter = Counter(p1[v] for v in nos)
    marginal2: Counter = Counter(p2[v] for v in nos)

    # informação mútua I(X;Y)
    mi = 0.0
    for (c1, c2), n_12 in conjunta.items():
        mi += (n_12 / n) * math.log((n_12 * n) / (marginal1[c1] * marginal2[c2]))

    # entropias H(X) e H(Y)
    h1 = -sum((cnt / n) * math.log(cnt / n) for cnt in marginal1.values())
    h2 = -sum((cnt / n) * math.log(cnt / n) for cnt in marginal2.values())

    # NMI normalizado pela média das entropias
    denominador = (h1 + h2) / 2.0
    if denominador == 0.0:
        return 1.0  # partições triviais idênticas
    return mi / denominador


def ari(p1: dict[No, int], p2: dict[No, int]) -> float:
    """Índice de Rand Ajustado entre duas partições (ARI).

    Mede a concordância entre partições corrigindo para concordância aleatória.
    ARI = 1.0 para partições idênticas, ARI ≈ 0.0 para partições aleatórias,
    ARI < 0.0 para concordância pior que o acaso.

    Tempo: O(n + k1*k2). Espaço: O(k1 * k2).
    Referência: Hubert & Arabie (1985), Journal of Classification.

    Args:
        p1: partição 1 — dict {nó: id_comunidade}.
        p2: partição 2 — dict {nó: id_comunidade}.

    Returns:
        Valor ARI em [-1.0, 1.0].
    """
    nos = list(p1.keys())
    n = len(nos)
    if n == 0:
        return 0.0

    # tabela de contingência
    contingencia: Counter = Counter((p1[v], p2[v]) for v in nos)

    # somas das linhas e colunas
    soma_linhas: Counter = Counter(p1[v] for v in nos)
    soma_colunas: Counter = Counter(p2[v] for v in nos)

    def c2(x: int) -> int:
        """Combinações de x tomados 2 a 2."""
        return x * (x - 1) // 2

    # Σ C(n_ij, 2)
    soma_nij = sum(c2(cnt) for cnt in contingencia.values())
    # Σ C(a_i, 2)  e  Σ C(b_j, 2)
    soma_ai = sum(c2(cnt) for cnt in soma_linhas.values())
    soma_bj = sum(c2(cnt) for cnt in soma_colunas.values())

    cn = c2(n)
    esperado = soma_ai * soma_bj / cn if cn > 0 else 0.0
    maximo = (soma_ai + soma_bj) / 2.0

    denominador = maximo - esperado
    if denominador == 0.0:
        return 1.0  # partições triviais idênticas
    return (soma_nij - esperado) / denominador