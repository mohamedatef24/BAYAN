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

# Pre-download the summarization model during build (network is available here)
# At runtime, the container has NO outbound DNS, so models must be cached
RUN python -c "\
from transformers import MBartForConditionalGeneration, AutoTokenizer, AutoConfig; \
import torch; \
repo = 'bayan10/summarization-model'; \
print('Downloading tokenizer...'); \
AutoTokenizer.from_pretrained(repo); \
print('Downloading config...'); \
AutoConfig.from_pretrained(repo); \
print('Downloading model (float16)...'); \
MBartForConditionalGeneration.from_pretrained(repo, torch_dtype=torch.float16); \
print('Model cached successfully!'); \
"

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
