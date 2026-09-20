"""Image Converter page: dedicated one-click format conversion."""

from __future__ import annotations

import streamlit as st

from components.results import record_result, render_dashboard
from components.upload import render_uploader
from core.converter import convert_image

TARGETS = ["JPEG", "PNG", "WEBP"]
LOSSY_TARGETS = {"JPEG", "WEBP"}


def _on_remove(image_id: str) -> None:
    uploads: list = st.session_state.get("conv_uploads", [])
    st.session_state["conv_uploads"] = [u for u in uploads if u.id != image_id]
    st.session_state.get("conv_previews", set()).discard(image_id)
    st.session_state.get("conv_results", {}).pop(image_id, None)


def _on_convert_all() -> None:
    uploads: list = st.session_state.get("conv_uploads", [])
    if not uploads:
        return
    target = st.session_state.get("conv_target", "WEBP").lower()
    quality = int(st.session_state.get("conv_quality", 90)) if target in ("jpeg", "webp") else 90

    progress = st.progress(0.0, text="Preparing…")
    status = st.empty()
    results: dict = st.session_state.setdefault("conv_results", {})

    for index, upload in enumerate(uploads, start=1):
        status.markdown(f"**Converting {index} of {len(uploads)} images** — {upload.filename}")
        progress.progress((index - 1) / len(uploads), text=f"Converting {index} of {len(uploads)} images")
        result = convert_image(upload.data, target, quality, filename=upload.filename)
        result.image_id = upload.id
        record_result(result, "conv_results")

    succeeded = sum(1 for u in uploads if results.get(u.id) and results[u.id].status == "success")
    progress.progress(1.0, text=f"✅ Conversion finished — {succeeded} succeeded, {len(uploads) - succeeded} failed.")
    status.empty()


def _on_convert_single(image_id: str) -> None:
    uploads: list = st.session_state.get("conv_uploads", [])
    upload = next((u for u in uploads if u.id == image_id), None)
    if upload is None:
        return
    target = st.session_state.get("conv_target", "WEBP").lower()
    quality = int(st.session_state.get("conv_quality", 90)) if target in ("jpeg", "webp") else 90
    result = convert_image(upload.data, target, quality, filename=upload.filename)
    result.image_id = upload.id
    record_result(result, "conv_results")


def render() -> None:
    st.markdown(
        "<div class='opt-section-title' style='margin-top:0.2rem'>🔄 Image Converter</div>"
        "<div class='opt-section-sub'>Convert between JPEG, PNG and WebP — with quality control "
        "and transparency-safe handling.</div>",
        unsafe_allow_html=True,
    )

    cfg_max_mb = int(st.session_state.get("cfg_max_mb", 20))
    cfg_max_mp = int(st.session_state.get("cfg_max_mp", 60))
    uploads = render_uploader(
        cache_key="conv", uploads_key="conv_uploads",
        max_file_mb=cfg_max_mb, max_pixels=cfg_max_mp * 1_000_000,
    )

    # Settings widgets render on every visit so their seeded session keys bind
    # before any upload interaction (Streamlit late-creation binding quirk).
    with st.container(border=True):
        st.markdown("### ⚙️ Conversion settings")
        target_col, quality_col = st.columns(2)
        target_col.selectbox("Convert to", TARGETS, index=2, key="conv_target",
                             help="JPEG: smallest photos, no transparency. PNG: lossless + alpha. "
                                  "WEBP: modern, best compression, supports transparency.")
        if st.session_state.get("conv_target") in LOSSY_TARGETS:
            quality_col.slider("Quality (applies to JPEG/WebP)", 10, 100, 90, key="conv_quality")
        else:
            quality_col.caption("PNG is lossless — no quality setting needed.")

        if any(u.has_alpha for u in uploads) and st.session_state.get("conv_target") == "JPEG":
            st.info("ℹ️ Some images contain transparency — transparent areas will be filled with white when converting to JPEG.")

    if not uploads:
        st.info("👆 **Add images above** — JPG, PNG, WEBP, BMP and TIFF inputs are all supported.")
        st.button("🔄 Convert", type="primary", width="stretch", disabled=True)
        return

    from components.upload import render_image_grid
    render_image_grid(
        uploads,
        results_key="conv_results",
        previews_key="conv_previews",
        on_remove=_on_remove,
        on_optimize=_on_convert_single,
        optimize_label="Convert",
    )

    st.button(
        f"🔄 Convert {len(uploads)} image{'s' if len(uploads) != 1 else ''}",
        type="primary", width="stretch", on_click=_on_convert_all,
    )

    live_ids = {u.id for u in uploads}
    results: dict = st.session_state.get("conv_results", {})
    st.session_state["conv_results"] = {k: v for k, v in results.items() if k in live_ids}
    ordered = [st.session_state["conv_results"][u.id] for u in uploads if u.id in st.session_state["conv_results"]]
    render_dashboard(ordered, key_prefix="conv", zip_name="converted-images.zip")
