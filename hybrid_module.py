
# hybrid_module.py

import torch
import pickle
from transformers import GPT2LMHeadModel, GPT2Tokenizer
from huggingface_hub import hf_hub_download

# ---------- Load Bigram ----------

def load_bigram(repo_id="bayan10/AutoComplete", filename="bigram_model_v4.pkl"):
    path = hf_hub_download(repo_id=repo_id, filename=filename)
    with open(path, "rb") as f:
        data = pickle.load(f)
    return data["unigrams"], data["bigrams"]

# ---------- Load GPT-2 ----------
def load_gpt2(model_name="aubmindlab/aragpt2-base"):
    tokenizer = GPT2Tokenizer.from_pretrained(model_name)
    model = GPT2LMHeadModel.from_pretrained(model_name)
    tokenizer.pad_token = tokenizer.eos_token
    model.config.pad_token_id = tokenizer.eos_token_id
    model.eval()
    return tokenizer, model

# ---------- GPT-2 scoring ----------
def gpt2_next_token_probs(prefix, tokenizer, model, top_k=50):
    inputs = tokenizer(
        prefix,
        return_tensors="pt",
        truncation=True,
        max_length=1024
    )

    with torch.no_grad():
        outputs = model(**inputs)
        logits = outputs.logits[0, -1]

    probs = torch.softmax(logits, dim=-1)
    top_probs, top_ids = torch.topk(probs, top_k)

    prob_dict = {}
    for idx, prob in zip(top_ids, top_probs):
        word = tokenizer.decode([idx]).strip()
        if word:
            prob_dict[word] = prob.item()

    return prob_dict

# ---------- Statistical autocomplete ----------


def statistical_autocomplete(text, unigrams, bigrams, top_k=20):
    tokens = text.strip().split()
    if not tokens:
        return []

    last_word = tokens[-1]
    candidates = []

    if last_word in bigrams:
        for w, c in bigrams[last_word].items():
            if len(w) < 3 or w == last_word:
                continue
            candidates.append((w, c))

    if not candidates:
        for w, c in unigrams.items():
            if len(w) < 3:
                continue
            candidates.append((w, c))

    total = sum(c for _, c in candidates)
    preds = [(w, c / total) for w, c in candidates]
    preds.sort(key=lambda x: x[1], reverse=True)
    preds = merge_similar_predictions(preds, top_k=top_k)
    return preds[:top_k]

# ---------- Hybrid autocomplete ----------
def hybrid_autocomplete(prefix, unigrams, bigrams, tokenizer, model, alpha=0.6, k=5):
    words = prefix.strip().split()
    if len(words) < 1:
        return []

    last_word = words[-1]
    if last_word not in bigrams:
        return []

    # -------- Statistical (Bigram) --------
    stat_candidates = statistical_autocomplete(
    prefix,
    unigrams,
    bigrams,
    top_k=20
)

    # -------- Neural (GPT-2) — ONCE --------
    gpt2_probs = gpt2_next_token_probs(prefix, tokenizer, model, top_k=50)

    # -------- Hybrid scoring --------
    results = []
    for w, stat_p in stat_candidates:
        neural_p = gpt2_probs.get(w, 1e-8)  # small value if not found
        score = alpha * stat_p + (1 - alpha) * neural_p
        results.append((w, score))

    return sorted(results, key=lambda x: x[1], reverse=True)[:k]

import re
from collections import defaultdict

def canonical_form(word):
    word = re.sub("[إأآا]", "ا", word)
    word = re.sub("ى", "ي", word)
    word = re.sub("ؤ", "و", word)
    word = re.sub("ئ", "ي", word)
    word = re.sub("ة", "ه", word)
    word = re.sub(r"[ًٌٍَُِّْ]", "", word)
    return word



def merge_similar_predictions(preds, top_k=20):
    groups = defaultdict(lambda: {"score": 0.0, "words": []})

    for w, p in preds:
        key = canonical_form(w)
        groups[key]["score"] += p
        groups[key]["words"].append(w)

    merged = sorted(
        groups.values(),
        key=lambda x: x["score"],
        reverse=True
    )

    return [
        (group["words"][0], group["score"])
        for group in merged[:top_k]
    ]







