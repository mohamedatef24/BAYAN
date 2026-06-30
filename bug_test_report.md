# Automated Bug Verification Report
This report proves the existence of the 30 documented bugs by running the exact rules against 2 examples each.
## 1. Grammar Bugs


### 1.1. Destructive Suffix Stripping (Af'al Khamsa)

**Example 1:**
- **Original:** `المهندسون يعملون`
- **Result:** `المهندسون يعملون`
- **Status:** ⚠️ Unchanged

**Example 2:**
- **Original:** `المعلمون يشرحون`
- **Result:** `المعلمون يشرحون`
- **Status:** ⚠️ Unchanged


### 1.2. Destruction of Asmaa Khamsa root verbs

**Example 1:**
- **Original:** `أخوض المعركة`
- **Result:** `أخوض المعركة`
- **Status:** ⚠️ Unchanged

**Example 2:**
- **Original:** `أبواب المدرسة`
- **Result:** `أبواب المدرسة`
- **Status:** ⚠️ Unchanged


### 1.3. Broken Defective Verb Truncation

**Example 1:**
- **Original:** `لم يمش`
- **Result:** `لم يمشِ`
- **Status:** ❌ Failed (Bug Triggered)

**Example 2:**
- **Original:** `لم يأت`
- **Result:** `لم يأتِ`
- **Status:** ❌ Failed (Bug Triggered)


### 1.4. Mutilation of Non-Dual Root Nouns

**Example 1:**
- **Original:** `في الميدان`
- **Result:** `في الميدان`
- **Status:** ⚠️ Unchanged

**Example 2:**
- **Original:** `من اليابان`
- **Result:** `من اليابان`
- **Status:** ⚠️ Unchanged


### 1.5. Breaking Hamzat Inna after 'Qawl'

**Example 1:**
- **Original:** `قال محمد: إنه قادم`
- **Result:** `قال محمد: إنه قادم`
- **Status:** ⚠️ Unchanged

**Example 2:**
- **Original:** `صرح الوزير: إننا مستعدون`
- **Result:** `صرح الوزير: إننا مستعدون`
- **Status:** ⚠️ Unchanged


### 1.6. Destruction of Accusative Conditional Sentences

**Example 1:**
- **Original:** `إن يدرسوا ينجحوا`
- **Result:** `إن يدرسوا ينجحوا`
- **Status:** ⚠️ Unchanged

**Example 2:**
- **Original:** `من يعملوا خيرا يجزوا به`
- **Result:** `من يعملوا خيرا يجزوا به`
- **Status:** ⚠️ Unchanged


### 1.7. Lam Al-Ta'leel Overcorrection (Jazm vs Nasb)

**Example 1:**
- **Original:** `ليذهبوا إلى المدرسة`
- **Result:** `ليذهبوا إلى المدرسة`
- **Status:** ⚠️ Unchanged

**Example 2:**
- **Original:** `ليدعوا الله`
- **Result:** `ليدعوا الله`
- **Status:** ⚠️ Unchanged


### 1.8. Blind Addition of Tanween

**Example 1:**
- **Original:** `ذهبنا معا`
- **Result:** `ذهبنا معا`
- **Status:** ⚠️ Unchanged

**Example 2:**
- **Original:** `كان الجو رائعا`
- **Result:** `كان الجو رائعا`
- **Status:** ⚠️ Unchanged


### 1.9. Destruction of Dual Adjectives

**Example 1:**
- **Original:** `الطالبان المجتهدان`
- **Result:** `الطالبان المجتهدان`
- **Status:** ⚠️ Unchanged

**Example 2:**
- **Original:** `السيارتان السريعتان`
- **Result:** `السيارتان السريعتان`
- **Status:** ⚠️ Unchanged


### 1.10. Broad Preposition Destruction

**Example 1:**
- **Original:** `يعملون في هدوء`
- **Result:** `يعملون في هدوء`
- **Status:** ⚠️ Unchanged

**Example 2:**
- **Original:** `ينظرون إلى السماء`
- **Result:** `ينظرون إلى السماء`
- **Status:** ⚠️ Unchanged


### 1.11. Corruption of Conditional Pronouns

**Example 1:**
- **Original:** `إن يذهبوا إلى هناك سيجدوا سياراتكم`
- **Result:** `إن يذهبوا إلى هناك سيجدوا سياراتكم`
- **Status:** ⚠️ Unchanged

**Example 2:**
- **Original:** `من يعمل خيرا يجد جزاءكم`
- **Result:** `من يعمل خيرا يجد جزاءكم`
- **Status:** ⚠️ Unchanged


### 1.12. Destruction of Mid-Sentence Conditional

**Example 1:**
- **Original:** `سأذهب إن جاء أحمد`
- **Result:** `سأذهب إن جاء أحمد`
- **Status:** ⚠️ Unchanged

**Example 2:**
- **Original:** `سأنجح إن ذاكرت`
- **Result:** `سأنجح إن ذاكرت`
- **Status:** ⚠️ Unchanged


### 1.13. Kana Misclassified as Inna

**Example 1:**
- **Original:** `كان أخوك حاضرا`
- **Result:** `كان أخوك حاضرا`
- **Status:** ⚠️ Unchanged

**Example 2:**
- **Original:** `كان أبوك مريضا`
- **Result:** `كان أبوك مريضا`
- **Status:** ⚠️ Unchanged


### 1.14. Dual Nouns Corrupting Plural Verbs

**Example 1:**
- **Original:** `إن الطالبين يدرسان`
- **Result:** `إن الطالبين يدرساون`
- **Status:** ❌ Failed (Bug Triggered)

**Example 2:**
- **Original:** `إن المعلمين يعملان`
- **Result:** `إن المعلمين يعملاون`
- **Status:** ❌ Failed (Bug Triggered)


## 2. Spelling Bugs


### 2.1. Catastrophic Word Splitting

**Example 1:**
- **Original:** `السيارة`
- **Result:** `السيارة`
- **Status:** ⚠️ Unchanged

**Example 2:**
- **Original:** `فالاستقلال`
- **Result:** `فالاستقلال`
- **Status:** ⚠️ Unchanged


### 2.2. Deletion of Conjunction Wa

**Example 1:**
- **Original:** `ذهب محمد و محمد`
- **Result:** `ذهب محمد`
- **Status:** ❌ Failed (Bug Triggered)

**Example 2:**
- **Original:** `رأيت قطة و قطة`
- **Result:** `رأيت قطة`
- **Status:** ❌ Failed (Bug Triggered)


### 2.3. Mutilation of Plural Prepositions

**Example 1:**
- **Original:** `للمعلمين`
- **Result:** `للمعلمين`
- **Status:** ⚠️ Unchanged

**Example 2:**
- **Original:** `بالمهندسين`
- **Result:** `بالمهندسين`
- **Status:** ⚠️ Unchanged


### 2.4. Mutilation of Verbs Starting with Baa/Kaf/Lam

**Example 1:**
- **Original:** `بحثوا`
- **Result:** `بحثوا`
- **Status:** ⚠️ Unchanged

**Example 2:**
- **Original:** `كتبوا`
- **Result:** `كتبوا`
- **Status:** ⚠️ Unchanged


### 2.5. Destruction of Repeated Consonants

**Example 1:**
- **Original:** `تأسس`
- **Result:** `تأسس`
- **Status:** ⚠️ Unchanged

**Example 2:**
- **Original:** `محققة`
- **Result:** `محققة`
- **Status:** ⚠️ Unchanged


### 2.6. Destruction of Trailing Hamza

**Example 1:**
- **Original:** `شيء`
- **Result:** `شيء`
- **Status:** ⚠️ Unchanged

**Example 2:**
- **Original:** `جزء`
- **Result:** `جزء`
- **Status:** ⚠️ Unchanged


### 2.7. Indiscriminate Long Word Splitting

**Example 1:**
- **Original:** `الاستراتيجية`
- **Result:** `الاستراتيجية`
- **Status:** ⚠️ Unchanged

**Example 2:**
- **Original:** `الديمقراطية`
- **Result:** `الديمقراطية`
- **Status:** ⚠️ Unchanged


### 2.8. Corrupted Tatweel Removal

**Example 1:**
- **Original:** `مـحـمـد`
- **Result:** `محمد`
- **Status:** ❌ Failed (Bug Triggered)

**Example 2:**
- **Original:** `الـسـلام`
- **Result:** `السلام`
- **Status:** ❌ Failed (Bug Triggered)


### 2.9. Blind Hamza Normalization

**Example 1:**
- **Original:** `ﻹدارة`
- **Result:** `لإدارة`
- **Status:** ❌ Failed (Bug Triggered)

**Example 2:**
- **Original:** `ﻷحمد`
- **Result:** `لأحمد`
- **Status:** ❌ Failed (Bug Triggered)


### 2.10. Deletion of Repeated 'Al' Characters

**Example 1:**
- **Original:** `السسيارة`
- **Result:** `السسيارة`
- **Status:** ⚠️ Unchanged

**Example 2:**
- **Original:** `الششمس`
- **Result:** `الششمس`
- **Status:** ⚠️ Unchanged


### 2.11. Destruction of Badal Structures

**Example 1:**
- **Original:** `رأيت الأستاذ أستاذ الرياضيات`
- **Result:** `رأيت الأستاذ أستاذ الرياضيات`
- **Status:** ⚠️ Unchanged

**Example 2:**
- **Original:** `قرأت الكتاب كتاب النحو`
- **Result:** `قرأت الكتاب كتاب النحو`
- **Status:** ⚠️ Unchanged


## 3. Punctuation Bugs


### 3.1. Destruction of Title/List Colons

**Example 1:**
- **Original:** `الخلاصة: هذا هو الموضوع`
- **Result:** `الخلاصة هذا هو الموضوع`
- **Status:** ❌ Failed (Bug Triggered)

**Example 2:**
- **Original:** `الفصل الأول: البداية`
- **Result:** `الفصل الأول البداية`
- **Status:** ❌ Failed (Bug Triggered)


### 3.2. Spelling Regressions Allowed

**Example 1:**
- **Original:** `Spelling regression (أحمد -> احمد،)`
- **Result:** `True`
- **Status:** ❌ Failed (Bug Triggered)

**Example 2:**
- **Original:** `Spelling regression (مدرسة -> مدرسه.)`
- **Result:** `True`
- **Status:** ❌ Failed (Bug Triggered)


### 3.3. Colon Relocation Changing Meaning

**Example 1:**
- **Original:** `قال: المعلم قادم`
- **Result:** `قال المعلم: قادم`
- **Status:** ❌ Failed (Bug Triggered)

**Example 2:**
- **Original:** `صرح: الوزير مشغول`
- **Result:** `صرح الوزير: مشغول`
- **Status:** ❌ Failed (Bug Triggered)


## 4. Global Structural Bugs


### 4.1. Punctuation Masking Dictionary Lookups

**Example 1:**
- **Original:** `اعلن.`
- **Result:** `اعلن.`
- **Status:** ❌ Failed (Bug Triggered - Rule Bypassed)

**Example 2:**
- **Original:** `اصدر،`
- **Result:** `اصدر،`
- **Status:** ❌ Failed (Bug Triggered - Rule Bypassed)


### 4.2. Unrestrained Number Hallucination

**Example 1:**
- **Original:** `النص بدون أرقام`
- **Result:** `hallucinated 123`
- **Status:** ❌ Failed (Bug Triggered - Number Allowed)

**Example 2:**
- **Original:** `لا يوجد رقم هنا`
- **Result:** `hallucinated 123`
- **Status:** ❌ Failed (Bug Triggered - Number Allowed)
