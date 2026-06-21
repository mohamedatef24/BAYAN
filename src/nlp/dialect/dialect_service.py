"""
Dialect-to-MSA (Modern Standard Arabic) conversion service.

Uses bayan10/dialect-to-msa-model (mT5 300M) to convert colloquial
Arabic dialects (Egyptian, Gulf, Levantine, Maghrebi) to formal MSA.

Singleton pattern — lazy-loads the model on first request to avoid
blocking server startup.
"""

import logging
import torch
from transformers import AutoTokenizer, AutoModelForSeq2SeqLM

logger = logging.getLogger(__name__)

_instance = None


class DialectConverter:
    """Converts dialect Arabic text to Modern Standard Arabic (MSA)."""

    PREFIX = "حوّل إلى الفصحى: "
    REPO_ID = "bayan10/dialect-to-msa-model"
    MAX_INPUT_LENGTH = 128
    MAX_OUTPUT_LENGTH = 128

    def __init__(self):
        self.device = "cpu"
        logger.info(f"[DIALECT] Loading model from '{self.REPO_ID}'...")

        self.tokenizer = AutoTokenizer.from_pretrained(self.REPO_ID)
        self.model = AutoModelForSeq2SeqLM.from_pretrained(
            self.REPO_ID, torch_dtype=torch.float16
        ).to(self.device)
        self.model.eval()

        logger.info("[DIALECT] Model loaded successfully (float16).")

    def convert(self, dialect_text: str, num_beams: int = 4) -> str:
        """Convert a single dialect sentence to MSA."""
        if not dialect_text or not dialect_text.strip():
            return dialect_text

        input_text = self.PREFIX + dialect_text.strip()
        inputs = self.tokenizer(
            input_text,
            return_tensors="pt",
            max_length=self.MAX_INPUT_LENGTH,
            truncation=True,
        ).to(self.device)

        with torch.no_grad():
            outputs = self.model.generate(
                **inputs,
                max_length=self.MAX_OUTPUT_LENGTH,
                num_beams=num_beams,
                early_stopping=True,
                no_repeat_ngram_size=3,
            )

        result = self.tokenizer.decode(outputs[0], skip_special_tokens=True)
        return result

    def is_ready(self) -> bool:
        """Check if the model is loaded and ready."""
        return self.model is not None and self.tokenizer is not None


def get_dialect_model() -> DialectConverter:
    """Get or create the singleton DialectConverter instance."""
    global _instance
    if _instance is None:
        _instance = DialectConverter()
    return _instance


def is_loaded() -> bool:
    """Check if the dialect model is loaded (without triggering lazy load)."""
    return _instance is not None and _instance.is_ready()
