"""Settings page: appearance, upload limits, defaults, privacy policy and data controls."""

from __future__ import annotations

import streamlit as st

from utils.file_utils import save_history


def render() -> None:
    st.markdown(
        "<div class='opt-section-title' style='margin-top:0.2rem'>⚙️ Settings</div>"
        "<div class='opt-section-sub'>Configure limits, appearance and data handling. "
        "Everything is stored for this session only.</div>",
        unsafe_allow_html=True,
    )

    left_col, right_col = st.columns(2, gap="large")

    with left_col:
        with st.container(border=True):
            st.markdown("### 🎨 Appearance")
            st.radio("Theme", ["Light", "Dark"], key="theme", index=0, horizontal=True,
                     help="Dark mode is applied via the app stylesheet — best effort.")

        with st.container(border=True):
            st.markdown("### 📥 Upload limits")
            st.number_input(
                "Maximum file size (MB)", min_value=1, max_value=200, value=20, key="cfg_max_mb",
                help="Larger files are rejected with a friendly message.",
            )
            st.slider(
                "Maximum image size (megapixels)", min_value=10, max_value=100, value=60,
                key="cfg_max_mp",
                help="Protects against decompression-bomb style images.",
            )
            if st.button("♻️ Clear upload cache", width="stretch"):
                for key in ("opt_cache", "conv_cache", "rz_cache"):
                    st.session_state.pop(key, None)
                st.toast("Upload cache cleared — files will be re-validated.", icon="♻️")

        with st.container(border=True):
            st.markdown("### 🗄️ Data")
            st.checkbox("Persist history between sessions", key="cfg_persist_history", value=True,
                        help="Stores lightweight records (names, sizes, dates) in data/history.json — never images.")
            if st.button("🗑️ Clear ALL session data", width="stretch"):
                for key in ("uploads", "conv_uploads", "rz_uploads", "opt_results",
                            "conv_results", "rz_results", "history", "stats",
                            "opt_cache", "conv_cache", "rz_cache"):
                    st.session_state.pop(key, None)
                save_history([])
                st.toast("All session data cleared.", icon="🗑️")
                st.rerun()

    with right_col:
        with st.container(border=True):
            st.markdown("### 🔒 Privacy")
            st.markdown(
                "**Your images are processed temporarily and are not intended for permanent storage.**"
            )
            st.markdown(
                "- Uploaded images are held in the application's memory (session state) only while "
                "you work with them.\n"
                "- Optimized results live in memory until you download them or close the session.\n"
                "- History records contain filenames, dates and file sizes — never image data.\n"
                "- Nothing is uploaded to third-party services by OptiPic.\n\n"
                "ℹ️ OptiPic is a Python (Streamlit) application, so processing happens on the "
                "machine running the server — this is *not* browser-only processing."
            )

        with st.container(border=True):
            st.markdown("### ℹ️ About OptiPic")
            st.markdown(
                "**OptiPic — Smart Image Optimizer**  \n"
                "*Smaller Images. Faster Web.*"
            )
            st.caption(
                "Built with Python 3.11+, Streamlit, Pillow and NumPy. "
                "A portfolio-grade demonstration of a complete image-optimization product."
            )
