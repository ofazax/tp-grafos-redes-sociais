"""Estrutura de grafo em lista de adjacência, em Python puro.

Cada nó guarda um dicionário {vizinho: peso}. Num grafo direcionado guardamos
também os predecessores, para calcular grau de entrada e PageRank em O(1) por nó.

Memória: O(n + m). Inserir nó ou aresta: O(1) em média. Testar aresta: O(1) em média.
"""
from __future__ import annotations

from collections.abc import Hashable, Iterable, Iterator

No = Hashable


class Grafo:
    """Grafo simples (sem arestas paralelas), direcionado ou não, com pesos.

    Grafos sem peso usam peso 1.0. Laços (u, u) são aceitos porque o Louvain
    cria laços ao agregar comunidades; os leitores de dados os descartam.
    """

    __slots__ = ("direcionado", "_adj", "_pred", "_m")

    def __init__(self, direcionado: bool = False) -> None:
        self.direcionado = direcionado
        self._adj: dict[No, dict[No, float]] = {}
        # No grafo não direcionado, predecessores e sucessores são o mesmo dicionário.
        self._pred: dict[No, dict[No, float]] = {} if direcionado else self._adj
        self._m = 0

    # ------------------------------------------------------------ construção
    def adicionar_no(self, u: No) -> None:
        """Adiciona o nó u (não faz nada se já existir). O(1)."""
        if u not in self._adj:
            self._adj[u] = {}
            if self.direcionado:
                self._pred[u] = {}

    def adicionar_aresta(self, u: No, v: No, peso: float = 1.0) -> None:
        """Adiciona a aresta (u, v), criando os nós se preciso. O(1).

        Se a aresta já existir, só atualiza o peso (não conta duas vezes).
        """
        self.adicionar_no(u)
        self.adicionar_no(v)
        if v not in self._adj[u]:
            self._m += 1
        self._adj[u][v] = peso
        if self.direcionado:
            self._pred[v][u] = peso
        else:
            self._adj[v][u] = peso

    @classmethod
    def de_arestas(cls, arestas: Iterable[tuple], direcionado: bool = False) -> "Grafo":
        """Cria um grafo a partir de pares (u, v) ou triplas (u, v, peso). O(m)."""
        g = cls(direcionado=direcionado)
        for aresta in arestas:
            g.adicionar_aresta(*aresta)
        return g

    # -------------------------------------------------------------- consulta
    def tem_no(self, u: No) -> bool:
        """True se o nó u existe. O(1)."""
        return u in self._adj

    def tem_aresta(self, u: No, v: No) -> bool:
        """True se existe a aresta (u, v). O(1)."""
        return u in self._adj and v in self._adj[u]

    def vizinhos(self, u: No) -> Iterator[No]:
        """Vizinhos de u (sucessores, no grafo direcionado). O(1) para começar."""
        return iter(self._adj[u])

    def predecessores(self, u: No) -> Iterator[No]:
        """Nós com aresta chegando em u (no não direcionado, os vizinhos)."""
        return iter(self._pred[u])

    def peso(self, u: No, v: No) -> float:
        """Peso da aresta (u, v). Lança KeyError se ela não existir. O(1)."""
        return self._adj[u][v]

    def grau_saida(self, u: No) -> int:
        """Número de arestas que saem de u. O(1)."""
        return len(self._adj[u])

    def grau_entrada(self, u: No) -> int:
        """Número de arestas que chegam em u. O(1)."""
        return len(self._pred[u])

    def grau(self, u: No) -> int:
        """Grau de u. O(1).

        Não direcionado: número de vizinhos, com laço contando 2 (assim a soma
        dos graus é sempre 2m). Direcionado: grau de entrada + grau de saída.
        """
        if self.direcionado:
            return len(self._adj[u]) + len(self._pred[u])
        return len(self._adj[u]) + (1 if u in self._adj[u] else 0)

    def nos(self) -> Iterator[No]:
        """Todos os nós, na ordem de inserção."""
        return iter(self._adj)

    def arestas(self) -> Iterator[tuple[No, No, float]]:
        """Todas as arestas (u, v, peso). No não direcionado, cada uma aparece uma vez. O(n + m)."""
        if self.direcionado:
            for u, vizinhos in self._adj.items():
                for v, peso in vizinhos.items():
                    yield u, v, peso
            return
        vistos: set[No] = set()
        for u, vizinhos in self._adj.items():
            for v, peso in vizinhos.items():
                if v not in vistos:
                    yield u, v, peso
            vistos.add(u)

    def numero_de_nos(self) -> int:
        """Quantidade de nós (n). O(1)."""
        return len(self._adj)

    def numero_de_arestas(self) -> int:
        """Quantidade de arestas (m). O(1)."""
        return self._m

    @property
    def adj(self) -> dict[No, dict[No, float]]:
        """Acesso direto à lista de adjacência, só para LEITURA nos laços pesados."""
        return self._adj

    # ------------------------------------------------------------- utilidades
    def __len__(self) -> int:
        return len(self._adj)

    def __contains__(self, u: No) -> bool:
        return u in self._adj

    def __repr__(self) -> str:
        tipo = "direcionado" if self.direcionado else "não direcionado"
        return f"Grafo({tipo}, n={self.numero_de_nos()}, m={self.numero_de_arestas()})"
