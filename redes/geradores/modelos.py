"""Geradores de grafos sintéticos: Erdős-Rényi, Barabási-Albert e Watts-Strogatz. Frente 1.

O Iago usa estes grafos, de 10^3 a 10^5 nós, para medir como o tempo dos algoritmos cresce.
Todo gerador recebe semente=None e usa random.Random(semente), nunca o random global:
com a mesma semente, o grafo sai igual. Os nós são os inteiros 0 a n-1.
Os nomes dos modelos são nomes próprios e não se traduzem.
"""

from __future__ import annotations

import math
import random

from redes.nucleo import Grafo


def _nos_isolados(n: int) -> Grafo:
    """Grafo não direcionado com os nós 0 a n-1 e nenhuma aresta. Tempo e espaço: O(n)."""
    g = Grafo()
    for i in range(n):
        g.adicionar_no(i)
    return g


def erdos_renyi(n: int, p: float, semente=None) -> Grafo:
    """Grafo aleatório G(n, p): cada um dos n(n-1)/2 pares vira aresta com probabilidade p.

    O jeito ingênuo sorteia todos os pares, em O(n²). Este pula direto para o próximo par
    sorteado: o tamanho do pulo segue uma distribuição geométrica.
    Tempo: O(n + m). Espaço: O(n + m).
    Referência: Batagelj e Brandes (2005), Efficient generation of large random networks,
    Physical Review E 71:036113 (algoritmo G(n, p)); modelo de Erdős e Rényi (1959) e Gilbert (1959).
    """
    if n < 0 or not 0 <= p <= 1:
        raise ValueError("use n >= 0 e 0 <= p <= 1")
    gerador = random.Random(semente)

    # Nós isolados também existem: todo nó de 0 a n-1 entra no grafo.
    g = _nos_isolados(n)

    # p = 0: nenhuma aresta.
    if p == 0:
        return g

    # p = 1: grafo completo. É um caso especial porque log(1 - p) = log(0) daria erro.
    if p == 1:
        for v in range(n):
            for w in range(v + 1, n):
                g.adicionar_aresta(v, w)
        return g

    log_q = math.log(1.0 - p)

    # Os pares (v, w) com w < v formam uma tabela triangular: a linha v tem (v, 0), ..., (v, v-1).
    # Começamos "antes" do primeiro par, (1, 0).
    v, w = 1, -1
    while v < n:
        # Pulo geométrico: quantos pares são pulados até o próximo que vira aresta.
        # 1 - random() fica em (0, 1], então o log nunca recebe zero.
        w += 1 + int(math.log(1.0 - gerador.random()) / log_q)

        # Passou do fim da linha v (w >= v): desconta o tamanho da linha e desce para a próxima.
        while w >= v and v < n:
            w -= v
            v += 1

        # Se ainda está dentro da tabela, o par (v, w) vira aresta.
        if v < n:
            g.adicionar_aresta(v, w)
    return g


def barabasi_albert(n: int, m: int, semente=None) -> Grafo:
    """Grafo com ligação preferencial: cada nó novo se liga a m nós antigos, com chance
    proporcional ao grau ("os ricos ficam mais ricos"). Gera hubs, como nas redes sociais.

    Começa com os nós 0 a m-1 sem arestas; o nó m se liga a todos eles. Total: m(n - m) arestas.
    Tempo: O(n·m) esperado. Espaço: O(n·m), por causa da lista de repetidos.
    Referência: Barabási e Albert (1999), Emergence of scaling in random networks, Science 286:509-512.
    """
    if not 1 <= m < n:
        raise ValueError("use 1 <= m < n")
    gerador = random.Random(semente)

    # Os m primeiros nós começam sem arestas.
    g = _nos_isolados(m)

    # O primeiro nó novo (o nó m) se liga a todos os m nós iniciais.
    alvos = list(range(m))

    # Cada nó aparece em "repetidos" uma vez por aresta que tem. Sortear um elemento desta
    # lista já é sortear com chance proporcional ao grau, sem calcular probabilidades.
    repetidos: list[int] = []

    for novo in range(m, n):
        # Liga o nó novo a cada um dos m alvos.
        for alvo in alvos:
            g.adicionar_aresta(novo, alvo)

        # Cada aresta nova soma 1 ao grau das duas pontas: os alvos uma vez cada, o novo m vezes.
        repetidos.extend(alvos)
        repetidos.extend([novo] * m)

        # Sorteia m alvos distintos para o próximo nó. O set descarta os repetidos.
        escolhidos: set[int] = set()
        while len(escolhidos) < m:
            escolhidos.add(gerador.choice(repetidos))

        # sorted() deixa a ordem fixa: com a mesma semente, o grafo sai igual.
        alvos = sorted(escolhidos)
    return g


def watts_strogatz(n: int, k: int, p: float, semente=None) -> Grafo:
    """Mundo pequeno: anel em que cada nó se liga aos k vizinhos mais próximos (k/2 de cada
    lado); depois, cada aresta é religada a um nó aleatório com probabilidade p.

    Com p pequeno, o agrupamento continua alto e as distâncias caem. O número de arestas não
    muda com a religação: sempre n·k/2.
    Tempo: O(n·k) esperado. Espaço: O(n·k).
    Referência: Watts e Strogatz (1998), Collective dynamics of 'small-world' networks, Nature 393:440-442.
    """
    if k < 0 or k % 2 != 0 or k >= n or not 0 <= p <= 1:
        raise ValueError("use k par, 0 <= k < n e 0 <= p <= 1")
    gerador = random.Random(semente)
    g = _nos_isolados(n)

    # 1) Anel: cada nó i se liga a i+1, i+2, ..., i+k/2. O % n fecha o anel (o último volta ao 0).
    for j in range(1, k // 2 + 1):
        for i in range(n):
            g.adicionar_aresta(i, (i + j) % n)

    # 2) Religação: cada aresta (i, i+j) do anel troca a ponta i+j por um nó sorteado, com chance p.
    for j in range(1, k // 2 + 1):
        for i in range(n):
            # Se i já é vizinho de todos, não há para onde religar: a aresta fica como está.
            if gerador.random() < p and g.grau(i) < n - 1:
                # Sorteia até achar w que não seja o próprio i nem já vizinho de i
                # (assim não surgem laços nem arestas repetidas).
                w = gerador.randrange(n)
                while w == i or g.tem_aresta(i, w):
                    w = gerador.randrange(n)

                g.remover_aresta(i, (i + j) % n)
                g.adicionar_aresta(i, w)
    return g
