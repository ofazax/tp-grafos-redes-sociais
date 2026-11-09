# Bases de dados

Baixe os arquivos das fontes oficiais e salve em `dados/brutos/` (essa pasta fica fora do Git).
O Karate Club já vem no repositório, em `tests/dados/`. Depois de carregar, confira se os
tamanhos batem com a tabela: são os mesmos valores dos testes dos leitores.

| Base | Uso no TP | Nós | Arestas | Onde salvar |
| --- | --- | --- | --- | --- |
| [Karate Club](https://networkrepository.com/karate.php) | Testes de corretude | 34 | 78 | já está em `tests/dados/` |
| [Twitch PT (SNAP)](https://snap.stanford.edu/data/twitch-social-networks.html) | Base principal: influenciadores | 1.912 | 31.299 | `dados/brutos/twitch/PTBR/` (do twitch.zip) |
| [ego-Facebook (SNAP)](https://snap.stanford.edu/data/ego-Facebook.html) | Segunda base, maior | 4.039 | 88.234 | `dados/brutos/facebook_combined.txt.gz` |
| [Network of Thrones](https://github.com/mathbeveridge/asoiaf) | Demonstração (livro 3) | 303 | 1.008 (ponderado) | `dados/brutos/asoiaf-book3-edges.csv` |

Cite o SNAP como: Leskovec, J.; Krevl, A. *SNAP Datasets: Stanford Large Network Dataset Collection*, 2014.
