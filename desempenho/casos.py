"""Grafos e funções de medição comuns a medir.py e comparar_networkx.py. Frente 3.

Os dois scripts medem os mesmos algoritmos nos mesmos grafos, com as mesmas regras:
tempo = mediana de 5 execuções com time.perf_counter, pico de memória com tracemalloc
(numa execução separada, porque o tracemalloc deixa o código mais lento) e TEPS da BFS.
Este arquivo não importa o NetworkX.
"""

from __future__ import annotations

import csv
import datetime
import gc
import importlib.metadata
import os
import platform
import random
import statistics
import time
import tracemalloc
from collections.abc import Callable, Iterator
from dataclasses import dataclass
from pathlib import Path

from redes.geradores import barabasi_albert, erdos_renyi, watts_strogatz
from redes.leitores import carregar_facebook, carregar_karate, carregar_thrones, carregar_twitch_ptbr
from redes.nucleo.grafo import Grafo, No

PASTA_RESULTADOS = Path(__file__).resolve().parent / "resultados"

# Grafos sintéticos de 10^3 a 10^5 nós, todos com grau médio 10 (m ~ 5n).
TAMANHOS = (1_000, 2_000, 5_000, 10_000, 20_000, 50_000, 100_000)
TAMANHOS_RAPIDO = (1_000, 2_000)
GRAU_MEDIO = 10
SEMENTE = 42
REPETICOES = 5

# A intermediação exata custa O(nm): com 5.000 nós já leva uns 20 s por execução, e com
# 10.000 passa de 1 minuto. Acima deste limite, só a versão amostrada (k origens) é medida.
MAX_N_EXATA = 5_000
K_AMOSTRA = 100

# Ordem em que os algoritmos aparecem no CSV e nos gráficos.
ALGORITMOS = ("bfs", "intermediacao_exata", f"intermediacao_k{K_AMOSTRA}", "pagerank", "numero_de_nucleo")

COLUNAS = (
    "implementacao",
    "algoritmo",
    "grafo",
    "tipo",
    "n",
    "m",
    "n_mais_m",
    "repeticoes",
    "tempo_mediana_s",
    "tempo_min_s",
    "tempo_max_s",
    "memoria_pico_mib",
    "teps",
    "diferenca_max",
)


@dataclass(frozen=True)
class Caso:
    """Um grafo de teste: nome do modelo ou da base, tipo e a função que o constrói."""

    nome: str
    tipo: str  # "sintetico" ou "base"
    construir: Callable[[], Grafo]


def casos(rapido: bool = False, com_bases: bool = True) -> Iterator[Caso]:
    """Os grafos medidos: ER, BA e WS em cada tamanho e, depois, as 4 bases.

    Os grafos são construídos só quando o caso é usado, para não ocupar memória com todos ao
    mesmo tempo. Com rapido=True, só os dois menores tamanhos (para conferir os scripts).
    """
    for n in TAMANHOS_RAPIDO if rapido else TAMANHOS:
        yield Caso("ER", "sintetico", lambda n=n: erdos_renyi(n, GRAU_MEDIO / (n - 1), semente=SEMENTE))
        yield Caso("BA", "sintetico", lambda n=n: barabasi_albert(n, GRAU_MEDIO // 2, semente=SEMENTE))
        yield Caso("WS", "sintetico", lambda n=n: watts_strogatz(n, GRAU_MEDIO, 0.1, semente=SEMENTE))
    if com_bases:
        yield Caso("Karate", "base", carregar_karate)
        yield Caso("Thrones", "base", carregar_thrones)
        yield Caso("Twitch PT", "base", lambda: carregar_twitch_ptbr()[0])
        yield Caso("ego-Facebook", "base", carregar_facebook)


def deve_medir(algoritmo: str, n: int, max_n_exata: int = MAX_N_EXATA) -> bool:
    """A intermediação exata só é medida até max_n_exata nós. A amostrada só quando n > k:
    com k >= n ela sorteia todos os nós e vira a exata (é o caso do Karate)."""
    if algoritmo == "intermediacao_exata":
        return n <= max_n_exata
    if algoritmo == f"intermediacao_k{K_AMOSTRA}":
        return n > K_AMOSTRA
    return True


def origem_da_bfs(g: Grafo) -> No:
    """Nó de onde sai a BFS: sorteado com a SEMENTE, então é o mesmo nos dois scripts."""
    nos = list(g.nos())
    return nos[random.Random(SEMENTE).randrange(len(nos))]


def arestas_alcancadas(g: Grafo, alcancados) -> int:
    """Número de arestas da componente percorrida pela BFS (o que entra na conta do TEPS).

    No não direcionado, cada aresta aparece no grau das duas pontas, por isso a divisão por 2.
    No direcionado, a BFS só percorre as arestas de saída: conta o grau de saída.
    Tempo: O(tamanho da componente).
    """
    if g.direcionado:
        return sum(g.grau_saida(v) for v in alcancados)
    return sum(g.grau(v) for v in alcancados) // 2


def medir_tempo(funcao: Callable[[], object], repeticoes: int = REPETICOES) -> list[float]:
    """Executa funcao() `repeticoes` vezes e devolve o tempo de cada execução, em segundos.

    Como o timeit da biblioteca padrão, o coletor de lixo fica desligado durante a medição,
    para uma coleta no meio de uma execução não atrapalhar a comparação.
    """
    tempos = []
    for _ in range(repeticoes):
        gc.collect()
        gc.disable()
        try:
            inicio = time.perf_counter()
            funcao()
            tempos.append(time.perf_counter() - inicio)
        finally:
            gc.enable()
    return tempos


def medir_memoria(funcao: Callable[[], object]) -> float:
    """Pico de memória, em MiB, alocado por funcao() (o grafo de entrada já existia e não conta)."""
    gc.collect()
    tracemalloc.start()
    try:
        funcao()
        _, pico = tracemalloc.get_traced_memory()
    finally:
        tracemalloc.stop()
    return pico / 2**20


def linha_de_resultado(
    implementacao: str,
    algoritmo: str,
    caso: Caso,
    g: Grafo,
    tempos: list[float],
    memoria_mib: float,
    teps: float | None = None,
    diferenca_max: float | None = None,
) -> dict:
    """Monta uma linha do CSV no formato de COLUNAS."""
    n, m = g.numero_de_nos(), g.numero_de_arestas()
    return {
        "implementacao": implementacao,
        "algoritmo": algoritmo,
        "grafo": caso.nome,
        "tipo": caso.tipo,
        "n": n,
        "m": m,
        "n_mais_m": n + m,
        "repeticoes": len(tempos),
        "tempo_mediana_s": f"{statistics.median(tempos):.6g}",
        "tempo_min_s": f"{min(tempos):.6g}",
        "tempo_max_s": f"{max(tempos):.6g}",
        "memoria_pico_mib": f"{memoria_mib:.4g}",
        "teps": "" if teps is None else f"{teps:.4g}",
        "diferenca_max": "" if diferenca_max is None else f"{diferenca_max:.3g}",
    }


class EscritorCsv:
    """Grava as linhas no CSV assim que cada medição termina (se o script parar no meio,
    o que já foi medido não se perde)."""

    def __init__(self, caminho: Path) -> None:
        """Abre o CSV (cria a pasta, se preciso) e escreve o cabeçalho com as COLUNAS."""
        caminho.parent.mkdir(parents=True, exist_ok=True)
        self._arquivo = open(caminho, "w", newline="", encoding="utf-8")
        self._escritor = csv.DictWriter(self._arquivo, fieldnames=COLUNAS)
        self._escritor.writeheader()

    def escrever(self, linha: dict) -> None:
        """Grava uma linha e esvazia o buffer, para ela já ficar no disco."""
        self._escritor.writerow(linha)
        self._arquivo.flush()

    def fechar(self) -> None:
        """Fecha o arquivo."""
        self._arquivo.close()


def _processador() -> str:
    """Nome do processador: no Linux vem de /proc/cpuinfo; nos outros sistemas, do platform."""
    try:
        with open("/proc/cpuinfo", encoding="utf-8") as arquivo:
            for linha in arquivo:
                if linha.startswith("model name"):
                    return linha.split(":", 1)[1].strip()
    except OSError:
        pass
    return platform.processor() or "desconhecido"


def _memoria_gib() -> str:
    """Memória RAM total, quando o sistema informa (Linux e macOS)."""
    try:
        return f"{os.sysconf('SC_PAGE_SIZE') * os.sysconf('SC_PHYS_PAGES') / 2**30:.1f} GiB"
    except (AttributeError, ValueError, OSError):
        return "desconhecida"


def salvar_ambiente(caminho: Path = PASTA_RESULTADOS / "ambiente.txt") -> None:
    """Grava a máquina e as versões em que as medições rodaram (o relatório precisa disso)."""
    try:
        versao_networkx = importlib.metadata.version("networkx")
    except importlib.metadata.PackageNotFoundError:
        versao_networkx = "não instalado"
    linhas = [
        f"data: {datetime.date.today().isoformat()}",
        f"processador: {_processador()} ({os.cpu_count()} threads)",
        f"memoria: {_memoria_gib()}",
        f"sistema: {platform.platform()}",
        f"python: {platform.python_version()} ({platform.python_implementation()})",
        f"networkx: {versao_networkx}",
    ]
    caminho.parent.mkdir(parents=True, exist_ok=True)
    caminho.write_text("\n".join(linhas) + "\n", encoding="utf-8")


def mostrar(linha: dict) -> None:
    """Mostra uma medição no terminal, para acompanhar o progresso."""
    extra = f"  TEPS {linha['teps']}" if linha["teps"] else ""
    if linha["diferenca_max"]:
        extra += f"  dif. {linha['diferenca_max']}"
    print(
        f"{linha['implementacao']:>8}  {linha['algoritmo']:<22} {linha['grafo']:<12} "
        f"n={linha['n']:<7} m={linha['m']:<7} {float(linha['tempo_mediana_s']):9.4f} s  "
        f"{float(linha['memoria_pico_mib']):8.2f} MiB{extra}",
        flush=True,
    )
