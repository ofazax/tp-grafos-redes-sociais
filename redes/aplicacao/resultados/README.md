Os resultados do problema aplicado (Frente 5) ficam nesta pasta.

## Como gerar

Da raiz do projeto, com a Twitch PT em `dados/brutos/twitch/PTBR/` (veja `dados/README.md`):

```bat
python -m redes.aplicacao.experimento
```

Leva cerca de 45 segundos: 15 no SIR e 30 nas centralidades (a intermediação exata é a mais lenta).
Com `--rodadas 10`, o SIR fica mais rápido, para conferir se tudo funciona. As opções `--beta`,
`--semente` e `--pasta` mudam o beta, a semente e a pasta onde os CSVs são gravados.

## O que é calculado

- Rede: Twitch PT, 1.912 streamers e 31.299 amizades.
- Limiar epidêmico: beta_c = <k> / (<k²> - <k>) = 0,0079.
- SIR em tempo discreto a partir de cada streamer, com beta = 0,012 (cerca de 1,5 beta_c), gamma = 1
  (cada infectado tenta transmitir uma única vez) e 100 rodadas por nó, semente 2026.
- Alcance rho(v): fração da rede atingida, na média das 100 rodadas.
- As 6 centralidades: grau, proximidade, harmônica, intermediação (exata), PageRank e número de núcleo.
- Tau-b de Kendall do ranking de cada centralidade contra o alcance (pergunta P1) e contra as
  visualizações reais (pergunta P2). O tau-b só olha a ordem e desconta os empates.

## Resultado (beta = 0,012, 100 rodadas, semente 2026)

| Centralidade | tau-b × alcance | tau-b × visualizações |
| --- | --- | --- |
| grau | 0,7033 | 0,4326 |
| proximidade | 0,7344 | 0,2889 |
| harmônica | **0,7435** | 0,3031 |
| intermediação | 0,5341 | 0,4133 |
| PageRank | 0,6592 | **0,4386** |
| número de núcleo | 0,7301 | 0,4034 |

- P1: a harmônica prevê melhor o alcance. Com as sementes 1, 2 e 3, a ordem das 6 centralidades
  se repete. Com beta = 0,016 (2 × beta_c), o número de núcleo passa à frente.
- P2: o PageRank prevê melhor as visualizações, quase empatado com o grau.
- H1 (núcleo supera o grau na P1): confirmada em todas as sementes e nos três valores de beta testados.
- H2 (0 < tau com as visualizações < tau com o alcance, para todas): confirmada.
- O próprio alcance concorda com as visualizações com tau = 0,3376.

## Arquivos

| Arquivo | Conteúdo |
| --- | --- |
| `alcance_twitch.csv` | uma linha por streamer, do maior para o menor alcance |
| `concordancia_twitch.csv` | uma linha por centralidade: tau-b contra o alcance e contra as visualizações |

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
