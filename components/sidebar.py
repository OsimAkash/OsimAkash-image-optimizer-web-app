"""Sidebar: branding, main navigation and quick session stats."""

from __future__ import annotations

from pathlib import Path

import streamlit as st

from utils.file_utils import format_bytes

ASSETS_DIR = Path(__file__).resolve().parent.parent / "assets"
LOGO_PATH = ASSETS_DIR / "logo.png"

PAGES = [
    "🏠 Home",
    "🗜️ Image Optimizer",
    "🔄 Image Converter",
    "📐 Image Resizer",
    "🕘 History",
    "⚙️ Settings",
]

TAGLINE = "Smaller Images. Faster Web."


def go_to(page: str) -> None:
    """Navigation helper usable from button callbacks anywhere."""
    st.session_state["nav"] = page


def render_sidebar() -> str:
    """Render branding + navigation and return the selected page label."""
    with st.sidebar:
        logo_col, text_col = st.columns([0.42, 0.58], vertical_alignment="center")
        with logo_col:
            if LOGO_PATH.exists():
                st.image(str(LOGO_PATH), width=64)
        with text_col:
            st.markdown(
                f"<div class='opt-brand'><h2>OptiPic</h2><p>{TAGLINE}</p></div>",
                unsafe_allow_html=True,
            )

        st.markdown("<div style='height:0.6rem'></div>", unsafe_allow_html=True)
        page = st.radio("Navigation", PAGES, key="nav", label_visibility="collapsed")

        st.markdown("<div style='height:0.8rem'></div>", unsafe_allow_html=True)
        stats = st.session_state.get("stats", {})
        if stats.get("processed", 0):
            st.markdown("**This session**")
            saved = stats.get("original_bytes", 0) - stats.get("optimized_bytes", 0)
            st.caption(
                f"🖼️ {stats.get('processed', 0)} images processed\n\n"
                f"💾 {format_bytes(max(saved, 0))} saved"
            )

        st.markdown("<div style='flex:1'></div>", unsafe_allow_html=True)
        with st.container(border=True):
            st.markdown("🔒 **Privacy**")
            st.caption("Images are processed temporarily and are not stored permanently.")

        st.caption("OptiPic v1.0 · Python + Streamlit")
    return page
