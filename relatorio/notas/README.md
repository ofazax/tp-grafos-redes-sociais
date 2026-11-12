# Notas de desenvolvimento (base para o relatório)

Cada um registra aqui, em LaTeX, o que implementou, por quê, a complexidade e os resultados dos testes.
No fim, o texto vai quase direto para o relatório SBC no Overleaf.

## Regras

1. **Edite só o seu arquivo** em `secoes/` (`brunno.tex`, `vitoria.tex`, `iago.tex`, `arthur.tex`, `ravi.tex`, `kaio.tex`).
   Assim ninguém mexe no mesmo arquivo e o Git não dá conflito.
2. **Atualize no mesmo PR do código.** Implementou uma função: troque `\afazer` por `\feito` na tabela,
   preencha o valor obtido nos testes e adicione uma linha no Registro. Commit sugerido:
   `docs: atualiza notas da frente N`.
3. Referência nova entra em `referencias.bib` (o Ravi organiza). Figuras vão em `figuras/`.
4. Escreva em frases completas, como no relatório.

## Comandos disponíveis

| Comando | Para quê |
|---|---|
| `\codigo{bfs}` | nomes de funções e arquivos (use `\_` no lugar de `_`) |
| `\feito`, `\andamento`, `\afazer` | situação na tabela |
| `\pendente{texto}` | lembrete em vermelho no PDF |
| `\registro{2026-11-12}{o que foi feito (PR #N)}` | entrada no registro |

## Compilar

- **Overleaf:** crie um projeto, faça upload da pasta `relatorio/notas/` e compile `notas.tex`.
- **Local (se tiver LaTeX):** `pdflatex notas && bibtex notas && pdflatex notas && pdflatex notas`.

O PDF gerado não vai para o Git.
