"""Algoritmo de Propagação de Rótulos para detecção de comunidades. Frente 4."""

from __future__ import annotations

import random
from collections import Counter

from redes.nucleo.grafo import Grafo, No


def propagacao_de_rotulos(
    g: Grafo, seed: int | None = 42
) -> dict[No, int]:
    """Detecta comunidades pelo algoritmo de Propagação de Rótulos (LPA).

    Cada nó adota o rótulo mais frequente entre seus vizinhos. Repete até
    nenhum rótulo mudar (convergência). Desempates são resolvidos
    aleatoriamente.

    Tempo: O(m) por iteração. Espaço: O(n).
    Referência: Raghavan et al. (2007), Physical Review E.

    Args:
        g: Grafo não direcionado.
        seed: semente para desempate aleatório.

    Returns:
        dict {nó: id_comunidade}.
    """
    if g.numero_de_nos() == 0:
        return {}

    rng = random.Random(seed)

    # cada nó começa com seu próprio rótulo
    rotulo: dict[No, int] = {v: i for i, v in enumerate(g.nos())}

    convergiu = False
    while not convergiu:
        convergiu = True
        nos_embaralhados = list(g.nos())
        rng.shuffle(nos_embaralhados)

        for v in nos_embaralhados:
            vizinhos = list(g.vizinhos(v))
            if not vizinhos:
                continue

            # conta a frequência de cada rótulo entre os vizinhos
            contagem = Counter(rotulo[w] for w in vizinhos)
            max_freq = max(contagem.values())

            # todos os rótulos com frequência máxima (desempate aleatório)
            candidatos = [r for r, f in contagem.items() if f == max_freq]
            novo_rotulo = rng.choice(candidatos)

            if novo_rotulo != rotulo[v]:
                rotulo[v] = novo_rotulo
                convergiu = False

    # renumera os IDs de 0 a k-1
    ids_unicos = sorted(set(rotulo.values()))
    remapeia = {antigo: novo for novo, antigo in enumerate(ids_unicos)}
    return {v: remapeia[r] for v, r in rotulo.items()}