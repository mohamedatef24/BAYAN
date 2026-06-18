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

# Copy application code
COPY src/ ./src/
COPY .env* ./

# Set environment variables
ENV PORT=7860
ENV DEBUG=False
ENV PYTHONUNBUFFERED=1

# Expose port
EXPOSE 7860

# Start the app with gunicorn (single worker to minimize RAM)
CMD ["gunicorn", "--chdir", "src", "app:app", "--bind", "0.0.0.0:7860", "--timeout", "120", "--workers", "1"]
