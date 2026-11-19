"""Algoritmo de Propagação de Rótulos para detecção de comunidades. Frente 4."""

from __future__ import annotations

import random
from collections import Counter

from redes.nucleo.grafo import Grafo, No


def propagacao_de_rotulos(
    g: Grafo, semente: int | None = None, max_iteracoes: int = 100
) -> dict[No, int]:
    """Detecta comunidades pelo algoritmo de Propagação de Rótulos (LPA).

    Cada nó adota o rótulo mais frequente entre seus vizinhos. Repete até
    nenhum rótulo precisar mudar (convergência de Raghavan et al., 2007) ou até
    atingir o número máximo de iterações. Desempates são resolvidos
    aleatoriamente.

    Tempo: O(m) por iteração. Espaço: O(n).
    Referência: Raghavan et al. (2007), Physical Review E.

    Args:
        g: Grafo não direcionado.
        semente: semente para desempate aleatório.
        max_iteracoes: limite de iterações para evitar oscilações infinitas.

    Returns:
        dict {nó: id_comunidade}.
    """
    if g.numero_de_nos() == 0:
        return {}

    rng = random.Random(semente)

    # cada nó começa com seu próprio rótulo
    rotulo: dict[No, int] = {v: i for i, v in enumerate(g.nos())}

    for _ in range(max_iteracoes):
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

            # se o nó já tem um dos rótulos mais frequentes, ele permanece com ele
            if rotulo[v] in candidatos:
                continue

            novo_rotulo = rng.choice(candidatos)
            rotulo[v] = novo_rotulo
            convergiu = False

        if convergiu:
            break

    # renumera os IDs de 0 a k-1
    ids_unicos = sorted(set(rotulo.values()))
    remapeia = {antigo: novo for novo, antigo in enumerate(ids_unicos)}
    return {v: remapeia[r] for v, r in rotulo.items()}