# Documento da Etapa 1 (Modelagem e Planejamento)

Entregável da Etapa 1: descrição do problema, levantamento de dados, justificativa da modelagem,
diagramas UML e plano de desenvolvimento. Usa o template oficial da SBC (`sbc-template.sty` e `sbc.bst`).

## Quem escreve cada seção

| Arquivo em `secoes/` | Seção | Responsável | Situação |
|---|---|---|---|
| `problema.tex` | Problema aplicado | Ravi | a escrever |
| `bases.tex` | Bases de dados | Brunno | pronta |
| `modelagem.tex` | Modelagem do grafo e diagrama de classes | Brunno | pronta |
| `casos_de_uso.tex` | Casos de uso e telas | Kaio | casos de uso montados a partir do PR #5; falta o esboço das telas |
| `sequencia.tex` | Diagrama de sequência | Iago | a fazer |
| `atividades.tex` | Diagrama de atividades do Louvain | Arthur | a fazer |
| `plano.tex` | Plano de desenvolvimento | Vitória | tabela de marcos pronta; falta o texto |
| `responsabilidades.tex` | Responsabilidades | Brunno | pronta |

Regras:
1. Cada um edita **só o próprio arquivo**, numa branch própria, e abre um PR.
2. Figuras vão em `figuras/`; o código-fonte dos diagramas (PlantUML) vai em `documentos/uml/`.
3. Referências entram em `referencias.bib` (cópia da lista do grupo em `relatorio/notas/referencias.bib`).
4. Os trechos `\pendente{...}` aparecem em vermelho no PDF. Antes de entregar, não pode sobrar nenhum.

## Compilar

- **Local (MiKTeX ou TeX Live):** `pdflatex etapa1 && bibtex etapa1 && pdflatex etapa1 && pdflatex etapa1`.
  No VS Code (LaTeX Workshop), use a receita *pdflatex ➞ bibtex ➞ pdflatex × 2*.
- **Overleaf:** faça upload da pasta `relatorio/etapa1/` e compile `etapa1.tex`.

O PDF não vai para o Git; ele é entregue no Canvas.
