// Sincronização do DOM com o estado retornado pelo backend (uma função por página/seção).

const SIR_CHART = { width: 532, height: 132, padX: 12, padY: 16 };

function buildSvgCurvePath(values, width, height, padX, padY, escalaFixa) {
  if (!values || values.length === 0) return '';
  const usableW = width - padX * 2;
  const usableH = height - padY * 2;
  const maxVal = Math.max(...values, 0.01);
  // escalaFixa: o valor que fica no topo do gráfico; curvas com a mesma escala podem ser comparadas.
  const scaleMax = escalaFixa || (maxVal > 0.35 ? 1.0 : Math.min(1.0, maxVal * 1.35));

  return values.map((v, idx) => {
    const x = padX + (idx / Math.max(1, values.length - 1)) * usableW;
    const norm = Math.min(1.0, Math.max(0.0, v / scaleMax));
    const y = padY + (1.0 - norm) * usableH;
    return `${idx === 0 ? 'M' : 'L'} ${x.toFixed(1)} ${y.toFixed(1)}`;
  }).join(' ');
}

function setInnerHtmlIfPresent(elementId, html) {
  const el = document.getElementById(elementId);
  if (el) el.innerHTML = html;
}

function applyBackendStateToDOM() {
  renderHeader();
  renderObterGrafoPage();
  renderVisualizarRedePage();
  renderMetricasPage();
  renderComunidadesPage();
  renderInfluenciadoresPage();
  renderResultadosPage();
  MAP_KEYS.forEach(drawMap);
}

// ---------------------------------------------------------------------------
// Header
// ---------------------------------------------------------------------------
function renderHeader() {
  const s = BACKEND_STATE.sessao;
  const cat = BACKEND_STATE.catalogo_bases;
  const isHomologatedBase = BASE_KEYS.includes(s.chave_base) && !s.arquivo_importado_nome;

  const headerSel = document.getElementById('headerDatasetSelect');
  if (headerSel) {
    let optsHtml = BASE_KEYS.map(k => {
      const b = cat[k];
      return `<option value="${k}">${b.nome} (${b.resumo_curto})</option>`;
    }).join('');
    if (!isHomologatedBase) {
      optsHtml = `<option value="custom" selected>${s.nome_grafo} (${s.vertices_str} nós • ${s.arestas_str} arestas)</option>` + optsHtml;
    }
    headerSel.innerHTML = optsHtml;
    if (isHomologatedBase) {
      headerSel.value = s.chave_base;
    }
  }
  setText('headerGraphBadge', s.badge_header);
}

// ---------------------------------------------------------------------------
// Página 1: Obter Grafo
// ---------------------------------------------------------------------------
function renderDatasetCard(key, base) {
  const isSel = sessionState.selectedDatasetKey === key;
  const cardCls = isSel
    ? 'ds-card text-left p-3 rounded-[10px] border-2 border-deepnavy bg-sagesoft transition-all cursor-pointer'
    : 'ds-card text-left p-3 rounded-[10px] border border-mutedgreen bg-offwhite hover:bg-sagelight transition-all cursor-pointer';
  const tagCls = isSel
    ? 'text-[9px] font-mono font-semibold px-1.5 py-0.5 rounded bg-deepnavy text-offwhite'
    : 'text-[9px] font-mono font-semibold px-1.5 py-0.5 rounded bg-sage text-deepnavy';
  return `
    <button type="button" onclick="selectRealDatasetCard('${key}')" class="${cardCls}">
      <div class="flex items-center justify-between">
        <strong class="text-xs font-bold text-deepnavy">${base.nome}</strong>
        <span class="${tagCls}">${base.tag}</span>
      </div>
      <p class="text-[10.5px] font-mono text-petrol mt-1">${base.resumo_curto}</p>
    </button>
  `;
}

function renderObterGrafoPage() {
  const s = BACKEND_STATE.sessao;
  const cat = BACKEND_STATE.catalogo_bases;

  setInnerHtmlIfPresent('realDatasetCardsGrid', BASE_KEYS.map(k => renderDatasetCard(k, cat[k])).join(''));

  const hasImportedFile = Boolean(s.arquivo_importado_nome);
  document.getElementById('fileUploadEmptyState').classList.toggle('hidden', hasImportedFile);
  document.getElementById('fileUploadLoadedState').classList.toggle('hidden', !hasImportedFile);
  if (hasImportedFile) {
    setText('uploadedFileNameDisplay', s.arquivo_importado_nome);
    setText('uploadedFileMetaDisplay', s.arquivo_importado_meta || '');
  }

  setText('realPathHint', s.origem);
  setText('statName', s.nome_grafo);
  setText('statV', s.vertices_str);
  setText('statE', s.arestas_str);
  setText('statLoops', s.lacos_str);
  setText('statType', s.config_curta);
  setText('statGT', s.comunidades_reais);
}

// ---------------------------------------------------------------------------
// Página 2: Visualizar Rede e Caminho Calculado
// ---------------------------------------------------------------------------
function renderVisualizarRedePage() {
  const vis = BACKEND_STATE.visualizacao;

  const srcIn = document.getElementById('pathSource');
  const dstIn = document.getElementById('pathTarget');
  if (srcIn && !srcIn.dataset.edited) srcIn.value = vis.origem_padrao;
  if (dstIn && !dstIn.dataset.edited) dstIn.value = vis.destino_padrao;

  updatePathDisplayFromState();

  if (vis.nos.length > 0) {
    const stillExists = sessionState.nodeIndexById[String(sessionState.selectedNodeId)] !== undefined;
    if (!stillExists) {
      sessionState.selectedNodeId = vis.nos[0].id;
    }
    selectInspectorNode(sessionState.selectedNodeId, false);
  }
}

function isPathVisible(caminho) {
  return !sessionState.pathClearedManually
    && caminho && caminho.encontrado
    && caminho.rota && caminho.rota.length > 0;
}

function renderPathStepBadge(rotulo, idx, caminho) {
  const isFirst = idx === 0;
  const isLast = idx === caminho.rota_rotulos.length - 1;
  const safeId = escapeJsString(caminho.rota[idx]);
  const badgeClass = (isFirst || isLast)
    ? 'px-2 py-1 rounded bg-[#22C55E] text-deepnavy font-mono text-[10px] font-bold cursor-pointer hover:opacity-90'
    : 'px-2 py-1 rounded bg-petrol font-mono text-[10px] border border-sage/60 cursor-pointer hover:bg-mutedgreen';
  const label = isFirst ? `Origem ${rotulo}` : (isLast ? `Destino ${rotulo}` : `Nó ${rotulo}`);
  const arrow = !isLast ? '<span class="text-sage text-xs font-mono">→</span>' : '';
  return `<span onclick="searchAndFlyToNode('network', '${safeId}')" class="${badgeClass}" title="Focar nó no mapa">${label}</span>${arrow}`;
}

function updatePathDisplayFromState() {
  const caminho = BACKEND_STATE.visualizacao.caminho;
  const pill = document.getElementById('pathStatusPill');
  const header = document.getElementById('pathResultHeader');
  const stepsEl = document.getElementById('pathStepsVisual');
  const overlayBadge = document.getElementById('canvasPathOverlayBadge');

  if (!isPathVisible(caminho)) {
    const titulo = caminho && caminho.erro_titulo ? caminho.erro_titulo : 'Nenhum caminho destacado no momento';
    const mensagem = caminho && caminho.erro_mensagem
      ? caminho.erro_mensagem
      : 'Informe os nós de origem e destino acima e clique em "Calcular e Destacar no Grafo".';
    pill.className = 'px-2.5 py-0.5 rounded bg-petrol text-sage font-mono text-[10px] font-semibold';
    pill.innerText = 'Inativo';
    header.innerText = titulo;
    stepsEl.innerHTML = `<span class="text-[10.5px] text-offwhite">${mensagem}</span>`;
    overlayBadge.classList.add('hidden');
    return;
  }

  pill.className = 'px-2.5 py-0.5 rounded bg-[#22C55E] text-deepnavy text-[10px] font-bold';
  pill.innerText = 'Visível no Grafo';
  header.innerText = caminho.resumo_header;
  stepsEl.innerHTML = caminho.rota_rotulos.map((rot, idx) => renderPathStepBadge(rot, idx, caminho)).join('');

  overlayBadge.classList.remove('hidden');
  setText('canvasPathOverlayText', `☍ Caminho (${caminho.algoritmo}): ` + caminho.rota_rotulos.join(' → '));
}

function selectInspectorNode(nodeId, redraw = true) {
  const idx = sessionState.nodeIndexById[String(nodeId)];
  const nodes = getVisualNodes();
  const clicked = idx !== undefined ? nodes[idx] : nodes[0];
  if (!clicked) return;
  sessionState.selectedNodeId = clicked.id;
  setText('inspNodeId', clicked.rotulo);
  setText('inspLabel', clicked.subtitulo);
  setText('inspDegree', clicked.degree + ' conexões');
  setText('inspPR', clicked.pagerank);
  setText('inspBet', clicked.betweenness);
  setText('inspKcore', 'k = ' + clicked.kcore);
  if (redraw) drawMap('network');
}

// ---------------------------------------------------------------------------
// Página 3: Métricas da Rede
// ---------------------------------------------------------------------------
function renderMetricasPage() {
  const met = BACKEND_STATE.metricas;

  setText('metricAvgDeg', met.grau_medio_str);
  setText('metricDensity', met.densidade_str);
  setText('metricDistDiam', met.dist_diam_str);
  setText('metricGiantComp', met.maior_comp_str);
  setText('metricAvgClust', met.clustering_medio_str);
  setText('metricTransitivity', met.transitividade_str);
  setText('metricTotalTriangles', met.total_triangulos_str);

  setInnerHtmlIfPresent('degreeHistogramContainer', met.histograma_grau.map(b => `
    <div style="height:${b.altura_barra}%;background-color:${b.cor};" class="flex-1 rounded-t-md relative transition-all duration-300">
      <span class="absolute -top-5 left-1/2 -translate-x-1/2 text-[9.5px] font-mono font-semibold text-deepnavy whitespace-nowrap">${b.rotulo}</span>
    </div>
  `).join(''));

  setInnerHtmlIfPresent('centralityTableBody', met.tabela_centralidades.map(r => `
    <tr class="hover:bg-sagelight">
      <td class="p-2.5 font-bold text-deepnavy">${r.vertice}</td>
      <td class="p-2.5 font-medium text-deepnavy">${r.closeness}</td>
      <td class="p-2.5 font-medium text-deepnavy">${r.harmonica}</td>
      <td class="p-2.5 font-medium text-deepnavy">${r.betweenness}</td>
      <td class="p-2.5 font-medium text-deepnavy">${r.pagerank}</td>
      <td class="p-2.5 font-medium text-deepnavy">${r.kcore}</td>
    </tr>
  `).join(''));
}

// ---------------------------------------------------------------------------
// Página 4: Comunidades
// ---------------------------------------------------------------------------
function renderComunidadesPage() {
  const com = BACKEND_STATE.comunidades;

  setText('modularityScore', com.modularidade_str);
  setText('modularitySubtext', com.subtitulo_q);
  setText('commCount', com.total_clusters_str);
  setText('nmiScoreVal', com.nmi_str);
  document.getElementById('nmiBar').style.width = com.nmi_pct + '%';
  setText('ariScoreVal', com.ari_str);
  document.getElementById('ariBar').style.width = com.ari_pct + '%';
  setText('gtComparisonLabel', com.rotulo_comparacao);
  // Só o Karate Club tem gabarito; nas outras bases, a comparação é entre o Louvain e o LPA.
  const temGabarito = String(com.rotulo_comparacao || '').startsWith('Gabarito');
  const alvoComparacao = temGabarito ? 'Partição real' : 'Louvain × LPA';
  setText('nmiHeader', `${alvoComparacao} (NMI)`);
  setText('ariHeader', `${alvoComparacao} (ARI)`);
  setText('btnShowAllCommunities', `Mostrar Todas as Comunidades (${com.total_clusters})`);

  renderCommunityListUI();
}

function renderCommunityListUI() {
  const lista = BACKEND_STATE.comunidades.lista || [];
  setInnerHtmlIfPresent('communityLegendList', lista.map(c => {
    const isSel = sessionState.selectedCommunityFilter === c.indice;
    const borderCls = isSel ? 'border-2 border-deepnavy' : 'border border-sage';
    return `
      <div onclick="filterCommunityOnGraph(${c.indice})" class="p-2.5 rounded-[10px] ${borderCls} bg-sagelight hover:border-deepnavy flex items-center justify-between cursor-pointer transition-all">
        <div class="flex items-center gap-2.5">
          <span style="background-color:${c.cor};" class="w-3.5 h-3.5 rounded-full border border-deepnavy shrink-0"></span>
          <div>
            <strong class="text-[11.5px] font-bold text-deepnavy block leading-tight">${c.nome}</strong>
            <span class="text-[10px] font-mono text-petrol">${c.meta}</span>
          </div>
        </div>
        <span class="px-2 py-0.5 rounded bg-deepnavy text-offwhite font-mono text-[10px] font-semibold">${c.qtd_nos} nós</span>
      </div>
    `;
  }).join(''));
}

// ---------------------------------------------------------------------------
// Página 5: Influenciadores & SIR
// ---------------------------------------------------------------------------
function renderInfluenciadoresPage() {
  const sir = BACKEND_STATE.sir;

  const sementeNoTop = sir.top_influenciadores.some(inf => inf.id === sir.no_semente);
  const opcaoSemente = sementeNoTop || !sir.no_semente ? '' : `
    <option value="${sir.no_semente}" selected>
      ${sir.no_semente_rotulo} (escolhido • Alcance: ${sir.alcance_str})
    </option>`;
  setInnerHtmlIfPresent('sirSeedNodeSelect', opcaoSemente + sir.top_influenciadores.map((inf, idx) => `
    <option value="${inf.id}" ${inf.id === sir.no_semente ? 'selected' : ''}>
      ${inf.rotulo_curto} (Top #${idx + 1} • Alcance: ${inf.alcance})
    </option>
  `).join(''));

  // Os controles mostram os parâmetros usados pelo backend (o beta muda com a rede ativa).
  const betaInput = document.getElementById('sirBeta');
  if (betaInput) betaInput.value = sir.beta;
  setText('sirBetaVal', Number(sir.beta).toFixed(3));
  const gammaInput = document.getElementById('sirGamma');
  if (gammaInput) gammaInput.value = sir.gamma;
  setText('sirGammaVal', Number(sir.gamma).toFixed(2));
  const runsInput = document.getElementById('sirRunsInput');
  if (runsInput) runsInput.value = sir.simulacoes;
  const seedInput = document.getElementById('sirSeedInput');
  if (seedInput) seedInput.value = sir.semente;
  setText('sirLimiarInfo', `${sir.limiar_str} • recomendado: β ≈ 1,5 × β_c`);

  setText('sirStatInfected', sir.infectados_str);
  setText('sirStatRecovered', sir.recuperados_str);
  setText('sirStatSusceptible', sir.suscetiveis_str);
  setText('sirGraphHeaderBadge', `Semente Ativa: ${sir.no_semente_rotulo} (Alcance: ${sir.alcance_str})`);
  setText('sirChartTitle', `Curvas Epidemiológicas S(t), I(t), R(t) — Semente ${sir.no_semente_rotulo}`);
  setText('sirPearsonFooter', sir.correlacao_str);
  setText('sirReachFooter', `Alcance: ${sir.alcance_str}`);

  const { width, height, padX, padY } = SIR_CHART;
  const escalaIR = Math.min(1.0, Math.max(...sir.curva_i, ...sir.curva_r, 0.001) * 1.15);
  const pct = x => `${(x * 100).toFixed(1).replace('.', ',')}%`;
  document.getElementById('sirSusceptibleCurve').setAttribute('d', buildSvgCurvePath(sir.curva_s, width, height, padX, padY, 1.0));
  document.getElementById('sirInfectedCurve').setAttribute('d', buildSvgCurvePath(sir.curva_i, width, height, padX, padY, escalaIR));
  document.getElementById('sirRecoveredCurve').setAttribute('d', buildSvgCurvePath(sir.curva_r, width, height, padX, padY, escalaIR));
  setText('sirChartSubtitle',
    `Média das ${sir.simulacoes} simulações por passo t • S(t) de 0 a 100%; I(t) e R(t) de 0 a ${pct(escalaIR)} da rede • `
    + `pico de I: ${pct(Math.max(...sir.curva_i))} • R final: ${pct(sir.curva_r[sir.curva_r.length - 1])}`);

  renderTopInfluencersTableUI();
}

function renderTopInfluencersTableUI() {
  const topList = BACKEND_STATE.sir.top_influenciadores || [];
  const activeSeed = String(BACKEND_STATE.sir.no_semente);
  setInnerHtmlIfPresent('topInfluencersTableBody', topList.map(item => {
    const rowBg = activeSeed === String(item.id) ? 'bg-sagesoft' : 'hover:bg-sagelight';
    return `
      <tr onclick="selectInfluencerOnGraph('${escapeJsString(item.id)}')" class="${rowBg} cursor-pointer transition-colors">
        <td class="p-2 font-bold text-deepnavy">${item.rank}</td>
        <td class="p-2 font-bold text-deepnavy">${item.vertice}</td>
        <td class="p-2 font-medium text-deepnavy">${item.grau}</td>
        <td class="p-2 font-medium text-deepnavy">${item.pagerank}</td>
        <td class="p-2 font-medium text-deepnavy">${item.kcore}</td>
        <td class="p-2 font-bold text-[#15803D]">${item.alcance}</td>
      </tr>
    `;
  }).join(''));
}

// ---------------------------------------------------------------------------
// Página 6: Resultados Consolidados & Exportação JSON
// ---------------------------------------------------------------------------
function renderResultadosPage() {
  const res = BACKEND_STATE.resultados;

  setInnerHtmlIfPresent('consolidatedRankingBody', res.ranking_consolidado.map(r => `
    <tr class="hover:bg-sagelight">
      <td class="p-2.5 font-bold text-deepnavy">${r.vertice}</td>
      <td class="p-2.5 font-medium text-deepnavy">${r.grau}</td>
      <td class="p-2.5 font-medium text-deepnavy">${r.pagerank}</td>
      <td class="p-2.5 font-medium text-deepnavy">${r.comunidade}</td>
      <td class="p-2.5 font-bold text-petrol">${r.alcance_sir}</td>
    </tr>
  `).join(''));

  const jsonBlock = document.getElementById('jsonPreviewBlock');
  if (jsonBlock) {
    jsonBlock.innerText = JSON.stringify(res.json_exportacao, null, 2);
  }
}
