// Página "Obter Grafo": bases homologadas, importação de arquivo e geração de grafos sintéticos.

const SUPPORTED_FILE_EXTENSIONS = ['.txt', '.csv'];

// Texto e parâmetros padrão exibidos para cada modelo sintético.
const SYNTH_MODEL_CONFIG = {
  ba: {
    paramLabel: 'Arestas por nó (m)',
    paramValue: 3,
    paramStep: 1,
    title: 'Propriedade Esperada (Barabási–Albert):',
    description: 'Distribuição de grau em lei de potência (Power-law), formação natural de hubs e baixo diâmetro.'
  },
  er: {
    paramLabel: 'Probabilidade (p)',
    paramValue: 0.05,
    paramStep: 0.01,
    title: 'Propriedade Esperada (Erdős–Rényi):',
    description: 'Grau concentrado em torno da média np e baixo coeficiente de agrupamento.'
  },
  ws: {
    paramLabel: 'Vizinhos k (Anel)',
    paramValue: 6,
    paramStep: 2,
    title: 'Propriedade Esperada (Watts–Strogatz):',
    description: 'Alto coeficiente de agrupamento local combinado com distâncias curtas.'
  }
};

// Opções de leitura escolhidas nos rádios "Direcionamento" e "Ponderação de Arestas".
function readGraphReadingOptions() {
  return {
    direcionado: readCheckedRadioValue('dirReal') === 'Direcionado',
    ponderado: readCheckedRadioValue('weightReal') === 'Com Peso'
  };
}

function setWeightedRadio(ponderado) {
  document.getElementById('weightYes').checked = ponderado;
  document.getElementById('weightNone').checked = !ponderado;
}

// Um novo grafo invalida os nós de origem/destino digitados manualmente.
function resetPathInputsEditedFlag() {
  document.getElementById('pathSource').dataset.edited = '';
  document.getElementById('pathTarget').dataset.edited = '';
}

function selectRealDatasetCard(key) {
  sessionState.selectedDatasetKey = key;
  const select = document.getElementById('selectRealDataset');
  if (select) select.value = key;
  const base = BACKEND_STATE.catalogo_bases[key];
  if (base) {
    setText('realPathHint', base.origem);
    setWeightedRadio(Boolean(base.ponderado_padrao));
  }
  applyBackendStateToDOM();
}

function previewRealDataset() {
  selectRealDatasetCard(document.getElementById('selectRealDataset').value);
}

async function switchDatasetFromHeader(datasetKey) {
  if (datasetKey === 'custom') return;
  sessionState.selectedDatasetKey = datasetKey;
  const base = BACKEND_STATE.catalogo_bases[datasetKey];
  setWeightedRadio(base ? Boolean(base.ponderado_padrao) : false);
  await loadRealGraph();
}

function handleRealFileUpload(event) {
  const file = event.target.files[0];
  if (!file) return;

  const lowerName = file.name.toLowerCase();
  if (!SUPPORTED_FILE_EXTENSIONS.some(ext => lowerName.endsWith(ext))) {
    event.target.value = '';
    return;
  }

  const importButton = document.getElementById('btnImportFile');
  setButtonLoading(importButton, true);
  const reader = new FileReader();
  reader.onload = async (e) => {
    resetPathInputsEditedFlag();
    await callBackendAPI({
      acao: 'importar_arquivo',
      nome: file.name,
      conteudo: e.target.result,
      ...readGraphReadingOptions()
    }, importButton);
    resetAllMaps();
  };
  reader.readAsText(file, 'utf-8');
}

async function removeImportedFile(btn = null) {
  const fileInput = document.getElementById('realFileInput');
  if (fileInput) fileInput.value = '';
  await loadRealGraph(btn || document.getElementById('btnRemoveFile'));
}

async function loadRealGraph(btn = null) {
  resetPathInputsEditedFlag();
  await callBackendAPI({
    acao: 'carregar_base',
    chave: sessionState.selectedDatasetKey || 'facebook',
    ...readGraphReadingOptions()
  }, btn);
  resetAllMaps();
}

function updateSynthParamsUI() {
  const model = document.getElementById('selectSynthModel').value;
  const config = SYNTH_MODEL_CONFIG[model] || SYNTH_MODEL_CONFIG.ws;
  const paramInput = document.getElementById('synthParam1');

  setText('paramLabel1', config.paramLabel);
  paramInput.value = config.paramValue;
  paramInput.step = config.paramStep;
  document.getElementById('synthModelDesc').innerHTML =
    `<div class="font-bold text-petrol">${config.title}</div><p>${config.description}</p>`;
}

async function generateSyntheticGraph(btn = null) {
  resetPathInputsEditedFlag();
  await callBackendAPI({
    acao: 'gerar_sintetico',
    modelo: document.getElementById('selectSynthModel').value,
    n: parseInt(document.getElementById('synthN').value) || 150,
    param: parseFloat(document.getElementById('synthParam1').value) || 3,
    semente: parseInt(document.getElementById('synthSeed').value) || 42
  }, btn);
  resetAllMaps();
}
