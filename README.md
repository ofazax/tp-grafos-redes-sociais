# TP Grafos: Análise de Redes Sociais

Ferramenta em Python puro que carrega uma rede social real, calcula grau, centralidades,
agrupamento e comunidades e mostra os resultados numa interface gráfica.
Bibliotecas de grafos (NetworkX etc.) só aparecem em `bench/`, para comparar desempenho.

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
app.py        entrada da interface (streamlit run app.py)
ui/           telas da interface
redes/        pacote do TP, sem NetworkX
  core/       classe Graph
  loaders/    leitura das bases
  generators/ grafos sintéticos
  metrics/    grau, caminhos, centralidades, clustering
  community/  modularidade, Louvain, Label Propagation
  applied/    problema aplicado
  viz/        layout do desenho da rede
bench/        benchmarks e comparação com o NetworkX
tests/        testes (pytest + Hypothesis)
data/         links das bases; data/raw/ fica fora do Git
docs/uml/     diagramas UML
```

## Fluxo de trabalho

Uma branch por tarefa, pull request para a `main` revisado por outro membro e
mensagens no padrão Conventional Commits (`feat:`, `fix:`, `test:`, `docs:`, `chore:`).
