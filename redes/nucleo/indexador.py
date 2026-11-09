"""Reindexação dos nós para inteiros 0..n-1.

Algoritmos pesados (Brandes, PageRank) ficam mais rápidos com listas indexadas
por inteiro do que com dicionários. O indexador guarda a ida e a volta dos IDs.
"""
from __future__ import annotations

from collections.abc import Hashable

from redes.nucleo.grafo import Grafo


class IndexadorDeNos:
    """Mapeia cada nó do grafo para um inteiro 0..n-1, na ordem de inserção. O(n)."""

    def __init__(self, g: Grafo) -> None:
        self.para_no: list[Hashable] = list(g.nos())
        self.para_indice: dict[Hashable, int] = {u: i for i, u in enumerate(self.para_no)}

    def __len__(self) -> int:
        return len(self.para_no)


def para_listas_indexadas(g: Grafo) -> tuple[IndexadorDeNos, list[list[int]]]:
    """Devolve o indexador e a lista de adjacência como list[list[int]]. O(n + m)."""
    indexador = IndexadorDeNos(g)
    indice = indexador.para_indice
    adj = [[indice[v] for v in g.vizinhos(u)] for u in indexador.para_no]
    return indexador, adj
