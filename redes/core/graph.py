"""Estrutura de grafo em lista de adjacência, em Python puro.

Cada nó guarda um dicionário {vizinho: peso}. Num grafo direcionado guardamos
também os predecessores, para calcular grau de entrada e PageRank em O(1) por nó.

Memória: O(n + m). Inserir nó ou aresta: O(1) em média. Testar aresta: O(1) em média.
"""
from __future__ import annotations

from collections.abc import Hashable, Iterable, Iterator

Node = Hashable


class Graph:
    """Grafo simples (sem arestas paralelas), direcionado ou não, com pesos.

    Grafos sem peso usam peso 1.0. Laços (u, u) são aceitos porque o Louvain
    cria laços ao agregar comunidades; os loaders de dados os descartam.
    """

    __slots__ = ("directed", "_adj", "_pred", "_m")

    def __init__(self, directed: bool = False) -> None:
        self.directed = directed
        self._adj: dict[Node, dict[Node, float]] = {}
        # No grafo não direcionado, predecessores e sucessores são o mesmo dicionário.
        self._pred: dict[Node, dict[Node, float]] = {} if directed else self._adj
        self._m = 0

    # ------------------------------------------------------------ construção
    def add_node(self, u: Node) -> None:
        """Adiciona o nó u (não faz nada se já existir). O(1)."""
        if u not in self._adj:
            self._adj[u] = {}
            if self.directed:
                self._pred[u] = {}

    def add_edge(self, u: Node, v: Node, weight: float = 1.0) -> None:
        """Adiciona a aresta (u, v), criando os nós se preciso. O(1).

        Se a aresta já existir, só atualiza o peso (não conta duas vezes).
        """
        self.add_node(u)
        self.add_node(v)
        if v not in self._adj[u]:
            self._m += 1
        self._adj[u][v] = weight
        if self.directed:
            self._pred[v][u] = weight
        else:
            self._adj[v][u] = weight

    @classmethod
    def from_edges(cls, edges: Iterable[tuple], directed: bool = False) -> "Graph":
        """Cria um grafo a partir de pares (u, v) ou triplas (u, v, peso). O(m)."""
        g = cls(directed=directed)
        for e in edges:
            g.add_edge(*e)
        return g

    # -------------------------------------------------------------- consulta
    def has_node(self, u: Node) -> bool:
        return u in self._adj

    def has_edge(self, u: Node, v: Node) -> bool:
        """True se existe a aresta (u, v). O(1)."""
        return u in self._adj and v in self._adj[u]

    def neighbors(self, u: Node) -> Iterator[Node]:
        """Vizinhos de u (sucessores, no grafo direcionado). O(1) para começar."""
        return iter(self._adj[u])

    def predecessors(self, u: Node) -> Iterator[Node]:
        """Nós com aresta chegando em u (no não direcionado, os vizinhos)."""
        return iter(self._pred[u])

    def weight(self, u: Node, v: Node) -> float:
        """Peso da aresta (u, v). Lança KeyError se ela não existir. O(1)."""
        return self._adj[u][v]

    def out_degree(self, u: Node) -> int:
        return len(self._adj[u])

    def in_degree(self, u: Node) -> int:
        return len(self._pred[u])

    def degree(self, u: Node) -> int:
        """Grau de u. O(1).

        Não direcionado: número de vizinhos, com laço contando 2 (assim a soma
        dos graus é sempre 2m). Direcionado: grau de entrada + grau de saída.
        """
        if self.directed:
            return len(self._adj[u]) + len(self._pred[u])
        return len(self._adj[u]) + (1 if u in self._adj[u] else 0)

    def nodes(self) -> Iterator[Node]:
        """Todos os nós, na ordem de inserção."""
        return iter(self._adj)

    def edges(self) -> Iterator[tuple[Node, Node, float]]:
        """Todas as arestas (u, v, peso). No não direcionado, cada uma aparece uma vez. O(n + m)."""
        if self.directed:
            for u, nbrs in self._adj.items():
                for v, w in nbrs.items():
                    yield u, v, w
            return
        seen: set[Node] = set()
        for u, nbrs in self._adj.items():
            for v, w in nbrs.items():
                if v not in seen:
                    yield u, v, w
            seen.add(u)

    def number_of_nodes(self) -> int:
        return len(self._adj)

    def number_of_edges(self) -> int:
        return self._m

    @property
    def adj(self) -> dict[Node, dict[Node, float]]:
        """Acesso direto à lista de adjacência, só para LEITURA nos laços pesados."""
        return self._adj

    # ------------------------------------------------------------- utilidades
    def __len__(self) -> int:
        return len(self._adj)

    def __contains__(self, u: Node) -> bool:
        return u in self._adj

    def __repr__(self) -> str:
        tipo = "direcionado" if self.directed else "não direcionado"
        return f"Graph({tipo}, n={self.number_of_nodes()}, m={self.number_of_edges()})"
