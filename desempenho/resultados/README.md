Os CSVs com os resultados das medições de desempenho ficam nesta pasta.

## Como gerar

Da raiz do projeto, com as 4 bases em `dados/brutos/` (veja `dados/README.md`):

```bat
python -m desempenho.medir
python -m desempenho.comparar_networkx
python -m desempenho.graficos
```

Os dois primeiros levam cerca de 30 e 60 minutos. Com `--rapido`, só os grafos de 1.000 e
2.000 nós, para conferir se tudo roda (os resultados vão para `*_rapido.csv`).

## O que é medido

- Grafos: Erdős–Rényi, Barabási–Albert e Watts–Strogatz (p = 0,1) com 1.000 a 100.000 nós e
  grau médio 10, semente 42, mais as 4 bases (Karate, Network of Thrones, Twitch PT e ego-Facebook).
- Algoritmos: BFS, intermediação exata (só até 5.000 nós, porque custa O(nm)), intermediação
  amostrada com k = 100, PageRank e k-core.
- Tempo: mediana de 5 execuções com `time.perf_counter`, com o coletor de lixo desligado.
- Memória: pico de memória alocada pelo algoritmo, medido com `tracemalloc` numa execução à parte.
- TEPS (só na BFS): arestas da componente percorrida divididas pelo tempo.
- NetworkX 3.7: os mesmos grafos, copiados para `networkx.Graph`. A coluna `diferenca_max` é a
  maior diferença entre o resultado dele e o nosso, em todos os nós.

## Arquivos

| Arquivo | Conteúdo |
| --- | --- |
| `ambiente.txt` | processador, memória, sistema e versões do Python e do NetworkX da medição |
| `medicoes_redes.csv` | tempo, memória e TEPS do nosso código |
| `medicoes_networkx.csv` | o mesmo para o NetworkX, mais `diferenca_max` |
| `inclinacoes.csv` | expoente b de tempo ~ (n + m)^b nos grafos sintéticos |
| `figuras/tempo_loglog` | tempo × (n + m) em log-log, um painel por algoritmo |
| `figuras/memoria_loglog` | pico de memória × (n + m) em log-log |
| `figuras/razao_networkx` | tempo do NetworkX ÷ tempo do nosso, nas bases |
| `figuras/teps_bfs` | TEPS da BFS nos grafos sintéticos |

Cada figura sai em PNG (slides) e em PDF (relatório).
