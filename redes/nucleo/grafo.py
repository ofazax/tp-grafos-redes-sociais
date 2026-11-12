from __future__ import annotations

from collections.abc import Hashable, Iterable, Iterator

# Qualquer objeto imutável/hashable (inteiro, string) pode ser um nó do grafo
No = Hashable


class Grafo:
    # Travando os atributos da classe para economizar memória (desativa o comportamento dinâmico, impedindo a criação acidental de novos atributos)
    __slots__ = ("direcionado", "_adj", "_pred", "_m")

    # Inicializa o grafo (Construtor)
    def __init__(self, direcionado: bool = False) -> None:

        # Indica se o grafo é direcionado ou não (booleano)
        self.direcionado = direcionado

        # Lista de adjacência: A chave externa é o nó de origem, a chave interna é o nó de destino e o valor é o peso da aresta (float)
        self._adj: dict[No, dict[No, float]] = {}

        # Lista de predecessores: Guarda as arestas de entrada, ou seja, quem aponta para o nó.
        # Se o grafo for não-direcionado, a lista de predecessores é a mesma que a lista de adjacência. Caso contrário, é uma lista separada.
        self._pred: dict[No, dict[No, float]] = {} if direcionado else self._adj

        # Conta o número de arestas inseridas. Inicialmente é zero.
        self._m = 0

    # Inserir nós e arestas:

    # Inicializa um dicionário vazio para um novo nó do grafo
    def adicionar_no(self, v: No) -> None:

        # Verifica se o nó já existe na lista de adjacência para não sobrescrever e apagar as conexões existentes.
        if v not in self._adj:

            # Inicializa um dicionário vazio para o nó v na lista de adjacência
            self._adj[v] = {}

            # Se o grafo for direcionado, o método também inicializa um dicionário vazio para o nó v na lista de predecessores.
            if self.direcionado:
                self._pred[v] = {}

    # Adiciona uma aresta entre os nós v (origem) e w (destino) com um peso inicial de 1.0, como convenção para grafos não ponderados.
    def adicionar_aresta(self, v: No, w: No, peso: float = 1.0) -> None:

        # Adiciona os nós v e w ao grafo para garantir que ambos existam antes da adição da aresta.
        self.adicionar_no(v)
        self.adicionar_no(w)

        # Se w não for adjacente a v, quer dizer que a aresta não existe, então incrementa o contador de arestas.
        # Se a aresta já existir , a aresta não é contada novamente.
        if w not in self._adj[v]:
            self._m += 1

        # Adiciona a aresta na lista de adjacência com v como nó de origem e w como nó de destino, atribuindo o peso da aresta.
        self._adj[v][w] = peso

        # Se o grafo for direcionado, adiciona também a aresta na lista de predecessores.
        if self.direcionado:
            self._pred[w][v] = peso

        # Se o grafo for não-direcionado, adiciona a aresta na lista de adjacência com w como nó de origem e v como nó de destino.
        else:
            self._adj[w][v] = peso

    # Cria o grafo a partir de uma lista de arestas. Essas arestas são representadas por tuplas (v, w, peso) ou (v, w).
    @classmethod
    def de_arestas(cls, arestas: Iterable[tuple], direcionado: bool = False) -> "Grafo":

        # Cria uma instância do grafo com o parâmetro direcionado especificado.
        g = cls(direcionado=direcionado)

        # Itera sobre cada aresta na lista de arestas e adiciona essas arestas ao grafo.
        for aresta in arestas:

            # Passa os elementos da tupla (v, w, peso) ou (v,w) como argumentos usando o operador de desempacotamento '*'.
            g.adicionar_aresta(*aresta)

        # Retorna o grafo criado a partir das arestas fornecidas.
        return g

    def remover_aresta(self, v: No, w: No) -> None:

        if not self.tem_aresta(v, w):
            raise KeyError(f"a aresta ({v!r},{w!r}) não existe")

        del self._adj[v][w]

        if self.direcionado:
            del self._pred[w][v]

        elif v != w:
            del self._adj[w][v]

        self._m -= 1

    # Consultas:

    # Checa se o nó v é uma chave no dicionário, ou seja, se o vértice v existe no grafo.
    def tem_no(self, v: No) -> bool:
        return v in self._adj

    # Checa se o nó v é uma chave no dicionário e se w é um vizinho de v, ou seja, se existe uma aresta entre v e w.
    def tem_aresta(self, v: No, w: No) -> bool:
        return v in self._adj and w in self._adj[v]

    # Percorre o dicionário de adjacência e retorna as chaves (vizinhos) do nó v, ou seja, para quem o v aponta.
    def vizinhos(self, v: No) -> Iterator[No]:
        return iter(self._adj[v])

    # Percorre o dicionário de predecessores e retorna as chaves do nó v, ou seja, quem aponta para o v.
    def predecessores(self, v: No) -> Iterator[No]:
        return iter(self._pred[v])

    # Retorna o peso da aresta entre v e w. Busca em dois níveis: _adj[v] acha o dicionário de adjacência do nó v, e [w] pega o peso guardado para w. Se não existir aresta, lança KeyError.
    def peso(self, v: No, w: No) -> float:
        return self._adj[v][w]

    # O len do dicionário de adjacência do nó v é o número de chaves, ou seja, quantos vizinhos v possui ou quantas arestas saem de v.
    def grau_saida(self, v: No) -> int:
        return len(self._adj[v])

    # O len do dicionário de predecessores do nó v é o número de chaves, ou seja, quantos predecessores v possui ou quantas arestas chegam em v.
    def grau_entrada(self, v: No) -> int:
        return len(self._pred[v])

    # No grafo direcionado, o grau é a soma do que entra e do que sai.
    # No grafo não direcionado, o grau é o número de vizinhos e + 1 se houver um laço (v,v), porque o laço conta 2 no grau (assim a soma dos graus é sempre 2m).
    def grau(self, v: No) -> int:
        if self.direcionado:
            return len(self._adj[v]) + len(self._pred[v])
        return len(self._adj[v]) + (1 if v in self._adj[v] else 0)

    # Listar nós e arestas:

    # Devolve todos os nós (as chaves do dicionario de adjacêcia), na ordem de inserção
    def nos(self) -> Iterator[No]:
        return iter(self._adj)

    # Devolve cada aresta como (origem, destino, peso), uma por vez (yield).
    def arestas(self) -> Iterator[tuple[No, No, float]]:

        # Direcionado: cada entrada do _adj é uma aresta diferente, então devolve todas.
        if self.direcionado:

            # Percorre o dicionario de adjacência e devolve um par chave-valor (v, vizinhos) para cada nó v.
            for v, vizinhos in self._adj.items():

                # Percorre o dicionario de vizinhos da chave v e devolve um par chave-valor (w, peso).
                for w, peso in vizinhos.items():

                    # Devolve a aresta como uma tupla (origem, destino, peso).
                    yield v, w, peso

            # Encerra aqui para não exercutar o não direcionado.
            return

        # Não direcionado: cada aresta aparece duas vezes no dicionario de adjacência.
        # "Vistos" é um conjunto que guarda os nós já percorridos.
        vistos: set[No] = set()

        # Percorre o dicionário de adjacência e devolve um par chave-valor (v, vizinhos) para cada nó v.
        for v, vizinhos in self._adj.items():

            # Percorre o dicionário de vizinhos da chave v e devolve um par chave-valor (w, peso).
            for w, peso in vizinhos.items():

                # Se w não estiver no conjunto de nós já percorridos, devolve a aresta como uma tupla (origem, destino, peso).
                if w not in vistos:
                    yield v, w, peso
            # Terminou de percorrer todos os vizinhos de v.
            vistos.add(v)

    # Lista o número de nós (Quantidade de chaves no dicionário de adjacência).
    def numero_de_nos(self) -> int:
        return len(self._adj)

    # Lista o número de arestas (Retorna o atributo _m, que é o contador de arestas inseridas).
    def numero_de_arestas(self) -> int:
        return self._m

    # Retorna o dicionário de adjacência do grafo, que é um atributo privado da classe.
    @property
    def adj(self) -> dict[No, dict[No, float]]:
        return self._adj

    # Métodos especiais: Python chama sozinho quando a gente usa a sintaxe da linguagem.

    # Chamado por "len(g)": devolve o número de nós.
    def __len__(self) -> int:
        return len(self._adj)

    # Chamado por "v in g": diz se o nó existe no grafo.
    def __contains__(self, v: No) -> bool:
        return v in self._adj

    # Chamado por "print(g)": mostra um resumo do grafo, ex: Grafo(não direcionado, n=34, m=78).
    # Funciona como o toString() do Java.
    def __repr__(self) -> str:
        tipo = "direcionado" if self.direcionado else "não direcionado"
        return f"Grafo({tipo}, n={self.numero_de_nos()}, m={self.numero_de_arestas()})"
