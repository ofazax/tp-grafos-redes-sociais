"""Entrada da interface. Rode da raiz do repositório: streamlit run app.py"""

from __future__ import annotations

import streamlit as st

from interface.servico_backend import iniciar_servidor_api_local, obter_sessao_backend
from interface.telas import renderizar_aplicacao_fiel_figma
from interface.tema import aplicar_tema_css

st.set_page_config(
    page_title="GrafoSocial | Análise de Grafos e Redes Sociais",
    page_icon="🕸️",
    layout="wide",
    initial_sidebar_state="collapsed",
)


def main() -> None:
    """Inicializa o servidor de API do backend `redes`, aplica o tema e renderiza a interface."""
    iniciar_servidor_api_local()
    obter_sessao_backend()
    aplicar_tema_css()
    renderizar_aplicacao_fiel_figma()


if __name__ == "__main__":
    main()
