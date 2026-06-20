"""
AutoComplete Rules — text processing utilities for Arabic autocomplete.
Completely independent from the correction pipeline.
"""

import re
from collections import defaultdict


def canonical_form(word: str) -> str:
    """
    Normalize Arabic word to a canonical form for deduplication.
    Collapses hamza variants, ta marbuta, alef maqsura, and diacritics.
    """
    word = re.sub("[إأآا]", "ا", word)
    word = re.sub("ى", "ي", word)
    word = re.sub("ؤ", "و", word)
    word = re.sub("ئ", "ي", word)
    word = re.sub("ة", "ه", word)
    word = re.sub(r"[ًٌٍَُِّْ]", "", word)
    return word


def merge_similar_predictions(preds: list, top_k: int = 20) -> list:
    """
    Merge predictions that differ only in diacritics/hamza variants.
    Groups by canonical form, sums scores, keeps the first surface form.
    """
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


def filter_suggestions(suggestions: list, min_len: int = 2, max_len: int = 30) -> list:
    """
    Filter autocomplete suggestions:
    - Remove too-short or too-long words
    - Remove non-Arabic words
    - Remove punctuation-only tokens
    """
    ARABIC_RE = re.compile(r'[\u0600-\u06FF]')
    filtered = []
    for word, score in suggestions:
        word = word.strip()
        if not word or len(word) < min_len or len(word) > max_len:
            continue
        if not ARABIC_RE.search(word):
            continue
        # Skip punctuation-only or whitespace-only
        if all(c in '.,;:!?،؛؟!.:«»"\'()-–—… \t\n' for c in word):
            continue
        filtered.append((word, score))
    return filtered


def extract_context(text: str, max_chars: int = 200) -> str:
    """
    Extract the last N characters of text, trimmed to a word boundary.
    This is the context sent to the autocomplete model.
    """
    if not text or len(text) <= max_chars:
        return text.strip()

    # Take last max_chars characters
    snippet = text[-max_chars:]

    # Trim to word boundary (don't send a partial word at the start)
    first_space = snippet.find(' ')
    if first_space > 0 and first_space < len(snippet) // 2:
        snippet = snippet[first_space + 1:]

    return snippet.strip()
