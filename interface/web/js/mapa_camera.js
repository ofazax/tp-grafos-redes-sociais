// Sistema de coordenadas e câmera dos mapas (pan, zoom animado e "voar até" — estilo Google Maps).

const CAMERA_ANIMATION_MS = {
  default: 340,
  reset: 280,
  zoomButton: 200,
  flyTo: 360
};

const FLY_TO_DEFAULT_ZOOM = 4.2;
const SEARCH_ZOOM_LARGE_GRAPH = 6.0;   // grafos com mais de LARGE_GRAPH_NODES nós
const SEARCH_ZOOM_SMALL_GRAPH = 3.2;
const LARGE_GRAPH_NODES = 500;

function getNodeWorldCoords(node, mapKey) {
  if (mapKey === 'communities') {
    return { wx: node.cx, wy: node.cy };
  }
  return { wx: node.x, wy: node.y };
}

// Pixels por unidade de mundo em zoom 1x.
function getBaseScale(w, h) {
  return Math.min(w, h) * CAMERA_BASE_SCALE_RATIO;
}

function worldToScreen(wx, wy, cam, w, h) {
  const scale = getBaseScale(w, h) * cam.zoom;
  return {
    sx: (w / 2) + cam.panX + (wx * scale),
    sy: (h / 2) + cam.panY + (wy * scale)
  };
}

function screenToWorld(sx, sy, cam, w, h) {
  const denom = Math.max(1e-6, getBaseScale(w, h) * cam.zoom);
  return {
    wx: (sx - (w / 2) - cam.panX) / denom,
    wy: (sy - (h / 2) - cam.panY) / denom
  };
}

function cancelCameraAnimation(cam) {
  if (cam.animId) {
    cancelAnimationFrame(cam.animId);
    cam.animId = null;
  }
}

// Interpola pan/zoom com easing cúbico (ease-out), redesenhando a cada quadro.
function animateCameraTo(mapKey, targetPanX, targetPanY, targetZoom, duration = CAMERA_ANIMATION_MS.default) {
  const cam = MAP_CAMERAS[mapKey];
  if (!cam) return;
  cancelCameraAnimation(cam);

  const startPanX = cam.panX;
  const startPanY = cam.panY;
  const startZoom = cam.zoom;
  const t0 = performance.now();

  function step(now) {
    const progress = Math.min(1.0, (now - t0) / duration);
    const ease = 1.0 - Math.pow(1.0 - progress, 3);
    cam.panX = startPanX + (targetPanX - startPanX) * ease;
    cam.panY = startPanY + (targetPanY - startPanY) * ease;
    cam.zoom = startZoom + (targetZoom - startZoom) * ease;
    drawMap(mapKey);
    cam.animId = progress < 1.0 ? requestAnimationFrame(step) : null;
  }
  cam.animId = requestAnimationFrame(step);
}

function resetMapView(mapKey) {
  animateCameraTo(mapKey, 0.0, 0.0, 1.0, CAMERA_ANIMATION_MS.reset);
}

function resetAllMaps() {
  MAP_KEYS.forEach(k => {
    const cam = MAP_CAMERAS[k];
    cam.panX = 0.0;
    cam.panY = 0.0;
    cam.zoom = 1.0;
    cam.hoverIdx = -1;
    drawMap(k);
  });
}

function zoomMapByButton(mapKey, factor) {
  const cam = MAP_CAMERAS[mapKey];
  if (!cam) return;
  const newZoom = clampZoom(cam.zoom * factor);
  const ratio = newZoom / cam.zoom;
  animateCameraTo(mapKey, cam.panX * ratio, cam.panY * ratio, newZoom, CAMERA_ANIMATION_MS.zoomButton);
}

// Centraliza o ponto (wx, wy) na tela, sem nunca afastar o zoom atual.
function flyToWorldPoint(mapKey, wx, wy, targetZoom = FLY_TO_DEFAULT_ZOOM) {
  const cam = MAP_CAMERAS[mapKey];
  const canvas = document.getElementById(cam.canvasId);
  if (!canvas) return;
  const { w, h } = getCanvasSize(canvas);
  const zoom = Math.max(cam.zoom, targetZoom);
  const scale = getBaseScale(w, h) * zoom;
  animateCameraTo(mapKey, -wx * scale, -wy * scale, zoom, CAMERA_ANIMATION_MS.flyTo);
}

function normalizeNodeQuery(value) {
  return String(value).trim().replace(/^#/, '').toLowerCase();
}

function searchAndFlyToNode(mapKey, query) {
  if (!query) return;
  const q = normalizeNodeQuery(query);
  const nodes = getVisualNodes();
  const node = nodes.find(
    n => String(n.id).toLowerCase() === q || String(n.rotulo).toLowerCase().replace(/^#/, '') === q
  );
  if (!node) return;

  selectInspectorNode(node.id, false);
  const { wx, wy } = getNodeWorldCoords(node, mapKey);
  const zoomTarget = nodes.length > LARGE_GRAPH_NODES ? SEARCH_ZOOM_LARGE_GRAPH : SEARCH_ZOOM_SMALL_GRAPH;
  flyToWorldPoint(mapKey, wx, wy, zoomTarget);
}

// Enquadra a rota calculada (bounding box dos nós do caminho) no mapa da rede.
function focusActivePathOnMap() {
  const caminho = BACKEND_STATE.visualizacao.caminho;
  if (!caminho || !caminho.encontrado || !caminho.rota || caminho.rota.length === 0) {
    resetMapView('network');
    return;
  }
  const nodes = getVisualNodes();
  const pathNodes = caminho.rota
    .map(id => sessionState.nodeIndexById[String(id)])
    .filter(idx => idx !== undefined)
    .map(idx => nodes[idx]);
  if (pathNodes.length === 0) return;

  const xs = pathNodes.map(n => n.x);
  const ys = pathNodes.map(n => n.y);
  const minX = Math.min(...xs), maxX = Math.max(...xs);
  const minY = Math.min(...ys), maxY = Math.max(...ys);
  const span = Math.max(maxX - minX, maxY - minY, 0.22);
  const targetZoom = Math.min(8.0, Math.max(1.4, 1.35 / span));
  flyToWorldPoint('network', (minX + maxX) / 2, (minY + maxY) / 2, targetZoom);
}

function focusActiveSirSeedOnMap() {
  const seedId = BACKEND_STATE.sir.no_semente;
  if (!seedId) return;
  searchAndFlyToNode('influencers', seedId);
}
