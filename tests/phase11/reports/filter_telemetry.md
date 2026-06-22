# Grammar Filter Telemetry Report

## Pipeline Funnel

| Stage | Count |
|---|---|
| Grammar raw outputs | 240 |
| Diffs extracted | 134 |
| **Accepted** | **44** |
| **Rejected** | **82** |

## Rejections by Filter

| Filter | Rejections | % of Total |
|---|---|---|
| PunctuationGuard | 32 | 39.0% |
| TanweenGuard | 30 | 36.6% |
| LatinGuard | 9 | 11.0% |
| DigitGuard | 5 | 6.1% |
| IVtoOOV | 3 | 3.7% |
| Jaccard_03 | 2 | 2.4% |
| StageLocker | 1 | 1.2% |

## Rejection Details

- **TanweenGuard**: `مهندساً` → `مهندسا` (sample: E004)
- **LatinGuard**: `GitHub` → `GitHuب` (sample: E022)
- **LatinGuard**: `Tesla` → `Teسla` (sample: E023)
- **LatinGuard**: `Node.js` → `Node ، jة` (sample: E027)
- **IVtoOOV**: `لعب` → `لعبوَ` (sample: G006)
- **TanweenGuard**: `جداً` → `جدا` (sample: G021)
- **IVtoOOV**: `يفعلون` → `يفعلوَ` (sample: G028)
- **TanweenGuard**: `كثيراً` → `كثيرا` (sample: G034)
- **TanweenGuard**: `غزيراً` → `غزيرا` (sample: G044)
- **PunctuationGuard**: `البلاد.` → `البلاد` (sample: H001)
- **PunctuationGuard**: `الماضية.` → `الماضية` (sample: H002)
- **PunctuationGuard**: `تحديثاً شاملاً.` → `تحديثا شاملا` (sample: H003)
- **TanweenGuard**: `مشروعاً جديداً` → `مشروعا جديدا` (sample: H004)
- **PunctuationGuard**: `الغربية.` → `الغربية` (sample: H004)
- **TanweenGuard**: `نمواً` → `نموا` (sample: H005)
- **PunctuationGuard**: `الأول.` → `الأول` (sample: H005)
- **PunctuationGuard**: `العالي.` → `العالي` (sample: H006)
- **PunctuationGuard**: `المدروسين.` → `المدروسين` (sample: H007)
- **PunctuationGuard**: `الظاهرة.` → `الظاهرة` (sample: H008)
- **PunctuationGuard**: `العينة.` → `العينة` (sample: H009)
- **PunctuationGuard**: `الفهم.` → `الفهم` (sample: H010)
- **PunctuationGuard**: `تطبيقات.` → `تطبيقات` (sample: H011)
- **PunctuationGuard**: `الأمامية.` → `الأمامية` (sample: H012)
- **PunctuationGuard**: `الطبيعية.` → `الطبيعية` (sample: H013)
- **TanweenGuard**: `وفقاً` → `وفقا` (sample: H014)
- **PunctuationGuard**: `بالتعويض.` → `بالتعويض` (sample: H014)
- **TanweenGuard**: `يوماً` → `يوما` (sample: H015)
- **PunctuationGuard**: `التعاقد.` → `التعاقد` (sample: H015)
- **PunctuationGuard**: `والأرجوان.` → `والأرجوان` (sample: H016)
- **TanweenGuard**: `سريعاً` → `سريعا` (sample: H018)
- **PunctuationGuard**: `القلوب.` → `القلوب` (sample: H018)
- **PunctuationGuard**: `المكتبة.` → `المكتبة` (sample: H019)
- **PunctuationGuard**: `خبزاً.` → `خبزا` (sample: H020)
- **PunctuationGuard**: `بوضوح.` → `بوضوح` (sample: H021)
- **PunctuationGuard**: `أجلها.` → `أجلها` (sample: H022)
- **PunctuationGuard**: `المدارك.` → `المدارك` (sample: H023)
- **PunctuationGuard**: `والصحة.` → `والصحة` (sample: H024)
- **PunctuationGuard**: `الصغير.` → `الصغير` (sample: H025)
- **PunctuationGuard**: `المستدامة.` → `المستدامة` (sample: H026)
- **PunctuationGuard**: `التعليمية.` → `التعليمية` (sample: H027)
- **PunctuationGuard**: `والجسدية.` → `والجسدية` (sample: H028)
- **PunctuationGuard**: `البشرية.` → `البشرية` (sample: H029)
- **TanweenGuard**: `دوراً مهماً` → `دورا مهما` (sample: H030)
- **PunctuationGuard**: `المعاصر.` → `المعاصر` (sample: H030)
- **TanweenGuard**: `جداً` → `جدا` (sample: P005)
- **TanweenGuard**: `خبزاً ولحماً` → `خبزا ولحما` (sample: P010)
- **PunctuationGuard**: `عدت.` → `عدت` (sample: P011)
- **PunctuationGuard**: `بخير.` → `بخير` (sample: P012)
- **PunctuationGuard**: `كتاباً.` → `كتابا` (sample: P015)
- **TanweenGuard**: `جداً` → `جدا` (sample: P020)
- **TanweenGuard**: `خيراً` → `خيرا` (sample: R018)
- **TanweenGuard**: `جداً` → `جدا` (sample: S003)
- **StageLocker**: `أرسل` → `أرسلت` (sample: S018)
- **IVtoOOV**: `فوراً` → `فورو` (sample: S018)
- **TanweenGuard**: `قليلاً` → `قليلا` (sample: S020)
- **TanweenGuard**: `غداً` → `غدا` (sample: S025)
- **TanweenGuard**: `جداً` → `جدا` (sample: S026)
- **TanweenGuard**: `جداً` → `جدا` (sample: S033)
- **TanweenGuard**: `جداً` → `جدا` (sample: S062)
- **TanweenGuard**: `ممطراً` → `ممطرا` (sample: S063)
- **TanweenGuard**: `جداً` → `جدا` (sample: S066)
- **TanweenGuard**: `دائماً` → `دائما` (sample: S069)
- **TanweenGuard**: `خبزاً` → `خبزا` (sample: S073)
- **TanweenGuard**: `جداً` → `جدا` (sample: S078)
- **LatinGuard**: `https://example.com` → `https://example.comا` (sample: SC001)
- **DigitGuard**: `2026-06-22` → `عشرين 26-06-22ا` (sample: SC009)
- **TanweenGuard**: `عصراً` → `عصرا` (sample: SC011)
- **TanweenGuard**: `مساءً` → `مساء` (sample: SC012)
- **DigitGuard**: `09:00 صباحاً` → `09:00ا صباحا` (sample: SC013)
- **DigitGuard**: `25.5 كيلومتر` → `ثلاث عشر كيلومترا` (sample: SC014)
- **DigitGuard**: `1,000,000` → `1 , 000 , 000` (sample: SC015)
- **DigitGuard**: `95.7%` → `95 ، 7 %` (sample: SC016)
- **Jaccard_03**: `100` → `مائة` (sample: SC018)
- **LatinGuard**: `35°C` → `35 ° C` (sample: SC019)
- **TanweenGuard**: `تقريباً` → `تقريبا` (sample: SC020)
- **LatinGuard**: `الوزن 75kg` → `الوزن75kg` (sample: SC021)
- **LatinGuard**: `print('مرحبا')` → `print ، ' مرحباا ،` (sample: SC022)
- **Jaccard_03**: `5;` → `خمسة ;` (sample: SC023)
- **LatinGuard**: `test() {}` → `test ، وذلك { }` (sample: SC024)
- **LatinGuard**: `{"name":"Mohamed"}` → `{ " name " : " Mohamed " }` (sample: SC026)
- **TanweenGuard**: `جداً` → `جدا` (sample: SC027)
- **TanweenGuard**: `شكراً` → `شكرا` (sample: SC029)
