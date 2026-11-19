"""Renderizador da interface conectada ao backend real (`redes`) com mapas interativos de grafos.

A tela é composta por arquivos estáticos em ``interface/web``:

* ``index.html``  — marcação da página (layout fiel ao protótipo do Figma);
* ``estilos.css`` — estilos complementares ao Tailwind;
* ``js/*.js``     — módulos do front-end, concatenados na ordem de ``MODULOS_JS``.

Como o ``components.html`` do Streamlit não serve arquivos locais, os recursos são lidos
e embutidos em um único documento HTML no momento da renderização.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from interface.servico_backend import iniciar_servidor_api_local, obter_sessao_backend

DIRETORIO_WEB = Path(__file__).resolve().parent / "web"

# Ordem importa: `estado.js` declara as constantes globais usadas pelos demais módulos.
MODULOS_JS: tuple[str, ...] = (
    "estado.js",
    "api.js",
    "interface_dom.js",
    "navegacao.js",
    "obter_grafo.js",
    "mapa_camera.js",
    "mapa_renderizacao.js",
    "mapa_eventos.js",
    "acoes_analise.js",
    "inicializacao.js",
)

MARCADOR_CSS = "/*__ESTILOS_CSS__*/"
MARCADOR_JS = "/*__SCRIPTS_JS__*/"
MARCADOR_API_URL = "__API_URL__"
MARCADOR_PAYLOAD = "__PAYLOAD_JSON__"

ALTURA_COMPONENTE_PX = 960


def _ler_recurso_web(caminho_relativo: str) -> str:
    """Lê um arquivo estático de ``interface/web`` (sem cache, para refletir edições a cada rerun)."""
    return (DIRETORIO_WEB / caminho_relativo).read_text(encoding="utf-8")


def _montar_scripts() -> str:
    """Concatena os módulos JS na ordem de dependência, identificando cada um."""
    partes = [f"// ===== {nome} =====\n{_ler_recurso_web(f'js/{nome}')}" for nome in MODULOS_JS]
    return "\n".join(partes)


def _serializar_payload(payload: dict[str, Any]) -> str:
    """Serializa o estado inicial para ser embutido com segurança dentro de ``<script>``."""
    return json.dumps(payload, ensure_ascii=False).replace("</", "<\\/")


def construir_html_aplicacao_figma() -> str:
    """Constrói o documento HTML/CSS/Canvas integrado ao servidor HTTP local do backend."""
    api_url = iniciar_servidor_api_local()
    sessao = obter_sessao_backend()
    with sessao.lock:
        payload_inicial = sessao.obter_payload_completo()

    html = (
        _ler_recurso_web("index.html")
        .replace(MARCADOR_CSS, _ler_recurso_web("estilos.css"))
        .replace(MARCADOR_JS, _montar_scripts())
        .replace(MARCADOR_API_URL, api_url)
    )
    # O payload é inserido por último para que seu conteúdo nunca seja reinterpretado como marcador.
    return html.replace(MARCADOR_PAYLOAD, _serializar_payload(payload_inicial), 1)


def renderizar_aplicacao_fiel_figma() -> None:
    """Renderiza a aplicação completa em tela cheia conectada ao backend `redes`."""
    import streamlit.components.v1 as components

    components.html(construir_html_aplicacao_figma(), height=ALTURA_COMPONENTE_PX, scrolling=False)
