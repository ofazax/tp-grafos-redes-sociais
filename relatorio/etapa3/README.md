# Relatório final (Etapa 3)

Entregável da Etapa 3: relatório técnico no template oficial da SBC (`sbc-template.sty` e `sbc.bst`),
com **12 a 15 páginas**. O enunciado pede: contextualização, modelagem, resultados, avaliação de
desempenho, conclusões, todos os artefatos (diagramas, resultados e telas) e o que cada integrante fez.

## Quem escreve cada seção

Os tamanhos somam cerca de 14 páginas. Se o PDF passar de 15, cada um corta da própria seção.

| Arquivo em `secoes/` | Seção | Responsável | Tamanho | Situação |
|---|---|---|---|---|
| (`etapa3.tex`) | Título, abstract e resumo | Brunno; Ravi completa a frase do resultado | 3/4 de página | pronto, falta o resultado |
| `introducao.tex` | 1. Introdução | Brunno | 3/4 de página | pronta |
| `trabalhos.tex` | 2. Trabalhos relacionados | Vitória | 1/2 página | a escrever |
| `problema.tex` | 3. Problema aplicado | Ravi | 3/4 de página | a escrever (resumir o da Etapa 1) |
| `bases.tex` | 4. Bases de dados e grafos sintéticos | Brunno | 1 página | pronta |
| `modelagem.tex` | 5. Modelagem do grafo e diagramas UML | Brunno | 1 página e meia | pronta |
| `caminhos.tex` | 6. Grau, caminhos e proximidade | Vitória | 3/4 de página | a escrever |
| `centralidades.tex` | 7. Centralidades | Iago | 1 página e meia | pronta (PR #23); dá para enxugar um pouco |
| `comunidades.tex` | 8. Agrupamento e comunidades | Arthur | 1 página | a escrever |
| `influenciadores.tex` | 9. Influenciadores na Twitch PT | Ravi | 1 página | a escrever |
| `interface.tex` | 10. Interface | Kaio | 1 página | a escrever |
| `desempenho.tex` | 11. Avaliação de desempenho | Iago | 1 página e meia | pronta (PR #23); dá para diminuir a figura |
| `limitacoes.tex` | 12. Limitações e ética | Arthur | 1/3 de página | a escrever |
| `conclusao.tex` | 13. Conclusão | Kaio | 1/3 de página | a escrever |
| `responsabilidades.tex` | 14. Responsabilidades | Brunno | 1/2 página | pronta; conferir no fim |

Cada arquivo a escrever já tem o título, o rótulo (`\label`) e um `\pendente{...}` em vermelho que
diz o que vai nele. As outras seções já apontam para esses rótulos (`\ref{sec:comunidades}` etc.),
então **não mude o `\section` nem o `\label`**: só troque o `\pendente` pelo texto.

## Regras

1. Cada um edita **só os próprios arquivos**, numa branch própria, e abre um PR. Assim ninguém
   tem conflito com ninguém.
2. Figuras vão em `figuras/`. Já estão lá os diagramas da Etapa 1 (`casos_de_uso.jpg`, `sequencia.png`) e os
   diagramas de classes e de pacotes em PDF (vetorial). O diagrama de atividades do Louvain entra
   com o PR #15; copie `relatorio/etapa1/figuras/atividades_louvain.png` para cá quando ele entrar.
   Prints da interface: PNG, com nome claro (`tela_comunidades.png`).
3. Referências: acrescente em `referencias.bib` **desta pasta**. Antes, procure a chave no arquivo
   (`Ctrl+F`): chave repetida dá erro no BibTeX.
4. Use `\codigo{...}` para nomes de função e de arquivo, e os números com vírgula decimal (`0{,}42`
   em fórmula, `0,42` no texto).
5. Os trechos `\pendente{...}` aparecem em vermelho no PDF. Na versão entregue, não pode sobrar nenhum.

## Compilar

- **Local (MiKTeX ou TeX Live):** `pdflatex etapa3 && bibtex etapa3 && pdflatex etapa3 && pdflatex etapa3`.
  No VS Code (LaTeX Workshop), use a receita *pdflatex ➞ bibtex ➞ pdflatex × 2*.
- **Overleaf:** faça upload da pasta `relatorio/etapa3/` e compile `etapa3.tex`.

O PDF não vai para o Git; ele vai no .zip da entrega.

## Antes de entregar (revisão final)

- [ ] Nenhum `\pendente` no PDF.
- [ ] Entre 12 e 15 páginas.
- [ ] Nomes completos de todos, curso, disciplina e instituição no cabeçalho.
- [ ] Resumo e abstract com o resultado principal.
- [ ] Tabela de responsabilidades conferida com o que cada um fez.
