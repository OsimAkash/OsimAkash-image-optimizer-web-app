"""History page: session statistics, persisted lightweight history and a chart."""

from __future__ import annotations

import streamlit as st

from utils.file_utils import format_bytes, save_history


def render() -> None:
    st.markdown(
        "<div class='opt-section-title' style='margin-top:0.2rem'>🕘 History & Statistics</div>"
        "<div class='opt-section-sub'>Lightweight records only — filenames and numbers, never image data.</div>",
        unsafe_allow_html=True,
    )

    stats: dict = st.session_state.get("stats", {})
    saved_bytes = max(stats.get("original_bytes", 0) - stats.get("optimized_bytes", 0), 0)
    avg_compression = (
        (1 - stats.get("optimized_bytes", 0) / stats["original_bytes"]) * 100
        if stats.get("original_bytes") else 0.0
    )

    st.markdown("### 📊 Session statistics")
    cols = st.columns(4)
    cols[0].metric("Images processed", stats.get("processed", 0))
    cols[1].metric("Total original size", format_bytes(stats.get("original_bytes", 0)))
    cols[2].metric("Total optimized size", format_bytes(stats.get("optimized_bytes", 0)))
    cols[3].metric("Total space saved", format_bytes(saved_bytes), delta=f"{avg_compression:.1f}%",
                   delta_color="off")
    cols2 = st.columns(4)
    cols2[0].metric("Average compression", f"{avg_compression:.1f}%")
    cols2[1].metric("Successful files", stats.get("succeeded", 0))
    cols2[2].metric("Failed files", stats.get("failed", 0))
    cols2[3].metric("Total processing time", f"{stats.get('time_seconds', 0.0):.2f} s")

    history: list[dict] = st.session_state.get("history", [])
    if not history:
        st.info("No history yet — optimize some images and they will be logged here.")
        return

    st.markdown("### 📈 Savings per image")
    successful = [r for r in history if r.get("status") == "success"][:20]
    if successful:
        import pandas as pd
        chart_data = pd.DataFrame({
            r["filename"][:28]: [r.get("saved_percent", 0.0)] for r in reversed(successful)
        }).T
        chart_data.columns = ["Saved %"]
        st.bar_chart(chart_data)
        st.caption("Latest 20 successful optimizations (oldest to newest, left to right).")

    st.markdown("### 🗂️ Optimization history")
    frame = st.session_state.get("history", [])
    import pandas as pd
    table = pd.DataFrame([
        {
            "Filename": r.get("filename", ""),
            "Date / time": r.get("timestamp", ""),
            "Original size": format_bytes(r.get("original_size", 0)),
            "Optimized size": format_bytes(r.get("optimized_size", 0)),
            "Saved": f"{r.get('saved_percent', 0.0):.2f}%",
            "Output format": r.get("output_format", ""),
            "Status": "✅ Success" if r.get("status") == "success" else f"❌ {r.get('error', 'Failed')}",
        }
        for r in frame
    ])
    st.dataframe(table, hide_index=True)

    action_cols = st.columns([1, 1, 3])
    if action_cols[0].button("🧹 Clear History", width="stretch"):
        st.session_state["history"] = []
        if st.session_state.get("cfg_persist_history", True):
            save_history([])
        st.rerun()
    if st.session_state.get("cfg_persist_history", True):
        action_cols[1].download_button(
            "⬇ Export JSON", data="\n".join(
                f"{r.get('timestamp','')}, {r.get('filename','')}, {r.get('saved_percent',0):.1f}%"
                for r in frame
            ),
            file_name="optipic-history.txt", mime="text/plain", width="stretch",
        )
    st.caption("History is stored locally on this machine only — original images are never saved.")
