"""Reindexação dos nós para inteiros 0..n-1.

Algoritmos pesados (Brandes, PageRank) ficam mais rápidos com listas indexadas
por inteiro do que com dicionários. O indexer guarda a ida e a volta dos IDs.
"""
from __future__ import annotations

from collections.abc import Hashable

from redes.core.graph import Graph


class NodeIndexer:
    """Mapeia cada nó do grafo para um inteiro 0..n-1, na ordem de inserção. O(n)."""

    def __init__(self, g: Graph) -> None:
        self.to_node: list[Hashable] = list(g.nodes())
        self.to_index: dict[Hashable, int] = {u: i for i, u in enumerate(self.to_node)}

    def __len__(self) -> int:
        return len(self.to_node)


def to_index_lists(g: Graph) -> tuple[NodeIndexer, list[list[int]]]:
    """Devolve o indexer e a lista de adjacência como list[list[int]]. O(n + m)."""
    idx = NodeIndexer(g)
    t = idx.to_index
    adj = [[t[v] for v in g.neighbors(u)] for u in idx.to_node]
    return idx, adj
