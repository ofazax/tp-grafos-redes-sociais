"""Influenciadores: limiar epidêmico e simulação SIR. Frente 5."""

from __future__ import annotations

import math
import random
from collections.abc import Hashable, Iterable

from redes.nucleo.grafo import Grafo, No
from redes.nucleo.indexador import para_listas_indexadas


def limiar_epidemico(g: Grafo) -> float:
    """Limiar epidêmico do SIR: beta_c = <k> / (<k²> - <k>).

    <k> é o grau médio e <k²> a média dos graus ao quadrado. Com recuperação em um passo
    (gamma = 1), beta é a chance de cada aresta transmitir, e o espalhamento só atinge uma
    fração fixa da rede quando beta passa de beta_c. Abaixo do limiar, todo surto morre
    pequeno. A fórmula vale para redes sem correlação entre os graus dos vizinhos (modelo de
    configuração); em redes reais, é uma aproximação. Graus muito desiguais deixam <k²>
    grande e o limiar pequeno: os hubs espalham com facilidade.

    Laços (v, v) são ignorados, como na simulação. Se nenhum nó tem grau 2 ou mais
    (<k²> = <k>), nenhum surto cresce, e o limiar é infinito.

    Tempo: O(n). Espaço: O(n).
    Referência: Newman (2002), "Spread of epidemic disease on networks", Physical Review E 66.
    """
    if g.direcionado:
        raise ValueError("o limiar epidêmico só está definido para grafo não direcionado")
    n = g.numero_de_nos()
    if n == 0:
        raise ValueError("o grafo não tem nós")

    # Grau sem laços: o laço não transmite para ninguém.
    graus = [g.grau(v) - (2 if g.tem_aresta(v, v) else 0) for v in g.nos()]
    k1 = sum(graus) / n
    k2 = sum(k * k for k in graus) / n

    if k2 - k1 <= 0:
        return math.inf
    return k1 / (k2 - k1)


def _validar_parametros(beta: float, gamma: float) -> None:
    # beta e gamma são probabilidades; gamma = 0 faria o infectado nunca se recuperar.
    if not 0.0 <= beta <= 1.0:
        raise ValueError(f"beta deve estar entre 0 e 1, recebeu {beta}")
    if not 0.0 < gamma <= 1.0:
        raise ValueError(f"gamma deve estar em (0, 1], recebeu {gamma}")


def _rodada_sir(
    adj: list[list[int]],
    origens: list[int],
    beta: float,
    gamma: float,
    rng: random.Random,
    estado: bytearray,
) -> list[int]:
    """Uma rodada do SIR sobre listas indexadas. Devolve os índices atingidos (recuperados).

    estado[i] vale 0 (suscetível), 1 (infectado) ou 2 (recuperado). Ele chega todo zerado e
    volta todo zerado: só os nós atingidos são tocados, então a rodada custa o tamanho do
    surto, e não O(n).
    """
    atingidos = list(dict.fromkeys(origens))
    for i in atingidos:
        estado[i] = 1
    infectados = atingidos[:]
    aleatorio = rng.random

    while infectados:
        proximos: list[int] = []
        for u in infectados:
            # u tenta transmitir, uma vez por passo, para cada vizinho ainda suscetível.
            for w in adj[u]:
                if estado[w] == 0 and aleatorio() < beta:
                    estado[w] = 1
                    atingidos.append(w)
                    proximos.append(w)
            # Depois de transmitir, u se recupera com chance gamma; senão, segue infectado.
            if gamma >= 1.0 or aleatorio() < gamma:
                estado[u] = 2
            else:
                proximos.append(u)
        infectados = proximos

    for i in atingidos:
        estado[i] = 0
    return atingidos


def simular_sir(
    g: Grafo,
    origens: No | Iterable[No],
    beta: float,
    gamma: float = 1.0,
    semente: int | None = None,
) -> set[No]:
    """Uma rodada do modelo SIR em tempo discreto. Devolve os nós atingidos.

    Cada nó é suscetível (S), infectado (I) ou recuperado (R). No passo 0, só as origens
    estão infectadas. A cada passo, cada infectado transmite para cada vizinho suscetível
    com probabilidade beta, de forma independente, e depois se recupera com probabilidade
    gamma. A rodada acaba quando não sobra infectado, e os atingidos são os recuperados
    (incluindo as origens). Com gamma = 1, cada infectado tem uma única chance de
    transmitir, como em Kitsak et al. (2010). No direcionado, a transmissão segue o sentido
    das arestas. Laços não transmitem (o nó já está infectado).

    `origens` pode ser um nó ou uma coleção de nós. A `semente` fixa o sorteio, para que o
    resultado possa ser repetido.

    Tempo: O(n + m) para montar as listas indexadas, mais O(n + m) no pior caso para a rodada
    (com gamma = 1, cada aresta é tentada no máximo uma vez em cada sentido). Com gamma < 1,
    um infectado tenta de novo a cada passo, em média 1/gamma passos. Espaço: O(n + m).
    Referência: Kitsak et al. (2010), "Identification of influential spreaders in complex
    networks", Nature Physics 6.
    """
    _validar_parametros(beta, gamma)
    lista = _lista_de_origens(g, origens)

    indexador, adj = para_listas_indexadas(g)
    indice = indexador.para_indice
    estado = bytearray(len(indexador))
    atingidos = _rodada_sir(adj, [indice[v] for v in lista], beta, gamma, random.Random(semente), estado)
    return {indexador.para_no[i] for i in atingidos}


def _lista_de_origens(g: Grafo, origens: No | Iterable[No]) -> list[No]:
    # Um nó do grafo vale como origem única, mesmo que seja iterável (uma string ou uma tupla).
    # Fora isso, uma coleção vira lista; qualquer outro valor é tratado como um nó só.
    if isinstance(origens, Hashable) and g.tem_no(origens):
        return [origens]
    if isinstance(origens, Iterable) and not isinstance(origens, (str, bytes)):
        lista = list(origens)
    else:
        lista = [origens]
    if not lista:
        raise ValueError("informe pelo menos um nó de origem")
    for v in lista:
        if not g.tem_no(v):
            raise ValueError(f"o nó de origem {v!r} não está no grafo")
    return lista


def poder_de_espalhamento(
    g: Grafo,
    beta: float,
    gamma: float = 1.0,
    rodadas: int = 100,
    semente: int | None = None,
    origens: Iterable[No] | None = None,
) -> dict[No, float]:
    """Alcance médio rho(v) do SIR que começa só em v: a fração da rede atingida, na média.

    Para cada origem v, roda `rodadas` simulações (Monte Carlo) e devolve
    rho(v) = (soma dos atingidos nas rodadas) / (rodadas * n), entre 1/n e 1. É a referência
    contra a qual os rankings das centralidades são comparados (pergunta P1). O valor de beta
    deve ficar um pouco acima do limiar epidêmico: abaixo dele todos os nós atingem pouco, e
    muito acima todos atingem quase a rede inteira, e o ranking não distingue ninguém.

    Por padrão simula a partir de todos os nós; `origens` restringe a alguns (útil em redes
    grandes). Um único gerador, criado com `semente`, é usado em todas as rodadas, então o
    resultado se repete com a mesma semente e a mesma ordem de inserção dos nós.

    Tempo: O(n + m) para indexar, mais O(rodadas * |origens| * (n + m)) no pior caso. Perto do
    limiar, quase todos os surtos são pequenos, e o custo real fica bem abaixo disso.
    Espaço: O(n + m).
    Referência: Kitsak et al. (2010), Nature Physics 6, 888-893.
    """
    _validar_parametros(beta, gamma)
    if rodadas < 1:
        raise ValueError(f"rodadas deve ser pelo menos 1, recebeu {rodadas}")

    indexador, adj = para_listas_indexadas(g)
    n = len(indexador)
    indice = indexador.para_indice

    if origens is None:
        lista = list(indexador.para_no)
    else:
        lista = list(origens)
        for v in lista:
            if v not in indice:
                raise ValueError(f"o nó de origem {v!r} não está no grafo")

    rng = random.Random(semente)
    estado = bytearray(n)
    resultado: dict[No, float] = {}
    for v in lista:
        i = indice[v]
        total = 0
        for _ in range(rodadas):
            total += len(_rodada_sir(adj, [i], beta, gamma, rng, estado))
        resultado[v] = total / (rodadas * n)
    return resultado


def _pares_empatados(valores: list[float]) -> int:
    """Quantos pares têm o mesmo valor numa lista já ordenada: soma de t(t-1)/2 por grupo."""
    total = 0
    inicio = 0
    for i in range(1, len(valores) + 1):
        if i == len(valores) or valores[i] != valores[inicio]:
            t = i - inicio
            total += t * (t - 1) // 2
            inicio = i
    return total


def _ordenar_contando_inversoes(valores: list[float]) -> tuple[list[float], int]:
    """Merge sort que conta as inversões: pares i < j com valores[i] > valores[j] (iguais não contam)."""
    if len(valores) <= 1:
        return valores, 0
    meio = len(valores) // 2
    esquerda, inv_esquerda = _ordenar_contando_inversoes(valores[:meio])
    direita, inv_direita = _ordenar_contando_inversoes(valores[meio:])

    juntos: list[float] = []
    inversoes = inv_esquerda + inv_direita
    i = j = 0
    while i < len(esquerda) and j < len(direita):
        if direita[j] < esquerda[i]:
            # direita[j] é menor que todos os que sobraram na esquerda: cada um é uma inversão.
            inversoes += len(esquerda) - i
            juntos.append(direita[j])
            j += 1
        else:
            juntos.append(esquerda[i])
            i += 1
    juntos.extend(esquerda[i:])
    juntos.extend(direita[j:])
    return juntos, inversoes


def tau_de_kendall(x: dict[No, float], y: dict[No, float]) -> float:
    """Tau-b de Kendall: concordância entre a ordem dos nós em x e em y, de -1 a 1.

    Um par de nós é concordante quando x e y o ordenam do mesmo jeito, e discordante quando o
    ordenam ao contrário. Com P concordantes, Q discordantes e n0 = n(n-1)/2 pares,
    tau_b = (P - Q) / sqrt((n0 - n1)(n0 - n2)), em que n1 e n2 contam os pares empatados em x
    e em y. Dá 1 quando as ordens são iguais, -1 quando são invertidas e perto de 0 quando
    não têm relação. Só a ordem importa, não os valores: dá para comparar medidas em escalas
    diferentes. O desconto dos empates (variante b) é o que permite comparar o número de
    núcleo, que tem poucos valores distintos.

    Usa os nós presentes nos dois dicionários. Devolve NaN se sobrar menos de 2 nós, ou se
    todos os valores de x (ou de y) forem iguais, porque aí não há ordem para comparar.

    Algoritmo de Knight: ordena os pares (x, y), conta os empates e conta as discordâncias como
    inversões de y num merge sort, sem comparar os n0 pares um a um.
    Tempo: O(n log n). Espaço: O(n).
    Referência: Kendall (1938), "A new measure of rank correlation"; Kendall (1945), "The
    treatment of ties in ranking problems"; Knight (1966), "A computer method for calculating
    Kendall's tau with ungrouped data" (o algoritmo, sem empates); Christensen (2005), "Fast
    algorithms for the calculation of Kendall's tau" (a versão com empates, usada aqui).
    """
    pares = sorted((x[v], y[v]) for v in x if v in y)
    n = len(pares)
    if n < 2:
        return math.nan

    n0 = n * (n - 1) // 2
    # Empates em x, e empates em x e y ao mesmo tempo (os pares iguais ficam vizinhos).
    n1 = _pares_empatados([a for a, _ in pares])
    n3 = _pares_empatados(pares)  # type: ignore[arg-type]
    # Com os pares ordenados por (x, y), um par discordante é uma inversão de y.
    ys_ordenados, discordantes = _ordenar_contando_inversoes([b for _, b in pares])
    n2 = _pares_empatados(ys_ordenados)

    denominador = math.sqrt((n0 - n1) * (n0 - n2))
    if denominador == 0:
        return math.nan
    # P - Q = (pares sem empate em x nem em y) - 2Q = n0 - n1 - n2 + n3 - 2Q.
    return (n0 - n1 - n2 + n3 - 2 * discordantes) / denominador


def comparar_rankings(
    centralidades: dict[str, dict[No, float]],
    referencias: dict[str, dict[No, float]],
) -> dict[str, dict[str, float]]:
    """Tau-b de cada centralidade contra cada referência: resultado[centralidade][referência].

    Exemplo: comparar_rankings({"grau": ..., "pagerank": ...}, {"alcance": rho, "visualizacoes": w})
    devolve {"grau": {"alcance": 0,7, "visualizacoes": 0,4}, ...}. A centralidade de maior tau
    contra o alcance responde à pergunta P1, e a de maior tau contra as visualizações, à P2.

    Tempo: O(c * r * n log n), com c centralidades e r referências. Espaço: O(n).
    """
    return {
        nome: {referencia: tau_de_kendall(valores, alvo) for referencia, alvo in referencias.items()}
        for nome, valores in centralidades.items()
    }
