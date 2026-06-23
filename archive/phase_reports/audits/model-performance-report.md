# BAYAN — Model Performance Report

**Date:** 2026-06-18

---

## Model Inventory

| # | Model | Repo | Architecture | Parameters | Disk |
|---|-------|------|-------------|------------|------|
| 1 | AraSpell | `bayan10/AraSpell-Model` | AraBERT Encoder-Decoder | ~220M | ~900MB |
| 2 | Grammar | `bayan10/Bayan_Arabic_Grammar` | Gradio Client + Rules | N/A (remote) | ~50MB (rules) |
| 3 | PuncAra-v1 | `bayan10/PuncAra-v1` | EncoderDecoderModel | 298M | ~1.2GB |
| 4 | Summarization | `bayan10/summarization-model` | MBart (float16) | ~610M | ~600MB |
| 5 | AraBERT MLM | `aubmindlab/bert-base-arabertv02` | AutoModelForMaskedLM | ~110M | ~500MB |

**Total estimated RAM:** ~3.2GB (well within HF Spaces 16GB limit)

---

## Loading Strategy

All NLP models use **lazy loading** — they are only loaded into memory on first inference request.

```
App Start
  ↓
Summarization loaded eagerly (used most often)
  ↓
First /api/spelling call → AraSpell loaded
First /api/grammar call  → Gradio Client connected
First /api/punctuation call → PuncAra-v1 loaded
```

### Cold Start Times

| Model | First Load | Subsequent |
|-------|-----------|------------|
| Summarization | ~5s (startup) | Instant |
| AraSpell | ~3-4s (first call) | Instant |
| Grammar (Gradio) | ~1-2s (first call) | Instant |
| PuncAra-v1 | ~3-4s (first call) | Instant |

---

## Inference Latency

### Standalone Endpoints

| Endpoint | Short text (10 words) | Medium (50 words) | Long (200 words) |
|----------|----------------------|-------------------|-------------------|
| /api/spelling | ~2-4s | ~8-15s | ~30-50s |
| /api/grammar | ~1-3s | ~2-5s | ~5-10s |
| /api/punctuation | ~1-2s | ~2-4s | ~5-10s |
| /api/summarize | ~1-2s | ~2-3s | ~3-5s |

### Full Pipeline (/api/analyze)

| Text Length | Latency | Notes |
|-------------|---------|-------|
| 1-10 words | 4-6s | Normal |
| 10-50 words | 8-16s | AraSpell dominates |
| 50-200 words | 20-50s | Within timeout |
| 200+ words | 50-120s | May approach timeout |

> [!WARNING]
> AraSpell is the bottleneck. It processes word-by-word with beam search decoding. Grammar and Punctuation are fast by comparison.

---

## Memory Profile

| Component | Estimated RAM |
|-----------|---------------|
| Python + Flask + Gunicorn | ~100MB |
| Summarization (MBart float16) | ~600MB |
| AraSpell (encoder-decoder + MLM) | ~1.0GB |
| PuncAra-v1 (encoder-decoder) | ~1.2GB |
| Grammar (Gradio Client) | ~50MB |
| camel-tools data | ~200MB |
| **Total Peak** | **~3.2GB** |

HF Spaces Free Tier: 16GB RAM → **~80% headroom** ✅

---

## Throughput

### Concurrent Request Handling

| Users | Endpoint | Success Rate | Avg Latency |
|-------|----------|-------------|-------------|
| 1 | /api/health | 100% | 0.59s |
| 3 | /api/health | 100% | 0.65s |
| 5 | /api/health | 100% | 0.79s |
| 1 | /api/analyze | 100% | 4.4s |
| 3 | /api/analyze | 100% | 8.5s |

> [!NOTE]
> Single Gunicorn worker means requests are serialized. Concurrent analyze requests queue up, roughly tripling latency with 3 concurrent users. This is acceptable for the current user base.

---

## Recommendations

1. **AraSpell optimization:** Consider batch processing or caching frequent corrections
2. **Worker count:** Could increase to 2 workers if RAM allows (currently ~3.2GB / 16GB)
3. **Model quantization:** PuncAra-v1 could potentially be quantized to INT8 (50% RAM savings)
4. **Long text chunking:** Implement text chunking in `/api/analyze` for texts > 200 words
