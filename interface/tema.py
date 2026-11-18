"""Tema visual, paleta de cores e configuração de tela cheia para o Streamlit."""

from __future__ import annotations

import html

PALETA: dict[str, str] = {
    "offwhite": "#FCFFF5",
    "sage": "#D1DBBD",
    "sage_light": "#EEF3E2",
    "sage_soft": "#E4ECD0",
    "mutedgreen": "#91AA9D",
    "petrol": "#3E606F",
    "deepnavy": "#193441",
    "code_bg": "#0F222B",
    "sucesso_bg": "#DCFCE7",
    "sucesso_bd": "#22C55E",
    "sucesso_fg": "#15803D",
    "erro_bg": "#FEE2E2",
    "erro_bd": "#EF4444",
    "erro_fg": "#B91C1C",
    "semente": "#FACC15",
}

CORES_COMUNIDADES: list[str] = [
    "#38BDF8",
    "#22C55E",
    "#F59E0B",
    "#A855F7",
    "#EC4899",
]


def esc(texto: object) -> str:
    """Escapa texto para uso seguro em atributos e blocos HTML."""
    return html.escape(str(texto), quote=True)


def aplicar_tema_css() -> None:
    """Remove o chrome padrão do Streamlit para exibir a interface em tela cheia."""
    import streamlit as st

    st.markdown(
        """
        <style>
        header[data-testid="stHeader"],
        [data-testid="stToolbar"],
        [data-testid="stDecoration"],
        [data-testid="stStatusWidget"],
        section[data-testid="stSidebar"],
        [data-testid="collapsedControl"],
        footer {
            display: none !important;
        }

        html, body, .stApp, [data-testid="stAppViewContainer"], [data-testid="stMain"] {
            margin: 0 !important;
            padding: 0 !important;
            width: 100vw !important;
            height: 100vh !important;
            overflow: hidden !important;
            background-color: #193441 !important;
        }

        .block-container, [data-testid="stMainBlockContainer"] {
            padding: 0 !important;
            margin: 0 !important;
            max-width: 100vw !important;
            width: 100vw !important;
            height: 100vh !important;
        }

        div[data-testid="stVerticalBlock"],
        div.element-container,
        [data-testid="stCustomComponentV1"] {
            margin: 0 !important;
            padding: 0 !important;
            width: 100vw !important;
            height: 100vh !important;
        }

        iframe {
            width: 100vw !important;
            height: 100vh !important;
            min-height: 100vh !important;
            border: none !important;
            display: block !important;
            margin: 0 !important;
            padding: 0 !important;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )
