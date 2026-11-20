Os resultados do problema aplicado (Frente 5) ficam nesta pasta.

## Como gerar

Da raiz do projeto, com a Twitch PT em `dados/brutos/twitch/PTBR/` (veja `dados/README.md`):

```bat
python -m redes.aplicacao.experimento
```

Leva cerca de 20 segundos. Com `--rodadas 10`, roda em 2 segundos, para conferir se tudo funciona.
As opções `--beta`, `--semente` e `--saida` mudam o beta, a semente e o arquivo de saída.

## O que é calculado

- Rede: Twitch PT, 1.912 streamers e 31.299 amizades.
- Limiar epidêmico: beta_c = <k> / (<k²> - <k>) = 0,0079.
- SIR em tempo discreto a partir de cada streamer, com beta = 0,012 (cerca de 1,5 beta_c), gamma = 1
  (cada infectado tenta transmitir uma única vez) e 100 rodadas por nó, semente 2026.
- Alcance rho(v): fração da rede atingida, na média das 100 rodadas.

## Arquivos

| Arquivo | Conteúdo |
| --- | --- |
| `alcance_twitch.csv` | uma linha por streamer, do maior para o menor alcance |

Colunas do `alcance_twitch.csv`:

| Coluna | Significado |
| --- | --- |
| `posicao` | posição no ranking de alcance (1 = maior); empates desfeitos pelo grau e depois pelo nó |
| `no` | identificador do streamer na base (`new_id`) |
| `alcance` | rho(v), fração da rede atingida (entre 1/n e 1) |
| `atingidos_medios` | rho(v) × n, quantos streamers são atingidos por rodada, em média |
| `grau` | número de amizades |
| `nucleo` | número de núcleo (k-core) |
| `visualizacoes` | visualizações reais do canal |
| `parceiro` | se o canal é parceiro da Twitch |
