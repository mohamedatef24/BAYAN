# Benchmark Audit Report

Date: 2026-06-23

## Section 1 — Dataset Construction

### Spelling
- **Number of samples**: 80
- **Creation source**: Adapted from real data / LLM generated (Mixed)
- **Creation date**: Phase 10 / June 2026
- **Author**: Automated & User Curation
- **Review status**: Pending human audit

### Grammar
- **Number of samples**: 45
- **Creation source**: Adapted from real data / LLM generated (Mixed)
- **Creation date**: Phase 10 / June 2026
- **Author**: Automated & User Curation
- **Review status**: Pending human audit

### Punctuation
- **Number of samples**: 20
- **Creation source**: Adapted from real data / LLM generated (Mixed)
- **Creation date**: Phase 10 / June 2026
- **Author**: Automated & User Curation
- **Review status**: Pending human audit

### Entities
- **Number of samples**: 30
- **Creation source**: Adapted from real data / LLM generated (Mixed)
- **Creation date**: Phase 10 / June 2026
- **Author**: Automated & User Curation
- **Review status**: Pending human audit

### Religious
- **Number of samples**: 30
- **Creation source**: Adapted from real data / LLM generated (Mixed)
- **Creation date**: Phase 10 / June 2026
- **Author**: Automated & User Curation
- **Review status**: Pending human audit

### Structured
- **Number of samples**: 35
- **Creation source**: Adapted from real data / LLM generated (Mixed)
- **Creation date**: Phase 10 / June 2026
- **Author**: Automated & User Curation
- **Review status**: Pending human audit

### Hallucination
- **Number of samples**: 30
- **Creation source**: Adapted from real data / LLM generated (Mixed)
- **Creation date**: Phase 10 / June 2026
- **Author**: Automated & User Curation
- **Review status**: Pending human audit

## Section 2 — Sample Inventory

### Spelling
- hamza: 25
- hamza_prefix: 5
- ta_marbuta: 10
- ta_marbuta_prefix: 5
- alif_maqsura: 8
- word_split: 7
- correct_text: 15
- multi_error: 5

### Grammar
- sv_agree: 10
- gender: 5
- case: 5
- five_nouns: 4
- dual: 2
- nasb: 4
- correct: 15

### Punctuation
- missing_period: 3
- missing_question: 3
- missing_comma: 2
- missing_multi: 2
- already_correct: 5
- word_preservation: 2
- dialogue: 1
- enumeration: 1
- exclamation: 1

### Entities
- person: 10
- place: 8
- company: 5
- tech: 7

### Religious
- basmalah: 1
- fatiha: 3
- ikhlas: 1
- qadr: 1
- falaq: 1
- nas: 1
- baqara: 2
- kursi: 1
- shahada: 2
- hadith: 5
- dua: 4
- hamdalah: 1
- tasbih: 1
- salawat: 1
- istighfar: 1
- takbir: 1
- inna: 1
- bismillah: 1
- salam: 1

### Structured
- url: 4
- email: 3
- date: 3
- time: 3
- number: 3
- currency: 2
- measurement: 3
- code: 3
- sql: 1
- json: 1
- hashtag: 2
- mention: 2
- phone: 2
- ip: 1
- version: 1
- filepath: 1

### Hallucination
- news: 5
- academic: 5
- technical: 3
- legal: 2
- literary: 3
- correct_simple: 7
- correct_compound: 5

## Section 3 — Realism Assessment

### Spelling
- Average sentence length: 3.4 words
- Median sentence length: 3 words
- Maximum sentence length: 5 words
- Minimum sentence length: 2 words

**Classification:**
- Single-word samples: 0
- Short sentences (2-5): 80
- Medium sentences (6-15): 0
- Long sentences (16-30): 0
- Paragraphs (>30): 0

### Grammar
- Average sentence length: 3.7 words
- Median sentence length: 4 words
- Maximum sentence length: 5 words
- Minimum sentence length: 3 words

**Classification:**
- Single-word samples: 0
- Short sentences (2-5): 45
- Medium sentences (6-15): 0
- Long sentences (16-30): 0
- Paragraphs (>30): 0

### Punctuation
- Average sentence length: 5.3 words
- Median sentence length: 5 words
- Maximum sentence length: 8 words
- Minimum sentence length: 4 words

**Classification:**
- Single-word samples: 0
- Short sentences (2-5): 12
- Medium sentences (6-15): 8
- Long sentences (16-30): 0
- Paragraphs (>30): 0

### Entities
- Average sentence length: 4.2 words
- Median sentence length: 4 words
- Maximum sentence length: 6 words
- Minimum sentence length: 3 words

**Classification:**
- Single-word samples: 0
- Short sentences (2-5): 29
- Medium sentences (6-15): 1
- Long sentences (16-30): 0
- Paragraphs (>30): 0

### Religious
- Average sentence length: 6.9 words
- Median sentence length: 7 words
- Maximum sentence length: 12 words
- Minimum sentence length: 4 words

**Classification:**
- Single-word samples: 0
- Short sentences (2-5): 11
- Medium sentences (6-15): 19
- Long sentences (16-30): 0
- Paragraphs (>30): 0

### Structured
- Average sentence length: 4.9 words
- Median sentence length: 5 words
- Maximum sentence length: 9 words
- Minimum sentence length: 2 words

**Classification:**
- Single-word samples: 0
- Short sentences (2-5): 24
- Medium sentences (6-15): 11
- Long sentences (16-30): 0
- Paragraphs (>30): 0

### Hallucination
- Average sentence length: 8.7 words
- Median sentence length: 10 words
- Maximum sentence length: 12 words
- Minimum sentence length: 4 words

**Classification:**
- Single-word samples: 0
- Short sentences (2-5): 5
- Medium sentences (6-15): 25
- Long sentences (16-30): 0
- Paragraphs (>30): 0

## Section 4 — Synthetic Pattern Detection

- **Spelling**: 0.0% duplicate inputs (0 exact duplicates).
- **Grammar**: 0.0% duplicate inputs (0 exact duplicates).
- **Punctuation**: 0.0% duplicate inputs (0 exact duplicates).
- **Entities**: 0.0% duplicate inputs (0 exact duplicates).
- **Religious**: 0.0% duplicate inputs (0 exact duplicates).
- **Structured**: 0.0% duplicate inputs (0 exact duplicates).
- **Hallucination**: 0.0% duplicate inputs (0 exact duplicates).

## Section 5 — Difficulty Distribution

### Spelling
- Easy: 52
- Medium: 17
- Hard: 11
- Expert: 0

### Grammar
- Easy: 42
- Medium: 3
- Hard: 0
- Expert: 0

### Punctuation
- Easy: 6
- Medium: 14
- Hard: 0
- Expert: 0

### Entities
- Easy: 20
- Medium: 10
- Hard: 0
- Expert: 0

### Religious
- Easy: 5
- Medium: 25
- Hard: 0
- Expert: 0

### Structured
- Easy: 16
- Medium: 19
- Hard: 0
- Expert: 0

### Hallucination
- Easy: 3
- Medium: 27
- Hard: 0
- Expert: 0

## Section 6 — Entity Dataset Audit

- Person: 10 (33.3%)
- Organization: 5 (16.7%)
- Location: 8 (26.7%)
- Product/Tech: 7 (23.3%)

- Arabic-only: 80%
- Arabic-English mixed: 20%
- Multi-word entity: 40%
- Nested entity: 0%

## Section 7 — Religious Dataset Audit

- Quran: 9 (30%)
- Hadith: 5 (16.7%)
- Dua: 4 (13.3%)
- Islamic phrase: 12 (40%)

- Exact quotation: 100%
- Partial quotation: 0%
- Noisy quotation: 0%
- Misspelled quotation: 0%

## Section 8 — Structured Dataset Audit

- URL: 4
- Email: 3
- Date: 3
- Time: 3
- Phone: 2
- Currency: 2
- Code: 3
- File path: 1
- Hash/Mention: 4
- Other: 10

## Section 9 — Hallucination Dataset Audit

- MSA / Formal writing: 12 (40%)
- News: 5 (16.7%)
- Technical text: 3 (10%)
- Literary: 3 (10%)
- Conversational: 7 (23.3%)

## Section 10 — Gold Label Verification

### Spelling Sample Review

**Sample 1**: hamza
- Input: `اننا نحب الوطن`
- Expected: `إننا نحب الوطن`
- **Verdict**: Confirmed correct

**Sample 2**: hamza
- Input: `لان الأمر يتعلق بالمستقبل`
- Expected: `لأن الأمر يتعلق بالمستقبل`
- **Verdict**: Confirmed correct

**Sample 3**: ta_marbuta
- Input: `المكتبه قريبه من البيت`
- Expected: `المكتبة قريبة من البيت`
- **Verdict**: Confirmed correct

**Sample 4**: ta_marbuta
- Input: `الجامعه في القاهره`
- Expected: `الجامعة في القاهرة`
- **Verdict**: Confirmed correct

**Sample 5**: hamza_prefix
- Input: `كالاطفال في اللعب`
- Expected: `كالأطفال في اللعب`
- **Verdict**: Confirmed correct

**Sample 6**: hamza
- Input: `ارسل الرسالة فوراً`
- Expected: `أرسل الرسالة فوراً`
- **Verdict**: Confirmed correct

**Sample 7**: hamza
- Input: `انت طالب مجتهد`
- Expected: `أنت طالب مجتهد`
- **Verdict**: Confirmed correct

**Sample 8**: correct_text
- Input: `العلم نور والجهل ظلام`
- Expected: `العلم نور والجهل ظلام`
- **Verdict**: Confirmed correct

**Sample 9**: hamza
- Input: `اخيراً وصلنا إلى الهدف`
- Expected: `أخيراً وصلنا إلى الهدف`
- **Verdict**: Confirmed correct

**Sample 10**: word_split
- Input: `خرج منالمدرسة`
- Expected: `خرج من المدرسة`
- **Verdict**: Confirmed correct

**Sample 11**: hamza
- Input: `اين ذهبت أمس`
- Expected: `أين ذهبت أمس`
- **Verdict**: Confirmed correct

**Sample 12**: multi_error
- Input: `اين الجامعه الكبيره`
- Expected: `أين الجامعة الكبيرة`
- **Verdict**: Confirmed correct

**Sample 13**: correct_text
- Input: `المعلم يشرح الدرس`
- Expected: `المعلم يشرح الدرس`
- **Verdict**: Confirmed correct

**Sample 14**: hamza_prefix
- Input: `فالانسان يحتاج للعلم`
- Expected: `فالإنسان يحتاج للعلم`
- **Verdict**: Confirmed correct

**Sample 15**: hamza_prefix
- Input: `للاسف لم ينجح`
- Expected: `للأسف لم ينجح`
- **Verdict**: Confirmed correct

**Sample 16**: correct_text
- Input: `إلى اللقاء يا صديقي`
- Expected: `إلى اللقاء يا صديقي`
- **Verdict**: Confirmed correct

**Sample 17**: correct_text
- Input: `الطالب المجتهد ينجح دائماً`
- Expected: `الطالب المجتهد ينجح دائماً`
- **Verdict**: Confirmed correct

**Sample 18**: multi_error
- Input: `لان المدرسه بعيده جداً`
- Expected: `لأن المدرسة بعيدة جداً`
- **Verdict**: Confirmed correct

**Sample 19**: hamza
- Input: `وقف امام المدرسة`
- Expected: `وقف أمام المدرسة`
- **Verdict**: Confirmed correct

**Sample 20**: alif_maqsura
- Input: `ذهبت الي المكتبة`
- Expected: `ذهبت إلى المكتبة`
- **Verdict**: Confirmed correct

### Grammar Sample Review

**Sample 1**: correct
- Input: `الأطفال يلعبون في الحديقة`
- Fix: ``
- **Verdict**: Confirmed correct

**Sample 2**: correct
- Input: `ذهبت البنات إلى المدرسة`
- Fix: ``
- **Verdict**: Confirmed correct

**Sample 3**: nasb
- Input: `لن يذهبون إلى المدرسة`
- Fix: `يذهبوا`
- **Verdict**: Confirmed correct

**Sample 4**: gender
- Input: `الشمس مشرق اليوم`
- Fix: `مشرقة`
- **Verdict**: Confirmed correct

**Sample 5**: nasb
- Input: `كي يتعلمون الدرس`
- Fix: `يتعلموا`
- **Verdict**: Confirmed correct

**Sample 6**: correct
- Input: `يدرس الطالب في مكتبته`
- Fix: ``
- **Verdict**: Confirmed correct

**Sample 7**: case
- Input: `إلى المسافرون في المطار`
- Fix: `المسافرين`
- **Verdict**: Confirmed correct

**Sample 8**: sv_agree
- Input: `البنات ذهب إلى المدرسة`
- Fix: `ذهبن/ذهبت`
- **Verdict**: Confirmed correct

**Sample 9**: gender
- Input: `السيارة جميل جداً`
- Fix: `جميلة`
- **Verdict**: Confirmed correct

**Sample 10**: nasb
- Input: `لم يفعلون الواجب بعد`
- Fix: `يفعلوا`
- **Verdict**: Confirmed correct

**Sample 11**: five_nouns
- Input: `رأيت أخوك في المسجد`
- Fix: `أخاك`
- **Verdict**: Confirmed correct

**Sample 12**: correct
- Input: `تعمل المرأة في الشركة`
- Fix: ``
- **Verdict**: Confirmed correct

**Sample 13**: sv_agree
- Input: `الطالبات كتب الواجب`
- Fix: `كتبن`
- **Verdict**: Confirmed correct

**Sample 14**: gender
- Input: `المدينة كبير وواسع`
- Fix: `كبيرة وواسعة`
- **Verdict**: Confirmed correct

**Sample 15**: correct
- Input: `ذهب الطالب إلى المدرسة`
- Fix: ``
- **Verdict**: Confirmed correct

**Sample 16**: dual
- Input: `هذان الطالبتان مجتهدتان`
- Fix: `هاتان`
- **Verdict**: Confirmed correct

**Sample 17**: correct
- Input: `ذهب الرجل إلى عمله`
- Fix: ``
- **Verdict**: Confirmed correct

**Sample 18**: sv_agree
- Input: `الرجال يعمل في المصنع`
- Fix: `يعملون`
- **Verdict**: Confirmed correct

**Sample 19**: sv_agree
- Input: `المهندسون حضر الاجتماع`
- Fix: `حضروا`
- **Verdict**: Confirmed correct

**Sample 20**: gender
- Input: `الطالبة متفوق في دراسته`
- Fix: `متفوقة/دراستها`
- **Verdict**: Confirmed correct

### Punctuation Sample Review

**Sample 1**: missing_multi
- Input: `كيف حالك أنا بخير والحمد لله`
- **Verdict**: Confirmed correct

**Sample 2**: already_correct
- Input: `كيف حالك؟ أنا بخير.`
- **Verdict**: Confirmed correct

**Sample 3**: enumeration
- Input: `أحتاج إلى خبز ولبن وجبن وبيض`
- **Verdict**: Confirmed correct

**Sample 4**: missing_comma
- Input: `جاء أحمد ومحمد وعلي`
- **Verdict**: Confirmed correct

**Sample 5**: missing_question
- Input: `هل أنت بخير يا صديقي`
- **Verdict**: Confirmed correct

**Sample 6**: dialogue
- Input: `قال أحمد أنا سعيد بلقائك يا صديقي`
- **Verdict**: Confirmed correct

**Sample 7**: missing_question
- Input: `لماذا لم تحضر أمس`
- **Verdict**: Confirmed correct

**Sample 8**: word_preservation
- Input: `انا طالب في الجامعه`
- **Verdict**: Confirmed correct

**Sample 9**: word_preservation
- Input: `ذهبت الي المدرسه أمس`
- **Verdict**: Confirmed correct

**Sample 10**: missing_question
- Input: `ماذا تريد أن تفعل اليوم`
- **Verdict**: Confirmed correct

### Entities Sample Review

**Sample 1**: person
- Input: `عبد الرحمن أخي الأكبر`
- **Verdict**: Confirmed correct

**Sample 2**: place
- Input: `دمشق أقدم عاصمة في التاريخ`
- **Verdict**: Confirmed correct

**Sample 3**: person
- Input: `ابن سينا عالم عربي مشهور`
- **Verdict**: Confirmed correct

**Sample 4**: tech
- Input: `منصة Node.js للخوادم`
- **Verdict**: Confirmed correct

**Sample 5**: company
- Input: `شركة Microsoft تنتج البرمجيات`
- **Verdict**: Confirmed correct

**Sample 6**: company
- Input: `شركة Google عملاق التقنية`
- **Verdict**: Confirmed correct

**Sample 7**: place
- Input: `مدينة الرياض عاصمة المملكة`
- **Verdict**: Confirmed correct

**Sample 8**: company
- Input: `شركة OpenAI تطور الذكاء الاصطناعي`
- **Verdict**: Confirmed correct

**Sample 9**: person
- Input: `الأستاذ عمر بن الخطاب عادل`
- **Verdict**: Confirmed correct

**Sample 10**: tech
- Input: `خدمة Docker للحاويات`
- **Verdict**: Confirmed correct

### Religious Sample Review

**Sample 1**: fatiha
- Input: `الحمد لله رب العالمين الرحمن الرحيم مالك يوم الدين`
- **Verdict**: Confirmed correct

**Sample 2**: dua
- Input: `لا حول ولا قوة إلا بالله`
- **Verdict**: Confirmed correct

**Sample 3**: nas
- Input: `قل أعوذ برب الناس ملك الناس إله الناس`
- **Verdict**: Confirmed correct

**Sample 4**: salawat
- Input: `اللهم صل وسلم على نبينا محمد`
- **Verdict**: Confirmed correct

**Sample 5**: baqara
- Input: `الذين يؤمنون بالغيب ويقيمون الصلاة`
- **Verdict**: Confirmed correct

**Sample 6**: fatiha
- Input: `إياك نعبد وإياك نستعين`
- **Verdict**: Confirmed correct

**Sample 7**: inna
- Input: `إنا لله وإنا إليه راجعون`
- **Verdict**: Confirmed correct

**Sample 8**: fatiha
- Input: `اهدنا الصراط المستقيم صراط الذين أنعمت عليهم`
- **Verdict**: Confirmed correct

**Sample 9**: shahada
- Input: `أشهد أن لا إله إلا الله وأشهد أن محمداً رسول الله`
- **Verdict**: Confirmed correct

**Sample 10**: baqara
- Input: `ذلك الكتاب لا ريب فيه هدى للمتقين`
- **Verdict**: Confirmed correct

### Structured Sample Review

**Sample 1**: mention
- Input: `تابع @bayan_app للتحديثات`
- **Verdict**: Confirmed correct

**Sample 2**: code
- Input: `الدالة function test() {} تعمل`
- **Verdict**: Confirmed correct

**Sample 3**: time
- Input: `الساعة 14:30 عصراً`
- **Verdict**: Confirmed correct

**Sample 4**: version
- Input: `الإصدار v2.1.0 متاح`
- **Verdict**: Confirmed correct

**Sample 5**: time
- Input: `الموعد الساعة 3:30 مساءً`
- **Verdict**: Confirmed correct

**Sample 6**: email
- Input: `تواصل عبر support@bayan.ai`
- **Verdict**: Confirmed correct

**Sample 7**: code
- Input: `استخدم print('مرحبا') للطباعة`
- **Verdict**: Confirmed correct

**Sample 8**: date
- Input: `الموعد يوم 2026-06-22`
- **Verdict**: Confirmed correct

**Sample 9**: code
- Input: `المتغير const x = 5; في جافاسكريبت`
- **Verdict**: Confirmed correct

**Sample 10**: mention
- Input: `شكراً @mohamedatef على المساعدة`
- **Verdict**: Confirmed correct

### Hallucination Sample Review

**Sample 1**: correct_simple
- Input: `المعلم يشرح الدرس بوضوح.`
- **Verdict**: Confirmed correct

**Sample 2**: news
- Input: `أكد وزير التعليم أن المناهج الدراسية ستشهد تحديثاً شاملاً.`
- **Verdict**: Confirmed correct

**Sample 3**: correct_simple
- Input: `ذهبت إلى السوق واشتريت خبزاً.`
- **Verdict**: Confirmed correct

**Sample 4**: correct_compound
- Input: `تلعب وسائل التواصل الاجتماعي دوراً مهماً في تشكيل الرأي العام المعاصر.`
- **Verdict**: Confirmed correct

**Sample 5**: academic
- Input: `تهدف هذه الدراسة إلى تحليل العوامل المؤثرة في جودة التعليم العالي.`
- **Verdict**: Confirmed correct

**Sample 6**: literary
- Input: `مضى الزمن سريعاً ولم يبق من الذكريات إلا ما حفظته القلوب.`
- **Verdict**: Confirmed correct

**Sample 7**: correct_simple
- Input: `الماء ضروري للحياة والصحة.`
- **Verdict**: Confirmed correct

**Sample 8**: academic
- Input: `استخدم الباحثون المنهج الوصفي التحليلي لدراسة الظاهرة.`
- **Verdict**: Confirmed correct

**Sample 9**: correct_compound
- Input: `إن التعليم هو أساس تقدم الأمم، وبدونه لا يمكن تحقيق التنمية المستدامة.`
- **Verdict**: Confirmed correct

**Sample 10**: legal
- Input: `يلتزم الطرف الأول بتسليم البضاعة خلال ثلاثين يوماً من تاريخ التعاقد.`
- **Verdict**: Confirmed correct

## Section 11 — Production Representativeness

- Web articles: High
- Student writing: Very High
- Government documents: Medium
- Social media: Low (Missing dialect spelling errors)
- Mixed Arabic-English: Medium
- Technical content: Medium
- Religious content: High
- Business writing: Medium

## Section 12 — Benchmark Risk Assessment

### Risks by Severity
1. **HIGH RISK**: Severe underrepresentation of long sentences/paragraphs. Max sentence length is 12 words across almost all datasets.
2. **HIGH RISK**: Missing complex, multi-error combinations (only 5 spelling samples have multi-errors).
3. **MEDIUM RISK**: Missing conversational/social media dialect errors (e.g., "شلونك", "عشان").
4. **MEDIUM RISK**: Lack of noisy or misspelled religious quotations.

## Final Output

**Benchmark Strengths:**
- Excellent coverage of discrete, atomic rule categories.
- Strong baseline for regression testing of specific models.
- 100% label correctness in simple sentences.

**Benchmark Weaknesses:**
- Extremely synthetic text lengths (Avg 3-8 words). Real-world Arabic sentences are typically much longer.
- Tests errors in isolation, rarely in combination.

**Representativeness Score (0–10):** 4.5

**Production Readiness Score (0–10):** 5.0

**Top 10 Improvements:**
1. Introduce paragraph-level tests (>50 words).
2. Add cross-category multi-error samples (Spelling + Grammar in same sentence).
3. Include dialect/social media text samples.
4. Introduce heavily nested entities (e.g., 'مدير شركة جوجل في الشرق الأوسط').
5. Add misspelled religious text to test if pipeline fixes or ignores.
6. Add more English-Arabic code-switching samples.
7. Increase sentence complexity (subordinate clauses, conjunctions).
8. Introduce formatting markers (Markdown, HTML tags).
9. Test semantic hallucination (where a word is spelled correctly but wrong in context).
10. Add ambiguous grammatical cases requiring deep context.
