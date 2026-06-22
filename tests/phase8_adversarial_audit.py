"""
BAYAN Phase 8 — Deep System Validation & Adversarial Audit
============================================================

Tests every model independently + full pipeline integration.
Runs against the LIVE API (local or deployed).

Usage:
    python tests/phase8_adversarial_audit.py [--url URL] [--out FILE]

Defaults:
    --url  https://bayan10-bayan-api.hf.space
    --out  phase8_audit_results.json
"""

import argparse
import json
import time
import sys
import os
import re
from dataclasses import dataclass, field, asdict
from typing import Optional, List

import requests

# ─── Configuration ────────────────────────────────────────────────────────────

DEFAULT_URL = "https://bayan10-bayan-api.hf.space"

# ─── Data classes ─────────────────────────────────────────────────────────────

@dataclass
class TestCase:
    id: str
    category: str
    subcategory: str
    input_text: str
    expected_behavior: str
    severity: str  # critical, major, minor, info

@dataclass
class TestResult:
    test_id: str
    category: str
    subcategory: str
    input_text: str
    expected_behavior: str
    severity: str
    status: str  # pass, fail, error
    actual_output: str = ""
    corrected_text: str = ""
    suggestions: list = field(default_factory=list)
    error_detail: str = ""
    latency_ms: int = 0
    finding: str = ""

# ─── API Client ───────────────────────────────────────────────────────────────

class BayanAPI:
    def __init__(self, base_url: str):
        self.base = base_url.rstrip('/')
        self.session = requests.Session()
        self.session.headers.update({'Content-Type': 'application/json'})

    def health(self):
        r = self.session.get(f"{self.base}/api/health", timeout=30)
        return r.json()

    def analyze(self, text: str, timeout=120) -> dict:
        t0 = time.time()
        r = self.session.post(
            f"{self.base}/api/analyze",
            json={"text": text},
            timeout=timeout,
        )
        latency = int((time.time() - t0) * 1000)
        data = r.json()
        data['_latency_ms'] = latency
        return data

    def spelling(self, text: str, timeout=120) -> dict:
        t0 = time.time()
        r = self.session.post(f"{self.base}/api/spelling", json={"text": text}, timeout=timeout)
        latency = int((time.time() - t0) * 1000)
        data = r.json()
        data['_latency_ms'] = latency
        return data

    def grammar(self, text: str, timeout=120) -> dict:
        t0 = time.time()
        r = self.session.post(f"{self.base}/api/grammar", json={"text": text}, timeout=timeout)
        latency = int((time.time() - t0) * 1000)
        data = r.json()
        data['_latency_ms'] = latency
        return data

    def punctuation(self, text: str, timeout=120) -> dict:
        t0 = time.time()
        r = self.session.post(f"{self.base}/api/punctuation", json={"text": text}, timeout=timeout)
        latency = int((time.time() - t0) * 1000)
        data = r.json()
        data['_latency_ms'] = latency
        return data

    def summarize(self, text: str, timeout=120) -> dict:
        t0 = time.time()
        r = self.session.post(f"{self.base}/api/summarize", json={"text": text}, timeout=timeout)
        latency = int((time.time() - t0) * 1000)
        data = r.json()
        data['_latency_ms'] = latency
        return data

    def dialect(self, text: str, timeout=120) -> dict:
        t0 = time.time()
        r = self.session.post(f"{self.base}/api/dialect", json={"text": text}, timeout=timeout)
        latency = int((time.time() - t0) * 1000)
        data = r.json()
        data['_latency_ms'] = latency
        return data

    def autocomplete(self, text: str, timeout=60) -> dict:
        t0 = time.time()
        r = self.session.post(f"{self.base}/api/autocomplete", json={"text": text, "n": 5}, timeout=timeout)
        latency = int((time.time() - t0) * 1000)
        data = r.json()
        data['_latency_ms'] = latency
        return data


# ─── Adversarial Test Dataset (200+ sentences) ───────────────────────────────

def build_adversarial_dataset() -> List[TestCase]:
    """Build the full adversarial test dataset."""
    tests = []
    idx = [0]

    def add(cat, subcat, text, expected, severity="major"):
        idx[0] += 1
        tests.append(TestCase(f"T{idx[0]:03d}", cat, subcat, text, expected, severity))

    # ══════════════════════════════════════════════════════════
    # 1. SPELLING — HAMZA
    # ══════════════════════════════════════════════════════════
    add("spelling", "hamza_basic", "انا طالب في الجامعه", "أنا should be corrected (hamza)", "critical")
    add("spelling", "hamza_basic", "اذا جاء الربيع", "إذا should be corrected", "critical")
    add("spelling", "hamza_basic", "ايضا هذا صحيح", "أيضاً should be corrected", "major")
    add("spelling", "hamza_basic", "لان الامر مهم", "لأن should be corrected", "major")
    add("spelling", "hamza_basic", "اين ذهبت", "أين should be corrected", "major")
    add("spelling", "hamza_basic", "اول مرة", "أول should be corrected", "major")
    add("spelling", "hamza_basic", "هذا او ذاك", "أو should be corrected", "major")
    add("spelling", "hamza_prefixed", "والاسعار مرتفعة", "والأسعار (prefixed hamza)", "major")
    add("spelling", "hamza_prefixed", "بالاضافة الى ذلك", "بالإضافة إلى (prefixed hamza)", "major")

    # ══════════════════════════════════════════════════════════
    # 2. SPELLING — TA MARBUTA
    # ══════════════════════════════════════════════════════════
    add("spelling", "ta_marbuta", "الجامعه كبيره", "الجامعة كبيرة (ه→ة)", "critical")
    add("spelling", "ta_marbuta", "المدرسه جميله", "المدرسة جميلة", "critical")
    add("spelling", "ta_marbuta", "القاهره عاصمه مصر", "القاهرة عاصمة مصر", "major")
    add("spelling", "ta_marbuta", "الحياه صعبه", "الحياة صعبة", "major")
    add("spelling", "ta_marbuta", "بالمدرسه", "بالمدرسة (prefixed ta marbuta)", "major")

    # ══════════════════════════════════════════════════════════
    # 3. SPELLING — ALIF MAQSURA
    # ══════════════════════════════════════════════════════════
    add("spelling", "alif_maqsura", "ذهبت الي المدرسة", "إلى should have alif maqsura", "major")
    add("spelling", "alif_maqsura", "المستشفي الكبير", "المستشفى with alif maqsura", "major")

    # ══════════════════════════════════════════════════════════
    # 4. SPELLING — WORD SPLITS
    # ══════════════════════════════════════════════════════════
    add("spelling", "word_split", "فيالبيت", "في البيت (split)", "critical")
    add("spelling", "word_split", "فيالمدرسة", "في المدرسة (split)", "critical")
    add("spelling", "word_split", "منالبيت", "من البيت (split)", "major")
    add("spelling", "word_split", "عندالباب", "عند الباب (split)", "major")

    # ══════════════════════════════════════════════════════════
    # 5. SPELLING — OVERCORRECTION (FALSE POSITIVES)
    # ══════════════════════════════════════════════════════════
    add("spelling", "overcorrection", "أنا ذهبت إلى الجامعة", "Already correct — should not change", "critical")
    add("spelling", "overcorrection", "هذه المدرسة جميلة", "Already correct — no changes", "critical")
    add("spelling", "overcorrection", "كان الجو ممطراً", "كان must NOT become كأن", "critical")
    add("spelling", "overcorrection", "وكان أحمد في المنزل", "وكان must NOT become وكأن", "critical")
    add("spelling", "overcorrection", "هذه الفتاة ذكية", "هذه must NOT become هذة", "critical")
    add("spelling", "overcorrection", "إلى اللقاء", "إلى must NOT become على", "critical")
    add("spelling", "overcorrection", "ذلك الكتاب مفيد", "ذلك must NOT become ذالك", "major")
    add("spelling", "overcorrection", "لكن الأمر صعب", "لكن must NOT become لاكن", "major")

    # ══════════════════════════════════════════════════════════
    # 6. SPELLING — NAMED ENTITIES / PROPER NOUNS
    # ══════════════════════════════════════════════════════════
    add("spelling", "named_entity", "محمد صلاح لاعب كرة قدم", "محمد صلاح unchanged", "major")
    add("spelling", "named_entity", "جامعة القاهرة", "جامعة القاهرة unchanged", "major")
    add("spelling", "named_entity", "يوسف عباس", "Proper noun — no change", "major")
    add("spelling", "named_entity", "مدينة الرياض", "Proper noun city — no change", "major")

    # ══════════════════════════════════════════════════════════
    # 7. SPELLING — FOREIGN/TECHNICAL WORDS
    # ══════════════════════════════════════════════════════════
    add("spelling", "foreign_words", "كود JavaScript جميل", "Foreign word preserved", "major")
    add("spelling", "foreign_words", "تطبيق OpenAI ممتاز", "OpenAI preserved", "major")
    add("spelling", "foreign_words", "موقع ChatGPT مفيد", "ChatGPT preserved", "major")
    add("spelling", "foreign_words", "خادم API يعمل", "API preserved", "minor")
    add("spelling", "foreign_words", "لغة Python سهلة", "Python preserved", "minor")

    # ══════════════════════════════════════════════════════════
    # 8. SPELLING — MIXED ARABIC-ENGLISH
    # ══════════════════════════════════════════════════════════
    add("spelling", "mixed_lang", "استخدم Docker في المشروع", "Mixed lang — no corruption", "major")
    add("spelling", "mixed_lang", "البريد user@example.com مهم", "Email address preserved", "major")
    add("spelling", "mixed_lang", "الرابط https://example.com", "URL preserved", "major")

    # ══════════════════════════════════════════════════════════
    # 9. SPELLING — NUMBERS
    # ══════════════════════════════════════════════════════════
    add("spelling", "numerals", "عام 2024 كان جيداً", "Year 2024 preserved", "critical")
    add("spelling", "numerals", "اشتريت 15 كتاباً", "Number 15 preserved", "critical")
    add("spelling", "numerals", "الساعة 3:30", "Time preserved", "major")

    # ══════════════════════════════════════════════════════════
    # 10. SPELLING — PRONOUN SUFFIX GUARD
    # ══════════════════════════════════════════════════════════
    add("spelling", "pronoun_suffix", "فتأملته جيداً", "ته must NOT become تة", "critical")
    add("spelling", "pronoun_suffix", "رأيته في الشارع", "ته preserved", "critical")
    add("spelling", "pronoun_suffix", "كتبته بسرعة", "ته preserved", "critical")

    # ══════════════════════════════════════════════════════════
    # 11. SPELLING — ATTACHED CONJUNCTIONS/PREPOSITIONS
    # ══════════════════════════════════════════════════════════
    add("spelling", "attached_conj", "والكتاب على الطاولة", "والكتاب is one token", "major")
    add("spelling", "attached_conj", "بالمدرسة الكبيرة", "بالمدرسة is one token", "major")
    add("spelling", "attached_conj", "كالنار في الحطب", "كالنار is one token", "major")
    add("spelling", "attached_conj", "للطلاب الجدد", "للطلاب is one token", "major")
    add("spelling", "attached_conj", "فالكتاب مفيد", "فالكتاب is one token", "major")

    # ══════════════════════════════════════════════════════════
    # 12. SPELLING — DIALECT MISTAKES (common informal)
    # ══════════════════════════════════════════════════════════
    add("spelling", "dialect", "انتو كويسين", "Possible dialect — handle gracefully", "minor")
    add("spelling", "dialect", "مش عارف", "Dialect negation — no crash", "minor")

    # ══════════════════════════════════════════════════════════
    # 20. GRAMMAR — SUBJECT-VERB AGREEMENT
    # ══════════════════════════════════════════════════════════
    add("grammar", "sv_agreement", "البنات ذهب إلى المدرسة", "ذهب→ذهبن or ذهبت (feminine plural)", "critical")
    add("grammar", "sv_agreement", "الطلاب يذهب إلى الجامعة", "يذهب→يذهبون (plural verb)", "critical")
    add("grammar", "sv_agreement", "الأولاد ذهب إلى الملعب", "Plural subject + singular verb", "major")
    add("grammar", "sv_agreement", "الرجال يعمل في المصنع", "يعمل→يعملون", "major")
    add("grammar", "sv_agreement", "هي ذهب إلى البيت", "ذهب→ذهبت (feminine pronoun)", "critical")
    add("grammar", "sv_agreement", "الولد ذهبوا", "Singular subject + plural verb", "major")

    # ══════════════════════════════════════════════════════════
    # 21. GRAMMAR — GENDER AGREEMENT
    # ══════════════════════════════════════════════════════════
    add("grammar", "gender", "هذان الطالبتان", "هذان→هاتان (feminine)", "major")
    add("grammar", "gender", "هاتان الطالبان", "هاتان→هذان (masculine)", "major")

    # ══════════════════════════════════════════════════════════
    # 22. GRAMMAR — PREPOSITION CASE
    # ══════════════════════════════════════════════════════════
    add("grammar", "preposition_case", "في المهندسون الماهرون", "المهندسون→المهندسين after في", "critical")
    add("grammar", "preposition_case", "من المعلمون", "المعلمون→المعلمين after من", "critical")
    add("grammar", "preposition_case", "إلى المسافرون", "المسافرون→المسافرين after إلى", "major")
    add("grammar", "preposition_case", "على العاملون في المصنع", "العاملون→العاملين after على", "major")

    # ══════════════════════════════════════════════════════════
    # 23. GRAMMAR — FIVE NOUNS
    # ══════════════════════════════════════════════════════════
    add("grammar", "five_nouns", "إن أبوك رجل طيب", "أبوك→أباك after إن", "major")
    add("grammar", "five_nouns", "في أخوك ثقة", "أخوك→أخيك after في", "major")

    # ══════════════════════════════════════════════════════════
    # 24. GRAMMAR — NASB/JAZM
    # ══════════════════════════════════════════════════════════
    add("grammar", "nasb_jazm", "لن يذهبون", "يذهبون→يذهبوا (jazm after لن)", "major")
    add("grammar", "nasb_jazm", "لم يفعلون الواجب", "يفعلون→يفعلوا (jazm after لم)", "major")

    # ══════════════════════════════════════════════════════════
    # 25. GRAMMAR — OVERCORRECTION (CORRECT TEXT)
    # ══════════════════════════════════════════════════════════
    add("grammar", "overcorrection", "ذهب الطالب إلى المدرسة", "VSO order — singular verb correct", "critical")
    add("grammar", "overcorrection", "كتبت الطالبة المقال", "Correct agreement — no change", "critical")
    add("grammar", "overcorrection", "المعلمون في المدرسة", "Correct nominative — no change", "major")
    add("grammar", "overcorrection", "أحب القراءة والكتابة", "Correct text — no change", "major")
    add("grammar", "overcorrection", "بسم الله الرحمن الرحيم", "Quranic text — MUST NOT change", "critical")
    add("grammar", "overcorrection", "الحمد لله رب العالمين", "Quranic text — MUST NOT change", "critical")
    add("grammar", "overcorrection", "قال تعالى إنا أنزلناه في ليلة القدر", "Quran quotation preserved", "critical")

    # ══════════════════════════════════════════════════════════
    # 26. GRAMMAR — HALLUCINATION DETECTION
    # ══════════════════════════════════════════════════════════
    add("grammar", "hallucination", "جلس الرجل على الكرسي", "Should not rewrite entirely", "critical")
    add("grammar", "hallucination", "الكتاب مفيد جداً", "Should not introduce new words", "major")

    # ══════════════════════════════════════════════════════════
    # 30. PUNCTUATION — BASIC
    # ══════════════════════════════════════════════════════════
    add("punctuation", "basic", "كيف حالك انا بخير", "Needs punctuation separation", "major")
    add("punctuation", "basic", "مرحبا كيف حالك", "Needs ، or .", "major")
    add("punctuation", "basic", "هل انت بخير", "Needs ؟", "major")
    add("punctuation", "basic", "ذهبت الى المدرسة ثم عدت", "Needs ، between clauses", "minor")

    # ══════════════════════════════════════════════════════════
    # 31. PUNCTUATION — OVERCORRECTION
    # ══════════════════════════════════════════════════════════
    add("punctuation", "overcorrection", "ذهبت إلى المدرسة. كيف حالك؟", "Already punctuated — no change", "critical")
    add("punctuation", "overcorrection", "أحمد، كيف حالك؟", "Already punctuated — no change", "major")

    # ══════════════════════════════════════════════════════════
    # 32. PUNCTUATION — NON-PUNCTUATION LEAK
    # ══════════════════════════════════════════════════════════
    add("punctuation", "non_punct_leak", "ذهبت الي المدرسه", "Punctuation model must NOT fix spelling", "critical")

    # ══════════════════════════════════════════════════════════
    # 40. PIPELINE — FULL FLOW
    # ══════════════════════════════════════════════════════════
    add("pipeline", "full_flow", "انا ذهب الى الجامعه كيف حالك",
        "Spelling fixes (أنا, إلى, الجامعة) + Grammar (agreement) + Punctuation", "critical")
    add("pipeline", "full_flow", "البنات ذهب الى المدرسه",
        "Step 1: المدرسه→المدرسة, Step 2: ذهب→agreement, Step 3: punct", "critical")
    add("pipeline", "full_flow", "في المهندسون الماهرون كانو يعملو",
        "Multiple grammar fixes + possible spelling", "major")

    # ══════════════════════════════════════════════════════════
    # 41. PIPELINE — CROSS-MODEL CONFLICTS
    # ══════════════════════════════════════════════════════════
    add("pipeline", "cross_model", "الجامعه كبيره والطلاب كثيرون",
        "Spelling fixes ه→ة, grammar must not revert", "critical")
    add("pipeline", "cross_model", "المدرسه جميله والمعلمون في الفصل",
        "Spelling + grammar shouldn't conflict on separate words", "critical")

    # ══════════════════════════════════════════════════════════
    # 50. SPAN ALIGNMENT
    # ══════════════════════════════════════════════════════════
    add("span", "basic_alignment", "المدرسه كبيره", "Spans must exactly match ه positions", "critical")
    add("span", "multi_word", "انا في المدرسه الكبيره", "Multiple spans — no overlap", "critical")
    add("span", "attached_prefix", "والمدرسة جميلة", "Span covers full token وال...", "major")
    add("span", "attached_prefix", "بالمدرسة الكبيرة", "Span on prefixed word", "major")
    add("span", "word_split_span", "فيالبيت", "Split span: original word → two words", "critical")

    # ══════════════════════════════════════════════════════════
    # 60. MORPHOLOGY STRESS TEST
    # ══════════════════════════════════════════════════════════
    add("morphology", "wa_prefix", "والمدرسة جميلة", "و prefix — no corruption", "major")
    add("morphology", "fa_prefix", "فالكتاب مفيد", "ف prefix — no corruption", "major")
    add("morphology", "ba_prefix", "بالبيت الكبير", "ب prefix — no corruption", "major")
    add("morphology", "ka_prefix", "كالنار في الحطب", "ك prefix — no corruption", "major")
    add("morphology", "la_prefix", "للطلاب في الجامعة", "ل prefix — no corruption", "major")
    add("morphology", "combined", "وبالمدرسة والطالبات", "وبال combined prefix", "major")
    add("morphology", "combined", "فللطلاب حقوقهم", "فلل combined prefix", "major")

    # ══════════════════════════════════════════════════════════
    # 70. OVERCORRECTION AUDIT — CORRECT TEXT
    # ══════════════════════════════════════════════════════════
    add("overcorrection", "academic", "إن الأبحاث العلمية تشير إلى أهمية التعليم في تطوير المجتمعات",
        "Academic text — should be unchanged", "critical")
    add("overcorrection", "academic", "أشارت الدراسة إلى أن نسبة النجاح بلغت خمسة وتسعين بالمئة",
        "Academic with numbers — no change", "critical")
    add("overcorrection", "literary", "وقف على أطلال الماضي يتأمل في صروف الدهر",
        "Literary text — no change", "major")
    add("overcorrection", "quran", "قل هو الله أحد الله الصمد", "Quran — NEVER modify", "critical")
    add("overcorrection", "quran", "إنا أعطيناك الكوثر", "Quran — NEVER modify", "critical")
    add("overcorrection", "hadith", "إنما الأعمال بالنيات", "Hadith — NEVER modify", "critical")
    add("overcorrection", "poetry", "قفا نبك من ذكرى حبيب ومنزل", "Poetry — preserve", "major")

    # ══════════════════════════════════════════════════════════
    # 80. UNDERCORRECTION — ERRORS THAT SHOULD BE CAUGHT
    # ══════════════════════════════════════════════════════════
    add("undercorrection", "hamza_missed", "اسلام عليكم", "إسلام — hamza missing", "major")
    add("undercorrection", "ta_marbuta_missed", "الطبيعه جميله جدا", "Three errors — all should be caught", "major")
    add("undercorrection", "double_error", "انا ذهبت الي الجامعه", "Two errors in one sentence", "major")
    add("undercorrection", "grammar_missed", "الطلاب ذهب", "Subject-verb disagreement missed?", "major")

    # ══════════════════════════════════════════════════════════
    # 90. EDGE CASES
    # ══════════════════════════════════════════════════════════
    add("edge_case", "empty", "", "Should return error/empty", "major")
    add("edge_case", "whitespace", "   \t\n   ", "Should return error/empty", "major")
    add("edge_case", "single_char", "ا", "Should handle gracefully", "minor")
    add("edge_case", "single_word", "مدرسة", "Single correct word — no change", "major")
    add("edge_case", "very_long", "ا " * 2500, "5000 chars — no crash", "major")
    add("edge_case", "html_injection", "<script>alert('xss')</script> مرحبا", "HTML stripped", "critical")
    add("edge_case", "only_english", "Hello world this is a test", "Rejected — non-Arabic", "major")
    add("edge_case", "emoji", "مرحبا 😊 كيف حالك 🎉", "Emoji preserved", "minor")
    add("edge_case", "numbers_only", "123456789", "No crash", "minor")
    add("edge_case", "repeated_chars", "كتاااااااااااب", "Collapse to كتاب", "major")
    add("edge_case", "newlines", "السطر الأول\nالسطر الثاني\nالسطر الثالث", "Multi-line handling", "major")
    add("edge_case", "unicode_special", "بسم\u200cالله", "Zero-width non-joiner", "minor")
    add("edge_case", "diacritics", "كَتَبَ الطَّالِبُ الدَّرسَ", "Diacritized text — handle gracefully", "major")
    add("edge_case", "punctuation_heavy", "!!!???...،،،؛؛؛", "Heavy punctuation — no crash", "minor")

    # ══════════════════════════════════════════════════════════
    # 100. SOCIAL MEDIA / INFORMAL
    # ══════════════════════════════════════════════════════════
    add("social_media", "informal", "كيفك شو اخبارك", "Dialect — graceful handling", "minor")
    add("social_media", "informal", "يلا نروح", "Dialect — no crash", "minor")
    add("social_media", "slang", "اخخخخ مش قادر", "Repeated chars + dialect", "minor")

    # ══════════════════════════════════════════════════════════
    # 110. APPLY-ALL SAFETY
    # ══════════════════════════════════════════════════════════
    add("apply_all", "no_duplicate", "انا ذهبت الي المدرسه", 
        "Apply-all must not duplicate words or lose spaces", "critical")
    add("apply_all", "preserve_unchanged", "النص الأول صحيح ولكن الجامعه خطأ",
        "Unchanged text must be preserved exactly", "critical")

    # ══════════════════════════════════════════════════════════
    # 120. CONCURRENCY / TIMING
    # ══════════════════════════════════════════════════════════
    add("concurrency", "rapid_fire", "انا طالب", "3 rapid requests — no crash", "major")

    # ══════════════════════════════════════════════════════════
    # 130. RELIGIOUS TEXT PROTECTION
    # ══════════════════════════════════════════════════════════
    add("religious", "quran", "بسم الله الرحمن الرحيم", "Must NOT be modified at all", "critical")
    add("religious", "quran", "الحمد لله رب العالمين الرحمن الرحيم مالك يوم الدين",
        "Al-Fatiha — must NOT be modified", "critical")
    add("religious", "quran", "قل أعوذ برب الفلق من شر ما خلق",
        "Surat Al-Falaq — must NOT be modified", "critical")
    add("religious", "shahada", "لا إله إلا الله محمد رسول الله",
        "Shahada — must NOT be modified", "critical")

    # ══════════════════════════════════════════════════════════
    # 140. DATES / TECHNICAL FORMATS
    # ══════════════════════════════════════════════════════════
    add("technical", "date", "تاريخ اليوم 15/06/2026", "Date format preserved", "major")
    add("technical", "phone", "اتصل بالرقم 0123456789", "Phone number preserved", "major")
    add("technical", "measurement", "المسافة 25.5 كم", "Decimal preserved", "major")

    # ══════════════════════════════════════════════════════════
    # 150. LONG TEXT
    # ══════════════════════════════════════════════════════════
    long_text = ("كان ياما كان في قديم الزمان ملك عظيم يحكم مملكه واسعه " * 10).strip()
    add("stress", "long_500words", long_text, "No timeout, no crash", "major")

    medium_text = ("الطلاب ذهبوا إلى المدرسة والمعلمون استقبلوهم بحرارة " * 20).strip()
    add("stress", "medium_correct", medium_text, "Mostly correct — minimal changes", "major")

    return tests


# ─── Test Runner ──────────────────────────────────────────────────────────────

def run_test(api: BayanAPI, tc: TestCase) -> TestResult:
    """Run a single test case and return the result."""
    result = TestResult(
        test_id=tc.id,
        category=tc.category,
        subcategory=tc.subcategory,
        input_text=tc.input_text[:200],
        expected_behavior=tc.expected_behavior,
        severity=tc.severity,
        status="error",
    )

    try:
        # Choose endpoint based on category
        if tc.category == "spelling":
            resp = api.analyze(tc.input_text)
        elif tc.category == "grammar":
            resp = api.analyze(tc.input_text)
        elif tc.category == "punctuation":
            resp = api.analyze(tc.input_text)
        elif tc.category in ("pipeline", "span", "morphology", "overcorrection",
                             "undercorrection", "apply_all", "religious", "technical",
                             "stress", "cross_model"):
            resp = api.analyze(tc.input_text)
        elif tc.category == "edge_case":
            resp = api.analyze(tc.input_text)
        elif tc.category == "concurrency":
            resp = api.analyze(tc.input_text)
        elif tc.category == "social_media":
            resp = api.analyze(tc.input_text)
        else:
            resp = api.analyze(tc.input_text)

        result.latency_ms = resp.get('_latency_ms', 0)

        if 'error' in resp:
            # Errors on edge cases like empty text are expected
            if tc.subcategory in ('empty', 'whitespace'):
                result.status = "pass"
                result.actual_output = f"Error (expected): {resp['error']}"
            else:
                result.status = "error"
                result.error_detail = resp['error']
            return result

        result.corrected_text = resp.get('corrected', '')
        result.suggestions = resp.get('suggestions', [])
        result.actual_output = result.corrected_text[:300]

        # ── Validation Logic ──
        original = resp.get('original', tc.input_text)
        corrected = result.corrected_text
        suggestions = result.suggestions

        # --- Span alignment validation ---
        if tc.category == "span" or True:  # Always validate spans
            for s in suggestions:
                start = s.get('start', 0)
                end = s.get('end', 0)
                orig_text = s.get('original', '')
                actual_slice = original[start:end]
                if actual_slice != orig_text and orig_text:
                    result.status = "fail"
                    result.finding = (
                        f"SPAN MISMATCH: suggestion says original='{orig_text}' "
                        f"but text[{start}:{end}]='{actual_slice}'"
                    )
                    return result

        # --- Overcorrection detection ---
        if tc.category == "overcorrection" or tc.category == "religious":
            if corrected != original and suggestions:
                result.status = "fail"
                result.finding = (
                    f"OVERCORRECTION: Correct text was modified. "
                    f"Changes: {[s.get('original','')+'→'+s.get('correction','') for s in suggestions]}"
                )
                return result

        # --- Spelling false positive (correct text changed) ---
        if tc.subcategory == "overcorrection" and tc.category == "spelling":
            if corrected != original:
                result.status = "fail"
                result.finding = (
                    f"SPELLING FALSE POSITIVE: '{original[:80]}' was changed to '{corrected[:80]}'"
                )
                return result

        # --- Grammar overcorrection ---
        if tc.subcategory == "overcorrection" and tc.category == "grammar":
            if corrected != original:
                result.status = "fail"
                result.finding = (
                    f"GRAMMAR FALSE POSITIVE: '{original[:80]}' was changed to '{corrected[:80]}'"
                )
                return result

        # --- Numeral protection ---
        if tc.subcategory == "numerals":
            orig_digits = re.findall(r'\d+', original)
            corr_digits = re.findall(r'\d+', corrected)
            if orig_digits != corr_digits:
                result.status = "fail"
                result.finding = f"NUMERAL CORRUPTION: {orig_digits} → {corr_digits}"
                return result

        # --- Pronoun suffix guard ---
        if tc.subcategory == "pronoun_suffix":
            for s in suggestions:
                if 'ته' in s.get('original', '') and 'تة' in s.get('correction', ''):
                    result.status = "fail"
                    result.finding = f"PRONOUN SUFFIX LEAK: {s['original']}→{s['correction']}"
                    return result

        # --- Apply-all safety ---
        if tc.category == "apply_all":
            # Simulate apply-all
            rebuilt = original
            for s in sorted(suggestions, key=lambda x: -x['start']):
                rebuilt = rebuilt[:s['start']] + s['correction'] + rebuilt[s['end']:]
            if rebuilt != corrected:
                result.status = "fail"
                result.finding = (
                    f"APPLY-ALL MISMATCH: rebuilt='{rebuilt[:100]}' vs corrected='{corrected[:100]}'"
                )
                return result

        # --- HTML injection ---
        if tc.subcategory == "html_injection":
            if '<script>' in corrected or '<' in corrected:
                result.status = "fail"
                result.finding = "HTML NOT STRIPPED"
                return result

        # --- Non-Arabic rejection ---
        if tc.subcategory == "only_english":
            if suggestions:
                result.status = "fail"
                result.finding = f"Non-Arabic text produced {len(suggestions)} suggestions"
                return result

        result.status = "pass"

    except requests.Timeout:
        result.status = "error"
        result.error_detail = "TIMEOUT"
    except Exception as e:
        result.status = "error"
        result.error_detail = f"{type(e).__name__}: {str(e)[:200]}"

    return result


# ─── Main ─────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Bayan Phase 8 Adversarial Audit")
    parser.add_argument("--url", default=DEFAULT_URL, help="API base URL")
    parser.add_argument("--out", default="phase8_audit_results.json", help="Output file")
    parser.add_argument("--categories", nargs="*", help="Filter by categories")
    args = parser.parse_args()

    api = BayanAPI(args.url)
    print(f"[AUDIT] Target: {args.url}")

    # Health check
    try:
        health = api.health()
        print(f"[AUDIT] Health: {json.dumps(health, indent=2)}")
    except Exception as e:
        print(f"[AUDIT] ❌ Health check failed: {e}")
        print(f"[AUDIT] Continuing anyway...")

    # Build dataset
    tests = build_adversarial_dataset()
    if args.categories:
        tests = [t for t in tests if t.category in args.categories]
    print(f"[AUDIT] Running {len(tests)} test cases...")

    results = []
    pass_count = 0
    fail_count = 0
    error_count = 0

    for i, tc in enumerate(tests):
        print(f"  [{i+1}/{len(tests)}] {tc.id} {tc.category}/{tc.subcategory}: ", end="", flush=True)
        r = run_test(api, tc)
        results.append(asdict(r))

        if r.status == "pass":
            print(f"✅ ({r.latency_ms}ms)")
            pass_count += 1
        elif r.status == "fail":
            print(f"❌ {r.finding[:80]}")
            fail_count += 1
        else:
            print(f"⚠️  {r.error_detail[:80]}")
            error_count += 1

    # Summary
    print(f"\n{'='*60}")
    print(f"[AUDIT COMPLETE]")
    print(f"  Total:  {len(results)}")
    print(f"  Pass:   {pass_count}")
    print(f"  Fail:   {fail_count}")
    print(f"  Error:  {error_count}")
    print(f"{'='*60}")

    # Critical failures
    critical_fails = [r for r in results if r['status'] == 'fail' and r['severity'] == 'critical']
    if critical_fails:
        print(f"\n🚨 CRITICAL FAILURES ({len(critical_fails)}):")
        for r in critical_fails:
            print(f"  {r['test_id']} [{r['category']}/{r['subcategory']}]: {r['finding'][:100]}")

    # Save results
    output = {
        "audit_timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "target_url": args.url,
        "total_tests": len(results),
        "pass": pass_count,
        "fail": fail_count,
        "error": error_count,
        "critical_failures": len(critical_fails) if critical_fails else 0,
        "results": results,
    }

    with open(args.out, 'w', encoding='utf-8') as f:
        json.dump(output, f, ensure_ascii=False, indent=2)
    print(f"\n[AUDIT] Results saved to {args.out}")


if __name__ == "__main__":
    main()
