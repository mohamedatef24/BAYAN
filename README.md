---
title: Bayan API
emoji: ✍️
colorFrom: green
colorTo: blue
sdk: docker
app_port: 7860
---

# BAYAN (بَيان) — AI-Powered Arabic Writing Assistant ✍️

**BAYAN** is a full-stack Arabic writing assistant — a Grammarly-style platform for Modern
Standard Arabic that combines fine-tuned Transformer models with handcrafted linguistic
rules. It corrects **spelling, grammar, and punctuation** in real time, and adds
**summarization, autocomplete, dialect→MSA translation, and Quran verification** — delivered
through a modern web app and a Chrome extension.

> Graduation Project — Cairo University, Faculty of Computers & Artificial Intelligence.

---

## 🌟 Overview

Production Arabic NLP is roughly 20% model training and 80% engineering safety scaffolding.
BAYAN reflects that: multiple fine-tuned models wrapped in a **deterministic, collision-free
correction engine** that guarantees stable, non-overlapping edits, plus religious-text
protection so sacred text is never altered.

The core `/api/analyze` endpoint runs a sequential pipeline:

```
Input → Spelling → Grammar → Punctuation → Diff
```

---

## 🧠 Core Features

| Feature | Model / Method |
|--------|-----------------|
| **Spelling** | Seq2Seq (BERT-based) beam candidates + Norvig-style edit distance, reranked by MLM fluency, Damerau-Levenshtein similarity, and in-/out-of-vocabulary acceptance; CAMeL Tools morphological reranking |
| **Grammar** | Gemma causal LM via chat-template prompting, with rule-based guards that reject generic/instructional output |
| **Punctuation** | Seq2Seq model inserting Arabic marks (`،` `؛` `؟` `.` `« »`) into continuous text |
| **Summarization** | mBART conditional generation with short/medium/long thresholds and a **safe extractive fallback** when abstractive output drifts too far from the source |
| **Autocomplete** | Local GPT-2 next-word prediction, surfaced as ghost text (accept with `Tab`) |
| **Dialect → MSA** | Dialect-to-Modern-Standard-Arabic translation (`src/nlp/dialect`) |
| **Quran Verification** | Dual-stage normalization + cascading anchor search + RapidFuzz fuzzy matching against an Uthmani-script database (`quran.py`) |

### Evaluation highlights
- **Grammar:** GLEU 75% · ChrF++ 88% — exceeding published SOTA (62–68% / 72–78%); ~60% hallucination reduction via LoRA
- **Spelling:** 95.63% word accuracy · 1.40% CER — outperforming Google Docs (~90%)

---

## 🏗️ Architecture

**Client–Server**, model-agnostic and modular:

```
Web UI / Chrome Extension  ⇄  Flask API (src/app.py)  ⇄  model_loader.py  ⇄  NLP models
```

- **Multi-stage correction engine** (`src/nlp/`) with `pipeline_context.py` and
  `stage_locker.py` ensuring collision-free, deterministic corrections across stages.
- **Backend:** Flask API — loads summarization on startup, lazily loads the rest; validates
  input length (10–5,000 chars). Endpoints: `/api/health`, `/api/analyze`, `/api/spelling`,
  `/api/summarize`, `/api/autocomplete`.
- **Frontend (`src/index.html`):** TailwindCSS + Vanilla JS, glassmorphism UI, a live
  `contenteditable` canvas with wavy underlines (red = spelling, yellow = grammar/punctuation),
  click-to-apply suggestion tooltips, a 0–100 document-score gauge, and a summarization panel.
- **Chrome Extension (Manifest V3, `extension/`):** popup, side panel, and inline
  content overlay — works on any webpage, with localization (`_locales`).

---

## 📁 Repository Layout

```
src/
  app.py            Flask API + endpoints
  model_loader.py   Loaders for all models
  nlp/              Correction engine: spelling, grammar, punctuation,
                    autocomplete, dialect + pipeline_context / stage_locker
  index.html, css/, js/, services/, middleware/, routes/
extension/          Chrome extension (MV3): popup, side panel, inline overlay
quran.py            Quran verification + quran_master.db
models/             Model checkpoints (not committed — see .gitignore)
Dockerfile          Container build (HF Spaces / any host, port 7860)
Procfile            gunicorn entrypoint
requirements.txt    Python dependencies
```

---

## 🚀 How to Run

### Option A — Docker (matches deployment)
```bash
docker build -t bayan .
docker run -p 7860:7860 bayan
```

### Option B — Local Python
```bash
pip install -r requirements.txt

# place model checkpoints under models/ (Spelling, Grammrar, Punctuation,
# Summarization, Autocomplete)

cd src && gunicorn app:app --bind 0.0.0.0:7860 --timeout 120 --workers 1
```

Then open **http://localhost:7860**.

### Chrome Extension
`chrome://extensions` → enable **Developer mode** → **Load unpacked** → select `extension/`.

---

## 🔌 API Quick Reference

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/api/health` | GET | Model load status |
| `/api/analyze` | POST | Full pipeline (spelling → grammar → punctuation) + suggestions diff |
| `/api/spelling` | POST | Spelling correction only |
| `/api/summarize` | POST | Summarize (`length`: 1 short / 2 medium / 3 long) |
| `/api/autocomplete` | POST | Next-word suggestions |

Example — `POST /api/analyze`:
```json
{ "text": "الطلاب ذهبو الى المدرسة" }
```
```json
{
  "original":  "الطلاب ذهبو الى المدرسة",
  "corrected": "ذهب الطلاب إلى المدرسة.",
  "suggestions": [
    { "original": "ذهبو",    "correction": "ذهبوا",     "type": "spelling" },
    { "original": "المدرسة", "correction": "المدرسة.", "type": "punctuation" }
  ],
  "status": "success"
}
```

---

## ⚙️ Tech Stack

Python · PyTorch · Hugging Face Transformers · Gemma · mBART · GPT-2 · BERT · LoRA ·
CAMeL Tools · RapidFuzz · Flask · Gunicorn · TailwindCSS · Vanilla JS · Chrome Extension
(MV3) · Docker · Hugging Face Spaces.

---

## 📄 License

MIT — see [`LICENSE`](LICENSE).

*Model weights and datasets are kept out of Git; checkpoints are hosted on the Hugging Face Hub.*
