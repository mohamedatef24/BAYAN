"""
autocomplete_service.py — Arabic Autocomplete Service
Lazy-loaded singleton backed by:
  1. Hybrid Engine: Bigram (bayan10/AutoComplete) + AraGPT-2 (aubmindlab/aragpt2-base)
  2. Rule-based fallback: prefix-match on curated Arabic word list (always available)

Set LOAD_AUTOCOMPLETE=true in environment to load the bigram + GPT-2 hybrid.
Without it, the rule-based fallback is used instantly with no network call.
"""

import logging
import time
import re
import os

import threading

logger = logging.getLogger(__name__)

# ── Lazy-loaded singletons ─────────────────────────────────────────────────
_autocomplete_engine = None
_load_error = None
_load_lock = threading.Lock()


# ─────────────────────────────────────────────────────────────────────────────
# RULE-BASED FALLBACK — instant, no model needed
# ─────────────────────────────────────────────────────────────────────────────

ARABIC_FREQUENT_WORDS = [
    # Demonstratives / relative / particles
    "الذي", "التي", "الذين", "اللواتي", "اللتان", "اللذان",
    "في", "من", "على", "إلى", "عن", "مع", "بعد", "قبل", "خلال",
    "حتى", "منذ", "بين", "حول", "تحت", "فوق", "أمام", "وراء", "دون",
    "و", "أو", "لكن", "ثم", "بل", "لا", "ما", "لم", "لن",
    "إن", "أن", "كأن", "لأن", "حيث", "إذا", "لو", "لما",
    # Common nouns
    "الكتاب", "الكلام", "المدرسة", "البيت", "الباب", "العلم",
    "الإنسان", "المعلم", "الطالب", "الطالبة", "الأستاذ", "الأستاذة",
    "الوقت", "اليوم", "الليل", "النهار", "السنة", "الشهر",
    "المدينة", "القرية", "البلد", "الدولة", "الحكومة", "الشعب",
    "العمل", "المنزل", "الأسرة", "العائلة", "الأب", "الأم",
    "الابن", "البنت", "الأخ", "الأخت", "الصديق", "الصديقة",
    "الطريق", "السيارة", "الحياة", "الموت", "الحرب", "السلام",
    "الماء", "الهواء", "الشمس", "القمر", "النجوم", "السماء",
    "الأرض", "البحر", "الجبل", "النهر", "الغابة", "الصحراء",
    "المال", "الغذاء", "الصحة", "المرض", "الدواء", "المستشفى",
    "القانون", "الحق", "الحقيقة", "المعرفة", "الثقافة", "التاريخ",
    "اللغة", "العربية", "الكلمة", "الجملة", "النص", "الكتابة",
    "القراءة", "الفهم", "التعلم", "التعليم", "الجامعة", "الكلية",
    "الإسلام", "الدين", "الله", "الرسول", "القرآن", "الصلاة",
    "المسجد", "مكة", "المدينة",
    "مصر", "السعودية", "الأردن", "سوريا", "لبنان", "العراق",
    "فلسطين", "المغرب", "تونس", "الجزائر", "ليبيا",
    # Verbs
    "قال", "قالت", "يقول", "تقول", "قالوا",
    "كان", "كانت", "يكون", "تكون", "كانوا",
    "ذهب", "ذهبت", "يذهب", "تذهب",
    "جاء", "جاءت", "يجيء", "تجيء",
    "أخذ", "أخذت", "يأخذ", "تأخذ",
    "علم", "علمت", "يعلم", "تعلم",
    "كتب", "كتبت", "يكتب", "تكتب",
    "قرأ", "قرأت", "يقرأ", "تقرأ",
    "سمع", "سمعت", "يسمع", "تسمع",
    "رأى", "رأت", "يرى", "ترى",
    "عمل", "عملت", "يعمل", "تعمل",
    "وجد", "وجدت", "يجد", "تجد",
    "أراد", "أرادت", "يريد", "تريد",
    "استطاع", "استطاعت", "يستطيع", "تستطيع",
    "يمكن", "يجب", "ينبغي", "يستحق",
    "أحب", "أحبت", "يحب", "تحب",
    "حاول", "حاولت", "يحاول", "تحاول",
    "تحدث", "تحدثت", "يتحدث", "تتحدث",
    "أجاب", "أجابت", "يجيب", "تجيب",
    "سأل", "سألت", "يسأل", "تسأل",
    "فهم", "فهمت", "يفهم", "تفهم",
    "فكر", "فكرت", "يفكر", "تفكر",
    # Adjectives
    "كبير", "كبيرة", "صغير", "صغيرة",
    "جديد", "جديدة", "قديم", "قديمة",
    "جميل", "جميلة", "طويل", "طويلة",
    "قصير", "قصيرة", "سريع", "سريعة",
    "صعب", "صعبة", "سهل", "سهلة",
    "مهم", "مهمة", "ضروري", "ضرورية",
    "ممتاز", "ممتازة", "رائع", "رائعة",
    "جيد", "جيدة", "قوي", "قوية",
    "ضعيف", "ضعيفة", "واضح", "واضحة",
    "مختلف", "مختلفة", "متشابه", "متشابهة",
    "أول", "أولى", "أخير", "أخيرة",
    "كثير", "كثيرة", "قليل", "قليلة",
    # Common adverbs / connectors
    "أيضاً", "كذلك", "فقط", "أحياناً", "دائماً", "أبداً",
    "جداً", "تماماً", "بالضبط", "هنا", "هناك",
    "الآن", "اليوم", "غداً", "أمس", "قريباً",
    "لذلك", "بسبب", "نتيجة", "رغم", "بينما",
    "عندما", "حينما", "مثل", "كما", "وكذلك",
    "أولاً", "ثانياً", "ثالثاً", "أخيراً",
    # Numbers
    "واحد", "اثنان", "ثلاثة", "أربعة", "خمسة",
    "ستة", "سبعة", "ثمانية", "تسعة", "عشرة",
    "عشرون", "ثلاثون", "مئة", "ألف", "مليون",
]

_WORD_INDEX = sorted(ARABIC_FREQUENT_WORDS)


class RuleBasedAutocomplete:
    """Instant prefix-based Arabic autocomplete using curated word list."""

    def __init__(self):
        self.word_list = _WORD_INDEX

    def predict(self, text: str, n: int = 5):
        if not text or not text.strip():
            return []
        words = text.strip().split()
        partial = words[-1] if words else ""
        partial_clean = re.sub(r'[\u064B-\u0652]', '', partial)
        if len(partial_clean) < 1:
            return []
        suggestions = [
            w for w in self.word_list
            if re.sub(r'[\u064B-\u0652]', '', w).startswith(partial_clean)
            and w != partial
        ]
        if len(suggestions) < n and len(partial_clean) >= 3:
            extra = [
                w for w in self.word_list
                if partial_clean in re.sub(r'[\u064B-\u0652]', '', w)
                and w not in suggestions and w != partial
            ]
            suggestions.extend(extra)
        return suggestions[:n]


# ─────────────────────────────────────────────────────────────────────────────
# HYBRID ENGINE — Bigram + AraGPT-2
# ─────────────────────────────────────────────────────────────────────────────

class HybridAutocompleteEngine:
    """
    Wraps hybrid_module.py:
      - Bigram data from HF Hub: bayan10/AutoComplete / bigram_model_v4.pkl
      - GPT-2: aubmindlab/aragpt2-base
    """

    def __init__(self):
        from nlp.autocomplete.hybrid_module import (
            load_bigram,
            load_gpt2,
            hybrid_autocomplete,
            statistical_autocomplete,
        )
        self._hybrid_autocomplete = hybrid_autocomplete
        self._statistical_autocomplete = statistical_autocomplete

        logger.info("[Autocomplete] Loading bigram model from HF: bayan10/AutoComplete...")
        self.unigrams, self.bigrams = load_bigram()
        logger.info(f"[Autocomplete] Bigram loaded: {len(self.bigrams)} bigram contexts, {len(self.unigrams)} unigrams")

        logger.info("[Autocomplete] Loading AraGPT-2 (aubmindlab/aragpt2-base)...")
        self.tokenizer, self.model = load_gpt2()
        logger.info("[Autocomplete] AraGPT-2 ready")

    def predict(self, text: str, n: int = 5):
        """Run hybrid autocomplete (bigram + GPT-2) and return top-n word strings."""
        try:
            results = self._hybrid_autocomplete(
                text,
                self.unigrams,
                self.bigrams,
                self.tokenizer,
                self.model,
                alpha=0.6,
                k=n,
            )
            # results: list of (word, score) tuples
            words = [w for (w, _score) in results if w]
            if words:
                return words

            # Fallback to pure statistical if hybrid returned nothing
            stat = self._statistical_autocomplete(text, self.unigrams, self.bigrams, top_k=n)
            return [w for (w, _) in stat if w][:n]
        except Exception as e:
            logger.warning(f"[Autocomplete] Hybrid predict failed: {e}")
            return []


# ─────────────────────────────────────────────────────────────────────────────
# UNIFIED SERVICE
# ─────────────────────────────────────────────────────────────────────────────

class AutocompleteService:
    """Unified interface: tries hybrid engine first, falls back to rule-based."""

    def __init__(self, hybrid_engine=None, fallback=None):
        self.hybrid = hybrid_engine
        self.fallback = fallback or RuleBasedAutocomplete()
        mode = "Hybrid (bigram+GPT2)" if self.hybrid else "Rule-based fallback"
        logger.info(f"[Autocomplete] Service ready — mode: {mode}")

    def predict(self, text: str, n: int = 5):
        if self.hybrid:
            try:
                results = self.hybrid.predict(text, n=n)
                if results:
                    logger.debug(f"[Autocomplete] Hybrid returned {len(results)}: {results}")
                    return results
            except Exception as e:
                logger.warning(f"[Autocomplete] Hybrid failed, using fallback: {e}")
        results = self.fallback.predict(text, n=n)
        logger.debug(f"[Autocomplete] Fallback returned {len(results)}: {results}")
        return results

    def correct(self, text: str) -> str:
        """Compat alias for pipeline compatibility."""
        suggestions = self.predict(text, n=1)
        return suggestions[0] if suggestions else text


# ─────────────────────────────────────────────────────────────────────────────
# LAZY SINGLETON
# ─────────────────────────────────────────────────────────────────────────────

def get_autocomplete_model() -> AutocompleteService:
    """
    Lazy-load autocomplete service.
    - If LOAD_AUTOCOMPLETE=true: loads Hybrid (bigram+AraGPT-2) from HF Hub
    - Otherwise: uses instant rule-based engine (no network required)
    Always returns a working service — never raises.
    """
    global _autocomplete_engine, _load_error, _load_lock

    if _autocomplete_engine is not None:
        return _autocomplete_engine

    with _load_lock:
        if _autocomplete_engine is not None:
            return _autocomplete_engine

        t0 = time.time()
        logger.info("[Autocomplete] Initializing service (lazy)...")

        hybrid_engine = None
        load_hybrid = os.environ.get("LOAD_AUTOCOMPLETE", "false").lower() == "true"

        if load_hybrid:
            try:
                logger.info("[Autocomplete] LOAD_AUTOCOMPLETE=true — loading Hybrid engine...")
                hybrid_engine = HybridAutocompleteEngine()
            except Exception as e:
                _load_error = str(e)
                logger.warning(f"[Autocomplete] Hybrid load failed: {e} — falling back to rule-based")
                hybrid_engine = None
        else:
            logger.info("[Autocomplete] LOAD_AUTOCOMPLETE not set — using rule-based engine")

        _autocomplete_engine = AutocompleteService(
            hybrid_engine=hybrid_engine,
            fallback=RuleBasedAutocomplete()
        )

        elapsed = time.time() - t0
        logger.info(f"[Autocomplete] Service ready in {elapsed:.2f}s")
        return _autocomplete_engine


def is_loaded() -> bool:
    return _autocomplete_engine is not None


def get_load_error() -> str:
    return _load_error or ""


def reset() -> None:
    global _autocomplete_engine, _load_error
    _autocomplete_engine = None
    _load_error = None
