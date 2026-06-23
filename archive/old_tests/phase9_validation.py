"""
BAYAN Phase 9 — Scientific Validation & Adversarial Benchmarking
=================================================================
Tests each model INDEPENDENTLY + full pipeline.
Produces precision/recall/F1 metrics with real API responses.

Usage:
    python tests/phase9_validation.py --url URL [--phase A|B|C|D|E|ALL]
"""

import argparse, json, time, re, sys, os
import requests
from dataclasses import dataclass, field, asdict
from typing import List, Optional, Dict, Tuple

# ─── Config ───────────────────────────────────────────────────────────────────
DEFAULT_URL = "https://bayan10-bayan-api.hf.space"

# ─── API Client ───────────────────────────────────────────────────────────────
class API:
    def __init__(self, base):
        self.base = base.rstrip('/')
        self.s = requests.Session()
        self.s.headers['Content-Type'] = 'application/json'

    def _post(self, endpoint, payload, timeout=180):
        t0 = time.time()
        try:
            r = self.s.post(f"{self.base}{endpoint}", json=payload, timeout=timeout)
            ms = int((time.time()-t0)*1000)
            d = r.json(); d['_ms'] = ms; d['_status'] = r.status_code
            return d
        except requests.Timeout:
            return {'error': 'TIMEOUT', '_ms': int((time.time()-t0)*1000), '_status': 0}
        except Exception as e:
            return {'error': str(e), '_ms': int((time.time()-t0)*1000), '_status': 0}

    def health(self): return self._post('/api/health', {})
    def spelling(self, text): return self._post('/api/spelling', {'text': text})
    def grammar(self, text): return self._post('/api/grammar', {'text': text})
    def punctuation(self, text): return self._post('/api/punctuation', {'text': text})
    def analyze(self, text): return self._post('/api/analyze', {'text': text})
    def summarize(self, text): return self._post('/api/summarize', {'text': text, 'length': 'short'})
    def dialect(self, text): return self._post('/api/dialect', {'text': text})
    def autocomplete(self, text): return self._post('/api/autocomplete', {'text': text, 'n': 5})

# ─── Test Case ────────────────────────────────────────────────────────────────
@dataclass
class TC:
    id: str
    phase: str
    category: str
    input: str
    expected_output: str = ""
    should_change: bool = True  # True=error should be fixed, False=correct text, no change
    error_words: list = field(default_factory=list)  # words that should be corrected
    correct_words: list = field(default_factory=list)  # words that must NOT change

@dataclass
class Result:
    tc_id: str; phase: str; category: str
    input: str; expected: str
    actual_output: str = ""
    changed: bool = False
    suggestions: list = field(default_factory=list)
    latency_ms: int = 0
    verdict: str = ""  # TP, FP, TN, FN, ERROR
    detail: str = ""
    api_status: int = 0
    raw_response: dict = field(default_factory=dict)

# ═══════════════════════════════════════════════════════════════════════════════
# PHASE A — RAW SPELLING MODEL VALIDATION
# ═══════════════════════════════════════════════════════════════════════════════
def build_spelling_tests() -> List[TC]:
    T = []
    n = [0]
    def add(cat, inp, exp, should_change=True, err=None, correct=None):
        n[0]+=1
        T.append(TC(f"A{n[0]:03d}", "A", cat, inp, exp, should_change,
                     err or [], correct or []))

    # ── A1: Hamza errors (SHOULD be corrected) ──
    add("hamza", "انا طالب في الجامعة", "أنا طالب في الجامعة", True, ["انا"])
    add("hamza", "اذا جاء الربيع تزهر الأشجار", "إذا جاء الربيع تزهر الأشجار", True, ["اذا"])
    add("hamza", "ايضا هذا الأمر مهم جداً", "أيضاً هذا الأمر مهم جداً", True, ["ايضا"])
    add("hamza", "لان الأمر يتعلق بالمستقبل", "لأن الأمر يتعلق بالمستقبل", True, ["لان"])
    add("hamza", "اين ذهبت أمس", "أين ذهبت أمس", True, ["اين"])
    add("hamza", "اول مرة أزور هذا المكان", "أول مرة أزور هذا المكان", True, ["اول"])
    add("hamza", "هذا او ذاك لا فرق", "هذا أو ذاك لا فرق", True, ["او"])
    add("hamza", "اكبر مدينة في العالم", "أكبر مدينة في العالم", True, ["اكبر"])
    add("hamza", "اصغر طالب في الصف", "أصغر طالب في الصف", True, ["اصغر"])
    add("hamza", "ابناء الوطن يعملون بجد", "أبناء الوطن يعملون بجد", True, ["ابناء"])
    add("hamza", "اطفال المدرسة يلعبون", "أطفال المدرسة يلعبون", True, ["اطفال"])
    add("hamza", "اخيراً وصلنا إلى الهدف", "أخيراً وصلنا إلى الهدف", True, ["اخيراً"])
    add("hamza", "وقف امام المدرسة", "وقف أمام المدرسة", True, ["امام"])
    # Prefixed hamza
    add("hamza_prefix", "والاسعار مرتفعة جداً", "والأسعار مرتفعة جداً", True, ["والاسعار"])
    add("hamza_prefix", "بالاضافة إلى ذلك", "بالإضافة إلى ذلك", True, ["بالاضافة"])
    add("hamza_prefix", "فالانسان يحتاج للعلم", "فالإنسان يحتاج للعلم", True, ["فالانسان"])

    # ── A2: Ta Marbuta errors ──
    add("ta_marbuta", "المدرسه كبيره وجميله", "المدرسة كبيرة وجميلة", True, ["المدرسه","كبيره","جميله"])
    add("ta_marbuta", "الجامعه في القاهره", "الجامعة في القاهرة", True, ["الجامعه","القاهره"])
    add("ta_marbuta", "السياره سريعه جداً", "السيارة سريعة جداً", True, ["السياره","سريعه"])
    add("ta_marbuta", "الشجره طويله", "الشجرة طويلة", True, ["الشجره","طويله"])
    add("ta_marbuta", "الحياه صعبه في المدينه", "الحياة صعبة في المدينة", True, ["الحياه","صعبه","المدينه"])
    add("ta_marbuta", "بالمدرسه الكبيره", "بالمدرسة الكبيرة", True, ["بالمدرسه","الكبيره"])

    # ── A3: Alif Maqsura ──
    add("alif_maqsura", "ذهبت الي المكتبة", "ذهبت إلى المكتبة", True, ["الي"])
    add("alif_maqsura", "المستشفي الكبير", "المستشفى الكبير", True, ["المستشفي"])
    add("alif_maqsura", "هدي الطالبة ممتاز", "هدى الطالبة ممتاز", True, ["هدي"])

    # ── A4: Word Splits ──
    add("word_split", "ذهبت فيالبيت", "ذهبت في البيت", True, ["فيالبيت"])
    add("word_split", "خرج منالمدرسة", "خرج من المدرسة", True, ["منالمدرسة"])
    add("word_split", "بقي عندالباب", "بقي عند الباب", True, ["عندالباب"])

    # ── A5: Correct text — MUST NOT change (overcorrection tests) ──
    add("correct_text", "أنا ذهبت إلى الجامعة", "أنا ذهبت إلى الجامعة", False, correct=["أنا","ذهبت","إلى","الجامعة"])
    add("correct_text", "هذه المدرسة جميلة جداً", "هذه المدرسة جميلة جداً", False, correct=["هذه","المدرسة","جميلة"])
    add("correct_text", "كان الجو ممطراً اليوم", "كان الجو ممطراً اليوم", False, correct=["كان"])
    add("correct_text", "وكان أحمد في المنزل", "وكان أحمد في المنزل", False, correct=["وكان"])
    add("correct_text", "إلى اللقاء يا صديقي", "إلى اللقاء يا صديقي", False, correct=["إلى"])
    add("correct_text", "ذلك الكتاب مفيد جداً", "ذلك الكتاب مفيد جداً", False, correct=["ذلك"])
    add("correct_text", "لكن الأمر صعب علينا", "لكن الأمر صعب علينا", False, correct=["لكن"])
    add("correct_text", "هذا أو ذاك سواء عندي", "هذا أو ذاك سواء عندي", False, correct=["أو"])

    # ── A6: Pronoun suffix guard ──
    add("pronoun_guard", "فتأملته جيداً في المساء", "فتأملته جيداً في المساء", False, correct=["فتأملته"])
    add("pronoun_guard", "رأيته في الشارع أمس", "رأيته في الشارع أمس", False, correct=["رأيته"])
    add("pronoun_guard", "كتبته بسرعة كبيرة", "كتبته بسرعة كبيرة", False, correct=["كتبته"])
    add("pronoun_guard", "سمعته يتحدث بوضوح", "سمعته يتحدث بوضوح", False, correct=["سمعته"])

    # ── A7: Named Entities ──
    add("named_entity", "محمد صلاح لاعب كرة قدم مصري", "", False, correct=["محمد","صلاح"])
    add("named_entity", "جامعة القاهرة من أعرق الجامعات", "", False, correct=["القاهرة"])
    add("named_entity", "مدينة الرياض عاصمة المملكة", "", False, correct=["الرياض"])
    add("named_entity", "عبدالله يدرس في الجامعة", "", False, correct=["عبدالله"])

    # ── A8: Numbers ──
    add("numbers", "عام 2024 كان جيداً جداً", "", False, correct=["2024"])
    add("numbers", "اشتريت 15 كتاباً من المعرض", "", False, correct=["15"])
    add("numbers", "الساعة 3:30 مساءً بالضبط", "", False, correct=["3:30"])

    # ── A9: Technical / Foreign ──
    add("foreign", "أستخدم Python في البرمجة", "", False, correct=["Python"])
    add("foreign", "تطبيق OpenAI ممتاز جداً", "", False, correct=["OpenAI"])
    add("foreign", "خادم Docker يعمل بنجاح", "", False, correct=["Docker"])
    add("foreign", "إطار TensorFlow مفيد للتعلم", "", False, correct=["TensorFlow"])

    # ── A10: Mixed Arabic/English ──
    add("mixed", "البريد user@example.com مهم جداً", "", False, correct=["user@example.com"])
    add("mixed", "الرابط https://google.com يعمل", "", False, correct=["https://google.com"])
    add("mixed", "الهاشتاق #الذكاء_الاصطناعي مهم", "", False, correct=["#الذكاء_الاصطناعي"])

    # ── A11: Religious text — MUST NOT change ──
    add("religious", "بسم الله الرحمن الرحيم", "بسم الله الرحمن الرحيم", False, correct=["بسم","الله","الرحمن","الرحيم"])
    add("religious", "الحمد لله رب العالمين", "الحمد لله رب العالمين", False, correct=["الحمد","لله","رب","العالمين"])
    add("religious", "لا إله إلا الله محمد رسول الله", "", False, correct=["إله","إلا","الله","محمد","رسول"])
    add("religious", "إنما الأعمال بالنيات", "", False, correct=["إنما","الأعمال","بالنيات"])

    # ── A12: Repeated chars ──
    add("repeated", "كتاااااب جميييل", "كتاب جميل", True, ["كتاااااب","جميييل"])

    # ── A13: Edge cases ──
    add("edge", "مدرسة", "مدرسة", False, correct=["مدرسة"])
    add("edge", "ا ب ت ث ج ح خ", "", False)
    add("edge", "😊 مرحبا 🎉 كيف حالك", "", False)

    return T

# ═══════════════════════════════════════════════════════════════════════════════
# PHASE B — RAW GRAMMAR MODEL VALIDATION
# ═══════════════════════════════════════════════════════════════════════════════
def build_grammar_tests() -> List[TC]:
    T = []
    n = [0]
    def add(cat, inp, exp, should_change=True, err=None, correct=None):
        n[0]+=1
        T.append(TC(f"B{n[0]:03d}", "B", cat, inp, exp, should_change,
                     err or [], correct or []))

    # ── B1: Subject-Verb Agreement (errors) ──
    add("sv_agree", "البنات ذهب إلى المدرسة", "", True, ["ذهب"])
    add("sv_agree", "الطلاب يذهب إلى الجامعة", "", True, ["يذهب"])
    add("sv_agree", "المهندسون حضر الاجتماع", "", True, ["حضر"])
    add("sv_agree", "الرجال يعمل في المصنع", "", True, ["يعمل"])
    add("sv_agree", "النساء ذهب إلى السوق", "", True, ["ذهب"])
    add("sv_agree", "الأولاد لعب في الحديقة", "", True, ["لعب"])

    # ── B2: Gender Agreement (errors) ──
    add("gender", "السيارة جميل والبيت كبير", "", True, ["جميل"])
    add("gender", "البنت ذكي في المدرسة", "", True, ["ذكي"])
    add("gender", "الطالبة متفوق في دراسته", "", True, ["متفوق"])

    # ── B3: Preposition Case (errors) ──
    add("case", "في المهندسون الماهرون جداً", "", True, ["المهندسون"])
    add("case", "من المعلمون الأكفاء في المدرسة", "", True, ["المعلمون"])
    add("case", "إلى المسافرون في المطار", "", True, ["المسافرون"])
    add("case", "على العاملون في المصنع", "", True, ["العاملون"])

    # ── B4: Five Nouns (errors) ──
    add("five_nouns", "إن أبوك رجل طيب جداً", "", True, ["أبوك"])
    add("five_nouns", "رأيت أخوك في المسجد أمس", "", True, ["أخوك"])

    # ── B5: Dual Forms (errors) ──
    add("dual", "هذان الطالبتان مجتهدتان", "", True, ["هذان"])
    add("dual", "هاتان الطالبان مجتهدان", "", True, ["هاتان"])

    # ── B6: Nasb/Jazm (errors) ──
    add("nasb", "لن يذهبون إلى المدرسة غداً", "", True, ["يذهبون"])
    add("nasb", "لم يفعلون الواجب بعد", "", True, ["يفعلون"])

    # ── B7: Correct grammar — MUST NOT change ──
    add("correct", "ذهب الطالب إلى المدرسة", "", False, correct=["ذهب","الطالب"])
    add("correct", "كتبت الطالبة المقال بنجاح", "", False, correct=["كتبت","الطالبة"])
    add("correct", "المعلمون في المدرسة يعملون", "", False, correct=["المعلمون","يعملون"])
    add("correct", "أحب القراءة والكتابة كثيراً", "", False, correct=["أحب","القراءة","والكتابة"])
    add("correct", "ذهبت البنات إلى المدرسة", "", False, correct=["ذهبت","البنات"])
    add("correct", "جاء المعلمون إلى الفصل", "", False, correct=["جاء","المعلمون"])

    # ── B8: Quranic text — MUST NOT change ──
    add("quran", "بسم الله الرحمن الرحيم", "", False, correct=["بسم","الله","الرحمن","الرحيم"])
    add("quran", "قل هو الله أحد الله الصمد", "", False)
    add("quran", "إنا أنزلناه في ليلة القدر", "", False)
    add("quran", "قل أعوذ برب الفلق من شر ما خلق", "", False)
    add("quran", "الحمد لله رب العالمين الرحمن الرحيم مالك يوم الدين", "", False)

    # ── B9: Hadith — MUST NOT change ──
    add("hadith", "إنما الأعمال بالنيات وإنما لكل امرئ ما نوى", "", False)
    add("hadith", "خيركم من تعلم القرآن وعلمه", "", False)

    # ── B10: Poetry — MUST NOT change ──
    add("poetry", "قفا نبك من ذكرى حبيب ومنزل", "", False)
    add("poetry", "على قدر أهل العزم تأتي العزائم", "", False)

    # ── B11: Academic Arabic — MUST NOT change ──
    add("academic", "إن الأبحاث العلمية تشير إلى أهمية التعليم في تطوير المجتمعات الحديثة", "", False)
    add("academic", "أشارت الدراسة إلى أن نسبة النجاح بلغت خمسة وتسعين بالمئة", "", False)
    add("academic", "تهدف هذه الدراسة إلى تحليل العوامل المؤثرة في جودة التعليم العالي", "", False)

    # ── B12: News Arabic — MUST NOT change ──
    add("news", "أعلن رئيس الوزراء عن خطة اقتصادية جديدة لتطوير البنية التحتية", "", False)
    add("news", "شهدت المنطقة تطورات ميدانية متسارعة خلال الأيام الماضية", "", False)

    return T

# ═══════════════════════════════════════════════════════════════════════════════
# PHASE C — RAW PUNCTUATION MODEL VALIDATION
# ═══════════════════════════════════════════════════════════════════════════════
def build_punctuation_tests() -> List[TC]:
    T = []
    n = [0]
    def add(cat, inp, exp, should_change=True, err=None, correct=None):
        n[0]+=1
        T.append(TC(f"C{n[0]:03d}", "C", cat, inp, exp, should_change,
                     err or [], correct or []))

    # ── C1: Missing punctuation (should add) ──
    add("missing_period", "ذهبت إلى المدرسة ثم عدت إلى البيت", "", True)
    add("missing_question", "هل أنت بخير يا صديقي", "", True)
    add("missing_comma", "مرحبا كيف حالك اليوم", "", True)
    add("missing_multi", "كيف حالك أنا بخير والحمد لله", "", True)

    # ── C2: Already punctuated — MUST NOT over-punctuate ──
    add("already_punct", "ذهبت إلى المدرسة. ثم عدت.", "", False)
    add("already_punct", "كيف حالك؟ أنا بخير.", "", False)
    add("already_punct", "أحمد، كيف حالك؟ هل أنت بخير؟", "", False)

    # ── C3: Punctuation must NOT change words ──
    add("no_word_change", "ذهبت الي المدرسه أمس", "", True)
    # ^ Only add punct — must NOT fix الي→إلى or المدرسه→المدرسة

    # ── C4: Position accuracy ──
    add("position", "سألته كيف حالك فقال أنا بخير", "", True)
    add("position", "ذهبت إلى المكتبة واشتريت كتاباً ثم عدت", "", True)

    return T

# ═══════════════════════════════════════════════════════════════════════════════
# PHASE D — FULL PIPELINE VALIDATION
# ═══════════════════════════════════════════════════════════════════════════════
def build_pipeline_tests() -> List[TC]:
    T = []
    n = [0]
    def add(cat, inp, exp="", should_change=True, err=None, correct=None):
        n[0]+=1
        T.append(TC(f"D{n[0]:03d}", "D", cat, inp, exp, should_change,
                     err or [], correct or []))

    # ── D1: Multi-stage corrections ──
    add("multi_stage", "انا ذهب الى الجامعه كيف حالك", "", True,
        ["انا","الى","الجامعه"])
    add("multi_stage", "البنات ذهب الى المدرسه", "", True,
        ["ذهب","الى","المدرسه"])
    add("multi_stage", "هي ذهب الي الجامعه", "", True,
        ["ذهب","الي","الجامعه"])

    # ── D2: Correct text through pipeline ──
    add("correct_pipeline", "أنا ذهبت إلى الجامعة.", "", False,
        correct=["أنا","ذهبت","إلى","الجامعة"])
    add("correct_pipeline", "ذهب الطالب إلى المدرسة.", "", False,
        correct=["ذهب","الطالب","إلى","المدرسة"])

    # ── D3: Cross-model conflict ──
    add("cross_conflict", "الجامعه كبيره والطلاب كثيرون", "", True,
        ["الجامعه","كبيره"])
    add("cross_conflict", "المدرسه جميله والمعلمون في الفصل", "", True,
        ["المدرسه","جميله"])

    # ── D4: Span alignment after pipeline ──
    add("span_align", "المدرسه كبيره جداً", "", True, ["المدرسه","كبيره"])
    add("span_align", "انا في المدرسه الكبيره", "", True, ["انا","المدرسه","الكبيره"])

    # ── D5: Religious text through pipeline ──
    add("religious_pipeline", "بسم الله الرحمن الرحيم", "", False,
        correct=["بسم","الله","الرحمن","الرحيم"])
    add("religious_pipeline", "الحمد لله رب العالمين", "", False,
        correct=["الحمد","لله","رب","العالمين"])

    # ── D6: Apply-all safety ──
    add("apply_all", "انا ذهبت الي المدرسه", "", True, ["انا","الي","المدرسه"])
    add("apply_all", "النص الأول صحيح ولكن الجامعه خطأ", "", True, ["الجامعه"])

    # ── D7: Long text ──
    long = "هذا النص طويل جداً " * 20
    add("long_text", long.strip(), "", False)

    # ── D8: Edge cases ──
    add("edge_empty", "", "", False)
    add("edge_short", "مرحبا", "", False)
    add("edge_html", "<script>alert('xss')</script> مرحبا بكم في الموقع", "", True)
    add("edge_english", "Hello world this is a test of English text only", "", False)

    return T

# ═══════════════════════════════════════════════════════════════════════════════
# PHASE E — ADVERSARIAL ATTACKS
# ═══════════════════════════════════════════════════════════════════════════════
def build_adversarial_tests() -> List[TC]:
    T = []
    n = [0]
    def add(cat, inp, exp="", should_change=False, err=None, correct=None):
        n[0]+=1
        T.append(TC(f"E{n[0]:03d}", "E", cat, inp, exp, should_change,
                     err or [], correct or []))

    # ── E1: Dialect ──
    add("dialect", "ازيك عامل ايه انهارده", "", True)
    add("dialect", "كيفك شو اخبارك اليوم", "", True)
    add("dialect", "شلونك وين رايح", "", True)

    # ── E2: Franco Arabic ──
    add("franco", "ana ray7 el gam3a", "", False)
    add("franco", "3ayz atkalem ma3ak", "", False)

    # ── E3: Excessive repetition ──
    add("repetition", "هههههههههه مضحك جداااااا", "", True)
    add("repetition", "لاااااااا مش ممكن", "", True)

    # ── E4: Emoji heavy ──
    add("emoji", "😊😊😊 مرحبا 🎉🎉🎉 كيف حالك 🌟", "", False)

    # ── E5: Mixed scripts ──
    add("mixed_script", "I love القراءة and الكتابة", "", False)
    add("mixed_script", "المشروع يستخدم React و Node.js", "", False)

    # ── E6: Code ──
    add("code", "print('مرحبا بالعالم')", "", False)
    add("code", "function test() { return 'مرحبا'; }", "", False)

    # ── E7: URLs and emails ──
    add("url", "زر الموقع https://www.example.com/path?q=test للمزيد", "", False)
    add("email", "أرسل لي على info@company.com رجاءً", "", False)

    # ── E8: Numbers/dates ──
    add("numbers", "تاريخ اليوم 15/06/2026 والساعة 14:30", "", False)
    add("numbers", "المسافة 25.5 كم والحرارة 35°C", "", False)

    # ── E9: Unicode edge cases ──
    add("unicode", "بسم\u200cالله", "", False)  # ZWNJ
    add("unicode", "مرحبا\u200bبكم", "", False)  # ZWS
    add("unicode", "كَتَبَ الطَّالِبُ الدَّرسَ", "", False)  # Diacritics

    # ── E10: Very long single word ──
    add("long_word", "واستغفروالذنوبهمجميعاًفإنهم محتاجون", "", True)

    # ── E11: Punctuation spam ──
    add("punct_spam", "!!!???...،،،؛؛؛:::...!!!", "", False)

    # ── E12: Newlines ──
    add("newlines", "السطر الأول\nالسطر الثاني\nالسطر الثالث", "", False)

    # ── E13: Hashtags/mentions ──
    add("hashtag", "مشروع #بيان رائع جداً @mohamedatef", "", False, correct=["#بيان","@mohamedatef"])

    return T

# ═══════════════════════════════════════════════════════════════════════════════
# RUNNER
# ═══════════════════════════════════════════════════════════════════════════════

def run_spelling_test(api: API, tc: TC) -> Result:
    """Test spelling model independently via /api/analyze (short text triggers spelling)."""
    r = Result(tc.id, tc.phase, tc.category, tc.input, tc.expected_output)
    resp = api.analyze(tc.input)
    r.api_status = resp.get('_status', 0)
    r.latency_ms = resp.get('_ms', 0)
    r.raw_response = {k: v for k, v in resp.items() if k not in ('_ms', '_status')}

    if 'error' in resp:
        if not tc.should_change and tc.input.strip() == "":
            r.verdict = "TN"; r.detail = "Empty input correctly rejected"
        else:
            r.verdict = "ERROR"; r.detail = resp['error']
        return r

    r.actual_output = resp.get('corrected', '')
    r.suggestions = resp.get('suggestions', [])
    r.changed = r.actual_output != resp.get('original', tc.input)

    if tc.should_change:
        if r.changed:
            # Check if the right words were corrected
            uncorrected_errors = []
            for ew in tc.error_words:
                if ew in r.actual_output:
                    uncorrected_errors.append(ew)
            if uncorrected_errors:
                r.verdict = "FN"
                r.detail = f"Errors NOT fixed: {uncorrected_errors}"
            else:
                r.verdict = "TP"
                r.detail = f"Corrected: {len(r.suggestions)} suggestions"
        else:
            r.verdict = "FN"
            r.detail = f"No changes made. Expected fix for: {tc.error_words}"
    else:
        if r.changed:
            # Check if protected words were corrupted
            corrupted = []
            for cw in tc.correct_words:
                if cw not in r.actual_output and cw in tc.input:
                    corrupted.append(cw)
            if corrupted:
                r.verdict = "FP"
                r.detail = f"OVERCORRECTION: corrupted words: {corrupted}"
            elif r.suggestions:
                r.verdict = "FP"
                changes = [f"{s.get('original','')}→{s.get('correction','')}" for s in r.suggestions]
                r.detail = f"Unnecessary changes: {changes}"
            else:
                r.verdict = "TN"
                r.detail = "Text changed but no suggestion objects"
        else:
            r.verdict = "TN"
            r.detail = "Correctly unchanged"

    return r

def run_grammar_test(api: API, tc: TC) -> Result:
    """Test grammar model via /api/grammar endpoint."""
    r = Result(tc.id, tc.phase, tc.category, tc.input, tc.expected_output)
    resp = api.grammar(tc.input)
    r.api_status = resp.get('_status', 0)
    r.latency_ms = resp.get('_ms', 0)
    r.raw_response = {k: v for k, v in resp.items() if k not in ('_ms', '_status')}

    if 'error' in resp:
        r.verdict = "ERROR"; r.detail = resp['error']
        return r

    r.actual_output = resp.get('corrected', resp.get('corrected_text', ''))
    r.changed = r.actual_output != tc.input

    if tc.should_change:
        if r.changed:
            uncorrected = [ew for ew in tc.error_words if ew in r.actual_output]
            if uncorrected:
                r.verdict = "FN"; r.detail = f"Errors NOT fixed: {uncorrected}"
            else:
                r.verdict = "TP"; r.detail = f"Grammar corrected"
        else:
            r.verdict = "FN"; r.detail = f"No changes made. Expected fix for: {tc.error_words}"
    else:
        if r.changed:
            corrupted = [cw for cw in tc.correct_words if cw not in r.actual_output and cw in tc.input]
            if corrupted:
                r.verdict = "FP"; r.detail = f"OVERCORRECTION: corrupted words: {corrupted}"
            else:
                # Check if it's a stylistic rewrite
                r.verdict = "FP"; r.detail = f"Unnecessary change: '{tc.input[:60]}' → '{r.actual_output[:60]}'"
        else:
            r.verdict = "TN"; r.detail = "Correctly unchanged"

    return r

def run_punctuation_test(api: API, tc: TC) -> Result:
    """Test punctuation model via /api/punctuation endpoint."""
    r = Result(tc.id, tc.phase, tc.category, tc.input, tc.expected_output)
    resp = api.punctuation(tc.input)
    r.api_status = resp.get('_status', 0)
    r.latency_ms = resp.get('_ms', 0)
    r.raw_response = {k: v for k, v in resp.items() if k not in ('_ms', '_status')}

    if 'error' in resp:
        r.verdict = "ERROR"; r.detail = resp['error']
        return r

    r.actual_output = resp.get('corrected', resp.get('corrected_text', ''))
    r.changed = r.actual_output != tc.input

    # Check if model changed WORDS (not just punctuation)
    punct_chars = set('.,،؛؟!:;?! ')
    orig_words = re.sub(r'[.,،؛؟!:;?!\s]+', ' ', tc.input).strip()
    corr_words = re.sub(r'[.,،؛؟!:;?!\s]+', ' ', r.actual_output).strip()
    word_change = orig_words != corr_words

    if word_change:
        r.verdict = "FP"
        r.detail = f"WORD CHANGE in punctuation model: '{orig_words[:50]}' → '{corr_words[:50]}'"
        return r

    if tc.should_change:
        if r.changed:
            r.verdict = "TP"; r.detail = f"Punctuation added"
        else:
            r.verdict = "FN"; r.detail = "No punctuation added"
    else:
        if r.changed:
            r.verdict = "FP"; r.detail = f"Over-punctuated: '{r.actual_output[:80]}'"
        else:
            r.verdict = "TN"; r.detail = "Correctly unchanged"

    return r

def run_pipeline_test(api: API, tc: TC) -> Result:
    """Test full pipeline via /api/analyze."""
    r = Result(tc.id, tc.phase, tc.category, tc.input, tc.expected_output)
    resp = api.analyze(tc.input)
    r.api_status = resp.get('_status', 0)
    r.latency_ms = resp.get('_ms', 0)
    r.raw_response = {k: v for k, v in resp.items() if k not in ('_ms', '_status')}

    if 'error' in resp:
        if tc.category in ('edge_empty', 'edge_short', 'edge_english') or tc.input.strip() == "":
            r.verdict = "TN"; r.detail = f"Edge case handled: {resp.get('error','')}"
        else:
            r.verdict = "ERROR"; r.detail = resp['error']
        return r

    original = resp.get('original', tc.input)
    r.actual_output = resp.get('corrected', '')
    r.suggestions = resp.get('suggestions', [])
    r.changed = r.actual_output != original

    # ── Span alignment check ──
    span_errors = []
    for s in r.suggestions:
        start, end = s.get('start', 0), s.get('end', 0)
        orig_text = s.get('original', '')
        actual_slice = original[start:end]
        if actual_slice != orig_text and orig_text:
            span_errors.append(f"SPAN[{start}:{end}] expected='{orig_text}' got='{actual_slice}'")

    if span_errors:
        r.verdict = "FP"
        r.detail = f"SPAN MISMATCH: {'; '.join(span_errors[:3])}"
        return r

    # ── Apply-all reconstruction check ──
    if tc.category == "apply_all" and r.suggestions:
        rebuilt = original
        for s in sorted(r.suggestions, key=lambda x: -x['start']):
            rebuilt = rebuilt[:s['start']] + s['correction'] + rebuilt[s['end']:]
        if rebuilt != r.actual_output:
            r.verdict = "FP"
            r.detail = f"APPLY-ALL MISMATCH: rebuilt≠corrected"
            return r

    if tc.should_change:
        if r.changed:
            uncorrected = [ew for ew in tc.error_words if ew in r.actual_output]
            if uncorrected:
                r.verdict = "FN"; r.detail = f"Errors NOT fixed: {uncorrected}"
            else:
                r.verdict = "TP"; r.detail = f"{len(r.suggestions)} fixes applied"
        else:
            r.verdict = "FN"; r.detail = f"No changes made. Expected fix for: {tc.error_words}"
    else:
        if r.changed:
            corrupted = [cw for cw in tc.correct_words if cw not in r.actual_output and cw in tc.input]
            if corrupted:
                r.verdict = "FP"; r.detail = f"OVERCORRECTION: corrupted: {corrupted}"
            elif r.suggestions:
                changes = [f"{s.get('original','')}→{s.get('correction','')}" for s in r.suggestions[:5]]
                r.verdict = "FP"; r.detail = f"Unnecessary changes: {changes}"
            else:
                r.verdict = "TN"; r.detail = "Minor change, no suggestion objects"
        else:
            r.verdict = "TN"; r.detail = "Correctly unchanged"

    return r

def run_adversarial_test(api: API, tc: TC) -> Result:
    """Run adversarial tests through full pipeline."""
    return run_pipeline_test(api, tc)

# ═══════════════════════════════════════════════════════════════════════════════
# METRICS
# ═══════════════════════════════════════════════════════════════════════════════

def calc_metrics(results: List[Result]) -> dict:
    tp = sum(1 for r in results if r.verdict == "TP")
    fp = sum(1 for r in results if r.verdict == "FP")
    tn = sum(1 for r in results if r.verdict == "TN")
    fn = sum(1 for r in results if r.verdict == "FN")
    err = sum(1 for r in results if r.verdict == "ERROR")
    total = len(results)
    precision = tp / (tp + fp) if (tp + fp) > 0 else 0
    recall = tp / (tp + fn) if (tp + fn) > 0 else 0
    f1 = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0
    fpr = fp / (fp + tn) if (fp + tn) > 0 else 0
    fnr = fn / (fn + tp) if (fn + tp) > 0 else 0
    latencies = [r.latency_ms for r in results if r.latency_ms > 0]
    p50 = sorted(latencies)[len(latencies)//2] if latencies else 0
    p95 = sorted(latencies)[int(len(latencies)*0.95)] if latencies else 0
    p99 = sorted(latencies)[int(len(latencies)*0.99)] if latencies else 0

    return {
        "total": total, "TP": tp, "FP": fp, "TN": tn, "FN": fn, "ERROR": err,
        "precision": round(precision, 4),
        "recall": round(recall, 4),
        "f1": round(f1, 4),
        "false_positive_rate": round(fpr, 4),
        "false_negative_rate": round(fnr, 4),
        "overcorrection_rate": round(fp / max(1, total), 4),
        "undercorrection_rate": round(fn / max(1, total), 4),
        "latency_p50_ms": p50,
        "latency_p95_ms": p95,
        "latency_p99_ms": p99,
    }

# ═══════════════════════════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════════════════════════

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--url", default=DEFAULT_URL)
    parser.add_argument("--phase", nargs="*", default=["ALL"])
    parser.add_argument("--out", default="phase9_results.json")
    args = parser.parse_args()

    api = API(args.url)
    phases = [p.upper() for p in args.phase]
    run_all = "ALL" in phases

    print(f"[P9] Target: {args.url}")
    print(f"[P9] Phases: {phases}")

    all_results = []
    all_metrics = {}

    # ── Phase A: Spelling ──
    if run_all or "A" in phases:
        tests = build_spelling_tests()
        print(f"\n{'='*60}")
        print(f"PHASE A — RAW SPELLING ({len(tests)} tests)")
        print(f"{'='*60}")
        results = []
        for i, tc in enumerate(tests):
            print(f"  [{i+1}/{len(tests)}] {tc.id} {tc.category}: ", end="", flush=True)
            r = run_spelling_test(api, tc)
            results.append(r)
            icon = {"TP":"✅","TN":"✅","FP":"❌","FN":"⚠️","ERROR":"💥"}[r.verdict]
            print(f"{icon} {r.verdict} ({r.latency_ms}ms) {r.detail[:70]}")
        m = calc_metrics(results)
        all_metrics["Phase_A_Spelling"] = m
        all_results.extend(results)
        print(f"\n  Precision={m['precision']} Recall={m['recall']} F1={m['f1']}")
        print(f"  FPR={m['false_positive_rate']} FNR={m['false_negative_rate']}")
        print(f"  Overcorrection={m['overcorrection_rate']} Undercorrection={m['undercorrection_rate']}")
        print(f"  Latency p50={m['latency_p50_ms']}ms p95={m['latency_p95_ms']}ms p99={m['latency_p99_ms']}ms")

    # ── Phase B: Grammar ──
    if run_all or "B" in phases:
        tests = build_grammar_tests()
        print(f"\n{'='*60}")
        print(f"PHASE B — RAW GRAMMAR ({len(tests)} tests)")
        print(f"{'='*60}")
        results = []
        for i, tc in enumerate(tests):
            print(f"  [{i+1}/{len(tests)}] {tc.id} {tc.category}: ", end="", flush=True)
            r = run_grammar_test(api, tc)
            results.append(r)
            icon = {"TP":"✅","TN":"✅","FP":"❌","FN":"⚠️","ERROR":"💥"}[r.verdict]
            print(f"{icon} {r.verdict} ({r.latency_ms}ms) {r.detail[:70]}")
        m = calc_metrics(results)
        all_metrics["Phase_B_Grammar"] = m
        all_results.extend(results)
        print(f"\n  Precision={m['precision']} Recall={m['recall']} F1={m['f1']}")
        print(f"  FPR={m['false_positive_rate']} FNR={m['false_negative_rate']}")

    # ── Phase C: Punctuation ──
    if run_all or "C" in phases:
        tests = build_punctuation_tests()
        print(f"\n{'='*60}")
        print(f"PHASE C — RAW PUNCTUATION ({len(tests)} tests)")
        print(f"{'='*60}")
        results = []
        for i, tc in enumerate(tests):
            print(f"  [{i+1}/{len(tests)}] {tc.id} {tc.category}: ", end="", flush=True)
            r = run_punctuation_test(api, tc)
            results.append(r)
            icon = {"TP":"✅","TN":"✅","FP":"❌","FN":"⚠️","ERROR":"💥"}[r.verdict]
            print(f"{icon} {r.verdict} ({r.latency_ms}ms) {r.detail[:70]}")
        m = calc_metrics(results)
        all_metrics["Phase_C_Punctuation"] = m
        all_results.extend(results)
        print(f"\n  Precision={m['precision']} Recall={m['recall']} F1={m['f1']}")

    # ── Phase D: Full Pipeline ──
    if run_all or "D" in phases:
        tests = build_pipeline_tests()
        print(f"\n{'='*60}")
        print(f"PHASE D — FULL PIPELINE ({len(tests)} tests)")
        print(f"{'='*60}")
        results = []
        for i, tc in enumerate(tests):
            print(f"  [{i+1}/{len(tests)}] {tc.id} {tc.category}: ", end="", flush=True)
            r = run_pipeline_test(api, tc)
            results.append(r)
            icon = {"TP":"✅","TN":"✅","FP":"❌","FN":"⚠️","ERROR":"💥"}[r.verdict]
            print(f"{icon} {r.verdict} ({r.latency_ms}ms) {r.detail[:70]}")
        m = calc_metrics(results)
        all_metrics["Phase_D_Pipeline"] = m
        all_results.extend(results)
        print(f"\n  Precision={m['precision']} Recall={m['recall']} F1={m['f1']}")
        print(f"  Span errors: {sum(1 for r in results if 'SPAN' in r.detail)}")
        print(f"  Apply-all errors: {sum(1 for r in results if 'APPLY-ALL' in r.detail)}")

    # ── Phase E: Adversarial ──
    if run_all or "E" in phases:
        tests = build_adversarial_tests()
        print(f"\n{'='*60}")
        print(f"PHASE E — ADVERSARIAL ({len(tests)} tests)")
        print(f"{'='*60}")
        results = []
        for i, tc in enumerate(tests):
            print(f"  [{i+1}/{len(tests)}] {tc.id} {tc.category}: ", end="", flush=True)
            r = run_adversarial_test(api, tc)
            results.append(r)
            icon = {"TP":"✅","TN":"✅","FP":"❌","FN":"⚠️","ERROR":"💥"}[r.verdict]
            print(f"{icon} {r.verdict} ({r.latency_ms}ms) {r.detail[:70]}")
        m = calc_metrics(results)
        all_metrics["Phase_E_Adversarial"] = m
        all_results.extend(results)

    # ── Summary ──
    print(f"\n{'='*60}")
    print(f"FINAL SUMMARY")
    print(f"{'='*60}")
    total_tp = sum(1 for r in all_results if r.verdict == "TP")
    total_fp = sum(1 for r in all_results if r.verdict == "FP")
    total_tn = sum(1 for r in all_results if r.verdict == "TN")
    total_fn = sum(1 for r in all_results if r.verdict == "FN")
    total_err = sum(1 for r in all_results if r.verdict == "ERROR")
    print(f"  Total tests: {len(all_results)}")
    print(f"  TP (correct fix): {total_tp}")
    print(f"  TN (correct no-change): {total_tn}")
    print(f"  FP (overcorrection): {total_fp}")
    print(f"  FN (undercorrection): {total_fn}")
    print(f"  ERROR: {total_err}")
    print(f"\n  PASS rate: {(total_tp+total_tn)/max(1,len(all_results))*100:.1f}%")
    print(f"  FAIL rate: {(total_fp+total_fn)/max(1,len(all_results))*100:.1f}%")

    # Critical failures
    fps = [r for r in all_results if r.verdict == "FP"]
    if fps:
        print(f"\n🚨 FALSE POSITIVES ({len(fps)}):")
        for r in fps[:20]:
            print(f"  {r.tc_id} [{r.category}] {r.detail[:90]}")

    fns = [r for r in all_results if r.verdict == "FN"]
    if fns:
        print(f"\n⚠️ FALSE NEGATIVES ({len(fns)}):")
        for r in fns[:20]:
            print(f"  {r.tc_id} [{r.category}] {r.detail[:90]}")

    # Save
    output = {
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "target": args.url,
        "metrics": all_metrics,
        "total_tests": len(all_results),
        "summary": {
            "TP": total_tp, "TN": total_tn, "FP": total_fp, "FN": total_fn, "ERROR": total_err,
            "pass_rate": round((total_tp+total_tn)/max(1,len(all_results)), 4),
        },
        "results": [asdict(r) for r in all_results],
    }
    with open(args.out, 'w', encoding='utf-8') as f:
        json.dump(output, f, ensure_ascii=False, indent=2)
    print(f"\n[P9] Results saved to {args.out}")


if __name__ == "__main__":
    main()
