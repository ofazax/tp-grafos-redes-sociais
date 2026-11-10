from __future__ import annotations

from collections.abc import Hashable, Iterable, Iterator

# Qualquer objeto imutável/hashable (inteiro, string) pode ser um nó do grafo
No = Hashable 


class Grafo:
    # Travando os atributos da classe para economizar memória (desativa o comportamento dinâmico, impedindo a criação acidental de novos atributos)
    __slots__= ("direcionado", "_adj", "_pred", "_m") 

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

   
    # Inserior nós e arestas:

    # Inicializa um dicionário vazio para um novo nó do grafo
    def adicionar_no(self, v: No) -> None:

        # Verifica se o nó já existe na lista de adjacência para não sobrescrever e apagar as conexões existentes.
        if v not in self._adj:

            # Inicializa um dicionário vazio para o nó v na lista de adjacência
            self._adj[v] = {}

            # Se o grafo for direcionado, o método também inicializa um dicinário vazio para o nó v na lista de predecessores.
            if self.direcionado:
                self._pred[v] = {}

    # Adiciona uma aresta entre os nós v (origem) e w (destino) com um peso inicial de 1.0, como convenção para grafos não ponderados.
    def adicionar_aresta(self, v: No, w: No, peso: float = 1.0) -> None: 
        
        # Adiciona os nós v e w ao grafo para garantir que ambos existam antes da adição da aresta. 
        self.adicionar_no(v)
        self.adicionar_no(w)

        # Se w não for adjacente a v, quer dizer que a aresta não existe, então incrementa o contador de arestas.
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

    # Cria o grafo a partir de uma lista de arestas. Essas arestas são reprentadas por tuplas (v, w, peso) ou (v, w). 
    @classmethod
    def de_arestas(cls, arestas: Iterable[tuple], direcionado: bool = False) -> "Grafo":
        
        # Cria uma instância do grafo com o parâmetro direcionado especificado.
        g = cls(direcionado=direcionado)

        # Itera sobre cada aresta na lista de arestas e adiciona essas aresas ao grafo.
        for aresta in arestas:

            # Passa os elementos da tupla (v, w, peso) ou (v,w) como argumentos usando o operador de desempacotamento '*'.
            g.adicionar_aresta(*aresta)
        
        # Retorna o grafo criado a partir das arestas fornecidas.
        return g

    # Consultas: 

    def tem_no(self, v:No) -> bool:
        return v in self._adj

    def tem_aresta(self, v: No, w: No) -> bool:
        return v in self._adj and w in self._adj[v]

    def vizinhos(self, v: No) -> Iterator[No]:
        return iter(self._adj[v])

    def predecessores(self, v: No) -> Iterator[No]:
        return iter(self._pred[v])

    def peso(self, v: No, w: No) -> float:
        return self._adj[v][w]

    def grau_saida(self, v: No) -> int:
        return len(self._adj[v])

    def grau_entrada(self, v: No) -> int:
        return len(self._pred[v])

    def grau(self, v: No) -> int:
        if self.direcionado:
            return len(self._adj[v]) + len(self._pred[v])
        return len(self._adj[v]) + (1 if v in self._adj[v] else 0)


    # Listar nós e arestas:

    def nos(self) -> Iterator[No]:
        return iter(self._adj)

    def arestas(self) -> Iterator[tuple[No, No, float]]:
        if self.direcionado:
            for v, vizinhos in self._adj.items():
                for w, peso in vizinhos.items():
                    yield v, w, peso
            return
        vistos: set[No] = set()
        for v, vizinhos in self._adj.items():
            for w, peso in vizinhos.items():
                if w not in vistos:
                    yield v, w, peso
            vistos.add(v)

    def numero_de_nos(self) -> int:
        return len(self._adj)

    def numero_de_arestas(self) -> int:
        return self._m

    @property
    def adj(self) -> dict[No, dict[No, float]]:
        return self._adj

    
    # Métodos especiais:

    def __len__(self) -> int: 
        return len(self._adj)

    def __contains__(self, v: No) -> bool:
        return v in self._adj

    def __repr__(self) -> str:
        tipo = "direcionado" if self.direcionado else "não direcionado"
        return f"Grafo({tipo}, n={self.numero_de_nos()}, m={self.numero_de_arestas()})"