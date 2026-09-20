"""Results dashboard: aggregate metrics, before/after comparison cards,
failure reporting, per-image downloads and ZIP packaging."""

from __future__ import annotations

import streamlit as st

from core.converter import MIME_TYPES
from utils.file_utils import create_zip, format_bytes, timestamp


def record_result(result, results_key: str) -> None:
    """Store a result in the page's result dict, update session stats + history.

    Re-processing the same image replaces the old record and re-balances the
    cumulative statistics so nothing is ever double-counted.
    """
    results: dict = st.session_state.setdefault(results_key, {})
    stats: dict = st.session_state.setdefault("stats", {
        "processed": 0, "succeeded": 0, "failed": 0,
        "original_bytes": 0, "optimized_bytes": 0, "time_seconds": 0.0,
    })

    def apply(record, sign: int) -> None:
        stats["processed"] += sign * 1
        if record.status == "success":
            stats["succeeded"] += sign * 1
            stats["original_bytes"] += sign * record.original_size
            stats["optimized_bytes"] += sign * record.optimized_size
            stats["time_seconds"] += sign * record.processing_time
        else:
            stats["failed"] += sign * 1

    previous = results.get(result.image_id)
    if previous is not None:
        apply(previous, -1)
    apply(result, +1)
    results[result.image_id] = result

    history: list = st.session_state.setdefault("history", [])
    history.insert(0, {
        "filename": result.original_filename,
        "timestamp": timestamp(),
        "original_size": result.original_size,
        "optimized_size": result.optimized_size,
        "saved_percent": result.saved_percent if result.status == "success" else 0.0,
        "output_format": result.output_format or "—",
        "status": result.status,
        "error": result.error,
    })
    del history[500:]

    if st.session_state.get("cfg_persist_history", True):
        from utils.file_utils import save_history
        save_history(history)


def summarize(results: list) -> dict:
    """Aggregate real numbers across a batch of results."""
    successful = [r for r in results if r.status == "success"]
    failed = [r for r in results if r.status == "failed"]
    original = sum(r.original_size for r in successful)
    optimized = sum(r.optimized_size for r in successful)
    avg_compression = (
        round((1 - optimized / original) * 100, 1) if original else 0.0
    )
    return {
        "total": len(results),
        "succeeded": len(successful),
        "failed": len(failed),
        "original_bytes": original,
        "optimized_bytes": optimized,
        "saved_bytes": max(original - optimized, 0),
        "saved_percent": avg_compression,
        "avg_time": round(sum(r.processing_time for r in successful) / len(successful), 3)
        if successful else 0.0,
    }


def render_dashboard(results: list, *, key_prefix: str, zip_name: str = "optimized-images.zip") -> None:
    """Render the full results dashboard: metrics, failures, before/after, ZIP."""
    if not results:
        return
    summary = summarize(results)

    st.markdown(
        "<div class='opt-section-title'>📊 Results dashboard</div>"
        "<div class='opt-section-sub'>Every number below is measured from the actual files.</div>",
        unsafe_allow_html=True,
    )

    metric_cols = st.columns(4)
    metric_cols[0].metric("Total Images", summary["total"])
    metric_cols[1].metric("Original Size", format_bytes(summary["original_bytes"]))
    metric_cols[2].metric("Optimized Size", format_bytes(summary["optimized_bytes"]))
    metric_cols[3].metric(
        "Space Saved",
        format_bytes(summary["saved_bytes"]),
        delta=f"{summary['saved_percent']}% smaller",
        delta_color="off",
    )

    extra_cols = st.columns(4)
    extra_cols[0].metric("Average Compression", f"{summary['saved_percent']}%")
    extra_cols[1].metric("Avg Processing Time", f"{summary['avg_time'] * 1000:.0f} ms")
    extra_cols[2].metric("Succeeded", summary["succeeded"])
    extra_cols[3].metric("Failed", summary["failed"])

    if summary["failed"]:
        with st.container(border=True):
            st.error(f"{summary['failed']} image(s) failed and were skipped — the rest of the batch was unaffected.")
            for result in results:
                if result.status == "failed":
                    st.markdown(
                        f"<div class='opt-meta-line'>📄 <strong>{result.original_filename}</strong> — "
                        f"{result.error}</div>",
                        unsafe_allow_html=True,
                    )

    successful = [r for r in results if r.status == "success"]
    if not successful:
        return

    zip_bytes = create_zip([(r.output_filename, r.data) for r in successful])
    st.download_button(
        f"⬇ Download All ({len(successful)} images)",
        data=zip_bytes,
        file_name=zip_name,
        mime="application/zip",
        type="primary",
        width="stretch",
        key=f"zip_{key_prefix}",
    )
    st.caption(f"📦 optimized-images.zip — {format_bytes(len(zip_bytes))}, generated on demand in memory.")

    for result in successful:
        render_before_after(result, key_prefix=key_prefix)


def render_before_after(result, *, key_prefix: str) -> None:
    """One before/after comparison card with a real download button."""
    with st.container(border=True):
        original_side, middle, optimized_side = st.columns([1.15, 0.42, 1.15], vertical_alignment="center")

        with original_side:
            st.markdown("**Original**")
            if result.thumb:
                st.image(result.thumb, width="stretch")
            st.markdown(
                f"<div class='opt-caption'><strong>{result.original_filename}</strong>"
                f"{format_bytes(result.original_size)} · {result.original_width} × {result.original_height}"
                f" · {result.original_format}</div>",
                unsafe_allow_html=True,
            )

        with middle:
            saved = result.saved_percent
            st.markdown(f"<div style='text-align:center'><span class='opt-saved-badge'>{saved:.2f}% smaller</span></div>",
                        unsafe_allow_html=True)
            st.markdown("<div class='opt-ba-arrow' style='text-align:center'>⬇</div>", unsafe_allow_html=True)

        with optimized_side:
            st.markdown("**Optimized**")
            if result.thumb:
                st.image(result.thumb, width="stretch")
            st.markdown(
                f"<div class='opt-caption'><strong>{result.output_filename}</strong>"
                f"{format_bytes(result.optimized_size)} · {result.new_width} × {result.new_height}"
                f" · {result.output_format} · quality {result.quality or '—'}</div>",
                unsafe_allow_html=True,
            )

        meta_cols = st.columns([1.4, 1, 1])
        details = []
        if result.background_applied:
            details.append("Transparency flattened for JPEG")
        if result.metadata_removed:
            details.append("Metadata removed for improved privacy")
        if result.note:
            details.append(result.note)
        if details:
            meta_cols[0].caption(" · ".join(details))
        meta_cols[0].caption(f"⚡ Processed in {result.processing_time * 1000:.0f} ms")

        if meta_cols[1].button("🔍 Full preview", key=f"full_{key_prefix}_{result.image_id}"):
            previews: set = st.session_state.setdefault(f"full_{key_prefix}", set())
            previews.symmetric_difference_update({result.image_id})

        if result.image_id in st.session_state.setdefault(f"full_{key_prefix}", set()):
            st.image(result.data, caption="Optimized — full size", width="stretch")

        meta_cols[2].download_button(
            "⬇ Download",
            data=result.data,
            file_name=result.output_filename,
            mime=MIME_TYPES.get(result.output_format.lower(), "application/octet-stream"),
            key=f"dl_{key_prefix}_{result.image_id}",
            width="stretch",
        )
