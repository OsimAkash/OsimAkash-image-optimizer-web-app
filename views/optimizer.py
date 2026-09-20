"""Image Optimizer page: upload → preview → settings → batch process → results."""

from __future__ import annotations

import streamlit as st

from components.results import record_result, render_dashboard
from components.settings import (build_settings_from_state, estimate_note,
                                 render_estimates_section, render_settings_panel)
from components.upload import render_image_grid, render_uploader
from core.optimizer import OptimizationResult, optimize_image, recommend_settings


def _on_remove(image_id: str) -> None:
    """Card callback: drop the image, its preview flag and any stored result."""
    uploads: list = st.session_state.get("uploads", [])
    st.session_state["uploads"] = [u for u in uploads if u.id != image_id]
    st.session_state.get("opt_previews", set()).discard(image_id)
    st.session_state.get("opt_results", {}).pop(image_id, None)


def _on_optimize_single(image_id: str) -> None:
    """Card callback: optimize just this image with the current (or smart) settings."""
    uploads: list = st.session_state.get("uploads", [])
    upload = next((u for u in uploads if u.id == image_id), None)
    if upload is None:
        return
    if st.session_state.get("smart", False):
        settings, _ = recommend_settings(upload.info)
    else:
        settings = build_settings_from_state()
    result = optimize_image(upload.data, settings, filename=upload.filename, image_id=upload.id)
    record_result(result, "opt_results")


def _on_optimize_all() -> None:
    """Run the whole batch; per-image failures never stop the run."""
    uploads: list = st.session_state.get("uploads", [])
    if not uploads:
        return
    smart = st.session_state.get("smart", False)
    fallback_settings = None if smart else build_settings_from_state()

    progress = st.progress(0.0, text="Preparing…")
    status = st.empty()
    results: dict = st.session_state.setdefault("opt_results", {})

    for index, upload in enumerate(uploads, start=1):
        status.markdown(f"**Processing {index} of {len(uploads)} images** — {upload.filename}")
        progress.progress((index - 1) / len(uploads), text=f"Processing {index} of {len(uploads)} images")
        settings = fallback_settings or recommend_settings(upload.info)[0]
        result = optimize_image(upload.data, settings, filename=upload.filename, image_id=upload.id)
        record_result(result, "opt_results")

    succeeded = sum(1 for u in uploads if results.get(u.id) and results[u.id].status == "success")
    failed = len(uploads) - succeeded
    progress.progress(1.0, text=f"✅ Done — {succeeded} succeeded, {failed} failed.")
    status.empty()


def render() -> None:
    cfg_max_mb = int(st.session_state.get("cfg_max_mb", 20))
    cfg_max_mp = int(st.session_state.get("cfg_max_mp", 60))

    uploads = render_uploader(
        cache_key="opt", uploads_key="uploads",
        max_file_mb=cfg_max_mb, max_pixels=cfg_max_mp * 1_000_000,
    )

    # NOTE: the settings panel renders on every visit (even with no uploads yet).
    # Widget keys are seeded at session start; creating the widgets on the first
    # page view — before any upload interaction — guarantees Streamlit binds them.
    render_settings_panel(uploads)

    if not uploads:
        _render_empty_state()
        st.button("🚀 Optimize", type="primary", width="stretch", disabled=True)
        return

    render_image_grid(
        uploads,
        results_key="opt_results",
        previews_key="opt_previews",
        on_remove=_on_remove,
        on_optimize=_on_optimize_single,
    )

    render_estimates_section(uploads)

    results: dict = st.session_state.get("opt_results", {})
    st.markdown(
        "<div class='opt-section-title'>🚀 Ready to optimize</div>"
        "<div class='opt-section-sub'>The current settings are applied to every image.</div>",
        unsafe_allow_html=True,
    )
    st.button(
        f"🚀 Optimize {len(uploads)} image{'s' if len(uploads) != 1 else ''}",
        type="primary", width="stretch", on_click=_on_optimize_all,
    )

    # Keep only results whose source image is still in the session.
    live_ids = {u.id for u in uploads}
    st.session_state["opt_results"] = {k: v for k, v in results.items() if k in live_ids}
    ordered = [st.session_state["opt_results"][u.id] for u in uploads if u.id in st.session_state["opt_results"]]
    render_dashboard(ordered, key_prefix="opt")

    st.caption(estimate_note())


def _render_empty_state() -> None:
    st.info(
        "👆 **Add images to get started.** Drop files above — then pick a preset, tune quality, "
        "choose an output format and optimize. Nothing is stored permanently."
    )
    with st.expander("💡 How the optimizer works"):
        st.markdown(
            "1. **Validate** — every file is checked (extension, MIME, real content, size, dimensions).\n"
            "2. **Smart Optimize (optional)** — the engine inspects format, size, transparency and "
            "content type, then picks ideal settings per image.\n"
            "3. **Process** — images are resized with LANCZOS, converted safely and re-encoded with "
            "format-aware quality settings.\n"
            "4. **Compare & download** — see before/after with real measured savings, then download "
            "single files or the whole batch as `optimized-images.zip`."
        )
