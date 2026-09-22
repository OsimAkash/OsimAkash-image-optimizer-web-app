from __future__ import annotations

import streamlit as st

# Streamlit ASGI app wrapper (safe fallback if st.App is not available)
app = getattr(st, "App", lambda *args, **kwargs: None)("streamlit_app.py") if hasattr(st, "App") else None

