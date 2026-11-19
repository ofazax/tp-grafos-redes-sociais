// Estado global do front-end: dados vindos do backend, seleção do usuário e câmeras dos mapas.

const API_URL = "__API_URL__";
let BACKEND_STATE = __PAYLOAD_JSON__;

// Bases públicas homologadas, na ordem de exibição (header e cards).
const BASE_KEYS = ['facebook', 'twitch', 'thrones', 'karate'];

// Identificadores dos três mapas interativos de grafo.
const MAP_KEYS = ['network', 'communities', 'influencers'];

// Centros (coordenadas de mundo) dos agrupamentos no mapa de comunidades.
// Devem coincidir com `centros_clusters` em `servico_backend.construir_subgrafo_visual_e_posicoes`.
const COMMUNITY_CENTERS = [
  [-0.52, -0.42],
  [0.52, -0.44],
  [0.0, 0.04],
  [-0.50, 0.48],
  [0.52, 0.46]
];

// Limites e fatores da câmera (zoom estilo Google Maps).
const CAMERA_MIN_ZOOM = 0.25;
const CAMERA_MAX_ZOOM = 35.0;
const CAMERA_BASE_SCALE_RATIO = 0.42;  // fração do menor lado do canvas ocupada pelo grafo em zoom 1x
const DEFAULT_CANVAS_WIDTH = 760;
const DEFAULT_CANVAS_HEIGHT = 560;

const sessionState = {
  selectedDatasetKey: BACKEND_STATE.sessao.chave_base || 'facebook',
  selectedNodeId: null,
  selectedCommunityFilter: 'all',
  pathClearedManually: false,
  nodeIndexById: {},
  neighborsByIdx: []
};

function createMapCamera(prefix, coordMode) {
  return {
    canvasId: `${prefix}Canvas`,
    minimapId: `${prefix}Minimap`,
    zoomLabelId: `${prefix}ZoomLabel`,
    coordMode,
    zoom: 1.0,
    panX: 0.0,
    panY: 0.0,
    isDragging: false,
    dragMoved: false,
    lastX: 0,
    lastY: 0,
    hoverIdx: -1,
    animId: null
  };
}

// Estado de câmera independente para cada um dos 3 mapas (pan, zoom, hover, drag)
const MAP_CAMERAS = {
  network: createMapCamera('network', 'fr'),
  communities: createMapCamera('communities', 'comm'),
  influencers: createMapCamera('influencers', 'fr')
};

function getVisualNodes() {
  return BACKEND_STATE.visualizacao.nos || [];
}

function getVisualEdges() {
  return BACKEND_STATE.visualizacao.arestas || [];
}

// Reconstrói os índices auxiliares (id → índice e lista de vizinhos) após cada resposta do backend.
function rebuildGraphIndexCache() {
  const nodes = getVisualNodes();
  const edges = getVisualEdges();
  sessionState.nodeIndexById = {};
  sessionState.neighborsByIdx = Array.from({ length: nodes.length }, () => new Set());

  nodes.forEach((n, idx) => {
    sessionState.nodeIndexById[String(n.id)] = idx;
  });
  edges.forEach(([uIdx, vIdx]) => {
    if (sessionState.neighborsByIdx[uIdx]) sessionState.neighborsByIdx[uIdx].add(vIdx);
    if (sessionState.neighborsByIdx[vIdx]) sessionState.neighborsByIdx[vIdx].add(uIdx);
  });
}

// Utilitários compartilhados
function escapeJsString(value) {
  return String(value).replace(/'/g, "\\'");
}

function clampZoom(zoom) {
  return Math.max(CAMERA_MIN_ZOOM, Math.min(CAMERA_MAX_ZOOM, zoom));
}

function getCanvasSize(canvas) {
  return {
    w: canvas.width || DEFAULT_CANVAS_WIDTH,
    h: canvas.height || DEFAULT_CANVAS_HEIGHT
  };
}

function getPointerPosition(evt, element) {
  const rect = element.getBoundingClientRect();
  return { mx: evt.clientX - rect.left, my: evt.clientY - rect.top };
}

function readCheckedRadioValue(name) {
  return document.querySelector(`input[name="${name}"]:checked`).value;
}

function setText(elementId, text) {
  document.getElementById(elementId).innerText = text;
}
