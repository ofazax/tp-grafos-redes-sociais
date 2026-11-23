# Relatório final (Etapa 3)

Entregável da Etapa 3: relatório técnico no template oficial da SBC (`sbc-template.sty` e `sbc.bst`),
com **12 a 15 páginas**. O enunciado pede: contextualização, modelagem, resultados, avaliação de
desempenho, conclusões, todos os artefatos (diagramas, resultados e telas) e o que cada integrante fez.

## Quem escreve cada seção

O relatório está completo: 15 páginas, contando as referências, e nenhum `\pendente` sobrando.
As seções de comunidades, interface, limitações e conclusão foram escritas na revisão final pelo
Brunno, a partir das notas e do código do Arthur e do Kaio (isso está dito na Seção 14).

| Arquivo em `secoes/` | Seção | Código de | Situação |
|---|---|---|---|
| (`etapa3.tex`) | Título, abstract e resumo | todos | pronto |
| `introducao.tex` | 1. Introdução | Brunno | pronta |
| `trabalhos.tex` | 2. Trabalhos relacionados | Vitória | pronta |
| `problema.tex` | 3. Problema aplicado | Ravi | pronta |
| `bases.tex` | 4. Bases de dados e grafos sintéticos | Brunno | pronta |
| `modelagem.tex` | 5. Modelagem do grafo e diagramas UML | Brunno | pronta |
| `caminhos.tex` | 6. Grau, caminhos e proximidade | Vitória | pronta |
| `centralidades.tex` | 7. Centralidades | Iago | pronta |
| `comunidades.tex` | 8. Agrupamento e comunidades | Arthur | pronta (texto do Brunno) |
| `influenciadores.tex` | 9. Influenciadores na Twitch PT | Ravi | pronta |
| `interface.tex` | 10. Interface | Kaio | pronta (texto do Brunno) |
| `desempenho.tex` | 11. Avaliação de desempenho | Iago | pronta |
| `limitacoes.tex` | 12. Limitações e ética | Arthur | pronta (texto do Brunno) |
| `conclusao.tex` | 13. Conclusão | Kaio | pronta (texto do Brunno) |
| `responsabilidades.tex` | 14. Responsabilidades | Brunno | pronta |

Se alguém mudar uma seção, compile de novo e confira se o PDF continua com no máximo 15 páginas.

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

O PDF compilado (`etapa3.pdf`) não vai para o Git. A versão entregue fica em
`relatorio/Relatorio-Tecnico-Analise-de-Redes-Sociais-Com-Grafos.pdf`.

## Antes de entregar (revisão final)

- [x] Nenhum `\pendente` no PDF.
- [x] Entre 12 e 15 páginas.
- [x] Nomes completos de todos, curso, disciplina e instituição no cabeçalho.
- [x] Resumo e abstract com o resultado principal.
- [x] Tabela de responsabilidades conferida com o que cada um fez.
