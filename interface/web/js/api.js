// Comunicação com o servidor HTTP local do backend e estados de carregamento dos botões.

const LOADING_TEXT = 'Carregando...';

// Ação do backend → botão principal que a dispara (fica em "Carregando..." durante a requisição).
const ACTION_BUTTON_MAP = {
  carregar_base: 'btnLoadReal',
  importar_arquivo: 'btnImportFile',
  gerar_sintetico: 'btnGenerateSynth',
  recalcular_layout: 'btnRecalcLayout',
  calcular_caminho: 'btnCalcPath',
  detectar_comunidades: 'btnDetectComm',
  simular_sir: 'btnRunSir'
};

// Selects que disparam requisições e por isso ficam bloqueados enquanto uma está em andamento.
const REQUEST_TRIGGER_SELECT_IDS = ['headerDatasetSelect', 'pathAlgo', 'commAlgo', 'sirSeedNodeSelect'];

const BACKEND_STATUS_DOT_CLASS = {
  loading: 'w-2.5 h-2.5 rounded-full bg-[#FACC15] animate-ping',
  idle: 'w-2.5 h-2.5 rounded-full bg-sage animate-pulse',
  error: 'w-2.5 h-2.5 rounded-full bg-[#EF4444]'
};

function setBackendStatus(status) {
  const dot = document.getElementById('backendStatusDot');
  if (dot) dot.className = BACKEND_STATUS_DOT_CLASS[status];
}

function setButtonLoading(btnOrId, isLoading, loadingText = LOADING_TEXT) {
  const btn = typeof btnOrId === 'string' ? document.getElementById(btnOrId) : btnOrId;
  if (!btn || btn.tagName !== 'BUTTON') return;

  if (isLoading) {
    if (!btn.dataset.originalHtml) {
      btn.dataset.originalHtml = btn.innerHTML;
    }
    btn.disabled = true;
    btn.classList.add('btn-loading');
    btn.innerHTML = `<span class="btn-spinner"></span><span>${loadingText}</span>`;
  } else {
    if (btn.dataset.originalHtml) {
      btn.innerHTML = btn.dataset.originalHtml;
      delete btn.dataset.originalHtml;
    }
    btn.disabled = false;
    btn.classList.remove('btn-loading');
  }
}

// Mantém um botão em "Carregando..." por um breve instante em ações síncronas (copiar/exportar).
function flashButtonLoading(btn, durationMs = 350) {
  setButtonLoading(btn, true);
  setTimeout(() => setButtonLoading(btn, false), durationMs);
}

function setInteractiveSelectsDisabled(disabled) {
  REQUEST_TRIGGER_SELECT_IDS.forEach(id => {
    const el = document.getElementById(id);
    if (el) el.disabled = disabled;
  });
}

// Botões afetados por uma requisição: o principal da ação e, se diferente, o que foi clicado.
function getRequestButtons(acao, triggerBtn) {
  const primaryBtn = document.getElementById(ACTION_BUTTON_MAP[acao]);
  const buttons = primaryBtn ? [primaryBtn] : [];
  if (triggerBtn && triggerBtn !== primaryBtn) buttons.push(triggerBtn);
  return buttons;
}

function waitForNextPaint() {
  return new Promise(resolve => requestAnimationFrame(() => requestAnimationFrame(resolve)));
}

async function callBackendAPI(payload, triggerBtn = null) {
  const buttons = getRequestButtons(payload.acao, triggerBtn);

  setBackendStatus('loading');
  buttons.forEach(btn => setButtonLoading(btn, true));
  setInteractiveSelectsDisabled(true);

  // Garante a pintura imediata do estado "Carregando..." antes da requisição
  await waitForNextPaint();

  try {
    const resp = await fetch(API_URL, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    });
    const json = await resp.json();
    setBackendStatus('idle');
    if (json.dados) {
      BACKEND_STATE = json.dados;
      sessionState.pathClearedManually = false;
      rebuildGraphIndexCache();
      applyBackendStateToDOM();
    }
    return json;
  } catch (err) {
    setBackendStatus('error');
    return { ok: false, erro: String(err) };
  } finally {
    buttons.forEach(btn => setButtonLoading(btn, false));
    setInteractiveSelectsDisabled(false);
  }
}
