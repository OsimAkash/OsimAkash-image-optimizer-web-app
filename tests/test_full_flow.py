"""Full-flow integration test: inject a validated image into the session, run the
Optimize batch through the real UI callbacks, and verify results, history and ZIP."""

from __future__ import annotations

from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

from components.sidebar import PAGES
from core.analyzer import UploadedImage, analyze_image, make_thumbnail

APP_PATH = str(Path(__file__).resolve().parents[1] / "streamlit_app.py")
SAMPLE = Path(__file__).resolve().parents[1] / "assets" / "sample-photo.jpg"


def _sample_upload() -> UploadedImage:
    data = SAMPLE.read_bytes()
    return UploadedImage(
        id="test-image-1",
        filename="sample-photo.jpg",
        data=data,
        thumb=make_thumbnail(data),
        info=analyze_image(data, filename="sample-photo.jpg"),
    )


def _app_on_optimizer_page() -> AppTest:
    app = AppTest.from_file(APP_PATH, default_timeout=60)
    app.run()
    app.sidebar.radio[0].set_value(PAGES[1]).run()
    return app


def test_optimizer_batch_end_to_end():
    app = _app_on_optimizer_page()
    assert not app.exception

    app.session_state["uploads"] = [_sample_upload()]
    app.run()
    assert not app.exception

    optimize_button = next(b for b in app.button if b.label and "Optimize 1 image" in b.label)
    optimize_button.click().run()
    assert not app.exception

    results = app.session_state["opt_results"]
    assert "test-image-1" in results
    result = results["test-image-1"]
    assert result.status == "success"
    assert result.output_format in ("JPEG", "WebP", "PNG")
    assert result.optimized_size > 0

    # history recorded with real numbers
    history = app.session_state["history"]
    assert history and history[0]["filename"] == "sample-photo.jpg"
    assert history[0]["status"] == "success"

    # dashboard rendered with the ZIP download present
    download_labels = [d.label for d in app.download_button]
    assert any("Download All" in label for label in download_labels)
    assert any(label == "⬇ Download" for label in download_labels)

    # cumulative session stats were updated from real sizes
    stats = app.session_state["stats"]
    assert stats["processed"] == 1
    assert stats["succeeded"] == 1
    assert stats["original_bytes"] == result.original_size
    assert stats["optimized_bytes"] == result.optimized_size


def test_reoptimizing_same_image_does_not_double_count():
    app = _app_on_optimizer_page()
    app.session_state["uploads"] = [_sample_upload()]
    app.run()

    for _ in range(2):
        button = next(b for b in app.button if b.label and "Optimize 1 image" in b.label)
        button.click().run()

    stats = app.session_state["stats"]
    assert stats["processed"] == 1  # replaced, not accumulated
