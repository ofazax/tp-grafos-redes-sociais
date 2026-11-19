// Ações de análise disparadas pelo usuário: caminhos, layout, comunidades, SIR e exportação.

const LAYOUT_SEED_INCREMENT = 7;
const LAYOUT_RECALC_ITERATIONS = 40;
const COMMUNITY_FOCUS_ZOOM = 2.2;

const SIR_DEFAULTS = { beta: 0.08, gamma: 0.02, runs: 30, seed: 42 };

// ---------------------------------------------------------------------------
// Caminhos (página Visualizar Rede)
// ---------------------------------------------------------------------------
async function computeAndHighlightPathOnGraph(btn = null) {
  const sourceInput = document.getElementById('pathSource');
  const targetInput = document.getElementById('pathTarget');
  sourceInput.dataset.edited = '1';
  targetInput.dataset.edited = '1';

  const res = await callBackendAPI({
    acao: 'calcular_caminho',
    algoritmo: document.getElementById('pathAlgo').value,
    origem: sourceInput.value.trim(),
    destino: targetInput.value.trim()
  }, btn);

  if (res.caminho && res.caminho.encontrado) {
    focusActivePathOnMap();
  }
}

function clearGraphPath() {
  sessionState.pathClearedManually = true;
  updatePathDisplayFromState();
  drawMap('network');
}

async function useSelectedNodeAsPathEndpoint(inputId, btn) {
  if (sessionState.selectedNodeId === null) return;
  document.getElementById(inputId).value = String(sessionState.selectedNodeId);
  await computeAndHighlightPathOnGraph(btn);
}

async function setClickedAsOrigin(btn = null) {
  await useSelectedNodeAsPathEndpoint('pathSource', btn);
}

async function setClickedAsTarget(btn = null) {
  await useSelectedNodeAsPathEndpoint('pathTarget', btn);
}

async function recalculateFRLayout(btn = null) {
  await callBackendAPI({
    acao: 'recalcular_layout',
    semente: (BACKEND_STATE.sessao.semente_ativa || 42) + LAYOUT_SEED_INCREMENT,
    iteracoes: LAYOUT_RECALC_ITERATIONS
  }, btn);
  resetMapView('network');
}

// ---------------------------------------------------------------------------
// Comunidades
// ---------------------------------------------------------------------------
function filterCommunityOnGraph(commIdx) {
  sessionState.selectedCommunityFilter = commIdx;
  renderCommunityListUI();
  if (commIdx === 'all') {
    resetMapView('communities');
    return;
  }
  const [cx, cy] = COMMUNITY_CENTERS[commIdx % COMMUNITY_CENTERS.length];
  flyToWorldPoint('communities', cx, cy, COMMUNITY_FOCUS_ZOOM);
}

async function runCommunityDetection(btn = null) {
  sessionState.selectedCommunityFilter = 'all';
  await callBackendAPI({
    acao: 'detectar_comunidades',
    algoritmo: document.getElementById('commAlgo').value,
    semente: parseInt(document.getElementById('commSeedInput').value) || 42
  }, btn);
  resetMapView('communities');
}

// ---------------------------------------------------------------------------
// Influenciadores & SIR
// ---------------------------------------------------------------------------
function readSirParameters() {
  return {
    beta: parseFloat(document.getElementById('sirBeta').value) || SIR_DEFAULTS.beta,
    gamma: parseFloat(document.getElementById('sirGamma').value) || SIR_DEFAULTS.gamma,
    simulacoes: parseInt(document.getElementById('sirRunsInput').value) || SIR_DEFAULTS.runs,
    semente: parseInt(document.getElementById('sirSeedInput').value) || SIR_DEFAULTS.seed
  };
}

async function selectInfluencerOnGraph(nodeId, btn = null) {
  await callBackendAPI({
    acao: 'simular_sir',
    no_semente: nodeId,
    ...readSirParameters()
  }, btn);
}

async function runSIRSimulation(btn = null) {
  await selectInfluencerOnGraph(document.getElementById('sirSeedNodeSelect').value, btn);
}

// ---------------------------------------------------------------------------
// Exportação dos resultados
// ---------------------------------------------------------------------------
function getExportJsonText() {
  return document.getElementById('jsonPreviewBlock').innerText;
}

function copyJsonToClipboard(btn = null) {
  flashButtonLoading(btn || document.getElementById('btnCopyJson'));
  const temp = document.createElement('textarea');
  temp.value = getExportJsonText();
  document.body.appendChild(temp);
  temp.select();
  document.execCommand('copy');
  document.body.removeChild(temp);
}

function buildExportFileName() {
  const safeName = (BACKEND_STATE.sessao.nome_grafo || 'grafo').toLowerCase().replace(/[^a-z0-9]+/g, '_');
  return `grafosocial_${safeName}.json`;
}

function quickExportJSON(btn = null) {
  flashButtonLoading(btn || document.getElementById('btnExportJson'));
  const blob = new Blob([getExportJsonText()], { type: 'application/json' });
  const url = URL.createObjectURL(blob);
  const link = document.createElement('a');
  link.href = url;
  link.download = buildExportFileName();
  link.click();
  URL.revokeObjectURL(url);
}
