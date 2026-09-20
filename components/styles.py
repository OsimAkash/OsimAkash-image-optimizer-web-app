"""OptiPic design system.

Injects a coherent, SaaS-style CSS layer on top of Streamlit: design tokens,
buttons, cards, upload zone, metrics, sidebar and responsive rules. Two themes
are provided — light (default) and dark.
"""

from __future__ import annotations

from string import Template

import streamlit as st

LIGHT_TOKENS = {
    "bg": "#F5F7FB",
    "surface": "#FFFFFF",
    "surface2": "#FAFBFF",
    "border": "#E4E9F2",
    "border_strong": "#C7D0DE",
    "text": "#0F172A",
    "muted": "#5B6B84",
    "primary": "#6366F1",
    "primary2": "#8B5CF6",
    "primary_soft": "#EEF0FE",
    "primary_shadow": "rgba(99, 102, 241, 0.32)",
    "success": "#10B981",
    "success_soft": "#E7F8F1",
    "danger": "#EF4444",
    "danger_soft": "#FDECEC",
    "warning": "#D97706",
    "shadow_sm": "0 1px 2px rgba(15, 23, 42, 0.05), 0 6px 20px rgba(15, 23, 42, 0.05)",
    "shadow_md": "0 2px 6px rgba(15, 23, 42, 0.06), 0 14px 34px rgba(15, 23, 42, 0.08)",
}

DARK_TOKENS = {
    "bg": "#0B1120",
    "surface": "#131C31",
    "surface2": "#0F1729",
    "border": "#233150",
    "border_strong": "#31456B",
    "text": "#E7ECF6",
    "muted": "#93A4BF",
    "primary": "#818CF8",
    "primary2": "#A78BFA",
    "primary_soft": "rgba(129, 140, 248, 0.14)",
    "primary_shadow": "rgba(99, 102, 241, 0.35)",
    "success": "#34D399",
    "success_soft": "rgba(52, 211, 153, 0.12)",
    "danger": "#F87171",
    "danger_soft": "rgba(248, 113, 113, 0.12)",
    "warning": "#FBBF24",
    "shadow_sm": "0 1px 2px rgba(0, 0, 0, 0.35), 0 6px 20px rgba(0, 0, 0, 0.25)",
    "shadow_md": "0 2px 6px rgba(0, 0, 0, 0.4), 0 14px 34px rgba(0, 0, 0, 0.35)",
}

_CSS_TEMPLATE = Template("""
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');

:root {
  --bg: $bg;
  --surface: $surface;
  --surface2: $surface2;
  --border: $border;
  --border-strong: $border_strong;
  --text: $text;
  --muted: $muted;
  --primary: $primary;
  --primary-2: $primary2;
  --primary-soft: $primary_soft;
  --primary-shadow: $primary_shadow;
  --success: $success;
  --success-soft: $success_soft;
  --danger: $danger;
  --danger-soft: $danger_soft;
  --warning: $warning;
  --shadow-sm: $shadow_sm;
  --shadow-md: $shadow_md;
  --radius: 14px;
  --radius-lg: 18px;
}

/* ---------- Base ---------- */
.stApp {
  background: var(--bg);
  color: var(--text);
  font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
}
.block-container { padding: 1.6rem 1rem 3.5rem; max-width: 1220px; }
h1, h2, h3, h4 { color: var(--text); letter-spacing: -0.02em; font-weight: 700; }
p, span, li { color: var(--text); }
a { color: var(--primary); }
hr { border-color: var(--border); }

#MainMenu, footer, [data-testid="stToolbar"], [data-testid="stDecoration"],
[data-testid="stStatusWidget"] { visibility: hidden; height: 0; }
[data-testid="stHeader"] { background: transparent; }

::-webkit-scrollbar { width: 9px; height: 9px; }
::-webkit-scrollbar-thumb { background: var(--border-strong); border-radius: 99px; }
::-webkit-scrollbar-track { background: transparent; }

/* ---------- Buttons ---------- */
.stApp button[kind="secondary"], .stApp .stButton > button, .stApp .stDownloadButton > button {
  border-radius: 12px;
  border: 1px solid var(--border) !important;
  background-color: var(--surface) !important;
  color: var(--text) !important;
  font-weight: 600;
  font-size: 0.92rem;
  padding: 0.46rem 1.05rem;
  box-shadow: var(--shadow-sm);
  transition: all .16s ease;
}
.stApp button[kind="secondary"]:hover, .stApp .stButton > button:hover {
  border-color: var(--primary) !important;
  color: var(--primary) !important;
  transform: translateY(-1px);
}
.stApp button[kind="primary"], .stApp .stDownloadButton > button[kind="primary"] {
  background-color: var(--primary) !important;
  background-image: linear-gradient(135deg, var(--primary), var(--primary-2)) !important;
  color: #fff !important;
  border: none !important;
  box-shadow: 0 4px 16px var(--primary-shadow);
}
.stApp button[kind="primary"]:hover, .stApp .stDownloadButton > button[kind="primary"]:hover {
  color: #fff !important; filter: brightness(1.06); transform: translateY(-1px);
}

/* ---------- Inputs ---------- */
div[data-baseweb="select"] > div, div[data-baseweb="input"] > div,
div[data-baseweb="textarea"] > div {
  background-color: var(--surface) !important;
  color: var(--text) !important;
  border-color: var(--border) !important;
  border-radius: 10px;
}
div[data-baseweb="select"] input, div[data-baseweb="input"] input,
div[data-baseweb="textarea"] textarea {
  background-color: transparent !important;
  color: var(--text) !important;
  border-color: transparent !important;
}
div[data-baseweb="select"] span { color: var(--text); }
label, .stMarkdown p { color: var(--text); }
label > div[data-testid="stMarkdownContainer"] p { font-weight: 600; font-size: 0.92rem; }

div[role="radiogroup"] { gap: 0.45rem; flex-wrap: wrap; }
div[role="radiogroup"] label[data-baseweb="radio"] {
  border: 1px solid var(--border);
  border-radius: 999px;
  background: var(--surface);
  padding: 7px 16px 7px 12px;
  margin-right: 2px;
  box-shadow: none;
  transition: all .15s ease;
}
div[role="radiogroup"] label[data-baseweb="radio"]:hover { border-color: var(--primary); }
div[role="radiogroup"] label[data-baseweb="radio"]:has(input:checked) {
  border-color: var(--primary);
  background: var(--primary-soft);
}
div[role="radiogroup"] label[data-baseweb="radio"]:has(input:checked) div { color: var(--primary); font-weight: 600; }

[data-testid="stSlider"] [role="slider"] {
  background: var(--primary);
  border: 3px solid var(--surface);
  box-shadow: 0 1px 6px var(--primary-shadow);
}
[data-testid="stSlider"] > div > div > div { background: linear-gradient(90deg, var(--primary), var(--primary-2)); }

/* ---------- Upload zone ---------- */
[data-testid="stFileUploaderDropzone"] {
  border: 2px dashed var(--border-strong);
  border-radius: var(--radius-lg);
  background: var(--surface);
  padding: 2.4rem 1.5rem;
  box-shadow: var(--shadow-sm);
  transition: all .18s ease;
}
[data-testid="stFileUploaderDropzone"]:hover { border-color: var(--primary); background: var(--primary-soft); }
[data-testid="stFileUploaderDropzone"] button {
  background: linear-gradient(135deg, var(--primary), var(--primary-2));
  color: #fff; border: none; border-radius: 999px; font-weight: 600;
  padding: 0.5rem 1.4rem;
}
[data-testid="stFileUploaderDropzone"] button:hover { color: #fff; filter: brightness(1.06); }

/* ---------- Metrics ---------- */
[data-testid="stMetric"] {
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: var(--radius);
  padding: 18px 20px;
  box-shadow: var(--shadow-sm);
}
[data-testid="stMetricLabel"] p { color: var(--muted); font-weight: 600; font-size: 0.82rem; text-transform: uppercase; letter-spacing: 0.05em; }
[data-testid="stMetricValue"] { color: var(--text); font-weight: 800; }

/* ---------- Containers / expanders / alerts ---------- */
[data-testid="stVerticalBlockBorderWrapper"] {
  border: 1px solid var(--border) !important;
  border-radius: var(--radius-lg) !important;
  background: var(--surface);
  box-shadow: var(--shadow-sm);
}
[data-testid="stExpander"] {
  border: 1px solid var(--border);
  border-radius: var(--radius) !important;
  background: var(--surface);
  overflow: hidden;
}
[data-testid="stExpander"] details { border: none !important; background: transparent; }
[data-testid="stExpander"] summary { font-weight: 600; }
[data-testid="stAlert"] { border-radius: 12px; border: 1px solid transparent; }
[data-testid="stAlert"], [data-testid="stAlert"] p { color: var(--text); }
[data-testid="stProgress"] > div { height: 10px; border-radius: 99px; background: var(--primary-soft); }

/* ---------- Images ---------- */
[data-testid="stImage"], [data-testid="stImage"] img, .stImage img {
  border-radius: 12px;
  box-shadow: var(--shadow-sm);
  max-width: 100%;
  height: auto;
}

/* ---------- Sidebar ---------- */
[data-testid="stSidebar"] {
  background: var(--surface2);
  border-right: 1px solid var(--border);
}
[data-testid="stSidebar"] .block-container { padding-top: 1.4rem; }
[data-testid="stSidebar"] div[role="radiogroup"] label {
  width: 100%;
  border-radius: 12px;
  padding: 9px 14px;
  font-size: 0.98rem;
  background: transparent;
  border-color: transparent;
  box-shadow: none;
}
[data-testid="stSidebar"] div[role="radiogroup"] label:hover { background: var(--primary-soft); border-color: transparent; }
[data-testid="stSidebar"] div[role="radiogroup"] label:has(input:checked) {
  background: linear-gradient(135deg, var(--primary), var(--primary-2));
  border-color: transparent;
}
[data-testid="stSidebar"] div[role="radiogroup"] label:has(input:checked) div { color: #fff; font-weight: 600; }

/* ---------- OptiPic custom classes ---------- */
.opt-hero { text-align: center; padding: 3.2rem 1rem 1.6rem; }
.opt-hero-badge {
  display: inline-block; padding: 6px 16px; border-radius: 999px;
  background: var(--primary-soft); color: var(--primary);
  font-weight: 600; font-size: 0.85rem; letter-spacing: 0.04em; margin-bottom: 1.2rem;
}
.opt-hero h1 {
  font-size: clamp(2.1rem, 4.6vw, 3.4rem); line-height: 1.12; font-weight: 800; margin: 0 0 0.9rem;
  background: linear-gradient(120deg, var(--primary), var(--primary-2) 60%, var(--primary));
  -webkit-background-clip: text; background-clip: text; -webkit-text-fill-color: transparent;
}
.opt-hero-sub {
  color: var(--muted); font-size: clamp(1rem, 1.6vw, 1.18rem); max-width: 620px;
  margin: 0 auto 1.8rem; line-height: 1.6;
}
.opt-hero-actions { display: flex; gap: 0.9rem; justify-content: center; flex-wrap: wrap; }

.opt-section-title { font-size: 1.45rem; font-weight: 800; margin: 2.4rem 0 0.3rem; letter-spacing: -0.02em; }
.opt-section-sub { color: var(--muted); margin: 0 0 1.2rem; }

.opt-card {
  background: var(--surface); border: 1px solid var(--border);
  border-radius: var(--radius-lg); padding: 1.25rem; box-shadow: var(--shadow-sm);
}
.opt-feature-icon {
  width: 46px; height: 46px; display: flex; align-items: center; justify-content: center;
  font-size: 1.35rem; border-radius: 13px; margin-bottom: 0.85rem;
  background: linear-gradient(135deg, var(--primary-soft), var(--primary-soft));
  border: 1px solid var(--border);
}
.opt-feature h4 { margin: 0 0 0.4rem; font-size: 1.02rem; }
.opt-feature p { color: var(--muted); font-size: 0.9rem; margin: 0; line-height: 1.55; }

.opt-why-item { display: flex; gap: 0.65rem; align-items: flex-start; padding: 0.5rem 0; }
.opt-why-item .opt-tick {
  min-width: 22px; height: 22px; border-radius: 999px; background: var(--success-soft);
  color: var(--success); display: flex; align-items: center; justify-content: center;
  font-size: 0.78rem; font-weight: 700; margin-top: 2px;
}
.opt-why-item div p { margin: 0; line-height: 1.5; font-size: 0.95rem; }
.opt-why-item div p strong { display: block; }

.opt-step {
  background: var(--surface); border: 1px solid var(--border); border-radius: var(--radius);
  padding: 1rem 1.1rem; box-shadow: var(--shadow-sm); height: 100%;
}
.opt-step-num {
  display: inline-flex; width: 28px; height: 28px; border-radius: 999px; margin-bottom: 0.6rem;
  background: linear-gradient(135deg, var(--primary), var(--primary-2));
  color: #fff; font-weight: 700; font-size: 0.85rem; align-items: center; justify-content: center;
}
.opt-step p { margin: 0; color: var(--muted); font-size: 0.87rem; line-height: 1.5; }
.opt-step strong { color: var(--text); font-size: 0.94rem; display: block; margin-bottom: 0.15rem; }

.opt-pill {
  display: inline-block; padding: 3px 11px; border-radius: 999px; font-size: 0.74rem;
  font-weight: 700; letter-spacing: 0.03em; margin-right: 6px; margin-bottom: 4px;
  background: var(--primary-soft); color: var(--primary);
}
.opt-pill-green { background: var(--success-soft); color: var(--success); }
.opt-pill-muted { background: transparent; color: var(--muted); border: 1px solid var(--border); }

.opt-file-name {
  font-weight: 700; font-size: 0.92rem; margin: 0.55rem 0 0.15rem;
  white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
}
.opt-meta-line { color: var(--muted); font-size: 0.8rem; margin: 0.15rem 0 0.65rem; }

.opt-ba { display: flex; align-items: stretch; gap: 0.8rem; }
.opt-ba-side { flex: 1; min-width: 0; }
.opt-ba-side .opt-caption { color: var(--muted); font-size: 0.8rem; line-height: 1.5; }
.opt-ba-side .opt-caption strong { color: var(--text); display: block; font-size: 0.85rem; }
.opt-ba-mid {
  display: flex; flex-direction: column; align-items: center; justify-content: center; gap: 0.3rem; min-width: 96px;
}
.opt-ba-arrow { font-size: 1.3rem; color: var(--muted); line-height: 1; }
.opt-saved-badge {
  display: inline-block; padding: 6px 12px; border-radius: 999px; font-weight: 800; font-size: 0.85rem;
  background: var(--success-soft); color: var(--success); white-space: nowrap;
}

.opt-rec { padding: 0.55rem 0.8rem; border-left: 3px solid var(--primary); background: var(--primary-soft); border-radius: 8px; margin-bottom: 0.5rem; }
.opt-rec strong { font-size: 0.88rem; display: block; }
.opt-rec span { color: var(--muted); font-size: 0.8rem; }

.opt-footer {
  margin-top: 3.2rem; padding-top: 1.2rem; border-top: 1px solid var(--border);
  color: var(--muted); font-size: 0.85rem; display: flex; justify-content: space-between; flex-wrap: wrap; gap: 0.5rem;
}
.opt-brand h2 { margin: 0.35rem 0 0; font-size: 1.35rem; }
.opt-brand p { color: var(--muted); font-size: 0.8rem; margin: 0.1rem 0 0; }
.opt-brand-mark {
  width: 54px; height: 54px; border-radius: 14px; box-shadow: var(--shadow-sm);
  border: 1px solid var(--border);
}

@media (max-width: 640px) {
  .opt-hero { padding-top: 2rem; }
  .opt-ba { flex-direction: column; }
  .opt-ba-mid { flex-direction: row; min-width: 0; }
  .block-container { padding: 1rem 0.7rem 3rem; }
}
""")


def render_theme(theme: str = "Light") -> None:
    """Inject the full design-system stylesheet for the given theme."""
    tokens = DARK_TOKENS if theme == "Dark" else LIGHT_TOKENS
    css = _CSS_TEMPLATE.safe_substitute(tokens)
    if theme == "Dark":
        # Override Streamlit's own theme variables at every root they may be
        # defined on, so native widgets follow the dark palette.
        css += """
        html, body, .stApp, [data-testid="stAppViewContainer"],
        [data-testid="stSidebar"], section.main, [data-testid="stMain"] {
          --background-color: #0B1120;
          --secondary-background-color: #131C31;
          --primary-color: #818CF8;
          --text-color: #E7ECF6;
        }
        .stApp div[data-baseweb="select"] > div,
        .stApp div[data-baseweb="input"] > div,
        .stApp div[data-baseweb="textarea"] > div,
        .stApp input, .stApp textarea {
          background-color: var(--surface) !important;
          color: var(--text) !important;
        }
        """
    st.markdown(f"<style>{css}</style>", unsafe_allow_html=True)


def pills(*labels: str) -> str:
    """Render small colored pills as an HTML snippet."""
    return "".join(f'<span class="opt-pill">{label}</span>' for label in labels)
