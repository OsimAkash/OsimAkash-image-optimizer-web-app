"""Home / landing page: hero, feature cards, why-section, workflow and privacy strip."""

from __future__ import annotations

import streamlit as st

from components.sidebar import TAGLINE, go_to
from utils.file_utils import format_bytes

FEATURES = [
    ("🗜️", "Smart Compression", "Intelligent quality selection per image — strong savings with visually lossless results."),
    ("📦", "Bulk Optimization", "Drop dozens of images at once and optimize everything in a single click."),
    ("🔄", "Format Conversion", "Convert between JPEG, PNG, WebP, BMP and TIFF with transparency-safe handling."),
    ("📐", "Image Resizing", "Scale by width, height or percentage with high-quality LANCZOS resampling."),
    ("🔍", "Quality Analysis", "Every result reports real sizes, dimensions, timing and measured savings."),
    ("🔒", "Privacy First", "Images are processed temporarily in memory and never permanently stored."),
]

WHY_POINTS = [
    ("Smaller file sizes", "Cut image weight by 60–90% without visibly changing quality."),
    ("Faster websites", "Lighter images mean quicker page loads and better Core Web Vitals."),
    ("Better storage efficiency", "Reclaim disk space across galleries, backups and media libraries."),
    ("Easy format conversion", "One click to move between JPEG, PNG and WebP."),
    ("Bulk optimization", "Process a whole folder's worth of images in one pass."),
    ("Simple workflow", "Upload → preset → optimize → download. No accounts, no friction."),
]


def render() -> None:
    st.markdown(
        """
        <div class="opt-hero">
          <div class="opt-hero-badge">✨ SMART IMAGE OPTIMIZER</div>
          <h1>Optimize Your Images.<br>Keep the Quality.</h1>
          <p class="opt-hero-sub">Compress, resize and convert images with powerful optimization
          tools built for speed and quality.</p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    primary_col, secondary_col = st.columns(2, gap="small")
    with primary_col:
        st.button("🚀 Start Optimizing", type="primary", width="stretch",
                  on_click=go_to, args=("🗜️ Image Optimizer",))
    with secondary_col:
        st.button("🧭 Explore Tools", width="stretch",
                  on_click=go_to, args=("🔄 Image Converter",))

    stats = st.session_state.get("stats", {})
    if stats.get("processed", 0):
        saved = max(stats.get("original_bytes", 0) - stats.get("optimized_bytes", 0), 0)
        kpi_cols = st.columns(3)
        kpi_cols[0].metric("Images processed this session", stats["processed"])
        kpi_cols[1].metric("Space saved this session", format_bytes(saved))
        avg = (1 - stats.get("optimized_bytes", 0) / stats.get("original_bytes", 1)) * 100 if stats.get("original_bytes") else 0
        kpi_cols[2].metric("Average compression", f"{avg:.1f}%")

    st.markdown("<div class='opt-section-title'>Everything you need</div>"
                "<div class='opt-section-sub'>Six tools that cover the full image-optimization workflow.</div>",
                unsafe_allow_html=True)
    for row_start in range(0, len(FEATURES), 3):
        cols = st.columns(3, gap="medium")
        for col, (icon, title, body) in zip(cols, FEATURES[row_start:row_start + 3]):
            with col:
                st.markdown(
                    f"<div class='opt-feature'><div class='opt-feature-icon'>{icon}</div>"
                    f"<h4>{title}</h4><p>{body}</p></div>",
                    unsafe_allow_html=True,
                )

    st.markdown("<div class='opt-section-title'>Why use OptiPic?</div>"
                "<div class='opt-section-sub'>Because images are usually the heaviest part of any website.</div>",
                unsafe_allow_html=True)
    why_left, why_right = st.columns([1.35, 1], gap="large")
    with why_left:
        for title, body in WHY_POINTS:
            st.markdown(
                f"<div class='opt-why-item'><div class='opt-tick'>✓</div>"
                f"<div><p><strong>{title}</strong>{body}</p></div></div>",
                unsafe_allow_html=True,
            )
    with why_right:
        with st.container(border=True):
            st.markdown(f"### {TAGLINE}")
            st.markdown(
                "OptiPic runs a real optimization engine built on Pillow: format-aware "
                "encoding, LANCZOS resizing, metadata stripping and transparent handling "
                "of alpha channels."
            )
            st.caption("Every percentage you see is calculated from the actual bytes before and after processing.")
            if st.button("Try it now — it's instant", key="home_try", width="stretch"):
                go_to("🗜️ Image Optimizer")
                st.rerun()

    st.markdown("<div class='opt-section-title'>How it works</div>"
                "<div class='opt-section-sub'>From upload to optimized ZIP in under a minute.</div>",
                unsafe_allow_html=True)
    steps_cols = st.columns(4, gap="medium")
    steps = [
        ("Upload", "Drag & drop JPG, PNG, WebP, BMP or TIFF files."),
        ("Tune", "Pick a preset or adjust quality, format and resize."),
        ("Optimize", "The engine compresses everything with live progress."),
        ("Download", "Grab single files or the whole batch as a ZIP."),
    ]
    for col, (index, (title, body)) in zip(steps_cols, enumerate(steps, start=1)):
        with col:
            st.markdown(f"<div class='opt-step'><span class='opt-step-num'>{index}</span>"
                        f"<strong>{title}</strong><p>{body}</p></div>", unsafe_allow_html=True)

    with st.container(border=True):
        privacy_cols = st.columns([0.08, 0.92])
        privacy_cols[0].markdown("### 🔒")
        privacy_cols[1].markdown(
            "**Privacy first.** Your images are processed temporarily and are not intended for "
            "permanent storage — optimized files live in memory until you download them."
        )

    st.markdown(
        f"<div class='opt-footer'><span><strong>OptiPic</strong> — {TAGLINE}</span>"
        f"<span>Built with Python · Streamlit · Pillow</span></div>",
        unsafe_allow_html=True,
    )
