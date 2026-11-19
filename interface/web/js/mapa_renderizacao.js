// Renderização dos mapas interativos (grafo completo em <canvas>) e do mini-mapa.
//
// Cada quadro é desenhado em camadas, nesta ordem:
//   1. halos de comunidades / anéis da semente SIR (conforme o mapa)
//   2. todas as arestas visíveis (em lote, com frustum culling)
//   3. arestas da vizinhança do nó sob o cursor
//   4. caminho calculado (somente no mapa da rede)
//   5. vértices com zoom semântico e rótulos

const COLORS = {
  offwhite: '#FCFFF5',
  deepnavy: '#193441',
  minimapBg: '#0F222B',
  mutedgreen: '#91AA9D',
  green: '#22C55E',
  greenDark: '#16A34A',
  greenDeep: '#15803D',
  yellow: '#FACC15',
  red: '#EF4444'
};

const SIR_STATE_COLORS = {
  SEED: COLORS.yellow,
  I: COLORS.red,
  R: COLORS.green,
  S: COLORS.mutedgreen
};

const LABEL_FONT_BOLD = 'bold 10.5px JetBrains Mono';
const LABEL_FONT_REGULAR = '10px JetBrains Mono';

const EDGE_CULL_MARGIN_PX = 20;
const NODE_CULL_MARGIN_PX = 24;

// Durante o arraste em grafos muito grandes, desenha só uma amostra das arestas para manter a fluidez.
const DRAG_EDGE_SAMPLING_THRESHOLD = 20000;
const DRAG_EDGE_SAMPLE_TARGET = 14000;

const COMMUNITY_HALO_RADIUS = 0.29;            // raio do halo em unidades de mundo
const SIR_SEED_RING_RADII = [45, 95, 150];     // px em zoom 1x

const MINIMAP_PADDING_PX = 10;
const MINIMAP_MAX_SAMPLED_NODES = 600;

// ---------------------------------------------------------------------------
// Preparação do quadro
// ---------------------------------------------------------------------------
function resizeCanvasToContainer(canvas) {
  const rect = canvas.parentElement.getBoundingClientRect();
  if (rect.width > 0 && rect.height > 0) {
    canvas.width = rect.width;
    canvas.height = rect.height;
  }
}

function updateZoomLabel(cam) {
  const zoomLbl = document.getElementById(cam.zoomLabelId);
  if (zoomLbl) {
    zoomLbl.innerText = `${Math.round(cam.zoom * 100)}% • ${BACKEND_STATE.sessao.vertices_str} nós`;
  }
}

// Projeta todos os nós para coordenadas de tela (arrays tipados reaproveitados no hit-test do mouse).
function projectNodesToScreen(nodes, mapKey, centerX, centerY, scale) {
  const nCount = nodes.length;
  const sxArr = new Float32Array(nCount);
  const syArr = new Float32Array(nCount);
  for (let i = 0; i < nCount; i++) {
    const { wx, wy } = getNodeWorldCoords(nodes[i], mapKey);
    sxArr[i] = centerX + wx * scale;
    syArr[i] = centerY + wy * scale;
  }
  return { sxArr, syArr };
}

function getHighlightedPathIds(mapKey) {
  const caminho = BACKEND_STATE.visualizacao.caminho;
  return mapKey === 'network' && isPathVisible(caminho) ? caminho.rota : [];
}

function drawMap(mapKey) {
  const cam = MAP_CAMERAS[mapKey];
  if (!cam) return;
  const canvas = document.getElementById(cam.canvasId);
  if (!canvas) return;

  resizeCanvasToContainer(canvas);
  const { w, h } = getCanvasSize(canvas);
  const ctx = canvas.getContext('2d');
  updateZoomLabel(cam);

  const nodes = getVisualNodes();
  if (nodes.length === 0) {
    ctx.clearRect(0, 0, w, h);
    return;
  }

  const scale = getBaseScale(w, h) * cam.zoom;
  const centerX = (w / 2) + cam.panX;
  const centerY = (h / 2) + cam.panY;
  const { sxArr, syArr } = projectNodesToScreen(nodes, mapKey, centerX, centerY, scale);
  cam._sxArr = sxArr;
  cam._syArr = syArr;

  const pathIds = getHighlightedPathIds(mapKey);
  const frame = {
    mapKey,
    cam,
    ctx,
    w,
    h,
    nodes,
    edges: getVisualEdges(),
    sxArr,
    syArr,
    centerX,
    centerY,
    scale,
    hoverIdx: cam.hoverIdx,
    hoverNeighbors: cam.hoverIdx >= 0 ? sessionState.neighborsByIdx[cam.hoverIdx] : null,
    commFilter: sessionState.selectedCommunityFilter,
    pathIds,
    pathSet: new Set(pathIds.map(String))
  };

  ctx.clearRect(0, 0, w, h);
  ctx.save();

  if (mapKey === 'communities') {
    drawCommunityHalos(frame);
    updateCommunityStatusLabel();
  }
  if (mapKey === 'influencers') {
    drawSirSeedRings(frame);
  }
  drawEdges(frame);
  drawHoverEgoEdges(frame);
  drawPathOverlay(frame);
  drawNodes(frame);

  ctx.restore();
  drawMinimap(mapKey);
}

// ---------------------------------------------------------------------------
// Camada 1: decorações específicas de cada mapa
// ---------------------------------------------------------------------------
function drawCommunityHalos({ ctx, centerX, centerY, scale, commFilter }) {
  const showHulls = document.getElementById('showClusterHullsToggle')?.checked ?? true;
  if (!showHulls) return;

  const communities = BACKEND_STATE.comunidades.lista || [];
  communities.forEach((c, idx) => {
    const [ccx, ccy] = COMMUNITY_CENTERS[idx % COMMUNITY_CENTERS.length];
    const isDimmed = commFilter !== 'all' && commFilter !== idx;
    ctx.save();
    ctx.globalAlpha = isDimmed ? 0.04 : 0.14;
    ctx.beginPath();
    ctx.arc(centerX + ccx * scale, centerY + ccy * scale, COMMUNITY_HALO_RADIUS * scale, 0, Math.PI * 2);
    ctx.fillStyle = c.cor;
    ctx.fill();
    ctx.globalAlpha = isDimmed ? 0.15 : 0.75;
    ctx.lineWidth = 1.8;
    ctx.setLineDash([6, 4]);
    ctx.strokeStyle = c.cor;
    ctx.stroke();
    ctx.restore();
  });
}

function updateCommunityStatusLabel() {
  const statusLabel = document.getElementById('commCanvasStatusLabel');
  if (!statusLabel) return;

  const com = BACKEND_STATE.comunidades;
  const communities = com.lista || [];
  const filter = sessionState.selectedCommunityFilter;
  if (filter === 'all') {
    statusLabel.innerText = `Grafo Completo: ${com.total_clusters} Comunidades (${com.algoritmo_ativo})`;
  } else {
    const selected = communities[filter] || communities[0];
    statusLabel.innerText = `Isolando ${selected.nome} (${selected.qtd_nos} nós)`;
  }
}

function drawSirSeedRings({ ctx, cam, sxArr, syArr }) {
  const seedIdx = sessionState.nodeIndexById[String(BACKEND_STATE.sir.no_semente)];
  if (seedIdx === undefined) return;

  const sx = sxArr[seedIdx];
  const sy = syArr[seedIdx];
  const zoomFactor = Math.pow(cam.zoom, 0.4);
  SIR_SEED_RING_RADII.forEach((radius, ringIdx) => {
    ctx.save();
    ctx.beginPath();
    ctx.arc(sx, sy, radius * zoomFactor, 0, Math.PI * 2);
    ctx.strokeStyle = ringIdx === 0 ? 'rgba(250, 204, 21, 0.42)' : 'rgba(239, 68, 68, 0.25)';
    ctx.lineWidth = 1.5;
    ctx.setLineDash([5, 5]);
    ctx.stroke();
    ctx.restore();
  });
}

// ---------------------------------------------------------------------------
// Camadas 2–4: arestas, vizinhança sob o cursor e caminho calculado
// ---------------------------------------------------------------------------
function isSegmentOutsideViewport(x1, y1, x2, y2, w, h, margin) {
  return (x1 < -margin && x2 < -margin) || (x1 > w + margin && x2 > w + margin)
    || (y1 < -margin && y2 < -margin) || (y1 > h + margin && y2 > h + margin);
}

function getEdgeStyle(nCount, zoom, mapKey) {
  const alpha = nCount > 1500
    ? Math.min(0.45, 0.11 * Math.pow(zoom, 0.45))
    : (nCount > 200 ? 0.28 : 0.52);
  const effectiveAlpha = mapKey === 'network' ? alpha : alpha * 0.85;
  return {
    strokeStyle: `rgba(145, 170, 157, ${effectiveAlpha})`,
    lineWidth: nCount > 1500 ? 0.75 : 1.1
  };
}

// Desenha em lote (um único stroke) todas as arestas visíveis no viewport.
function drawEdges({ ctx, cam, w, h, nodes, edges, sxArr, syArr, mapKey, commFilter }) {
  const totalEdges = edges.length;
  const stepEdge = (cam.isDragging && totalEdges > DRAG_EDGE_SAMPLING_THRESHOLD)
    ? Math.ceil(totalEdges / DRAG_EDGE_SAMPLE_TARGET)
    : 1;
  const filterByCommunity = mapKey === 'communities' && commFilter !== 'all';

  ctx.beginPath();
  for (let eIdx = 0; eIdx < totalEdges; eIdx += stepEdge) {
    const [u, v] = edges[eIdx];
    const x1 = sxArr[u], y1 = syArr[u];
    const x2 = sxArr[v], y2 = syArr[v];

    if (isSegmentOutsideViewport(x1, y1, x2, y2, w, h, EDGE_CULL_MARGIN_PX)) continue;
    if (filterByCommunity && nodes[u].comm !== commFilter && nodes[v].comm !== commFilter) continue;

    ctx.moveTo(x1, y1);
    ctx.lineTo(x2, y2);
  }

  const style = getEdgeStyle(nodes.length, cam.zoom, mapKey);
  ctx.strokeStyle = style.strokeStyle;
  ctx.lineWidth = style.lineWidth;
  ctx.stroke();
}

function drawHoverEgoEdges({ ctx, hoverIdx, hoverNeighbors, sxArr, syArr, mapKey }) {
  if (hoverIdx < 0 || !hoverNeighbors) return;

  const hx = sxArr[hoverIdx], hy = syArr[hoverIdx];
  ctx.beginPath();
  hoverNeighbors.forEach(nbIdx => {
    ctx.moveTo(hx, hy);
    ctx.lineTo(sxArr[nbIdx], syArr[nbIdx]);
  });
  ctx.strokeStyle = mapKey === 'network' ? 'rgba(25, 52, 65, 0.75)' : 'rgba(250, 204, 21, 0.78)';
  ctx.lineWidth = 2.0;
  ctx.stroke();
}

function strokeSegment(ctx, x1, y1, x2, y2, strokeStyle, lineWidth) {
  ctx.beginPath();
  ctx.moveTo(x1, y1);
  ctx.lineTo(x2, y2);
  ctx.strokeStyle = strokeStyle;
  ctx.lineWidth = lineWidth;
  ctx.stroke();
}

function drawPathOverlay({ ctx, pathIds, sxArr, syArr }) {
  for (let i = 0; i < pathIds.length - 1; i++) {
    const uIdx = sessionState.nodeIndexById[String(pathIds[i])];
    const vIdx = sessionState.nodeIndexById[String(pathIds[i + 1])];
    if (uIdx === undefined || vIdx === undefined) continue;
    const x1 = sxArr[uIdx], y1 = syArr[uIdx];
    const x2 = sxArr[vIdx], y2 = syArr[vIdx];

    ctx.lineCap = 'round';
    strokeSegment(ctx, x1, y1, x2, y2, 'rgba(34, 197, 94, 0.32)', 9);   // brilho externo
    strokeSegment(ctx, x1, y1, x2, y2, COLORS.greenDark, 3.5);           // traço principal

    ctx.beginPath();
    ctx.arc((x1 + x2) / 2, (y1 + y2) / 2, 4.2, 0, Math.PI * 2);
    ctx.fillStyle = COLORS.greenDeep;
    ctx.fill();
  }
}

// ---------------------------------------------------------------------------
// Camada 5: vértices com zoom semântico
// ---------------------------------------------------------------------------

// Parâmetros que só dependem do quadro (calculados uma vez, fora do laço de nós).
function buildNodeRenderContext(frame) {
  const { nodes, cam } = frame;
  const nCount = nodes.length;
  return {
    sizeMode: document.getElementById('visSizeBy')?.value || 'degree',
    maxDeg: Math.max(nodes[0]?.degree || 1, 1),
    maxPr: Math.max(...nodes.slice(0, 30).map(n => parseFloat(n.pagerank) || 0.001), 0.001),
    zoomScaleRadius: Math.pow(cam.zoom, 0.32),
    baseNodeScale: nCount > 1500 ? 0.52 : (nCount > 250 ? 0.72 : 1.0),
    baseLineWidth: nCount > 1000 ? 0.8 : 1.4,
    topSirIds: new Set((BACKEND_STATE.sir.top_influenciadores || []).map(t => String(t.id))),
    sirSeedId: String(BACKEND_STATE.sir.no_semente),
    selectedId: String(sessionState.selectedNodeId),
    // Zoom semântico: quanto maior o zoom, mais rótulos (dos nós mais importantes) aparecem.
    labelRankCutoff: nCount <= 60 ? nCount : Math.min(nCount, Math.floor(14 * Math.pow(cam.zoom, 1.45)))
  };
}

function getBaseNodeRadius(node, rc) {
  let r = 6.5 * rc.baseNodeScale;
  if (rc.sizeMode === 'degree') {
    r = (4.5 + (node.degree / rc.maxDeg) * 9.5) * rc.baseNodeScale;
  } else if (rc.sizeMode === 'pagerank') {
    r = (4.5 + ((parseFloat(node.pagerank) || 0) / rc.maxPr) * 10.5) * rc.baseNodeScale;
  }
  return Math.max(2.2, Math.min(18.0, r * rc.zoomScaleRadius));
}

function getNodeAlpha(frame, node, flags) {
  const { mapKey, commFilter, pathSet } = frame;
  if (mapKey === 'communities' && commFilter !== 'all' && node.comm !== commFilter && !flags.isHover) {
    return 0.12;
  }
  if (pathSet.size > 0 && !flags.inPath && !flags.isSel && !flags.isHover) {
    return 0.35;
  }
  return 1.0;
}

// Calcula raio, cores e espessura do contorno de um vértice conforme o mapa e seu estado.
function getNodeStyle(frame, rc, node, flags) {
  const style = {
    r: getBaseNodeRadius(node, rc),
    fill: node.color,
    stroke: COLORS.offwhite,
    lw: rc.baseLineWidth
  };

  if (frame.mapKey === 'communities') {
    style.fill = node.comm_color;
    style.stroke = node.is_hub ? COLORS.offwhite : COLORS.deepnavy;
    if (node.is_hub) {
      style.r = Math.max(style.r, 9.5);
      style.lw = 2.6;
    }
  } else if (frame.mapKey === 'influencers') {
    const sirState = flags.isSirSeed ? 'SEED' : (node.sir_state || 'S');
    style.fill = SIR_STATE_COLORS[sirState] || SIR_STATE_COLORS.S;
    if (sirState === 'SEED') {
      style.r = Math.max(style.r, 11.5);
      style.lw = 2.8;
    } else if (rc.topSirIds.has(flags.idStr)) {
      style.r = Math.max(style.r, 8.5);
      style.lw = 2.0;
    }
  } else if (flags.inPath) {
    const { pathIds } = frame;
    const isEndpoint = flags.idStr === String(pathIds[0]) || flags.idStr === String(pathIds[pathIds.length - 1]);
    style.fill = isEndpoint ? COLORS.green : COLORS.deepnavy;
    style.stroke = COLORS.green;
    style.r = Math.max(style.r, 10.5);
    style.lw = 3.0;
  } else if (flags.isSel) {
    style.stroke = COLORS.deepnavy;
    style.r = Math.max(style.r, 9.5);
    style.lw = 2.8;
  }

  if (flags.isHover) {
    style.r = Math.max(style.r + 2.5, 10.5);
    style.stroke = COLORS.yellow;
    style.lw = 3.0;
  } else if (flags.isHoverNeighbor) {
    style.stroke = COLORS.green;
    style.lw = 2.0;
  }
  return style;
}

function drawNodeLabel(frame, node, idx, sx, sy, r, flags, rc) {
  const isStarred = (frame.mapKey === 'communities' && node.is_hub) || (frame.mapKey === 'influencers' && flags.isSirSeed);
  const showLabel = flags.isHover || flags.isSel || flags.inPath || isStarred || idx < rc.labelRankCutoff;
  if (!showLabel) return;

  const { ctx } = frame;
  ctx.fillStyle = frame.mapKey === 'network' ? COLORS.deepnavy : COLORS.offwhite;
  ctx.font = (flags.inPath || flags.isSel || flags.isHover || idx < 8) ? LABEL_FONT_BOLD : LABEL_FONT_REGULAR;
  ctx.fillText((isStarred ? '★' : '') + node.rotulo, sx + r + 4, sy + 3.5);
}

function drawNodes(frame) {
  const { ctx, nodes, sxArr, syArr, w, h, hoverIdx, hoverNeighbors, pathSet } = frame;
  const rc = buildNodeRenderContext(frame);
  const margin = NODE_CULL_MARGIN_PX;

  // Desenha da menor importância para a maior (para que hubs e selecionados fiquem sempre no topo)
  for (let i = nodes.length - 1; i >= 0; i--) {
    const sx = sxArr[i], sy = syArr[i];
    if (sx < -margin || sx > w + margin || sy < -margin || sy > h + margin) continue;

    const node = nodes[i];
    const idStr = String(node.id);
    const flags = {
      idStr,
      inPath: pathSet.has(idStr),
      isSel: rc.selectedId === idStr,
      isHover: i === hoverIdx,
      isHoverNeighbor: hoverNeighbors ? hoverNeighbors.has(i) : false,
      isSirSeed: idStr === rc.sirSeedId
    };

    ctx.globalAlpha = getNodeAlpha(frame, node, flags);
    const { r, fill, stroke, lw } = getNodeStyle(frame, rc, node, flags);

    ctx.beginPath();
    ctx.arc(sx, sy, r, 0, Math.PI * 2);
    ctx.fillStyle = fill;
    ctx.fill();
    if (r > 2.8 || flags.inPath || flags.isSel || flags.isHover) {
      ctx.lineWidth = lw;
      ctx.strokeStyle = stroke;
      ctx.stroke();
    }

    drawNodeLabel(frame, node, i, sx, sy, r, flags, rc);
  }
}

// ---------------------------------------------------------------------------
// Mini-mapa estilo Google Maps / Radar no canto inferior esquerdo
// ---------------------------------------------------------------------------
function minimapScale(mini) {
  return {
    scaleX: (mini.width - MINIMAP_PADDING_PX * 2) / 2,
    scaleY: (mini.height - MINIMAP_PADDING_PX * 2) / 2
  };
}

function drawMinimap(mapKey) {
  const cam = MAP_CAMERAS[mapKey];
  const mini = document.getElementById(cam.minimapId);
  const mainCanvas = document.getElementById(cam.canvasId);
  if (!mini || !mainCanvas) return;

  const mw = mini.width;
  const mh = mini.height;
  const mctx = mini.getContext('2d');
  mctx.clearRect(0, 0, mw, mh);
  mctx.fillStyle = COLORS.minimapBg;
  mctx.fillRect(0, 0, mw, mh);

  const nodes = getVisualNodes();
  const nCount = nodes.length;
  if (nCount === 0) return;

  const { scaleX, scaleY } = minimapScale(mini);
  const step = Math.max(1, Math.floor(nCount / MINIMAP_MAX_SAMPLED_NODES));
  for (let i = 0; i < nCount; i += step) {
    const n = nodes[i];
    const { wx, wy } = getNodeWorldCoords(n, mapKey);
    mctx.fillStyle = mapKey === 'communities' ? n.comm_color : COLORS.mutedgreen;
    mctx.fillRect((mw / 2) + wx * scaleX, (mh / 2) + wy * scaleY, 1.8, 1.8);
  }

  // Retângulo do Viewport Atual
  const { w, h } = getCanvasSize(mainCanvas);
  const topLeft = screenToWorld(0, 0, cam, w, h);
  const bottomRight = screenToWorld(w, h, cam, w, h);
  const rx1 = Math.max(1, (mw / 2) + topLeft.wx * scaleX);
  const ry1 = Math.max(1, (mh / 2) + topLeft.wy * scaleY);
  const rx2 = Math.min(mw - 1, (mw / 2) + bottomRight.wx * scaleX);
  const ry2 = Math.min(mh - 1, (mh / 2) + bottomRight.wy * scaleY);

  mctx.strokeStyle = COLORS.yellow;
  mctx.lineWidth = 1.5;
  mctx.strokeRect(rx1, ry1, Math.max(6, rx2 - rx1), Math.max(6, ry2 - ry1));
}
