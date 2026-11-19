// Navegação entre páginas da sidebar e sub-abas da página de métricas.

// Página (id da <section>) → mapa interativo que precisa ser redesenhado ao ficar visível.
const PAGE_MAP_KEY = {
  'page-uc04': 'network',
  'page-uc11': 'communities',
  'page-uc14': 'influencers'
};

// Atraso para o canvas ter dimensões reais após remover `hidden` da seção.
const PAGE_REDRAW_DELAY_MS = 30;

function navigateTo(pageId) {
  const targetSection = document.getElementById(pageId);
  if (!targetSection) return;

  document.querySelectorAll('.page-section').forEach(sec => sec.classList.add('hidden'));
  targetSection.classList.remove('hidden');

  document.querySelectorAll('.nav-item').forEach(btn => btn.classList.remove('active'));
  const activeBtn = document.getElementById('nav-' + pageId);
  if (activeBtn) activeBtn.classList.add('active');

  const mapKey = PAGE_MAP_KEY[pageId];
  if (mapKey) {
    setTimeout(() => drawMap(mapKey), PAGE_REDRAW_DELAY_MS);
  }
}

function switchMetricSubtab(subId) {
  document.querySelectorAll('.metric-tab').forEach(b => b.classList.remove('active'));
  document.querySelectorAll('.metric-subpanel').forEach(p => p.classList.add('hidden'));
  const panel = document.getElementById(subId);
  if (panel) panel.classList.remove('hidden');
  const btn = document.getElementById('btn-' + subId);
  if (btn) btn.classList.add('active');
}
