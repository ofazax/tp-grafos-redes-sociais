# TP Grafos: Análise de Redes Sociais

Ferramenta em Python puro que carrega uma rede social real, calcula grau, centralidades,
agrupamento e comunidades e mostra os resultados numa interface gráfica.
Bibliotecas de grafos (NetworkX etc.) só aparecem em `desempenho/`, para comparar desempenho.

## Como rodar (Windows, Prompt de Comando)

```bat
py -3.13 -m venv .venv
.venv\Scripts\activate.bat
python -m pip install --upgrade pip
pip install -r requirements.txt -r requirements-dev.txt
pytest
streamlit run app.py
```

No PowerShell, ative com `.venv\Scripts\Activate.ps1`; no Linux ou macOS, com `source .venv/bin/activate`.

## Estrutura

```text
app.py          entrada da interface (streamlit run app.py)
interface/      telas da interface
redes/          pacote do TP, sem NetworkX
  nucleo/       classe Grafo
  leitores/     leitura das bases
  geradores/    grafos sintéticos
  metricas/     grau, caminhos, centralidades, agrupamento
  comunidades/  modularidade, Louvain, propagação de rótulos
  aplicacao/    problema aplicado (influenciadores)
  visualizacao/ posicionamento dos nós no desenho da rede
desempenho/     medições e comparação com o NetworkX
tests/          testes (pytest + Hypothesis)
dados/          links das bases; dados/brutos/ fica fora do Git
documentos/uml/ diagramas UML
```

O código usa nomes em português (`Grafo`, `adicionar_aresta`, `grau`...). Siglas e nomes
próprios de algoritmos ficam como são conhecidos: `bfs`, `dijkstra`, `pagerank`, `louvain`.

## Fluxo de trabalho

Uma branch por tarefa, pull request para a `main` revisado por outro membro e
mensagens no padrão Conventional Commits (`feat:`, `fix:`, `test:`, `docs:`, `chore:`).
