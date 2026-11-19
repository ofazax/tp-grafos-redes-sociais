// Ponto de entrada: monta índices, liga eventos dos mapas e pinta o estado inicial.

document.addEventListener('DOMContentLoaded', () => {
  rebuildGraphIndexCache();
  MAP_KEYS.forEach(bindInteractiveMapEvents);
  applyBackendStateToDOM();

  window.addEventListener('resize', () => MAP_KEYS.forEach(drawMap));
});
