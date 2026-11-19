// Interação com os mapas: arrastar (pan), zoom pela roda do mouse, hover com tooltip, clique e mini-mapa.

const WHEEL_ZOOM_FACTOR = 1.18;
const DOUBLE_CLICK_ZOOM_FACTOR = 1.85;
const WHEEL_IDLE_REDRAW_MS = 110;  // após parar de rolar, redesenha com todas as arestas
const DRAG_THRESHOLD_PX = 2;       // deslocamento mínimo para um clique virar arraste
const TOOLTIP_OFFSET_PX = 14;

// Índice do nó sob o ponteiro (usa as posições de tela calculadas no último drawMap).
function findHoveredNodeIdx(cam, mx, my) {
  const sxArr = cam._sxArr;
  const syArr = cam._syArr;
  if (!sxArr || !syArr) return -1;
  const nCount = sxArr.length;
  const hitRadius = nCount > 1000 ? 9 : 13;
  const hitRadiusSq = hitRadius * hitRadius;
  for (let i = 0; i < nCount; i++) {
    const dx = sxArr[i] - mx;
    const dy = syArr[i] - my;
    if (dx * dx + dy * dy <= hitRadiusSq) {
      return i;
    }
  }
  return -1;
}

function showNodeTooltip(tooltip, node, evt) {
  setText('ttTitle', `${node.rotulo} (${node.subtitulo})`);
  setText('ttLine1', `Grau: ${node.degree} • PageRank: ${node.pagerank}`);
  setText('ttLine2', `k-Core: ${node.kcore} • Comunidade #${node.comm + 1}`);
  tooltip.style.left = (evt.clientX + TOOLTIP_OFFSET_PX) + 'px';
  tooltip.style.top = (evt.clientY + TOOLTIP_OFFSET_PX) + 'px';
  tooltip.classList.remove('hidden');
}

// Ação executada ao clicar em um nó, conforme o mapa.
function handleNodeClick(mapKey, node) {
  if (mapKey === 'network') {
    selectInspectorNode(node.id, true);
  } else if (mapKey === 'communities') {
    filterCommunityOnGraph(node.comm);
  } else if (mapKey === 'influencers') {
    selectInfluencerOnGraph(node.id);
  }
}

// Zoom mantendo fixo o ponto do mundo sob o cursor (estilo Google Maps).
function zoomAtScreenPoint(cam, mx, my, w, h, factor) {
  const newZoom = clampZoom(cam.zoom * factor);
  const ratio = newZoom / cam.zoom;
  const offsetX = mx - w / 2;
  const offsetY = my - h / 2;
  cam.panX = offsetX - (offsetX - cam.panX) * ratio;
  cam.panY = offsetY - (offsetY - cam.panY) * ratio;
  cam.zoom = newZoom;
}

function bindInteractiveMapEvents(mapKey) {
  const cam = MAP_CAMERAS[mapKey];
  const canvas = document.getElementById(cam.canvasId);
  const mini = document.getElementById(cam.minimapId);
  const tooltip = document.getElementById('mapHoverTooltip');
  if (!canvas) return;

  canvas.addEventListener('mousedown', (evt) => {
    cancelCameraAnimation(cam);
    cam.isDragging = true;
    cam.dragMoved = false;
    cam.lastX = evt.clientX;
    cam.lastY = evt.clientY;
  });

  window.addEventListener('mouseup', () => {
    if (cam.isDragging) {
      cam.isDragging = false;
      drawMap(mapKey);
    }
  });

  canvas.addEventListener('mousemove', (evt) => {
    if (cam.isDragging) {
      const dx = evt.clientX - cam.lastX;
      const dy = evt.clientY - cam.lastY;
      if (Math.hypot(dx, dy) > DRAG_THRESHOLD_PX) cam.dragMoved = true;
      cam.panX += dx;
      cam.panY += dy;
      cam.lastX = evt.clientX;
      cam.lastY = evt.clientY;
      tooltip.classList.add('hidden');
      drawMap(mapKey);
      return;
    }

    const { mx, my } = getPointerPosition(evt, canvas);
    const hitIdx = findHoveredNodeIdx(cam, mx, my);
    if (hitIdx !== cam.hoverIdx) {
      cam.hoverIdx = hitIdx;
      canvas.style.cursor = hitIdx >= 0 ? 'pointer' : 'grab';
      drawMap(mapKey);
    }

    if (hitIdx >= 0) {
      showNodeTooltip(tooltip, getVisualNodes()[hitIdx], evt);
    } else {
      tooltip.classList.add('hidden');
    }
  });

  canvas.addEventListener('mouseleave', () => {
    cam.hoverIdx = -1;
    tooltip.classList.add('hidden');
    drawMap(mapKey);
  });

  // Zoom suave com roda do mouse centrado no cursor (estilo Google Maps)
  canvas.addEventListener('wheel', (evt) => {
    evt.preventDefault();
    cancelCameraAnimation(cam);
    const { mx, my } = getPointerPosition(evt, canvas);
    const { w, h } = getCanvasSize(canvas);
    zoomAtScreenPoint(cam, mx, my, w, h, evt.deltaY < 0 ? WHEEL_ZOOM_FACTOR : 1 / WHEEL_ZOOM_FACTOR);

    // Enquanto rola, trata como arraste (amostragem de arestas); ao parar, redesenha completo.
    cam.isDragging = true;
    drawMap(mapKey);
    clearTimeout(cam._wheelTimer);
    cam._wheelTimer = setTimeout(() => {
      cam.isDragging = false;
      drawMap(mapKey);
    }, WHEEL_IDLE_REDRAW_MS);
  }, { passive: false });

  // Clique simples seleciona o nó; duplo clique aproxima o zoom no ponto clicado
  canvas.addEventListener('click', (evt) => {
    if (cam.dragMoved) return;
    const { mx, my } = getPointerPosition(evt, canvas);
    const hitIdx = findHoveredNodeIdx(cam, mx, my);
    if (hitIdx >= 0) {
      handleNodeClick(mapKey, getVisualNodes()[hitIdx]);
    }
  });

  canvas.addEventListener('dblclick', (evt) => {
    const { mx, my } = getPointerPosition(evt, canvas);
    const { w, h } = getCanvasSize(canvas);
    const { wx, wy } = screenToWorld(mx, my, cam, w, h);
    flyToWorldPoint(mapKey, wx, wy, Math.min(CAMERA_MAX_ZOOM, cam.zoom * DOUBLE_CLICK_ZOOM_FACTOR));
  });

  // Clique no mini-mapa move a câmera diretamente para aquela região
  if (mini) {
    mini.addEventListener('click', (evt) => {
      const { mx, my } = getPointerPosition(evt, mini);
      const { scaleX, scaleY } = minimapScale(mini);
      const wx = (mx - mini.width / 2) / scaleX;
      const wy = (my - mini.height / 2) / scaleY;
      flyToWorldPoint(mapKey, wx, wy, cam.zoom);
    });
  }
}
