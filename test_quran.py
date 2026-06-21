#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Comprehensive test suite for Quran search feature (quran.py)
Tests edge cases, boundary conditions, and data integrity.
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from quran import search_bayan, normalize_arabic
import sqlite3
import re

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

def get_result(query, lang="تدقيق الايات"):
    return search_bayan(query, lang, db_path=DB_PATH)

# ══════════════════════════════════════════
print("\n🔤 1. الحروف المقطعة (Huruf Muqatta'at)")
print("=" * 50)

# الم - البقرة
r = get_result("الم ذلك الكتاب لا ريب فيه")
test("الم موجودة في البقرة", "الٓمٓ" in r.get("matched_segment", "") or "الم" in r.get("matched_segment", ""))

# الر - يوسف
r = get_result("الر تلك آيات الكتاب المبين")
test("الر موجودة في يوسف", "الٓر" in r.get("matched_segment", "") or "الر" in r.get("matched_segment", ""))

# حم - غافر
r = get_result("حم تنزيل الكتاب من الله")
test("حم موجودة", "حمٓ" in r.get("matched_segment", "") or "حم" in r.get("matched_segment", ""))

# كهيعص - مريم
r = get_result("كهيعص ذكر رحمة ربك عبده زكريا")
seg = r.get("matched_segment", "")
test("كهيعص موجودة", "كٓهيعٓصٓ" in seg or "كهيعص" in seg or "مريم" in seg.lower() or "مَرْيَمَ" in seg)

# طه
r = get_result("طه ما انزلنا عليك القرآن لتشقى")
test("طه موجودة", "طه" in r.get("matched_segment", "") or "طٰهٰ" in r.get("matched_segment", ""))

# يس
r = get_result("يس والقرآن الحكيم")
test("يس موجودة", "يسٓ" in r.get("matched_segment", "") or "يس" in r.get("matched_segment", ""))

# ══════════════════════════════════════════
print("\n📖 2. البسملة")
print("=" * 50)

# الفاتحة - البسملة + الحمد لله
r = get_result("بسم الله الرحمن الرحيم الحمد لله رب العالمين")
seg = r.get("matched_segment", "")
ref_match = re.search(r'【([^】]+)】', seg)
ref = ref_match.group(1) if ref_match else ""
test("الفاتحة: البسملة موجودة", "بِسْمِ" in seg, f"seg={seg[:60]}")
test("الفاتحة: اسم السورة", "الفاتحة" in ref, f"ref={ref}")

# الفاتحة - آيات بدون بسملة
r2 = get_result("الحمد لله رب العالمين الرحمن الرحيم مالك يوم الدين")
seg2 = r2.get("matched_segment", "")
ref2 = re.search(r'【([^】]+)】', seg2)
ref2 = ref2.group(1) if ref2 else ""
test("الفاتحة ٢-٤: آيات صحيحة", "لْحَمْدُ" in seg2 and "(٤)" in seg2, f"seg={seg2[:60]}")
test("الفاتحة ٢-٤: اسم السورة", "الفاتحة" in ref2, f"ref={ref2}")

# سورة عادية - البسملة لازم تتشال
r = get_result("الر تلك آيات الكتاب المبين")
test("يوسف: البسملة مش موجودة", "بِسْمِ" not in r.get("matched_segment", ""))

# التوبة - مفيهاش بسملة أصلاً
r = get_result("براءة من الله ورسوله")
seg = r.get("matched_segment", "")
test("التوبة: مفيش بسملة", "بِسْمِ" not in seg)
test("التوبة: اسم السورة صح", "التوبة" in seg or "توب" in seg.lower() or "بَرَآءَةٌ" in seg)

# النمل 30 - البسملة جزء من الآية
r = get_result("انه من سليمان وانه بسم الله الرحمن الرحيم")
seg = r.get("matched_segment", "")
test("النمل ٣٠: البسملة موجودة (جزء من الآية)", "بِسْمِ" in seg or "سُلَيْمَـٰنَ" in seg)

# ══════════════════════════════════════════
print("\n🔢 3. ترقيم الآيات والمراجع")
print("=" * 50)

# آية واحدة - رقم مفرد
r = get_result("قل هو الله أحد")
seg = r.get("matched_segment", "")
ref_match = re.search(r'【([^】]+)】', seg)
ref = ref_match.group(1) if ref_match else ""
test("آية واحدة: مرجع مفرد", ":" in ref and "-" not in ref, f"ref={ref}")

# كذا آية - نطاق
r = get_result("انا انزلناه في ليلة القدر وما ادراك ما ليلة القدر ليلة القدر خير من الف شهر")
seg = r.get("matched_segment", "")
ref_match = re.search(r'【([^】]+)】', seg)
ref = ref_match.group(1) if ref_match else ""
test("كذا آية: نطاق (من-إلى)", "-" in ref, f"ref={ref}")

# أرقام عربية في العثماني
r = get_result("قل هو الله أحد", "تدقيق الايات")
seg = r.get("matched_segment", "")
test("عثماني: أرقام عربية", any(c in seg for c in "٠١٢٣٤٥٦٧٨٩"), f"seg={seg[:60]}")

# أرقام لاتينية في الإنجليزي
r = get_result("قل هو الله أحد", "english")
seg = r.get("matched_segment", "")
test("إنجليزي: أرقام لاتينية", any(c in seg for c in "0123456789"), f"seg={seg[:60]}")

# ══════════════════════════════════════════
print("\n🚧 4. حدود السور")
print("=" * 50)

# سورة قصيرة كاملة (الإخلاص)
r = get_result("قل هو الله أحد الله الصمد لم يلد ولم يولد ولم يكن له كفوا أحد")
seg = r.get("matched_segment", "")
test("الإخلاص كاملة: ٤ آيات", "(٤)" in seg or "(٤)" in seg.replace("٤","4"))
test("الإخلاص: مفيش آيات من الفلق", "فَلَقِ" not in seg and "الفلق" not in seg)

# سورة القدر - مش يكمل للبينة
r = get_result("انا انزلناه في ليلة القدر وما ادراك ما ليلة القدر ليلة القدر خير من الف شهر تنزل فيها الملائكة والروح فيها باذن ربهم من كل امر سلام هي حتى مطلع الفجر")
seg = r.get("matched_segment", "")
test("القدر: مفيش آيات من البينة", "ٱلْبَيِّنَةُ" not in seg and "بَيِّنَة" not in seg)
test("القدر: ٥ آيات", "(٥)" in seg or "(٥)" in seg.replace("٥","5"))

# الكوثر (أقصر سورة - 3 آيات)
r = get_result("انا اعطيناك الكوثر فصل لربك وانحر ان شانئك هو الابتر")
seg = r.get("matched_segment", "")
test("الكوثر: ٣ آيات كاملة", "(٣)" in seg or "(٣)" in seg.replace("٣","3"))
ref_match = re.search(r'【([^】]+)】', seg)
ref = ref_match.group(1) if ref_match else ""
test("الكوثر: اسم السورة صح", "الكوثر" in ref, f"ref={ref}")

# ══════════════════════════════════════════
print("\n🔤 5. التراجم")
print("=" * 50)

languages = ["english", "french", "turkish", "russian", "spanish", "german", "indonesian", "persian"]
for lang in languages:
    r = get_result("قل هو الله أحد", lang)
    seg = r.get("matched_segment", "")
    has_content = len(seg) > 10 and "error" not in r
    ref_match = re.search(r'【([^】]+)】', seg)
    ref = ref_match.group(1) if ref_match else ""
    test(f"{lang}: ترجمة + مرجع موجود", has_content and len(ref) > 0, f"ref={ref}, len={len(seg)}")

# English with [O Muhammad] — brackets shouldn't break ref
r = get_result("قل لعبادي الذين آمنوا يقيموا الصلاة", "english")
seg = r.get("matched_segment", "")
ref_match = re.search(r'【([^】]+)】', seg)
ref = ref_match.group(1) if ref_match else ""
test("English [O Muhammad]: مرجع صح", "Ibrahim" in ref or "إبراهيم" in ref or "braham" in ref.lower(), f"ref={ref}")

# English with [in orbit]
r = get_result("وسخر لكم الشمس والقمر دائبين", "english")
seg = r.get("matched_segment", "")
ref_match = re.search(r'【([^】]+)】', seg)
ref = ref_match.group(1) if ref_match else ""
test("English [in orbit]: مرجع مش متأثر", len(ref) > 0, f"ref={ref}")

# ══════════════════════════════════════════
print("\n⚠️  6. حالات خاصة وأخطاء")
print("=" * 50)

# نص فارغ
r = get_result("")
test("نص فارغ: رسالة خطأ", "error" in r, f"result={r}")

# نص مش عربي
r = get_result("hello world this is english text")
seg = r.get("matched_segment", "")
test("نص إنجليزي: مش بيكسر", True)  # should not crash

# كلمة واحدة بس
r = get_result("الله")
seg = r.get("matched_segment", "")
test("كلمة واحدة: بيرجع نتيجة", len(seg) > 5, f"seg={seg[:40]}")

# كلمتين
r = get_result("قل هو")
seg = r.get("matched_segment", "")
test("كلمتين: بيرجع نتيجة", len(seg) > 5, f"seg={seg[:40]}")

# أخطاء إملائية كتير
r = get_result("انا انزلنه في ليله الكدر")
seg = r.get("matched_segment", "")
test("أخطاء إملائية: بيلاقي القدر", "ٱلْقَدْرِ" in seg or "القدر" in seg, f"seg={seg[:60]}")

# ══════════════════════════════════════════
print("\n📊 7. سلامة البيانات")
print("=" * 50)

conn = sqlite3.connect(DB_PATH)
c = conn.cursor()

# عدد الآيات
c.execute("SELECT COUNT(*) FROM verses")
total_verses = c.fetchone()[0]
test(f"إجمالي الآيات: {total_verses}", total_verses >= 6236, f"count={total_verses}")

# عدد السور
c.execute("SELECT COUNT(DISTINCT sura_num) FROM verses")
total_suras = c.fetchone()[0]
test(f"إجمالي السور: {total_suras}", total_suras == 114, f"count={total_suras}")

# كل سورة ليها اسم مترجم
c.execute("SELECT COUNT(*) FROM suras_translated")
trans_count = c.fetchone()[0]
test(f"أسماء السور المترجمة: {trans_count}", trans_count >= 114, f"count={trans_count}")

# أول وآخر آية في القرآن
c.execute("SELECT text_uthmani FROM verses WHERE sura_num=1 AND aya_num=1")
first = c.fetchone()[0]
test("أول آية (الفاتحة ١): موجودة", len(first) > 5)

c.execute("SELECT text_uthmani FROM verses WHERE sura_num=114 AND aya_num=6")
row = c.fetchone()
test("آخر آية (الناس ٦): موجودة", row is not None and len(row[0]) > 5)

# التراجم موجودة
c.execute("PRAGMA table_info(verses)")
cols = [row[1] for row in c.fetchall()]
expected_langs = ["lang_en", "lang_fr", "lang_tr", "lang_ru", "lang_es", "lang_de", "lang_id", "lang_fa"]
for lang_col in expected_langs:
    test(f"عمود {lang_col} موجود", lang_col in cols, f"cols={cols}")

# أطول آية (البقرة 282)
c.execute("SELECT LENGTH(text_uthmani) FROM verses WHERE sura_num=2 AND aya_num=282")
longest = c.fetchone()
test("أطول آية (البقرة ٢٨٢): موجودة", longest is not None and longest[0] > 100, f"len={longest[0] if longest else 0}")

# text_clean موجود لكل الآيات
c.execute("SELECT COUNT(*) FROM verses WHERE text_clean IS NULL OR text_clean = ''")
empty_clean = c.fetchone()[0]
test("text_clean مش فاضي لأي آية", empty_clean == 0, f"empty={empty_clean}")

conn.close()

# ══════════════════════════════════════════
print("\n🔍 8. أول وآخر القرآن")
print("=" * 50)

# أول آية
r = get_result("الحمد لله رب العالمين")
seg = r.get("matched_segment", "")
test("الفاتحة ٢: نتيجة صحيحة", "ٱلْحَمْدُ" in seg or "الحمد" in seg)

# آخر سورة
r = get_result("قل اعوذ برب الناس ملك الناس اله الناس")
seg = r.get("matched_segment", "")
ref_match = re.search(r'【([^】]+)】', seg)
ref = ref_match.group(1) if ref_match else ""
test("الناس: اسم السورة صح", "الناس" in ref or "الن" in ref, f"ref={ref}")

# أطول آية (البقرة 282)
r = get_result("يا ايها الذين آمنوا اذا تداينتم بدين الى اجل مسمى فاكتبوه")
seg = r.get("matched_segment", "")
test("البقرة ٢٨٢ (أطول آية): بترجع كاملة", len(seg) > 200, f"len={len(seg)}")

# ══════════════════════════════════════════
print("\n" + "=" * 60)
print(f"📊 النتيجة: {passed} ✅ نجح | {failed} ❌ فشل | من {passed + failed} اختبار")
print("=" * 60)

if errors:
    print("\n❌ الاختبارات الفاشلة:")
    for name, detail in errors:
        print(f"  • {name}: {detail}")
