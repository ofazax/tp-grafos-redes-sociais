"""Gráficos de desempenho para o relatório e os slides. Frente 3.

Uso, da raiz do projeto, depois de medir.py e comparar_networkx.py:
    python -m desempenho.graficos

Lê desempenho/resultados/medicoes_redes.csv e medicoes_networkx.csv e salva, em
desempenho/resultados/figuras/, cada gráfico em PNG (slides) e em PDF (relatório):
    tempo_loglog     tempo × (n + m), um painel por algoritmo, com a inclinação da reta
    memoria_loglog   pico de memória × (n + m)
    razao_networkx   quantas vezes o nosso código é mais rápido que o NetworkX, nas bases
    teps_bfs         TEPS da BFS nos grafos sintéticos
Também salva inclinacoes.csv: o expoente b de tempo ~ (n + m)^b, ajustado nos sintéticos.
"""

from __future__ import annotations

import csv
import math
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
from matplotlib.ticker import FuncFormatter, LogLocator, NullFormatter

from desempenho.casos import ALGORITMOS, K_AMOSTRA, PASTA_RESULTADOS

PASTA_FIGURAS = PASTA_RESULTADOS / "figuras"

# Títulos curtos: as figuras têm 8 polegadas de largura, para caberem no relatório SBC
# (15 cm de texto) com letra legível, e continuam boas nos slides.
TITULOS = {
    "bfs": "BFS",
    "intermediacao_exata": "Intermediação exata",
    f"intermediacao_k{K_AMOSTRA}": f"Intermediação k = {K_AMOSTRA}",
    "pagerank": "PageRank",
    "numero_de_nucleo": "k-core",
}

# Complexidade teórica de cada algoritmo (expoente em log-log e rótulo da reta de referência).
# Nos sintéticos m ~ 5n, então O(nm) cresce como (n + m)^2. O PageRank faz O(n + m) por
# iteração, com um número de iterações que quase não muda com o tamanho.
TEORIA_TEMPO = {
    "bfs": (1, "O(n + m)"),
    "intermediacao_exata": (2, "O(nm)"),
    f"intermediacao_k{K_AMOSTRA}": (1, "O(km)"),
    "pagerank": (1, "O(n + m)"),
    "numero_de_nucleo": (1, "O(n + m)"),
}
TEORIA_MEMORIA = {algoritmo: (1, "O(n + m)") for algoritmo in ALGORITMOS}

# Cores: azul = nosso código, laranja = NetworkX (paleta conferida para daltonismo e contraste).
COR = {"redes": "#2a78d6", "networkx": "#eb6834"}
NOME = {"redes": "redes (nosso)", "networkx": "NetworkX 3.7"}
# Formato do marcador = modelo do grafo (a cor sozinha nunca carrega a informação).
MARCADOR = {"ER": "o", "BA": "s", "WS": "^"}
MARCADOR_BASE = "D"

FUNDO = "#ffffff"
TINTA = "#0b0b0b"
TINTA_2 = "#52514e"
TINTA_FRACA = "#898781"
GRADE = "#e1e0d9"
EIXO = "#c3c2b7"


def _estilo() -> None:
    """Estilo comum das figuras: fundo branco, grade clara e sem as bordas de cima e da direita."""
    plt.rcParams.update(
        {
            "font.family": "sans-serif",
            "font.size": 10,
            "xtick.labelsize": 8.5,
            "ytick.labelsize": 8.5,
            "axes.labelsize": 9.5,
            "legend.fontsize": 9,
            "legend.title_fontsize": 9.5,
            "figure.facecolor": FUNDO,
            "axes.facecolor": FUNDO,
            "axes.edgecolor": EIXO,
            "axes.labelcolor": TINTA_2,
            "axes.titlesize": 10.5,
            "axes.titleweight": "bold",
            "axes.titlecolor": TINTA,
            "axes.titlelocation": "left",
            "axes.spines.top": False,
            "axes.spines.right": False,
            "xtick.color": TINTA_FRACA,
            "ytick.color": TINTA_FRACA,
            "xtick.labelcolor": TINTA_2,
            "ytick.labelcolor": TINTA_2,
            "legend.frameon": False,
            "lines.linewidth": 2,
            "lines.solid_capstyle": "round",
            "lines.solid_joinstyle": "round",
            "savefig.facecolor": FUNDO,
        }
    )


# --------------------------------------------------------------------------- leitura


def ler(caminho: Path) -> list[dict]:
    """Linhas do CSV, com os números já convertidos."""
    if not caminho.exists():
        raise SystemExit(f"falta {caminho}: rode antes medir.py e comparar_networkx.py")
    linhas = []
    with open(caminho, newline="", encoding="utf-8") as arquivo:
        for linha in csv.DictReader(arquivo):
            for chave in ("n", "m", "n_mais_m", "repeticoes"):
                linha[chave] = int(linha[chave])
            for chave in ("tempo_mediana_s", "memoria_pico_mib", "teps", "diferenca_max"):
                linha[chave] = float(linha[chave]) if linha[chave] else None
            linhas.append(linha)
    return linhas


def selecionar(linhas: list[dict], **filtro) -> list[dict]:
    """Linhas em que cada coluna do filtro tem o valor pedido. Tempo: O(número de linhas)."""
    return [linha for linha in linhas if all(linha[k] == v for k, v in filtro.items())]


def inclinacao(pontos: list[tuple[float, float]]) -> float | None:
    """Expoente b do ajuste y = a·x^b por mínimos quadrados em log-log (None com < 3 pontos).

    Tempo: O(p), para p pontos.
    """
    if len(pontos) < 3:
        return None
    xs = [math.log10(x) for x, _ in pontos]
    ys = [math.log10(y) for _, y in pontos]
    mx, my = sum(xs) / len(xs), sum(ys) / len(ys)
    sxx = sum((x - mx) ** 2 for x in xs)
    sxy = sum((x - mx) * (y - my) for x, y in zip(xs, ys))
    return sxy / sxx


# --------------------------------------------------------------------------- formatação


def _br(valor: float, casas: int = 0) -> str:
    """Número no formato brasileiro: 1.234,5."""
    texto = f"{valor:,.{casas}f}"
    return texto.replace(",", "_").replace(".", ",").replace("_", ".")


def _rotulo_contagem(valor: float, _pos=None) -> str:
    """Marcas do eixo n + m: 100, 1 mil, 10 mil, 100 mil, 1 milhão."""
    if valor >= 1e6:
        return f"{_br(valor / 1e6)} milhão" if valor < 2e6 else f"{_br(valor / 1e6)} milhões"
    if valor >= 1e3:
        return f"{_br(valor / 1e3)} mil"
    return _br(valor)


def _rotulo_potencia(valor: float, _pos=None) -> str:
    """Marcas do eixo n + m como potências de 10 (10², 10³...): curtas, cabem nos painéis."""
    return f"$10^{{{round(math.log10(valor))}}}$"


def _rotulo_tempo(valor: float, _pos=None) -> str:
    """Marcas do eixo de tempo: 10 µs, 1 ms, 100 ms, 1 s, 10 s."""
    if valor >= 1:
        return f"{_br(valor)} s"
    if valor >= 1e-3:
        return f"{_br(valor * 1e3)} ms"
    return f"{_br(valor * 1e6)} µs"


def _rotulo_memoria(valor: float, _pos=None) -> str:
    """Marcas do eixo de memória, sempre em MiB: 0,01 MiB, 1 MiB, 1.000 MiB."""
    if valor >= 1:
        return f"{_br(valor)} MiB"
    return f"{valor:g}".replace(".", ",") + " MiB"


def _eixo_log(eixo, formatador_x, formatador_y) -> None:
    """Eixos x e y em escala log, com uma marca por potência de 10 e a grade só nelas."""
    eixo.set_xscale("log")
    eixo.set_yscale("log")
    for alvo, formatador in ((eixo.xaxis, formatador_x), (eixo.yaxis, formatador_y)):
        alvo.set_major_locator(LogLocator(base=10, numticks=12))
        alvo.set_major_formatter(FuncFormatter(formatador))
        alvo.set_minor_formatter(NullFormatter())
    eixo.grid(True, which="major", color=GRADE, linewidth=0.8)
    eixo.set_axisbelow(True)
    eixo.tick_params(which="minor", length=0)


def _legenda_comum(eixo) -> None:
    """Legenda num painel vazio: cor = implementação, formato = grafo, tracejado = teoria.

    Uma legenda só, com um cabeçalho em negrito para cada grupo (três legendas separadas
    se encostavam no painel pequeno)."""
    eixo.axis("off")

    def cabecalho(texto):
        """Entrada da legenda sem marcador, usada como título de cada grupo."""
        return Line2D([], [], linestyle="none", label=texto)

    alcas = [cabecalho("Implementação")]
    alcas += [Line2D([], [], color=COR[i], marker="o", markersize=6, label=NOME[i]) for i in ("redes", "networkx")]
    alcas.append(cabecalho("Grafo"))
    alcas += [
        Line2D([], [], color=TINTA_FRACA, marker=MARCADOR[m], linestyle="none", markersize=6, label=rotulo)
        for m, rotulo in (("ER", "Erdős–Rényi"), ("BA", "Barabási–Albert"), ("WS", "Watts–Strogatz"))
    ]
    alcas.append(
        Line2D([], [], color=TINTA_FRACA, marker=MARCADOR_BASE, linestyle="none", markersize=6, label="bases reais")
    )
    alcas.append(cabecalho("Referência"))
    alcas.append(
        Line2D([], [], color=TINTA_FRACA, linewidth=1.2, linestyle=(0, (4, 3)), label="complexidade teórica")
    )
    legenda = eixo.legend(handles=alcas, loc="center left", handlelength=2.2, labelspacing=0.55)
    for texto in legenda.get_texts():
        if texto.get_text() in ("Implementação", "Grafo", "Referência"):
            texto.set_color(TINTA)
            texto.set_fontweight("bold")
            # Sem marcador ao lado, o cabeçalho começa onde começariam os marcadores.
            texto.set_position((-2.2 * texto.get_fontsize() * 1.25, 0))
        else:
            texto.set_color(TINTA_2)


def _salvar(figura, nome: str) -> None:
    """Salva a figura em PNG (slides) e em PDF (relatório) na pasta de figuras e a fecha."""
    PASTA_FIGURAS.mkdir(parents=True, exist_ok=True)
    for extensao in ("png", "pdf"):
        figura.savefig(PASTA_FIGURAS / f"{nome}.{extensao}", dpi=200, bbox_inches="tight")
    plt.close(figura)
    print(f"figura: {PASTA_FIGURAS / nome}.png e .pdf")


# --------------------------------------------------------------------------- gráficos


def _reta_teorica(eixo, pontos: list[tuple[float, float]], expoente: float, rotulo: str) -> None:
    """Reta de inclinação `expoente` (a complexidade teórica), paralela aos nossos pontos e
    4 vezes abaixo deles, para não cobri-los. Em log-log, O(n + m) é inclinação 1 e O(nm),
    com m proporcional a n, é inclinação 2."""
    if len(pontos) < 2:
        return
    xs = [math.log10(x) for x, _ in pontos]
    ys = [math.log10(y) for _, y in pontos]
    mx, my = sum(xs) / len(xs), sum(ys) / len(ys)
    inicio, fim = min(xs), max(xs)
    altura = [my + expoente * (x - mx) - math.log10(4) for x in (inicio, fim)]
    eixo.plot(
        [10**inicio, 10**fim], [10**y for y in altura],
        color=TINTA_FRACA, linewidth=1.2, linestyle=(0, (4, 3)), zorder=1,
    )
    # O rótulo fica no começo da reta, embaixo dela: os dados estão acima, então ali está vazio.
    eixo.annotate(
        rotulo, (10**inicio, 10 ** altura[0]), xytext=(4, -6), textcoords="offset points",
        ha="left", va="top", fontsize=9, color=TINTA_2,
    )
    # Folga embaixo da reta, para o rótulo não encostar no eixo.
    eixo.set_ylim(bottom=min(eixo.get_ylim()[0], 10 ** altura[0] / 6))


def grafico_loglog(
    linhas: list[dict], coluna: str, formatador_y, rotulo_y: str, nome: str, teoria: dict
) -> dict:
    """Um painel por algoritmo, em log-log: cada modelo sintético vira uma linha por
    implementação; as bases aparecem como losangos e a reta tracejada mostra a complexidade
    teórica. Devolve as inclinações calculadas."""
    figura, eixos = plt.subplots(2, 3, figsize=(8, 5.6), constrained_layout=True)
    inclinacoes = {}
    for eixo, algoritmo in zip(eixos.flat, ALGORITMOS):
        textos = []
        nossos_sinteticos = []
        for implementacao in ("redes", "networkx"):
            dados = selecionar(linhas, implementacao=implementacao, algoritmo=algoritmo)
            sinteticos = []
            for modelo, marcador in MARCADOR.items():
                pontos = sorted((l["n_mais_m"], l[coluna]) for l in selecionar(dados, grafo=modelo) if l[coluna])
                if not pontos:
                    continue
                sinteticos += pontos
                eixo.plot(
                    *zip(*pontos),
                    color=COR[implementacao],
                    marker=marcador,
                    markersize=4.5,
                    markeredgecolor=FUNDO,
                    markeredgewidth=0.8,
                    linewidth=1.4,
                    alpha=0.9,
                )
            bases = [(l["n_mais_m"], l[coluna]) for l in selecionar(dados, tipo="base") if l[coluna]]
            if bases:
                eixo.plot(
                    *zip(*bases),
                    color=COR[implementacao],
                    marker=MARCADOR_BASE,
                    markersize=5.5,
                    markeredgecolor=FUNDO,
                    markeredgewidth=0.8,
                    linestyle="none",
                )
            b = inclinacao(sinteticos)
            inclinacoes[(algoritmo, implementacao)] = b
            if b is not None:
                textos.append(f"{NOME[implementacao].split(' ')[0]} {_br(b, 2)}")
            if implementacao == "redes":
                nossos_sinteticos = sinteticos
        # Primeiro a escala log, depois a reta: a folga embaixo dela só faz sentido em log.
        _eixo_log(eixo, _rotulo_potencia, formatador_y)
        if algoritmo in teoria:
            _reta_teorica(eixo, nossos_sinteticos, *teoria[algoritmo])
        eixo.set_title(TITULOS[algoritmo])
        if textos:
            # Três linhas curtas no canto de cima à esquerda, a região que os dados não ocupam.
            eixo.text(
                0.03, 0.97, "inclinação\n" + "\n".join(textos),
                transform=eixo.transAxes, va="top", ha="left", fontsize=8, color=TINTA_2, linespacing=1.3,
                bbox={"facecolor": FUNDO, "edgecolor": "none", "pad": 1.5, "alpha": 0.9},
            )
    for eixo in eixos[1]:
        eixo.set_xlabel("n + m (nós + arestas)")
    for eixo in eixos[:, 0]:
        eixo.set_ylabel(rotulo_y)
    _legenda_comum(eixos.flat[-1])
    _salvar(figura, nome)
    return inclinacoes


def grafico_razao(redes: list[dict], networkx: list[dict]) -> None:
    """Tempo do NetworkX dividido pelo nosso, em cada base: acima de 1×, o nosso é mais rápido.

    O Karate fica de fora: os tempos dele são de microssegundos e a razão vira ruído.
    """
    bases = ("Thrones", "Twitch PT", "ego-Facebook")
    figura, eixos = plt.subplots(1, len(bases), figsize=(8, 3.4), sharey=True, constrained_layout=True)
    maior = 1.0
    razoes = {}
    for base in bases:
        for algoritmo in ALGORITMOS:
            nosso = selecionar(redes, grafo=base, algoritmo=algoritmo)
            deles = selecionar(networkx, grafo=base, algoritmo=algoritmo)
            if nosso and deles:
                razoes[(base, algoritmo)] = deles[0]["tempo_mediana_s"] / nosso[0]["tempo_mediana_s"]
                maior = max(maior, razoes[(base, algoritmo)])
    posicoes = list(range(len(ALGORITMOS)))[::-1]
    for eixo, base in zip(eixos, bases):
        n = selecionar(redes, grafo=base)
        for y, algoritmo in zip(posicoes, ALGORITMOS):
            r = razoes.get((base, algoritmo))
            if r is None:
                continue
            eixo.barh(y, r, height=0.5, color=COR["redes"])
            # Abaixo de 1×, o rótulo vai depois da linha de 1×, para a linha não cortar o texto.
            eixo.text(max(r, 1) + maior * 0.03, y, f"{_br(r, 1)}×", va="center", ha="left", fontsize=8.5, color=TINTA)
        eixo.axvline(1, color=TINTA_FRACA, linewidth=1)
        eixo.set_xlim(0, maior * 1.25)
        eixo.set_yticks(posicoes, [TITULOS[a] for a in ALGORITMOS])
        eixo.tick_params(axis="y", length=0)
        eixo.grid(True, axis="x", color=GRADE, linewidth=0.8)
        eixo.set_axisbelow(True)
        eixo.xaxis.set_major_formatter(FuncFormatter(lambda v, _p: f"{_br(v)}×"))
        # Nome da base no título e o tamanho logo abaixo, em letra menor.
        eixo.set_title(base, pad=16)
        if n:
            eixo.text(
                0, 1.02, f"n = {_br(n[0]['n'])} · m = {_br(n[0]['m'])}",
                transform=eixo.transAxes, va="bottom", ha="left", fontsize=8, color=TINTA_2,
            )
    figura.supxlabel(
        "tempo do NetworkX ÷ tempo do nosso (à direita da linha de 1×, o nosso é mais rápido)",
        fontsize=9, color=TINTA_2,
    )
    _salvar(figura, "razao_networkx")


def grafico_teps(linhas: list[dict]) -> None:
    """TEPS da BFS (arestas percorridas por segundo) × n, nos grafos sintéticos."""
    figura, eixo = plt.subplots(figsize=(8, 4.5), constrained_layout=True)
    for implementacao in ("redes", "networkx"):
        dados = selecionar(linhas, implementacao=implementacao, algoritmo="bfs", tipo="sintetico")
        for modelo, marcador in MARCADOR.items():
            pontos = sorted((l["n"], l["teps"] / 1e6) for l in selecionar(dados, grafo=modelo) if l["teps"])
            if pontos:
                eixo.plot(
                    *zip(*pontos), color=COR[implementacao], marker=marcador, markersize=6,
                    markeredgecolor=FUNDO, markeredgewidth=1, linewidth=1.6,
                )
    eixo.set_xscale("log")
    eixo.xaxis.set_major_locator(LogLocator(base=10))
    eixo.xaxis.set_major_formatter(FuncFormatter(_rotulo_contagem))
    eixo.xaxis.set_minor_formatter(NullFormatter())
    eixo.tick_params(which="minor", length=0)
    eixo.set_ylim(bottom=0)
    eixo.yaxis.set_major_formatter(FuncFormatter(lambda v, _p: _br(v)))
    eixo.grid(True, which="major", color=GRADE, linewidth=0.8)
    eixo.set_axisbelow(True)
    eixo.set_xlabel("n (nós)")
    eixo.set_ylabel("milhões de arestas por segundo")
    eixo.set_title("TEPS da BFS")
    alcas = [Line2D([], [], color=COR[i], marker="o", markersize=6, label=NOME[i]) for i in ("redes", "networkx")]
    alcas += [
        Line2D([], [], color=TINTA_FRACA, marker=MARCADOR[m], linestyle="none", markersize=6, label=m)
        for m in MARCADOR
    ]
    legenda = eixo.legend(handles=alcas, loc="lower left", ncols=5, fontsize=9)
    for texto in legenda.get_texts():
        texto.set_color(TINTA_2)
    _salvar(figura, "teps_bfs")


def salvar_inclinacoes(tempo: dict, memoria: dict) -> None:
    """Grava inclinacoes.csv: o expoente do tempo e o da memória de cada algoritmo."""
    caminho = PASTA_RESULTADOS / "inclinacoes.csv"
    with open(caminho, "w", newline="", encoding="utf-8") as arquivo:
        escritor = csv.writer(arquivo)
        escritor.writerow(["algoritmo", "implementacao", "inclinacao_tempo", "inclinacao_memoria"])
        for algoritmo in ALGORITMOS:
            for implementacao in ("redes", "networkx"):
                bt, bm = tempo.get((algoritmo, implementacao)), memoria.get((algoritmo, implementacao))
                escritor.writerow(
                    [algoritmo, implementacao, "" if bt is None else f"{bt:.3f}", "" if bm is None else f"{bm:.3f}"]
                )
    print(f"tabela: {caminho}")


def resumo(redes: list[dict], networkx: list[dict], tempo: dict) -> None:
    """Tabela no terminal: inclinação e tempos na Twitch PT, a base principal."""
    print("\nalgoritmo               inclinação (redes / nx)   Twitch PT: redes      NetworkX     razão")
    for algoritmo in ALGORITMOS:
        br, bn = tempo.get((algoritmo, "redes")), tempo.get((algoritmo, "networkx"))
        nosso = selecionar(redes, grafo="Twitch PT", algoritmo=algoritmo)
        deles = selecionar(networkx, grafo="Twitch PT", algoritmo=algoritmo)
        tn = nosso[0]["tempo_mediana_s"] if nosso else None
        td = deles[0]["tempo_mediana_s"] if deles else None
        razao = f"{_br(td / tn, 1)}×" if tn and td else "-"
        print(
            f"{TITULOS[algoritmo]:<23} "
            f"{(_br(br, 2) if br else '-'):>6} / {(_br(bn, 2) if bn else '-'):<6}       "
            f"{(_rotulo_tempo(tn) if tn else '-'):>12}   {(_rotulo_tempo(td) if td else '-'):>12}   {razao:>6}"
        )


def principal() -> None:
    """Lê os dois CSVs e gera todas as figuras, a tabela de inclinações e o resumo."""
    _estilo()
    redes = ler(PASTA_RESULTADOS / "medicoes_redes.csv")
    networkx = ler(PASTA_RESULTADOS / "medicoes_networkx.csv")
    todas = redes + networkx
    tempo = grafico_loglog(
        todas, "tempo_mediana_s", _rotulo_tempo, "tempo (mediana de 5)", "tempo_loglog", TEORIA_TEMPO
    )
    memoria = grafico_loglog(
        todas, "memoria_pico_mib", _rotulo_memoria, "pico de memória", "memoria_loglog", TEORIA_MEMORIA
    )
    grafico_razao(redes, networkx)
    grafico_teps(todas)
    salvar_inclinacoes(tempo, memoria)
    resumo(redes, networkx, tempo)


if __name__ == "__main__":
    principal()
