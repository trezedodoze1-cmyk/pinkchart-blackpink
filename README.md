# PINKCHART · BLACKPINK + SOLOS (v2)

Site responsivo de fã para acompanhar **BLACKPINK, JENNIE, LISA, ROSÉ e JISOO** com visual preto e rosa.

## Navegação compacta

- Seletor de **Todos / BLACKPINK / JENNIE / LISA / ROSÉ / JISOO**, disponível no início da página.
- Seletor de **álbum, EP ou single**, que filtra músicas por lançamento sem uma lista enorme.
- Abas **Visão geral**, **Músicas** (7 por página), **Álbuns**, **Charts**, **Histórico** e **Fontes**.
- Quatro indicadores: streams totais, streams diários, ouvintes mensais e seguidores. Ao filtrar álbum, streams totais e diários passam a ser específicos do álbum *se a fonte fornecer esses totais*; ouvintes/seguidores continuam sendo do perfil do artista.
- Histórico por artista e charts diários/semanais por país. Exportação CSV do ranking visível.
- Layout compacto para celular sem exigir descer por grandes seções.

## Como visualizar

Abra `pinkchart-preview.html` ou `BLACKPINK_SOLOS_PINKCHART_PREVIA.html` no navegador: funciona **offline**, usando os snapshots e catálogos já incluídos. O `index.html` é a versão multi-arquivo pronta para hospedagem.

## Como ativar atualizações automáticas

1. Descompacte e envie **todos** os arquivos do projeto para um repositório GitHub público, no ramo `main`. Não envie apenas o HTML de prévia.
2. Em **Settings → Pages**, selecione **Source: GitHub Actions**.
3. Na aba **Actions** do repositório, autorize a execução. O workflow `.github/workflows/update-and-deploy.yml` publica o site e também é executado diariamente às 10:00 e domingo às 11:00 no horário de Cuiabá (UTC−4).
4. Para coletar **seguidores** via Spotify API, configure os secrets opcionais `SPOTIFY_CLIENT_ID` e `SPOTIFY_CLIENT_SECRET` em **Settings → Secrets and variables → Actions**. Sem essas credenciais, seguidores não serão coletados para as artistas solo e o antigo valor aproximado do grupo será preservado.
5. Você pode executar manualmente via **Actions → Atualizar charts e publicar site → Run workflow → all**.

Script: `python scripts/update_all.py --mode daily`, `--mode weekly`, ou `--mode all` (Python 3.12+; instale `pip install -r scripts/requirements.txt`).

## De onde vêm os dados?

- **Kworb**: streams acumulados e diários por perfil, faixas e álbuns (links diferentes para cada integrante); inclui participações quando registradas no perfil.
- **Spotify Top**: ouvintes mensais, quando publicados e identificados como pertencentes ao artista certo.
- **Spotify Charts** via páginas públicas Kworb: posições diárias e semanais nos países configurados; disponibilidade varia.
- **Spotify Web API**: seguidores por artista mediante autenticação opcional.

**Transparência importante:** o projeto começa com uma seleção de medições de outubro de 2026, de datas variadas (ver cada indicador). Os catálogos de álbuns incluem tracklists confirmadas; quando uma faixa ainda não tem contagem coletada, aparece `—`, nunca um número fictício. O script tenta atualizar dados públicos após configurar o agendamento, mas páginas de terceiros podem bloquear ou mudar os dados. Histórico não é preenchido retroativamente de modo simulado.

No filtro **Todos**, números de perfis não são somados, pois participações podem constar em mais de uma carreira. Totais de álbuns segundo Kworb também podem incluir versões, edições especiais ou contagens diferentes da soma das faixas exibidas. Para álbuns não encontrados nos dados Kworb, a contagem agregada fica `—` até que uma fonte confiável a forneça.

## Arquivos importantes

- `index.html` — site publicável.
- `assets/app.js` e `assets/styles.css` — navegação, filtros, design e gráficos.
- `data/artists.json` — dados atuais de cinco perfis.
- `data/catalog.json` — agrupamentos de faixa por álbum.
- `data/artist-history.json` — histórico por artista.
- `data/charts-history-all.json` — histórico conjunto de charts.
- `scripts/update_all.py` — atualização para cinco artistas.
- `data/latest.json`, `data/history.json` etc. — backups legados do BLACKPINK **mantidos** para preservar o progresso inicial da versão anterior.

Projeto de fã sem afiliação ao Spotify, YG Entertainment ou artistas/gravadoras.
