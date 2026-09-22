"""OptiPic design system.

Injects a coherent, SaaS-style CSS layer on top of Streamlit: design tokens,
buttons, cards, upload zone, metrics, sidebar and responsive rules. Two themes
are provided — light (default) and dark.
"""

from __future__ import annotations

from string import Template

import streamlit as st

LIGHT_TOKENS = {
    "bg": "#F8FAFC",
    "surface": "rgba(255, 255, 255, 0.88)",
    "surface2": "rgba(248, 250, 252, 0.92)",
    "border": "rgba(226, 232, 240, 0.85)",
    "border_strong": "rgba(203, 213, 225, 0.95)",
    "text": "#0F172A",
    "muted": "#64748B",
    "primary": "#4F46E5",
    "primary2": "#7C3AED",
    "primary3": "#C026D3",
    "primary_soft": "rgba(79, 70, 229, 0.08)",
    "primary_shadow": "rgba(79, 70, 229, 0.28)",
    "success": "#10B981",
    "success_soft": "rgba(16, 185, 129, 0.12)",
    "danger": "#EF4444",
    "danger_soft": "rgba(239, 68, 68, 0.12)",
    "warning": "#F59E0B",
    "shadow_sm": "0 2px 8px -2px rgba(15, 23, 42, 0.05), 0 1px 3px rgba(15, 23, 42, 0.04)",
    "shadow_md": "0 12px 30px -6px rgba(15, 23, 42, 0.08), 0 4px 12px -2px rgba(15, 23, 42, 0.04)",
}

DARK_TOKENS = {
    "bg": "#0A0F1D",
    "surface": "rgba(17, 24, 39, 0.78)",
    "surface2": "rgba(13, 19, 33, 0.85)",
    "border": "rgba(255, 255, 255, 0.09)",
    "border_strong": "rgba(255, 255, 255, 0.16)",
    "text": "#F8FAFC",
    "muted": "#94A3B8",
    "primary": "#6366F1",
    "primary2": "#8B5CF6",
    "primary3": "#D946EF",
    "primary_soft": "rgba(99, 102, 241, 0.16)",
    "primary_shadow": "rgba(99, 102, 241, 0.40)",
    "success": "#34D399",
    "success_soft": "rgba(52, 211, 153, 0.16)",
    "danger": "#F87171",
    "danger_soft": "rgba(248, 113, 113, 0.16)",
    "warning": "#FBBF24",
    "shadow_sm": "0 2px 8px -2px rgba(0, 0, 0, 0.4), 0 1px 3px rgba(0, 0, 0, 0.3)",
    "shadow_md": "0 14px 34px -6px rgba(0, 0, 0, 0.5), 0 4px 12px -2px rgba(0, 0, 0, 0.35)",
}

_CSS_TEMPLATE = Template("""
@import url('https://fonts.googleapis.com/css2?family=Outfit:wght@500;600;700;800;900&family=Plus+Jakarta+Sans:wght@400;500;600;700;800&display=swap');

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
  --primary-3: $primary3;
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
  --radius-lg: 20px;
}

/* ---------- Base Layout & Mesh Background ---------- */
.stApp {
  background-color: var(--bg);
  background-image: 
    radial-gradient(at 0% 0%, rgba(99, 102, 241, 0.07) 0px, transparent 50%),
    radial-gradient(at 100% 100%, rgba(217, 70, 239, 0.06) 0px, transparent 50%),
    radial-gradient(at 50% 50%, rgba(59, 130, 246, 0.04) 0px, transparent 60%);
  color: var(--text);
  font-family: 'Plus Jakarta Sans', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
  letter-spacing: -0.01em;
}

.block-container {
  padding: 1.8rem 1.2rem 4rem;
  max-width: 1240px;
}

h1, h2, h3, h4, h5, h6 {
  font-family: 'Outfit', 'Plus Jakarta Sans', sans-serif;
  color: var(--text);
  letter-spacing: -0.03em;
  font-weight: 700;
}

p, span, li {
  color: var(--text);
  line-height: 1.6;
}

a {
  color: var(--primary);
  text-decoration: none;
  font-weight: 600;
  transition: all .15s ease;
}
a:hover {
  filter: brightness(1.15);
  text-decoration: underline;
}

hr {
  border: none;
  height: 1px;
  background: linear-gradient(90deg, transparent, var(--border), transparent);
  margin: 1.8rem 0;
}

#MainMenu, footer, [data-testid="stToolbar"], [data-testid="stDecoration"],
[data-testid="stStatusWidget"] {
  visibility: hidden;
  height: 0;
}
[data-testid="stHeader"] {
  background: transparent;
}

::-webkit-scrollbar {
  width: 8px;
  height: 8px;
}
::-webkit-scrollbar-thumb {
  background: var(--border-strong);
  border-radius: 99px;
}
::-webkit-scrollbar-track {
  background: transparent;
}

/* ---------- Buttons & Interactive Elements ---------- */
.stApp button[kind="secondary"], .stApp .stButton > button, .stApp .stDownloadButton > button {
  border-radius: 12px;
  border: 1px solid var(--border) !important;
  background: var(--surface) !important;
  backdrop-filter: blur(12px);
  -webkit-backdrop-filter: blur(12px);
  color: var(--text) !important;
  font-weight: 600;
  font-size: 0.92rem;
  padding: 0.52rem 1.15rem;
  box-shadow: var(--shadow-sm);
  transition: all .2s cubic-bezier(0.16, 1, 0.3, 1);
}

.stApp button[kind="secondary"]:hover, .stApp .stButton > button:hover {
  border-color: var(--primary) !important;
  color: var(--primary) !important;
  transform: translateY(-2px);
  box-shadow: 0 6px 18px -3px var(--primary-shadow);
}

.stApp button[kind="secondary"]:active, .stApp .stButton > button:active {
  transform: translateY(0);
}

.stApp button[kind="primary"], .stApp .stDownloadButton > button[kind="primary"] {
  background: linear-gradient(135deg, var(--primary) 0%, var(--primary-2) 50%, var(--primary-3) 100%) !important;
  color: #FFFFFF !important;
  border: none !important;
  border-radius: 12px;
  font-weight: 700;
  letter-spacing: -0.01em;
  box-shadow: 0 6px 20px -3px var(--primary-shadow);
  transition: all .2s cubic-bezier(0.16, 1, 0.3, 1);
}

.stApp button[kind="primary"]:hover, .stApp .stDownloadButton > button[kind="primary"]:hover {
  color: #FFFFFF !important;
  filter: brightness(1.08);
  transform: translateY(-2px);
  box-shadow: 0 10px 26px -3px var(--primary-shadow);
}

.stApp button[kind="primary"]:active, .stApp .stDownloadButton > button[kind="primary"]:active {
  transform: translateY(0);
}

/* ---------- Inputs, Selects & Sliders ---------- */
div[data-baseweb="select"] > div, div[data-baseweb="input"] > div,
div[data-baseweb="textarea"] > div {
  background: var(--surface) !important;
  backdrop-filter: blur(12px);
  -webkit-backdrop-filter: blur(12px);
  color: var(--text) !important;
  border: 1px solid var(--border) !important;
  border-radius: 12px;
  box-shadow: var(--shadow-sm);
  transition: all .18s ease;
}

div[data-baseweb="select"] > div:hover, div[data-baseweb="input"] > div:hover {
  border-color: var(--primary) !important;
}

div[data-baseweb="select"] input, div[data-baseweb="input"] input,
div[data-baseweb="textarea"] textarea {
  background-color: transparent !important;
  color: var(--text) !important;
  border-color: transparent !important;
  font-family: inherit;
}

div[data-baseweb="select"] span {
  color: var(--text);
}

label, .stMarkdown p {
  color: var(--text);
}

label > div[data-testid="stMarkdownContainer"] p {
  font-weight: 600;
  font-size: 0.92rem;
}

div[role="radiogroup"] {
  gap: 0.5rem;
  flex-wrap: wrap;
}

div[role="radiogroup"] label[data-baseweb="radio"] {
  border: 1px solid var(--border);
  border-radius: 999px;
  background: var(--surface);
  backdrop-filter: blur(10px);
  padding: 8px 18px 8px 14px;
  margin-right: 4px;
  box-shadow: var(--shadow-sm);
  transition: all .18s ease;
}

div[role="radiogroup"] label[data-baseweb="radio"]:hover {
  border-color: var(--primary);
  transform: translateY(-1px);
}

div[role="radiogroup"] label[data-baseweb="radio"]:has(input:checked) {
  border-color: var(--primary);
  background: var(--primary-soft);
  box-shadow: 0 2px 10px var(--primary-shadow);
}

div[role="radiogroup"] label[data-baseweb="radio"]:has(input:checked) div {
  color: var(--primary);
  font-weight: 700;
}

[data-testid="stSlider"] [role="slider"] {
  background: linear-gradient(135deg, var(--primary), var(--primary-2));
  border: 3px solid var(--surface);
  box-shadow: 0 2px 8px var(--primary-shadow);
  width: 20px;
  height: 20px;
}

[data-testid="stSlider"] > div > div > div {
  background: linear-gradient(90deg, var(--primary) 0%, var(--primary-2) 50%, var(--primary-3) 100%);
  border-radius: 99px;
}

/* ---------- Upload Zone ---------- */
[data-testid="stFileUploaderDropzone"] {
  border: 2px dashed var(--border-strong) !important;
  border-radius: var(--radius-lg) !important;
  background: var(--surface) !important;
  backdrop-filter: blur(16px);
  -webkit-backdrop-filter: blur(16px);
  padding: 2.8rem 1.6rem;
  box-shadow: var(--shadow-sm);
  transition: all .22s cubic-bezier(0.16, 1, 0.3, 1);
  text-align: center;
}

[data-testid="stFileUploaderDropzone"]:hover {
  border-color: var(--primary) !important;
  background: var(--primary-soft) !important;
  transform: translateY(-2px);
  box-shadow: 0 8px 24px -4px var(--primary-shadow);
}

[data-testid="stFileUploaderDropzone"] button {
  background: linear-gradient(135deg, var(--primary), var(--primary-2)) !important;
  color: #FFFFFF !important;
  border: none !important;
  border-radius: 999px !important;
  font-weight: 700 !important;
  padding: 0.55rem 1.6rem !important;
  box-shadow: 0 4px 14px var(--primary-shadow);
}

[data-testid="stFileUploaderDropzone"] button:hover {
  color: #FFFFFF !important;
  filter: brightness(1.08);
}

/* ---------- Metrics & KPI Cards ---------- */
[data-testid="stMetric"] {
  background: var(--surface);
  backdrop-filter: blur(16px);
  -webkit-backdrop-filter: blur(16px);
  border: 1px solid var(--border);
  border-radius: var(--radius);
  padding: 18px 22px;
  box-shadow: var(--shadow-sm);
  position: relative;
  overflow: hidden;
  transition: all .2s ease;
}

[data-testid="stMetric"]:hover {
  transform: translateY(-2px);
  border-color: var(--border-strong);
  box-shadow: var(--shadow-md);
}

[data-testid="stMetric"]::before {
  content: '';
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  height: 3px;
  background: linear-gradient(90deg, var(--primary), var(--primary-2), var(--primary-3));
  opacity: 0.7;
}

[data-testid="stMetricLabel"] p {
  color: var(--muted);
  font-weight: 700;
  font-size: 0.8rem;
  text-transform: uppercase;
  letter-spacing: 0.06em;
}

[data-testid="stMetricValue"] {
  font-family: 'Outfit', sans-serif;
  color: var(--text);
  font-weight: 800;
  font-size: 1.8rem;
  letter-spacing: -0.03em;
}

/* ---------- Containers, Expanders & Cards ---------- */
[data-testid="stVerticalBlockBorderWrapper"] {
  border: 1px solid var(--border) !important;
  border-radius: var(--radius-lg) !important;
  background: var(--surface) !important;
  backdrop-filter: blur(16px);
  -webkit-backdrop-filter: blur(16px);
  box-shadow: var(--shadow-sm);
  transition: all .2s ease;
}

[data-testid="stExpander"] {
  border: 1px solid var(--border);
  border-radius: var(--radius) !important;
  background: var(--surface);
  backdrop-filter: blur(12px);
  overflow: hidden;
  box-shadow: var(--shadow-sm);
}

[data-testid="stExpander"] details {
  border: none !important;
  background: transparent;
}

[data-testid="stExpander"] summary {
  font-weight: 700;
  font-size: 0.95rem;
}

[data-testid="stAlert"] {
  border-radius: 14px;
  border: 1px solid var(--border);
  backdrop-filter: blur(10px);
}

[data-testid="stAlert"], [data-testid="stAlert"] p {
  color: var(--text);
}

[data-testid="stProgress"] > div {
  height: 10px;
  border-radius: 99px;
  background: var(--primary-soft);
  overflow: hidden;
}

[data-testid="stProgress"] > div > div {
  background: linear-gradient(90deg, var(--primary), var(--primary-2), var(--primary-3));
  border-radius: 99px;
}

/* ---------- Images & Previews ---------- */
[data-testid="stImage"], [data-testid="stImage"] img, .stImage img {
  border-radius: 12px;
  box-shadow: var(--shadow-sm);
  max-width: 100%;
  height: auto;
  transition: transform .2s ease;
}

/* ---------- Sidebar Styling ---------- */
[data-testid="stSidebar"] {
  background: var(--surface2) !important;
  backdrop-filter: blur(20px);
  -webkit-backdrop-filter: blur(20px);
  border-right: 1px solid var(--border);
}

[data-testid="stSidebar"] .block-container {
  padding-top: 1.5rem;
}

[data-testid="stSidebar"] div[role="radiogroup"] label {
  width: 100%;
  border-radius: 12px;
  padding: 10px 16px;
  font-size: 0.96rem;
  font-weight: 600;
  background: transparent;
  border: 1px solid transparent;
  box-shadow: none;
  transition: all .16s ease;
}

[data-testid="stSidebar"] div[role="radiogroup"] label:hover {
  background: var(--primary-soft);
  border-color: transparent;
  transform: translateX(2px);
}

[data-testid="stSidebar"] div[role="radiogroup"] label:has(input:checked) {
  background: linear-gradient(135deg, var(--primary) 0%, var(--primary-2) 100%);
  border-color: transparent;
  box-shadow: 0 4px 14px var(--primary-shadow);
}

[data-testid="stSidebar"] div[role="radiogroup"] label:has(input:checked) div {
  color: #FFFFFF !important;
  font-weight: 700;
}

/* ---------- OptiPic Custom Hero & Components ---------- */
.opt-hero {
  text-align: center;
  padding: 3.5rem 1.2rem 2.2rem;
  position: relative;
}

.opt-hero-badge {
  display: inline-flex;
  align-items: center;
  gap: 0.45rem;
  padding: 7px 18px;
  border-radius: 999px;
  background: var(--primary-soft);
  border: 1px solid rgba(99, 102, 241, 0.25);
  color: var(--primary);
  font-weight: 700;
  font-size: 0.82rem;
  letter-spacing: 0.05em;
  margin-bottom: 1.4rem;
  box-shadow: 0 2px 10px var(--primary-shadow);
}

.opt-hero-badge .pulse-dot {
  width: 8px;
  height: 8px;
  border-radius: 999px;
  background: var(--success);
  box-shadow: 0 0 8px var(--success);
  display: inline-block;
  animation: opt-pulse 2s infinite;
}

@keyframes opt-pulse {
  0% { transform: scale(0.95); box-shadow: 0 0 0 0 rgba(16, 185, 129, 0.7); }
  70% { transform: scale(1); box-shadow: 0 0 0 8px rgba(16, 185, 129, 0); }
  100% { transform: scale(0.95); box-shadow: 0 0 0 0 rgba(16, 185, 129, 0); }
}

.opt-hero h1 {
  font-size: clamp(2.3rem, 5vw, 3.8rem);
  line-height: 1.1;
  font-weight: 900;
  margin: 0 0 1.1rem;
  background: linear-gradient(135deg, var(--text) 0%, var(--primary) 60%, var(--primary-2) 100%);
  -webkit-background-clip: text;
  background-clip: text;
  -webkit-text-fill-color: transparent;
  letter-spacing: -0.04em;
}

.opt-hero-sub {
  color: var(--muted);
  font-size: clamp(1.05rem, 1.7vw, 1.25rem);
  max-width: 640px;
  margin: 0 auto 2.2rem;
  line-height: 1.65;
  font-weight: 500;
}

.opt-section-title {
  font-family: 'Outfit', sans-serif;
  font-size: 1.55rem;
  font-weight: 800;
  margin: 2.6rem 0 0.35rem;
  letter-spacing: -0.03em;
  color: var(--text);
}

.opt-section-sub {
  color: var(--muted);
  font-size: 0.95rem;
  margin: 0 0 1.3rem;
  font-weight: 500;
}

.opt-feature {
  background: var(--surface);
  backdrop-filter: blur(16px);
  -webkit-backdrop-filter: blur(16px);
  border: 1px solid var(--border);
  border-radius: var(--radius-lg);
  padding: 1.5rem;
  box-shadow: var(--shadow-sm);
  height: 100%;
  transition: all .22s cubic-bezier(0.16, 1, 0.3, 1);
}

.opt-feature:hover {
  transform: translateY(-4px);
  border-color: rgba(99, 102, 241, 0.3);
  box-shadow: var(--shadow-md);
}

.opt-feature-icon {
  width: 52px;
  height: 52px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 1.55rem;
  border-radius: 16px;
  margin-bottom: 1.1rem;
  background: linear-gradient(135deg, var(--primary-soft), var(--primary-soft));
  border: 1px solid var(--border);
  box-shadow: 0 2px 8px var(--primary-shadow);
}

.opt-feature h4 {
  margin: 0 0 0.5rem;
  font-size: 1.12rem;
  font-weight: 700;
}

.opt-feature p {
  color: var(--muted);
  font-size: 0.92rem;
  margin: 0;
  line-height: 1.6;
}

.opt-why-item {
  display: flex;
  gap: 0.85rem;
  align-items: flex-start;
  padding: 0.65rem 0;
}

.opt-why-item .opt-tick {
  min-width: 24px;
  height: 24px;
  border-radius: 999px;
  background: var(--success-soft);
  color: var(--success);
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 0.82rem;
  font-weight: 800;
  margin-top: 2px;
  border: 1px solid rgba(16, 185, 129, 0.25);
}

.opt-why-item div p {
  margin: 0;
  line-height: 1.55;
  font-size: 0.95rem;
}

.opt-why-item div p strong {
  display: block;
  font-size: 1rem;
  color: var(--text);
  margin-bottom: 0.15rem;
}

.opt-step {
  background: var(--surface);
  backdrop-filter: blur(14px);
  -webkit-backdrop-filter: blur(14px);
  border: 1px solid var(--border);
  border-radius: var(--radius);
  padding: 1.25rem 1.15rem;
  box-shadow: var(--shadow-sm);
  height: 100%;
  transition: all .2s ease;
}

.opt-step:hover {
  transform: translateY(-3px);
  border-color: var(--border-strong);
  box-shadow: var(--shadow-md);
}

.opt-step-num {
  display: inline-flex;
  width: 32px;
  height: 32px;
  border-radius: 999px;
  margin-bottom: 0.75rem;
  background: linear-gradient(135deg, var(--primary), var(--primary-2));
  color: #FFFFFF;
  font-weight: 800;
  font-size: 0.9rem;
  align-items: center;
  justify-content: center;
  box-shadow: 0 3px 10px var(--primary-shadow);
}

.opt-step strong {
  color: var(--text);
  font-size: 1.02rem;
  display: block;
  margin-bottom: 0.3rem;
  font-weight: 700;
}

.opt-step p {
  margin: 0;
  color: var(--muted);
  font-size: 0.88rem;
  line-height: 1.55;
}

.opt-pill {
  display: inline-block;
  padding: 4px 12px;
  border-radius: 999px;
  font-size: 0.76rem;
  font-weight: 700;
  letter-spacing: 0.04em;
  margin-right: 6px;
  margin-bottom: 5px;
  background: var(--primary-soft);
  color: var(--primary);
  border: 1px solid rgba(99, 102, 241, 0.2);
}

.opt-pill-green {
  background: var(--success-soft);
  color: var(--success);
  border: 1px solid rgba(16, 185, 129, 0.25);
}

.opt-pill-muted {
  background: transparent;
  color: var(--muted);
  border: 1px solid var(--border);
}

.opt-file-name {
  font-family: 'Outfit', sans-serif;
  font-weight: 700;
  font-size: 0.98rem;
  margin: 0.65rem 0 0.25rem;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  color: var(--text);
}

.opt-meta-line {
  color: var(--muted);
  font-size: 0.83rem;
  margin: 0.2rem 0 0.75rem;
  line-height: 1.5;
}

.opt-saved-badge {
  display: inline-flex;
  align-items: center;
  gap: 0.3rem;
  padding: 6px 14px;
  border-radius: 999px;
  font-weight: 800;
  font-size: 0.88rem;
  letter-spacing: -0.01em;
  background: var(--success-soft);
  color: var(--success);
  border: 1px solid rgba(16, 185, 129, 0.3);
  box-shadow: 0 2px 10px rgba(16, 185, 129, 0.15);
  white-space: nowrap;
}

.opt-rec {
  padding: 0.75rem 1rem;
  border-left: 4px solid var(--primary);
  background: var(--primary-soft);
  border-radius: 10px;
  margin-bottom: 0.65rem;
  border-top: 1px solid var(--border);
  border-right: 1px solid var(--border);
  border-bottom: 1px solid var(--border);
}

.opt-rec strong {
  font-size: 0.92rem;
  display: block;
  color: var(--text);
  margin-bottom: 0.15rem;
}

.opt-rec span {
  color: var(--muted);
  font-size: 0.84rem;
}

.opt-footer {
  margin-top: 3.8rem;
  padding-top: 1.4rem;
  border-top: 1px solid var(--border);
  color: var(--muted);
  font-size: 0.88rem;
  display: flex;
  justify-content: space-between;
  flex-wrap: wrap;
  gap: 0.6rem;
}

.opt-brand h2 {
  margin: 0.3rem 0 0;
  font-size: 1.4rem;
  font-weight: 800;
  background: linear-gradient(135deg, var(--text), var(--primary));
  -webkit-background-clip: text;
  background-clip: text;
  -webkit-text-fill-color: transparent;
}

.opt-brand p {
  color: var(--muted);
  font-size: 0.82rem;
  margin: 0.1rem 0 0;
  font-weight: 600;
}

@media (max-width: 640px) {
  .opt-hero { padding-top: 2rem; }
  .block-container { padding: 1.2rem 0.8rem 3.5rem; }
}
""")


def render_theme(theme: str = "Light") -> None:
    """Inject the full design-system stylesheet for the given theme."""
    tokens = DARK_TOKENS if theme == "Dark" else LIGHT_TOKENS
    css = _CSS_TEMPLATE.safe_substitute(tokens)
    if theme == "Dark":
        css += """
        html, body, .stApp, [data-testid="stAppViewContainer"],
        [data-testid="stSidebar"], section.main, [data-testid="stMain"] {
          --background-color: #0A0F1D;
          --secondary-background-color: #111827;
          --primary-color: #818CF8;
          --text-color: #F8FAFC;
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
