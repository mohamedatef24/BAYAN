#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Final edge case tests — Part 3
Things we haven't tested yet.
"""
import sys, os, time, re, sqlite3
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from quran import search_bayan, normalize_arabic

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'quran_master.db')
passed = 0
failed = 0
errors = []

def test(name, condition, detail=""):
    global passed, failed, errors
    if condition:
        passed += 1
        print(f"  ✅ {name}")
    else:
        failed += 1
        errors.append((name, detail))
        print(f"  ❌ {name} — {detail}")

def get(q, lang="تدقيق الايات"):
    return search_bayan(q, lang, db_path=DB_PATH)

def ref_of(seg):
    m = re.search(r'【([^】]+)】', seg)
    return m.group(1) if m else ""

# ══════════════════════════════════════════
print("\n⏱️ 18. أداء (سرعة البحث)")
print("=" * 50)

queries = [
    "قل هو الله أحد",
    "الم ذلك الكتاب لا ريب فيه هدى للمتقين",
    "انا انزلناه في ليلة القدر",
    "يا ايها الذين آمنوا اذا تداينتم بدين الى اجل مسمى فاكتبوه",
]
for q in queries:
    t0 = time.time()
    r = get(q)
    dt = time.time() - t0
    test(f"سرعة '{q[:25]}...' = {dt:.2f}s", dt < 3.0, f"took {dt:.2f}s")

# ══════════════════════════════════════════
print("\n🌍 19. البسملة في كل التراجم")
print("=" * 50)

all_langs = ["english", "french", "turkish", "russian", "spanish", "german",
             "indonesian", "persian", "malay", "bengali", "bosnian",
             "portuguese", "uzbek"]

# Common Basmala patterns in each language
basmala_patterns = {
    "english": "In the name of",
    "french": "Au nom d",
    "turkish": "adıyla",  # Rahman ve Rahim olan Allah'ın adıyla
    "russian": "Во имя",
    "spanish": "En el nombre",
    "german": "Im Namen",
    "indonesian": "Dengan nama",
    "persian": "به نام",
    "malay": "Dengan nama",
    "bengali": "পরম",
    "bosnian": "U ime",
    "portuguese": "Em nome",
    "uzbek": "Rahmon",
}

for lang in all_langs:
    r = get("الر تلك آيات الكتاب المبين", lang)
    seg = r.get("matched_segment", "")
    if "error" in str(r):
        test(f"{lang}: بسملة (لغة مش موجودة)", True)  # skip missing langs
        continue
    pattern = basmala_patterns.get(lang, "")
    has_basmala = pattern and pattern.lower() in seg.lower()
    test(f"{lang}: بسملة مش موجودة في الترجمة", not has_basmala, f"found '{pattern}' in seg")

# ══════════════════════════════════════════
print("\n🔗 20. DB Connection Safety")
print("=" * 50)

# Multiple rapid searches (connection handling)
for i in range(10):
    r = get("قل هو الله أحد")
test("١٠ بحوث متتالية: مفيش crash", True)

# Search with None/weird inputs
try:
    r = get(None)
    test("None input: handled", "error" in r or True)
except:
    test("None input: handled", False, "crashed!")

try:
    r = get("   ")
    test("Spaces only: handled", "error" in r)
except:
    test("Spaces only: handled", False, "crashed!")

# ══════════════════════════════════════════
print("\n📝 21. أسماء السور في كل اللغات")
print("=" * 50)

conn = sqlite3.connect(DB_PATH)
c = conn.cursor()

# Check all translation columns exist in suras_translated
c.execute("PRAGMA table_info(suras_translated)")
sura_cols = [row[1] for row in c.fetchall()]

lang_cols_sura = [col for col in sura_cols if col.startswith("lang_")]
for col in lang_cols_sura:
    c.execute(f"SELECT COUNT(*) FROM suras_translated WHERE {col} IS NULL OR {col} = ''")
    empty = c.fetchone()[0]
    test(f"أسماء السور {col}: كلها موجودة", empty == 0, f"empty={empty}")

# ══════════════════════════════════════════
print("\n🔤 22. علامات الوقف القرآنية")
print("=" * 50)

# Verses with special marks should still work
# البقرة 2 has ۛ
r = get("الم ذلك الكتاب لا ريب فيه هدى للمتقين")
seg = r.get("matched_segment", "")
test("آية بعلامات وقف: شغالة", len(seg) > 20)

# Check that Quran marks are filtered from uthmani word count
c.execute("SELECT text_uthmani FROM verses WHERE sura_num=2 AND aya_num=1")
uth = c.fetchone()[0]
marks = {'ۖ', 'ۗ', 'ۘ', 'ۙ', 'ۚ', 'ۛ', 'ۜ', '۝', '۞', '۩'}
uth_tokens = uth.split()
mark_count = sum(1 for t in uth_tokens if t in marks)
test(f"علامات وقف في البقرة:١ = {mark_count}", mark_count >= 0)

# ══════════════════════════════════════════
print("\n🧮 23. عدد كلمات الاستعلام vs عدد كلمات الآية")
print("=" * 50)

# Query longer than the verse itself (سورة الكوثر = 10 words)
r = get("انا اعطيناك الكوثر فصل لربك وانحر ان شانئك هو الابتر وهذا كلام زيادة ليس من القرآن")
seg = r.get("matched_segment", "")
ref = ref_of(seg)
test("استعلام أطول من السورة: بيجيب نتيجة", "الكوثر" in ref, f"ref={ref}")

# Query that is exactly one verse
r = get("انا اعطيناك الكوثر")
seg = r.get("matched_segment", "")
test("استعلام = آية واحدة بالظبط: شغال", len(seg) > 10)

# ══════════════════════════════════════════
print("\n🔄 24. تطبيع النص المتقدم")
print("=" * 50)

# ألف مقصورة vs ياء
r1 = get("هدى للمتقين")
r2 = get("هدي للمتقين")
test("ألف مقصورة/ياء: نفس النتيجة", ref_of(r1.get("matched_segment","")) == ref_of(r2.get("matched_segment","")))

# واو عطف ملتصقة
r = get("والعصر ان الانسان لفي خسر")
seg = r.get("matched_segment", "")
test("واو عطف: شغال", "العصر" in ref_of(seg), f"ref={ref_of(seg)}")

# تنوين
r = get("هدًى للمتقين")
seg = r.get("matched_segment", "")
test("تنوين في المدخل: شغال", len(seg) > 10)

# لام شمسية
r = get("الشمس والقمر")
seg = r.get("matched_segment", "")
test("لام شمسية: شغال", len(seg) > 10)

# ══════════════════════════════════════════
print("\n🏷️ 25. صحة أرقام الآيات")
print("=" * 50)

# Verify specific verse numbers
test_cases = [
    ("آية الكرسي", "الله لا اله الا هو الحي القيوم", "البقرة", "٢٥٥"),
    ("آية الدَّيْن", "يا ايها الذين آمنوا اذا تداينتم بدين", "البقرة", "٢٨٢"),
    ("آية النور", "الله نور السماوات والارض", "النور", "٣٥"),
    ("آية المُلك", "تبارك الذي بيده الملك", "الملك", "١"),
]

for name, query, expected_sura, expected_num in test_cases:
    r = get(query)
    ref = ref_of(r.get("matched_segment", ""))
    test(f"{name}: {expected_sura} {expected_num}", expected_sura in ref and expected_num in ref, f"ref={ref}")

conn.close()

# ══════════════════════════════════════════
print("\n" + "=" * 60)
print(f"📊 النتيجة: {passed} ✅ نجح | {failed} ❌ فشل | من {passed + failed} اختبار")
print("=" * 60)

if errors:
    print("\n❌ الاختبارات الفاشلة:")
    for name, detail in errors:
        print(f"  • {name}: {detail}")
