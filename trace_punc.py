import sys, os, re
sys.path.insert(0, 'src')
import logging; logging.basicConfig(level=logging.INFO)
print("Starting...")

import torch
print(f"CUDA available: {torch.cuda.is_available()}")

from transformers import EncoderDecoderModel, AutoTokenizer
print("Loading PuncAra-v1...")
model = EncoderDecoderModel.from_pretrained("bayan10/PuncAra-v1")
tokenizer = AutoTokenizer.from_pretrained("bayan10/PuncAra-v1")
model.eval()
print("Model loaded!")

inp = "التزم الرياضي بتناول وجباته الصحية وحساب سعراته بدقة رغبة في بناء كتلة عضلية قوية ويا له من التزام حديدي يثير الإعجاب"
print(f"\nINPUT: {inp}")

# Raw inference
from nlp.punctuation.punctuation_rules import arabic_preprocessing
processed = arabic_preprocessing(inp)
inputs = tokenizer(processed, return_tensors="pt", padding=True, truncation=True, max_length=128)
print("Running inference...")
with torch.no_grad():
    outputs = model.generate(
        inputs.input_ids,
        attention_mask=inputs.attention_mask,
        decoder_start_token_id=tokenizer.cls_token_id,
        bos_token_id=tokenizer.cls_token_id,
        eos_token_id=tokenizer.sep_token_id,
        pad_token_id=tokenizer.pad_token_id,
        max_length=128, num_beams=3, repetition_penalty=1.2,
        length_penalty=1.0, early_stopping=True, do_sample=False
    )
raw = tokenizer.decode(outputs[0], skip_special_tokens=True)
print(f"[A] RAW MODEL: {raw}")

# Strip non-punc
from nlp.punctuation.punctuation_service import PunctuationChecker
checker = PunctuationChecker(model, tokenizer, torch.device('cpu'))
stripped = checker._strip_non_punctuation_changes(inp, raw)
print(f"[B] STRIPPED:   {stripped}")
if stripped != raw:
    rw, sw = raw.split(), stripped.split()
    for w1, w2 in zip(rw, sw):
        if w1 != w2:
            print(f"    LOST: '{w1}' -> '{w2}'")

# Postprocess
from nlp.punctuation.punctuation_rules import arabic_postprocessing
final = arabic_postprocessing(stripped)
print(f"[C] FINAL:      {final}")

# Diffs
from app import get_word_diffs
from nlp.punctuation.punctuation_rules import validate_punctuation_diff
if final != inp:
    diffs = get_word_diffs(inp, final)
    print(f"[D] DIFFS ({len(diffs)}):")
    for d in diffs:
        o, c = d.get('original',''), d.get('correction','')
        valid = validate_punctuation_diff(d)
        oa = re.sub(r'[^\u0600-\u06FFa-zA-Z]','',o)
        ca = re.sub(r'[^\u0600-\u06FFa-zA-Z]','',c)
        alpha_ok = oa == ca
        s = "PASS" if valid and alpha_ok else "BLOCKED"
        r = ""
        if not valid: r += " safety"
        if not alpha_ok: r += " alpha"
        print(f"    [{d['start']}:{d['end']}] '{o}' -> '{c}'  [{s}{r}]")
else:
    print("[D] NO DIFFS!")
print("\nDONE")
