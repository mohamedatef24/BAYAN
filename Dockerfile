FROM python:3.12-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install Python dependencies
# Install CPU-only PyTorch first (saves ~1.5GB vs full torch with CUDA)
COPY requirements.txt .
RUN pip install --no-cache-dir torch --index-url https://download.pytorch.org/whl/cpu && \
    pip install --no-cache-dir -r requirements.txt

# Pre-download models during build (network is available here)
# At runtime, the container has NO outbound DNS, so models must be cached

# 1. Summarization model (MBart, float16)
RUN python -c "\
from transformers import MBartForConditionalGeneration, AutoTokenizer, AutoConfig; \
import torch; \
repo = 'bayan10/summarization-model'; \
print('Downloading summarization tokenizer...'); \
AutoTokenizer.from_pretrained(repo); \
print('Downloading summarization config...'); \
AutoConfig.from_pretrained(repo); \
print('Downloading summarization model (float16)...'); \
MBartForConditionalGeneration.from_pretrained(repo, torch_dtype=torch.float16); \
print('Summarization model cached!'); \
"

# 2. Spelling model (AraSpell — AraBERT encoder-decoder + checkpoint)
RUN python -c "\
from huggingface_hub import hf_hub_download; \
from transformers import AutoTokenizer, EncoderDecoderModel, AutoModelForMaskedLM; \
print('Downloading AraSpell checkpoint...'); \
hf_hub_download(repo_id='bayan10/AraSpell-Model', filename='last_model.pt'); \
print('Downloading AraBERT tokenizer...'); \
AutoTokenizer.from_pretrained('aubmindlab/bert-base-arabertv02'); \
print('Downloading AraBERT encoder-decoder...'); \
EncoderDecoderModel.from_encoder_decoder_pretrained('aubmindlab/bert-base-arabertv02', 'aubmindlab/bert-base-arabertv02'); \
print('Downloading AraBERT MLM (for ContextualCorrector)...'); \
AutoModelForMaskedLM.from_pretrained('aubmindlab/bert-base-arabertv02'); \
print('Spelling model + MLM cached!'); \
"

# 3. Grammar — camel-tools MLE disambiguator data
RUN camel_data -i light

# 4. Punctuation model (PuncAra-v1 — EncoderDecoderModel)
RUN python -c "\
from transformers import EncoderDecoderModel, AutoTokenizer; \
repo = 'bayan10/PuncAra-v1'; \
print('Downloading PuncAra-v1 tokenizer...'); \
AutoTokenizer.from_pretrained(repo); \
print('Downloading PuncAra-v1 model...'); \
EncoderDecoderModel.from_pretrained(repo); \
print('PuncAra-v1 cached!'); \
"

# 5. Dialect-to-MSA model (mT5, float16)
RUN python -c "\
from transformers import AutoTokenizer, AutoModelForSeq2SeqLM; \
import torch; \
repo = 'bayan10/dialect-to-msa-model'; \
print('Downloading dialect tokenizer...'); \
AutoTokenizer.from_pretrained(repo); \
print('Downloading dialect model (float16)...'); \
AutoModelForSeq2SeqLM.from_pretrained(repo, torch_dtype=torch.float16); \
print('Dialect model cached!'); \
"

# Copy application code
COPY src/ ./src/
COPY quran.py ./
COPY quran_master.db ./
COPY .env* ./

# Minify JS/CSS for production
RUN pip install --no-cache-dir rjsmin rcssmin && \
    python -c "\
import os, rjsmin, rcssmin; \
for root, dirs, files in os.walk('src'): \
    for f in files: \
        p = os.path.join(root, f); \
        if f.endswith('.js'): \
            with open(p) as fh: src = fh.read(); \
            with open(p, 'w') as fh: fh.write(rjsmin.jsmin(src)); \
        elif f.endswith('.css'): \
            with open(p) as fh: src = fh.read(); \
            with open(p, 'w') as fh: fh.write(rcssmin.cssmin(src)); \
"

# Bundle JS files in dependency order (replaces 33 script tags)
RUN python -c "\
import os; \
js_order = [ \
    'js/vendor/supabase.min.js', 'js/auth/config.js', 'js/vendor-loader.js', \
    'js/auth/client.js', 'js/auth/session.js', 'js/auth/auth.js', 'js/auth/auth-ui.js', \
    'js/theme.js', 'js/vendor/FileSaver.min.js', 'js/dialogs.js', 'js/i18n.js', \
    'js/analytics.js', 'js/onboarding.js', 'js/renderer.js', 'js/selection.js', \
    'js/ui.js', 'js/documents/doc-utils.js', 'js/editor.js', 'js/autocomplete.js', \
    'js/format.js', 'js/documents/import.js', 'js/documents/export.js', \
    'js/documents/documents.js', 'js/sync/sync-queue.js', 'js/sync/sync-resolver.js', \
    'js/sync/sync-manager.js', 'js/documents-cloud/documents-api.js', \
    'js/documents-cloud/documents-state.js', 'js/documents-cloud/documents-ui.js', \
    'js/summaries/summaries-api.js', 'js/summaries/summaries-ui.js', \
    'js/settings-sync/settings-api.js', 'js/settings-sync/settings-sync.js', \
    'js/app.js', \
]; \
bundle = ''; \
for f in js_order: \
    p = os.path.join('src', f); \
    if os.path.exists(p): \
        with open(p) as fh: bundle += fh.read() + '\n'; \
with open('src/js/bayan.bundle.js', 'w') as fh: fh.write(bundle); \
print(f'Bundled {len(js_order)} JS files'); \
"

# Set environment variables
ENV PORT=7860
ENV DEBUG=False
ENV PYTHONUNBUFFERED=1

# Expose port
EXPOSE 7860

# Start the app with gunicorn (single worker to minimize RAM)
# Timeout 300s: full pipeline (spelling ~50s + grammar ~8s + punctuation ~30s + cold start)
CMD ["gunicorn", "--chdir", "src", "app:app", "--bind", "0.0.0.0:7860", "--timeout", "300", "--workers", "1"]
