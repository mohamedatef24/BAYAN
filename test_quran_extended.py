#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Extended test suite — Part 2
Additional edge cases beyond the 55 core tests.
"""

import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from quran import search_bayan, normalize_arabic
import sqlite3, re

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
print("\n🔁 9. آيات متشابهة في سور مختلفة")
print("=" * 50)

# "الحمد لله" موجودة في الفاتحة والأنعام والكهف وسبأ وفاطر
# نتأكد إن النتيجة آية كاملة مش مقطوعة
r = get("الحمد لله الذي خلق السماوات والأرض")
seg = r.get("matched_segment", "")
ref = ref_of(seg)
test("آية متشابهة: اسم سورة موجود", len(ref) > 0, f"ref={ref}")
test("آية متشابهة: آية كاملة", "(١)" in seg or "(٢)" in seg, f"seg={seg[:60]}")

# "فبأي آلاء ربكما تكذبان" مكررة 31 مرة في الرحمن
r = get("فبأي آلاء ربكما تكذبان")
seg = r.get("matched_segment", "")
ref = ref_of(seg)
test("آية مكررة (فبأي آلاء): بترجع نتيجة", len(seg) > 10, f"ref={ref}")

# "ويل يومئذ للمكذبين" مكررة 10 مرات في المرسلات
r = get("ويل يومئذ للمكذبين")
seg = r.get("matched_segment", "")
test("آية مكررة (ويل): بترجع نتيجة", len(seg) > 10)

# ══════════════════════════════════════════
print("\n📏 10. آيات قصيرة جداً")
print("=" * 50)

# "طه" - كلمة واحدة
r = get("طه")
seg = r.get("matched_segment", "")
test("آية كلمة واحدة (طه): نتيجة", len(seg) > 5)

# "والفجر" 
r = get("والفجر")
seg = r.get("matched_segment", "")
test("آية قصيرة (والفجر): نتيجة", len(seg) > 5)

# "والضحى"
r = get("والضحى")
seg = r.get("matched_segment", "")
test("آية قصيرة (والضحى): نتيجة", len(seg) > 5)

# "مدهامتان" (الرحمن 64)
r = get("مدهامتان")
seg = r.get("matched_segment", "")
test("آية كلمة واحدة (مدهامتان): نتيجة", len(seg) > 5)

# "والعصر"
r = get("والعصر")
seg = r.get("matched_segment", "")
ref = ref_of(seg)
test("والعصر: اسم سورة", "العصر" in ref or "عصر" in ref.lower(), f"ref={ref}")

# ══════════════════════════════════════════
print("\n🔤 11. كل الحروف المقطعة (29 سورة)")
print("=" * 50)

muqattaat = [
    ("الم", "البقرة/آل عمران"),
    ("المص", "الأعراف"),
    ("الر", "يونس/هود/يوسف"),
    ("المر", "الرعد"),
    ("كهيعص", "مريم"),
    ("طه", "طه"),
    ("طسم", "الشعراء/القصص"),
    ("طس", "النمل"),
    ("يس", "يس"),
    ("ص", "ص"),
    ("حم", "غافر وغيرها"),
    ("عسق", "الشورى"),
    ("ق", "ق"),
    ("ن", "القلم"),
]

for letters, sura in muqattaat:
    r = get(letters)
    seg = r.get("matched_segment", "")
    has_result = len(seg) > 5 and "error" not in str(r)
    test(f"حروف مقطعة '{letters}' ({sura})", has_result, f"seg={seg[:40]}")

# ══════════════════════════════════════════
print("\n🧹 12. تنظيف المدخلات")
print("=" * 50)

# مسافات زيادة
r = get("  قل   هو   الله   أحد  ")
seg = r.get("matched_segment", "")
test("مسافات زيادة: شغال", len(seg) > 10)

# تشكيل كامل في المدخل
r = get("قُلْ هُوَ اللَّهُ أَحَدٌ")
seg = r.get("matched_segment", "")
test("مدخل بتشكيل كامل: شغال", len(seg) > 10)

# بدون تشكيل خالص
r = get("قل هو الله احد")
seg = r.get("matched_segment", "")
test("مدخل بدون تشكيل: شغال", len(seg) > 10)

# همزات مختلفة
r = get("إنا أنزلناه في ليلة القدر")
seg1 = r.get("matched_segment", "")
r = get("انا انزلناه في ليله القدر")
seg2 = r.get("matched_segment", "")
test("همزات مختلفة: نفس النتيجة", "القدر" in ref_of(seg1) and "القدر" in ref_of(seg2))

# تاء مربوطة vs هاء
r = get("ليله القدر")
seg = r.get("matched_segment", "")
test("تاء مربوطة/هاء: شغال", "القدر" in ref_of(seg), f"ref={ref_of(seg)}")

# ══════════════════════════════════════════
print("\n🌍 13. أسماء السور في التراجم")
print("=" * 50)

# English surah name
r = get("قل هو الله أحد", "english")
ref = ref_of(r.get("matched_segment", ""))
test("English: Surah name = Al-Ikhlas", "Ikhlas" in ref or "ikhlas" in ref.lower(), f"ref={ref}")

# French surah name
r = get("قل هو الله أحد", "french")
ref = ref_of(r.get("matched_segment", ""))
test("French: Surah name exists", len(ref) > 0, f"ref={ref}")

# Turkish surah name
r = get("قل هو الله أحد", "turkish")
ref = ref_of(r.get("matched_segment", ""))
test("Turkish: Surah name exists", len(ref) > 0, f"ref={ref}")

# Russian surah name
r = get("قل هو الله أحد", "russian")
ref = ref_of(r.get("matched_segment", ""))
test("Russian: Surah name exists", len(ref) > 0, f"ref={ref}")

# ══════════════════════════════════════════
print("\n🗃️ 14. سلامة البيانات المتقدمة")
print("=" * 50)

conn = sqlite3.connect(DB_PATH)
c = conn.cursor()

# لا توجد فجوات في ترقيم الآيات
c.execute("""
    SELECT sura_num, MAX(aya_num) as max_aya, COUNT(*) as cnt 
    FROM verses 
    GROUP BY sura_num 
    HAVING max_aya != cnt
""")
gaps = c.fetchall()
test("ترقيم الآيات: مفيش فجوات", len(gaps) == 0, f"gaps={gaps}")

# كل آية ليها text_uthmani
c.execute("SELECT COUNT(*) FROM verses WHERE text_uthmani IS NULL OR text_uthmani = ''")
empty_uth = c.fetchone()[0]
test("text_uthmani مش فاضي لأي آية", empty_uth == 0, f"empty={empty_uth}")

# كل آية ليها ترجمة إنجليزية
c.execute("SELECT COUNT(*) FROM verses WHERE lang_en IS NULL OR lang_en = ''")
empty_en = c.fetchone()[0]
test("lang_en مش فاضي لأي آية", empty_en == 0, f"empty={empty_en}")

# كل آية ليها ترجمة فرنسية
c.execute("SELECT COUNT(*) FROM verses WHERE lang_fr IS NULL OR lang_fr = ''")
empty_fr = c.fetchone()[0]
test("lang_fr مش فاضي لأي آية", empty_fr == 0, f"empty={empty_fr}")

# أسماء السور بالعربي
c.execute("SELECT COUNT(*) FROM suras_translated WHERE ar IS NULL OR ar = ''")
empty_ar = c.fetchone()[0]
test("أسماء السور بالعربي: كلها موجودة", empty_ar == 0, f"empty={empty_ar}")

# أسماء السور بالإنجليزي
c.execute("SELECT COUNT(*) FROM suras_translated WHERE lang_en IS NULL OR lang_en = ''")
empty_en_s = c.fetchone()[0]
test("أسماء السور بالإنجليزي: كلها موجودة", empty_en_s == 0, f"empty={empty_en_s}")

# عدد آيات بعض السور المعروفة
known_counts = {1: 7, 2: 286, 3: 200, 9: 129, 12: 111, 36: 83, 55: 78, 97: 5, 108: 3, 112: 4, 114: 6}
for sura, expected in known_counts.items():
    c.execute("SELECT COUNT(*) FROM verses WHERE sura_num = ?", (sura,))
    actual = c.fetchone()[0]
    test(f"سورة {sura}: {actual} آية (متوقع {expected})", actual == expected, f"actual={actual}")

conn.close()

# ══════════════════════════════════════════
print("\n🔀 15. البسملة في التراجم")
print("=" * 50)

# English: Basmala should be stripped from non-Fatiha
r = get("الر تلك آيات الكتاب المبين", "english")
seg = r.get("matched_segment", "")
test("English: بسملة مش موجودة", "In the name of" not in seg, f"seg={seg[:60]}")

# French: same
r = get("الر تلك آيات الكتاب المبين", "french")
seg = r.get("matched_segment", "")
test("French: بسملة مش موجودة", "Au nom d" not in seg and "Bismillah" not in seg.lower(), f"seg={seg[:60]}")

# ══════════════════════════════════════════
print("\n⚡ 16. أداء وحالات حدّية")
print("=" * 50)

# نص طويل جداً (أول ربع من البقرة)
long_text = "الم ذلك الكتاب لا ريب فيه هدى للمتقين الذين يؤمنون بالغيب ويقيمون الصلاة ومما رزقناهم ينفقون والذين يؤمنون بما انزل اليك وما انزل من قبلك وبالآخرة هم يوقنون اولئك على هدى من ربهم واولئك هم المفلحون"
r = get(long_text)
seg = r.get("matched_segment", "")
test("نص طويل: بيرجع نتيجة", len(seg) > 50, f"len={len(seg)}")
test("نص طويل: سورة البقرة", "البقرة" in ref_of(seg) or "بقر" in ref_of(seg).lower(), f"ref={ref_of(seg)}")

# نص فيه أرقام
r = get("123 الله")
test("نص فيه أرقام: مش بيكسر", True)  # should not crash

# علامات ترقيم
r = get("قل هو الله أحد!!!")
seg = r.get("matched_segment", "")
test("علامات ترقيم: شغال", len(seg) > 5)

# تكرار نفس الكلمة
r = get("الله الله الله")
seg = r.get("matched_segment", "")
test("تكرار كلمة: مش بيكسر", True)

# حرف واحد
r = get("ق")
seg = r.get("matched_segment", "")
test("حرف واحد (ق): شغال", len(seg) > 5)

# حرف واحد (ص)
r = get("ص")
seg = r.get("matched_segment", "")
test("حرف واحد (ص): شغال", len(seg) > 5)

# حرف واحد (ن)
r = get("ن")
seg = r.get("matched_segment", "")
test("حرف واحد (ن): شغال", len(seg) > 5)

# ══════════════════════════════════════════
print("\n🎯 17. دقة التطابق")
print("=" * 50)

# آية الكرسي
r = get("الله لا اله الا هو الحي القيوم لا تأخذه سنة ولا نوم")
seg = r.get("matched_segment", "")
ref = ref_of(seg)
test("آية الكرسي: البقرة ٢٥٥", "البقرة" in ref or "بقر" in ref.lower(), f"ref={ref}")
test("آية الكرسي: رقم ٢٥٥", "٢٥٥" in ref or "255" in ref, f"ref={ref}")

# خواتيم البقرة
r = get("آمن الرسول بما انزل اليه من ربه والمؤمنون")
seg = r.get("matched_segment", "")
ref = ref_of(seg)
test("خواتيم البقرة: ٢٨٥", "٢٨٥" in ref or "285" in ref, f"ref={ref}")

# آية النور ٣٥ (آية النور)
r = get("الله نور السماوات والأرض مثل نوره كمشكاة")
seg = r.get("matched_segment", "")
ref = ref_of(seg)
test("آية النور: سورة النور", "النور" in ref or "نور" in ref.lower(), f"ref={ref}")

# سورة يس آية 82
r = get("انما امره اذا اراد شيئا ان يقول له كن فيكون")
seg = r.get("matched_segment", "")
test("كن فيكون: نتيجة صحيحة", len(seg) > 20)

# ══════════════════════════════════════════
print("\n" + "=" * 60)
print(f"📊 النتيجة: {passed} ✅ نجح | {failed} ❌ فشل | من {passed + failed} اختبار")
print("=" * 60)

if errors:
    print("\n❌ الاختبارات الفاشلة:")
    for name, detail in errors:
        print(f"  • {name}: {detail}")
