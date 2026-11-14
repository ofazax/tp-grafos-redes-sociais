"""Caminhos e conectividade: BFS, DFS, componentes conexas e Dijkstra. Frente 2."""

from __future__ import annotations

# heapq transforma uma lista comum em fila de prioridade (heap): tirar o menor custa O(log n).
import heapq

# deque é uma fila de duas pontas: tirar do começo (popleft) custa O(1).
# Numa lista comum, list.pop(0) custa O(n), porque desloca todos os outros elementos.
from collections import deque
from collections.abc import Callable

from redes.nucleo.grafo import Grafo, No


def bfs(g: Grafo, origem: No) -> dict[No, int]:
    """Distância, em número de arestas, de origem até cada nó alcançável.

    Busca em largura: visita primeiro os vizinhos da origem (distância 1),
    depois os vizinhos deles (distância 2), e assim por diante, em camadas.
    Nós que não são alcançáveis a partir da origem não aparecem no resultado.
    No grafo direcionado, segue o sentido das arestas. Não considera os pesos.

    Tempo: O(n + m). Espaço: O(n).
    Referência: Cormen et al., Introduction to Algorithms, 4ª ed., cap. 20.
    """
    # Avisa se a origem não existe, em vez de falhar no meio da busca.
    if origem not in g:
        raise KeyError(f"o nó {origem!r} não está no grafo")

    # Guarda a distância de cada nó já descoberto. A origem está a distância 0 dela mesma.
    # Também serve de "conjunto de visitados": se o nó está aqui, já foi descoberto.
    distancia: dict[No, int] = {origem: 0}

    # Fila dos nós descobertos que ainda não tiveram os vizinhos examinados.
    fila: deque[No] = deque([origem])

    # Enquanto houver nó esperando na fila...
    while fila:

        # ...tira o mais antigo (o primeiro que entrou é o primeiro que sai).
        v = fila.popleft()

        # Examina cada vizinho de v.
        for w in g.vizinhos(v):

            # Se w ainda não foi descoberto, este é o caminho mais curto até ele.
            if w not in distancia:

                # w está um passo além de v.
                distancia[w] = distancia[v] + 1

                # Entra no fim da fila, para ter os vizinhos examinados depois.
                fila.append(w)

    return distancia


def ordem_dfs(g: Grafo, origem: No) -> list[No]:
    """Nós alcançáveis a partir de origem, na ordem em que a busca em profundidade os visita.

    Busca em profundidade: segue por um caminho até não ter mais para onde ir
    e só então volta para tentar o próximo vizinho. É iterativa, com pilha
    explícita, porque a recursão do Python para em cerca de 1.000 níveis.
    A ordem é a mesma da versão recursiva: os vizinhos são visitados na ordem
    em que aparecem em g.vizinhos().

    Tempo: O(n + m). Espaço: O(n + m), porque um nó pode entrar na pilha mais de uma vez.
    Referência: Cormen et al., Introduction to Algorithms, 4ª ed., cap. 20; Tarjan (1972).
    """
    if origem not in g:
        raise KeyError(f"o nó {origem!r} não está no grafo")

    # Nós já visitados (set tem consulta "w in visitados" em O(1)).
    visitados: set[No] = set()

    # Resultado: os nós na ordem de visita.
    ordem: list[No] = []

    # Pilha dos nós a visitar: o último que entrou é o primeiro que sai.
    pilha: list[No] = [origem]

    while pilha:

        # Tira o nó do topo da pilha (o mais recente).
        v = pilha.pop()

        # Um nó pode ter sido empilhado por mais de um vizinho; visita só na primeira vez.
        if v in visitados:
            continue

        # Marca como visitado e registra na ordem.
        visitados.add(v)
        ordem.append(v)

        # Empilha os vizinhos ainda não visitados. O reversed inverte a ordem para
        # que o primeiro vizinho fique no topo da pilha e seja o próximo a ser visitado.
        for w in reversed(list(g.vizinhos(v))):
            if w not in visitados:
                pilha.append(w)

    return ordem


def componentes_conexas(g: Grafo) -> list[set[No]]:
    """Componentes conexas do grafo: uma lista de conjuntos de nós.

    Cada componente é um "pedaço" do grafo em que todo nó alcança todos os
    outros. Nó isolado forma uma componente sozinho. As componentes saem na
    ordem em que o primeiro nó de cada uma aparece em g.nos(). No grafo
    direcionado, o sentido das arestas é ignorado (componentes fracamente conexas).

    Faz uma BFS a partir de cada nó ainda não visitado. Como cada nó e cada
    aresta são examinados uma única vez no total, o custo é o de uma BFS só.

    Tempo: O(n + m). Espaço: O(n).
    Referência: Cormen et al., Introduction to Algorithms, 4ª ed., cap. 20; Hopcroft e Tarjan (1973).
    """
    # Nós que já foram colocados em alguma componente.
    visitados: set[No] = set()

    # Resultado: uma entrada por componente.
    componentes: list[set[No]] = []

    # Tenta começar uma busca em cada nó do grafo.
    for inicio in g.nos():

        # Se o nó já foi alcançado por uma busca anterior, a componente dele já está na lista.
        if inicio in visitados:
            continue

        # Nó ainda não visitado: ele inaugura uma componente nova.
        componente: set[No] = {inicio}
        visitados.add(inicio)
        fila: deque[No] = deque([inicio])

        # BFS: tudo o que for alcançado a partir de inicio pertence a esta componente.
        while fila:
            v = fila.popleft()

            for w in g.vizinhos(v):
                if w not in visitados:
                    visitados.add(w)
                    componente.add(w)
                    fila.append(w)

            # No direcionado, anda também contra o sentido das arestas (por quem aponta para v),
            # para que v -> w e w fiquem na mesma componente saindo de qualquer um dos dois.
            if g.direcionado:
                for w in g.predecessores(v):
                    if w not in visitados:
                        visitados.add(w)
                        componente.add(w)
                        fila.append(w)

        # A fila esvaziou: a componente está completa.
        componentes.append(componente)

    return componentes


def dijkstra(
    g: Grafo,
    origem: No,
    distancia: Callable[[float], float] | None = None,
) -> dict[No, float]:
    """Menor distância, somando os pesos das arestas, de origem até cada nó alcançável.

    O parâmetro distancia é uma função que converte o peso de uma aresta em
    comprimento. Sem ele, o comprimento é o próprio peso. Na Network of Thrones
    o peso é o número de interações, então use distancia=lambda peso: 1 / peso:
    quem interage mais fica mais perto.

    Os comprimentos não podem ser negativos (lança ValueError), porque o
    algoritmo de Dijkstra só é correto nesse caso. Nós não alcançáveis não
    aparecem no resultado. O dicionário sai em ordem crescente de distância.

    Tempo: O((n + m) log n), com heap binário (heapq). Espaço: O(n + m).
    Referência: Dijkstra (1959), Numerische Mathematik 1:269-271; Cormen et al., 4ª ed., cap. 22.
    """
    if origem not in g:
        raise KeyError(f"o nó {origem!r} não está no grafo")

    # Distância definitiva de cada nó já resolvido. Um nó só entra aqui uma vez.
    menor_distancia: dict[No, float] = {}

    # Desempate do heap: se duas entradas têm a mesma distância, o Python compararia
    # os nós, e nós de tipos diferentes (inteiro e texto) não se comparam.
    # Com um contador único no meio da tupla, a comparação nunca chega ao nó.
    contador = 0

    # Fila de prioridade com tuplas (distância até o nó, desempate, nó).
    # O heappop sempre devolve a tupla de menor distância.
    fila: list[tuple[float, int, No]] = [(0.0, contador, origem)]

    while fila:

        # Tira o nó mais próximo da origem entre os que estão esperando.
        d, _, v = heapq.heappop(fila)

        # O mesmo nó pode estar na fila várias vezes, com distâncias diferentes.
        # A primeira vez que ele sai é a menor; as outras são entradas velhas e são ignoradas.
        if v in menor_distancia:
            continue

        # Como nenhum comprimento é negativo, nenhum caminho que ainda está na fila
        # consegue chegar em v com menos que d. A distância de v está resolvida.
        menor_distancia[v] = d

        for w in g.vizinhos(v):

            # Vizinho já resolvido não melhora mais.
            if w in menor_distancia:
                continue

            # Comprimento da aresta (v, w): o peso, ou o peso convertido pela função.
            peso = g.peso(v, w)
            comprimento = peso if distancia is None else distancia(peso)

            if comprimento < 0:
                raise ValueError(f"a aresta ({v!r}, {w!r}) tem comprimento negativo: {comprimento}")

            # Candidato: chegar em w passando por v. Entra na fila e disputa com os outros.
            contador += 1
            heapq.heappush(fila, (d + comprimento, contador, w))

    return menor_distancia