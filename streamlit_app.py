"""OptiPic — Smart Image Optimizer.

Streamlit entry point: session bootstrap, theming, sidebar navigation and page
routing. All image processing lives in :mod:`core`, all reusable UI in
:mod:`components`, and every page in :mod:`views`.

Run with:  streamlit run streamlit_app.py
"""

from __future__ import annotations

import logging

import streamlit as st

# Importing the engine installs Pillow's decompression-bomb guard before anything else.
import core.optimizer  # noqa: F401  (sets Image.MAX_IMAGE_PIXELS)
from components.sidebar import PAGES, LOGO_PATH, render_sidebar
from components.styles import render_theme
from utils.file_utils import load_history
from views import converter, history, home, resizer
from views import optimizer as optimizer_view
from views import settings as settings_view

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-7s | %(name)s | %(message)s",
)
logger = logging.getLogger("optipic")

st.set_page_config(
    page_title="OptiPic — Smart Image Optimizer",
    page_icon=str(LOGO_PATH) if LOGO_PATH.exists() else "🖼️",
    layout="wide",
    initial_sidebar_state="expanded",
)


def init_session_state() -> None:
    """Create every session key once — no scattered mutable globals."""
    defaults: dict = {
        # uploads per tool
        "uploads": [], "conv_uploads": [], "rz_uploads": [],
        # per-tool validation caches (upload id -> UploadedImage or error tuple)
        "opt_cache": {}, "conv_cache": {}, "rz_cache": {},
        # preview toggles
        "opt_previews": set(), "conv_previews": set(), "rz_previews": set(),
        # results per tool (image id -> result)
        "opt_results": {}, "conv_results": {}, "rz_results": {},
        # cumulative statistics + lightweight history
        "stats": {
            "processed": 0, "succeeded": 0, "failed": 0,
            "original_bytes": 0, "optimized_bytes": 0, "time_seconds": 0.0,
        },
        "history": [],
        # per-page UI flags (not widget-bound)
        "show_estimates": False,
        # NOTE: widget-bound keys (opt_*, conv_*, rz_*, cfg_*, theme) are deliberately
        # NOT seeded here. Streamlit ignores API-seeded values for widgets first
        # created after the browser has sent widget-state messages (e.g. after a
        # navigation click), which made defaults silently revert. Instead every
        # widget declares its own default via value=/index=, and presets change
        # values through on_click callbacks — the documented mechanism.
    }
    for key, value in defaults.items():
        st.session_state.setdefault(key, value)

    if st.session_state.get("cfg_persist_history", True) and not st.session_state["history"]:
        st.session_state["history"] = load_history()


def route_page(page: str) -> None:
    """Dispatch the selected navigation entry to its view."""
    if page == PAGES[0]:
        home.render()
    elif page == PAGES[1]:
        optimizer_view.render()
    elif page == PAGES[2]:
        converter.render()
    elif page == PAGES[3]:
        resizer.render()
    elif page == PAGES[4]:
        history.render()
    else:
        settings_view.render()


def main() -> None:
    init_session_state()
    render_theme(st.session_state.get("theme", "Light"))
    page = render_sidebar()
    route_page(page)
    logger.debug("Rendered page: %s", page)


if __name__ == "__main__":
    main()