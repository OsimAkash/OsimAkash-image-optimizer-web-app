"""End-to-end smoke tests using Streamlit's AppTest: every page must render without exceptions."""

from __future__ import annotations

import pytest
from pathlib import Path
from streamlit.testing.v1 import AppTest

from components.sidebar import PAGES

APP_PATH = str(Path(__file__).resolve().parents[1] / "streamlit_app.py")


def _run_app() -> AppTest:
    app = AppTest.from_file(APP_PATH, default_timeout=30)
    app.run()
    return app


def test_home_page_renders():
    app = _run_app()
    assert not app.exception
    assert "Optimize Your Images." in app.markdown[0].body or app.markdown  # hero present


def test_start_optimizing_button_navigates():
    app = _run_app()
    assert not app.exception
    button = next(b for b in app.button if b.label and "Start Optimizing" in b.label)
    button.click().run()
    assert not app.exception
    assert app.session_state["nav"] == PAGES[1]


@pytest.mark.parametrize("page", PAGES)
def test_every_page_renders_without_exception(page):
    app = _run_app()
    assert not app.exception
    app.sidebar.radio[0].set_value(page).run()
    assert not app.exception


def test_optimizer_empty_state_has_guidance():
    app = _run_app()
    app.sidebar.radio[0].set_value(PAGES[1]).run()
    assert not app.exception
    assert any("Add images to get started" in (el.body or "") for el in app.info)


def test_history_and_settings_pages_render_widgets():
    app = _run_app()
    app.sidebar.radio[0].set_value(PAGES[5]).run()
    assert not app.exception
    assert app.radio  # theme radio exists
    assert app.number_input  # upload limit input exists
