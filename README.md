# OptiPic — Smart Image Optimizer

> **Smaller Images. Faster Web.**

OptiPic is a complete, production-quality **image optimization web application** built with
Python and Streamlit. Compress, resize and convert images with real, measured results —
every percentage shown in the UI is calculated from the actual bytes before and after
processing.

---

## 📋 Project Overview

OptiPic turns a slow, multi-step image workflow (external tools, manual resizing, guesswork
quality settings) into a single clean web experience:

1. **Upload** — drag & drop JPG, PNG, WebP, BMP or TIFF files (multiple at once).
2. **Validate** — every file is checked for extension, MIME type, *actual* image content,
   corruption, empty payloads, size limits and decompression-bomb dimensions.
3. **Preview** — image cards show thumbnail, format, dimensions, mode and file size.
4. **Tune** — pick a preset (Maximum Compression → High Quality) or adjust quality, output
   format, resizing and metadata removal. **Smart Optimize** can choose ideal settings per
   image automatically.
5. **Optimize** — batch processing with live progress; individual failures never stop the run.
6. **Compare & Download** — before/after cards with measured savings, single downloads and a
   `optimized-images.zip` bundle built with Python's `zipfile`.

## ✨ Features

| Area | What you get |
|---|---|
| Smart Compression | Mode presets + custom 10–100 quality slider; format-aware encoders |
| Smart Optimize | Per-image recommendations from format, size, dimensions, transparency & content type |
| Bulk Optimization | Multi-file batches with progress bar and per-file error isolation |
| Format Conversion | JPEG ⇄ PNG ⇄ WebP, plus BMP/TIFF inputs; transparency-safe JPEG conversion |
| Image Resizing | By width / height / percentage, aspect-ratio control, LANCZOS resampling, width presets |
| Size Estimation | Clearly-labeled *estimates* (e.g. "Potential savings: ~65–72%") before processing |
| Before/After | Side-by-side comparison with real sizes, dimensions and "% smaller" badge |
| Results Dashboard | Total images, original/optimized size, space saved, avg compression, avg time |
| History & Statistics | Lightweight session + local JSON history (never image data), savings chart |
| Privacy | In-memory processing, metadata stripping, no permanent storage, honest privacy notes |
| Theming | Polished light theme by default with a dark mode toggle |

## 🛠 Technology Stack

- **Python 3.11+**
- **Streamlit** — UI framework
- **Pillow (PIL)** — image processing engine (LANCZOS resampling, format encoders, EXIF)
- **NumPy** — content statistics used by Smart Optimize (photo-vs-graphic heuristics)
- **Standard library** — `zipfile` (ZIP downloads), `pathlib`, `io.BytesIO`, `tempfile`, `json`, `logging`
- **pytest** — test suite (65 tests)

## 📁 Project Structure

```
image-optimizer/
│
├── app.py                    # Vercel ASGI entry point
├── streamlit_app.py          # Streamlit UI entry point: session init, theming, navigation
├── requirements.txt          # streamlit, Pillow, numpy (+ pytest for tests)
├── README.md
├── .gitignore
├── .streamlit/
│   └── config.toml           # Base theme + server upload cap
│
├── core/                     # Image-processing engine (no Streamlit imports)
│   ├── optimizer.py          # optimize_image(), presets, Smart Optimize, savings math
│   ├── converter.py          # Format conversion, mode/transparency handling, encoders
│   ├── resizer.py            # Dimension math + LANCZOS resizing
│   └── analyzer.py           # Image analysis, thumbnails, size estimation
│
├── utils/                    # Pure-Python helpers
│   ├── validators.py         # Upload validation (extension/MIME/content/size/bombs)
│   └── file_utils.py         # Formatting, safe names, ZIP creation, history persistence
│
├── components/               # Reusable Streamlit UI
│   ├── styles.py             # Design system (CSS tokens, light/dark themes)
│   ├── sidebar.py            # Branding + navigation
│   ├── upload.py             # Drag-and-drop uploader + image card grid
│   ├── settings.py           # Optimizer settings panel, presets, estimates
│   └── results.py            # Results dashboard, before/after cards, ZIP downloads
│
├── views/                    # One module per page
│   ├── home.py               # Landing page (hero, features, why, workflow)
│   ├── optimizer.py          # Main optimizer workflow
│   ├── converter.py          # Dedicated converter tool
│   ├── resizer.py            # Dedicated resizer tool
│   ├── history.py            # History + statistics
│   └── settings.py           # App settings + privacy policy
│
├── tests/                    # pytest suite (65 tests)
├── assets/                   # logo.png, sample-photo.jpg
└── data/                     # Created at runtime for optional history.json (gitignored)
```

## 🚀 Installation

### 1. Virtual environment setup

**Windows (PowerShell / CMD):**

```bat
cd "D:\python\image optimizer web app"
python -m venv venv
venv\Scripts\activate
```

**Linux / macOS:**

```bash
cd path/to/image-optimizer
python3 -m venv venv
source venv/bin/activate
```

### 2. Install dependencies

```bash
pip install -r requirements.txt
```

### 3. Run the application

```bash
streamlit run streamlit_app.py
```

The app opens at **http://localhost:8501** automatically.

For Vercel, `app.py` exposes the Streamlit ASGI application. The Vercel Python runtime
requires Streamlit 1.50 or newer for this entrypoint pattern.

## 🧪 Testing

```bash
# run the full suite
pytest

# run with verbose output
pytest -v

# run one area only
pytest tests/test_optimizer.py
```

The suite covers: upload validation, compression, resizing, format conversion, savings
calculation, ZIP creation, corrupted/invalid input handling — plus AppTest smoke tests that
render every page of the running app.

## ⚙️ Configuration

| Setting | Where | Default |
|---|---|---|
| Max file size per upload | Settings page (`cfg_max_mb`) | 20 MB |
| Max image dimensions | Settings page (`cfg_max_mp`) | 60 megapixels |
| Persist history | Settings page (`cfg_persist_history`) | On → `data/history.json` |
| Theme | Settings page (`theme`) | Light (dark mode supported) |
| Server upload cap | `.streamlit/config.toml` (`maxUploadSize`) | 200 MB |
| Decompression-bomb guard | `core/optimizer.py` (`Image.MAX_IMAGE_PIXELS`) | 80 MP |

## 🎯 How the Optimization Engine Works

`core/optimizer.py:optimize_image()` runs a 7-step pipeline:

1. **Decode** — the upload is opened from `BytesIO` and fully loaded once; EXIF orientation
   is honored via `ImageOps.exif_transpose()`.
2. **Quality resolution** — compression modes map to fixed quality levels
   (Maximum Compression → 60, Balanced → 80, High Quality → 92); *Custom* uses the slider.
3. **Resize** — when requested, dimensions are computed (width/height/percent, with or
   without aspect ratio) and applied with `Image.Resampling.LANCZOS`.
4. **Mode preparation** — the image is converted to a mode the target format can encode.
   Transparent images destined for JPEG are composited onto a white background instead of
   crashing; alpha is preserved for PNG/WebP; CMYK sources become RGB.
5. **Encode** — format-aware settings: JPEG (optimize + progressive), WebP (efficient
   encoder method, lossless at quality 100), PNG (optimizer on). EXIF/ICC are written only
   when *Remove Metadata* is off.
6. **Fallback** — if the format and dimensions are unchanged and the re-encoded file is not
   smaller, the original bytes are returned ("Already well optimized").
7. **Measure** — savings, dimensions, timing and format are read from the actual result and
   reported in the UI.

**Smart Optimize** inspects each image (format, megapixels, byte size, alpha channel,
photo-vs-graphic content detected via NumPy) and picks settings per image — e.g. a large
JPEG becomes *WebP + 82% quality*, a transparent PNG keeps its alpha (WebP when it's big),
a very large photo is resized to 2560 px before compressing.

**Size estimation** encodes a ≤512 px sample of the image with the exact target
settings, measures its bytes-per-pixel and extrapolates — always reported as a range and
labeled as an estimate.

## 🔒 Privacy

Your images are processed **temporarily** and are not intended for permanent storage:
uploads and results live in the session's memory, history stores only filenames/dates/sizes,
and no data is sent to third-party services. OptiPic is honest about its architecture — it
is a Python/Streamlit app, so processing happens on the machine running the server, not
in the browser.

## 🧰 Troubleshooting

| Problem | Fix |
|---|---|
| `streamlit: command not found` | Activate the virtual environment first, or run `python -m streamlit run app.py` |
| Port 8501 already in use | `streamlit run app.py --server.port 8502` |
| "File exceeds the allowed size" | Raise the limit on the Settings page (server cap: 200 MB in `config.toml`) |
| "Image dimensions are too large" | The decompression-bomb guard rejected the image; raise it in Settings if safe |
| Dark mode looks off | Theme is applied via CSS; reload the browser tab after switching |
| History missing after restart | Enable *Persist history* on the Settings page |
| Slow huge batches | Large images take time; enable Smart Optimize to cap dimensions automatically |

## 🔭 Future Improvements

- AVIF and HEIF support
- Parallel batch processing (process pool) for large workloads
- Visual before/after slider with full-resolution pan & zoom
- Preset profiles saved to disk
- Optional lossless PNG palette quantization for graphics
- Docker packaging and one-click cloud deployment

---

Built as a portfolio-grade demonstration: **OptiPic — Smaller Images. Faster Web.**
