"""
Example usage:
    from bayan_inference_hf import BayanConverter
    converter = BayanConverter()
    result = converter.convert("عايز اشتكي من موظف في فرعكم")
    print(result)
"""

from transformers import AutoTokenizer, AutoModelForSeq2SeqLM
import torch

class BayanConverter:
    PREFIX   = "حوّل إلى الفصحى: "
    REPO_ID  = "bayan10/dialect-to-msa-model"   # ← الموديل على HuggingFace Hub

    def __init__(self, model_path: str = None, device: str = None):
        """
        model_path: لو None، بيحمّل من HuggingFace Hub (bayan10/dialect-to-msa-model)
                    لو حددت مسار محلي، بيحمّل من هناك بدل كده
        """
        self.device = device or ("cuda" if torch.cuda.is_available() else "cpu")
        source = model_path or self.REPO_ID

        print(f"Loading model from '{source}' on {self.device}...")
        self.tokenizer = AutoTokenizer.from_pretrained(source)
        self.model = AutoModelForSeq2SeqLM.from_pretrained(source).to(self.device)
        self.model.eval()
        print("Ready.")

    def convert(self, dialect_text: str, num_beams: int = 4) -> str:
        """تحويل جملة عامية واحدة إلى الفصحى الحديثة."""
        input_text = self.PREFIX + dialect_text
        inputs = self.tokenizer(
            input_text,
            return_tensors="pt",
            max_length=128,
            truncation=True,
        ).to(self.device)

        with torch.no_grad():
            outputs = self.model.generate(
                **inputs,
                max_length=128,
                num_beams=num_beams,
                early_stopping=True,
                no_repeat_ngram_size=3,
            )
        return self.tokenizer.decode(outputs[0], skip_special_tokens=True)

    def convert_batch(self, texts: list[str], num_beams: int = 4) -> list[str]:
        """تحويل مجموعة جمل دفعة واحدة (أسرع من واحدة واحدة)."""
        inputs_list = [self.PREFIX + t for t in texts]
        inputs = self.tokenizer(
            inputs_list,
            return_tensors="pt",
            max_length=128,
            truncation=True,
            padding=True,
        ).to(self.device)

        with torch.no_grad():
            outputs = self.model.generate(
                **inputs,
                max_length=128,
                num_beams=num_beams,
                early_stopping=True,
                no_repeat_ngram_size=3,
            )
        return self.tokenizer.batch_decode(outputs, skip_special_tokens=True)
