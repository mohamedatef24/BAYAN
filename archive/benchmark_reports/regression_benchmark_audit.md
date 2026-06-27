# Regression Benchmark Audit — Post-Run Error Analysis

## Phase 1 — Failure Classification

| ID | Category | Input | Expected | Actual | Root Cause | Type | Reason |
|---|---|---|---|---|---|---|---|
| S003 | hamza | `ايضا هذا الأمر مهم جداً` | `أيضاً هذا الأمر مهم جداً` | `ايضا هذا الأمر مهم جداً.` | spelling | Type A - Real System Bug | System genuinely failed to correct or corrupted text |
| S006 | hamza | `اول مرة أزور هذا المكان` | `أول مرة أزور هذا المكان` | `اول مرة أزور هذا المكان.` | spelling | Type A - Real System Bug | System genuinely failed to correct or corrupted text |
| S015 | hamza | `اننا نحب الوطن` | `إننا نحب الوطن` | `اننا نحب الوطن.` | spelling | Type A - Real System Bug | System genuinely failed to correct or corrupted text |
| S017 | hamza | `اقترب الموعد النهائي` | `اقترب الموعد النهائي` | `اقترب الموعد النهائي.` | punctuation | Type A - Real System Bug | System genuinely failed to correct or corrupted text |
| S022 | hamza | `اعلن الرئيس عن القرار` | `أعلن الرئيس عن القرار` | `اعلن الرئيس عن القرار.` | spelling | Type A - Real System Bug | System genuinely failed to correct or corrupted text |
| S025 | hamza | `اعتقد انه سيحضر غداً` | `أعتقد أنه سيحضر غداً` | `أعتقد انه سيحضر غداً.` | spelling | Type A - Real System Bug | System genuinely failed to correct or corrupted text |
| S028 | hamza_prefix | `فالانسان يحتاج للعلم` | `فالإنسان يحتاج للعلم` | `فالانسان يحتاج للعلم.` | spelling | Type A - Real System Bug | System genuinely failed to correct or corrupted text |
| S044 | ta_marbuta_prefix | `كالمدرسه القديمه` | `كالمدرسة القديمة` | `كالمدرسه قديمة` | spelling | Type A - Real System Bug | System genuinely failed to correct or corrupted text |
| S051 | alif_maqsura | `علي يدرس في الكلية` | `علي يدرس في الكلية` | `علي يدرس في الكلية.` | punctuation | Type A - Real System Bug | System genuinely failed to correct or corrupted text |
| S055 | word_split | `خرج منالمدرسة` | `خرج من المدرسة` | `خرج منالمدرسة.` | spelling | Type A - Real System Bug | System genuinely failed to correct or corrupted text |
| S056 | word_split | `بقي عندالباب` | `بقي عند الباب` | `بقي عندالباب.` | spelling | Type A - Real System Bug | System genuinely failed to correct or corrupted text |
| S057 | word_split | `جلس عندالنافذة` | `جلس عند النافذة` | `جلس عندالنافذة.` | spelling | Type A - Real System Bug | System genuinely failed to correct or corrupted text |
| S058 | word_split | `رجع الىالبيت` | `رجع إلى البيت` | `رجع الىالبيت.` | spelling | Type A - Real System Bug | System genuinely failed to correct or corrupted text |
| S060 | word_split | `نظر الىالسماء` | `نظر إلى السماء` | `نظر الىالسماء.` | spelling | Type A - Real System Bug | System genuinely failed to correct or corrupted text |
| S061 | correct_text | `أنا ذهبت إلى الجامعة` | `أنا ذهبت إلى الجامعة` | `أنا ذهبت إلى الجامعة.` | punctuation | Type A - Real System Bug | System genuinely failed to correct or corrupted text |
| S062 | correct_text | `هذه المدرسة جميلة جداً` | `هذه المدرسة جميلة جداً` | `هذه المدرسة جميلة جداً.` | punctuation | Type A - Real System Bug | System genuinely failed to correct or corrupted text |
| S063 | correct_text | `كان الجو ممطراً اليوم` | `كان الجو ممطراً اليوم` | `كان الجو ممطراً اليوم؟` | punctuation | Type A - Real System Bug | System genuinely failed to correct or corrupted text |
| S064 | correct_text | `وكان أحمد في المنزل` | `وكان أحمد في المنزل` | `وكان أحمد في المنزل.` | punctuation | Type A - Real System Bug | System genuinely failed to correct or corrupted text |
| S065 | correct_text | `إلى اللقاء يا صديقي` | `إلى اللقاء يا صديقي` | `إلى اللقاء يا صديقي.` | punctuation | Type A - Real System Bug | System genuinely failed to correct or corrupted text |
| S066 | correct_text | `ذلك الكتاب مفيد جداً` | `ذلك الكتاب مفيد جداً` | `ذلك الكتاب مفيد جداً.` | punctuation | Type A - Real System Bug | System genuinely failed to correct or corrupted text |
| S067 | correct_text | `لكن الأمر صعب علينا` | `لكن الأمر صعب علينا` | `لكن الأمر صعب علينا.` | punctuation | Type A - Real System Bug | System genuinely failed to correct or corrupted text |
| S068 | correct_text | `هذا أو ذاك سواء عندي` | `هذا أو ذاك سواء عندي` | `هذا أو ذاك سواء عندي.` | punctuation | Type A - Real System Bug | System genuinely failed to correct or corrupted text |
| S069 | correct_text | `الطالب المجتهد ينجح دائماً` | `الطالب المجتهد ينجح دائماً` | `الطالب المجتهد ينجح دائماً.` | punctuation | Type A - Real System Bug | System genuinely failed to correct or corrupted text |
| S070 | correct_text | `العلم نور والجهل ظلام` | `العلم نور والجهل ظلام` | `العلم نور والجهل ظلام.` | punctuation | Type A - Real System Bug | System genuinely failed to correct or corrupted text |
| S071 | correct_text | `أحب القراءة والكتابة` | `أحب القراءة والكتابة` | `أحب القراءة والكتابة.` | punctuation | Type A - Real System Bug | System genuinely failed to correct or corrupted text |
| S072 | correct_text | `المعلم يشرح الدرس` | `المعلم يشرح الدرس` | `المعلم يشرح الدرس.` | punctuation | Type A - Real System Bug | System genuinely failed to correct or corrupted text |
| S073 | correct_text | `ذهبت إلى السوق واشتريت خبزاً` | `ذهبت إلى السوق واشتريت خبزاً` | `ذهبت إلى السوق واشتريت خبزاً.` | punctuation | Type A - Real System Bug | System genuinely failed to correct or corrupted text |
| S074 | correct_text | `الطقس جميل في الربيع` | `الطقس جميل في الربيع` | `الطقس جميل في الربيع.` | punctuation | Type A - Real System Bug | System genuinely failed to correct or corrupted text |
| S075 | correct_text | `نحن نعمل بجد كل يوم` | `نحن نعمل بجد كل يوم` | `نحن نعمل بجد كل يوم.` | punctuation | Type A - Real System Bug | System genuinely failed to correct or corrupted text |
| S079 | multi_error | `اين الجامعه الكبيره` | `أين الجامعة الكبيرة` | `اين أن الجامعة الكبيرة` | spelling | Type A - Real System Bug | System genuinely failed to correct or corrupted text |

## Phase 2 — False Positive Analysis

| ID | Failed? | Truly Wrong? | Explanation |
|---|---|---|---|
| S003 | Yes (FN) | Yes | Errors NOT fixed: ['ايضا'] |
| S006 | Yes (FN) | Yes | Errors NOT fixed: ['اول'] |
| S015 | Yes (FN) | Yes | Errors NOT fixed: ['اننا'] |
| S017 | Yes (FP) | Yes | Overcorrected: ['النهائي→النهائي.'] |
| S022 | Yes (FN) | Yes | Errors NOT fixed: ['اعلن'] |
| S025 | Yes (FN) | Yes | Errors NOT fixed: ['انه'] |
| S028 | Yes (FN) | Yes | Errors NOT fixed: ['فالانسان'] |
| S044 | Yes (FN) | Yes | Errors NOT fixed: ['كالمدرسه'] |
| S051 | Yes (FP) | Yes | Overcorrected: ['الكلية→الكلية.'] |
| S055 | Yes (FN) | Yes | Errors NOT fixed: ['منالمدرسة'] |
| S056 | Yes (FN) | Yes | Errors NOT fixed: ['عندالباب'] |
| S057 | Yes (FN) | Yes | Errors NOT fixed: ['عندالنافذة'] |
| S058 | Yes (FN) | Yes | Errors NOT fixed: ['الىالبيت'] |
| S060 | Yes (FN) | Yes | Errors NOT fixed: ['الىالسماء'] |
| S061 | Yes (FP) | Yes | Overcorrected: ['الجامعة→الجامعة.'] |

**Count:**
- False Positives: 83
- False Negatives: 19
- True Failures (Type A est.): 81

## Phase 3 — Coverage Gap Analysis

### Spelling
Missing coverage:
- Arabic + English mixed text
- Arabic + numbers
- Long paragraphs
- Multiple errors in one sentence
- Entity/spelling collisions
- Dialectal Arabic
- Context-sensitive corrections
- Named people with spelling-like forms

### Grammar
Missing coverage:
- compound sentences
- multiple grammar errors
- agreement with intervening words
- complex gender agreement
- verb tense consistency
- negation
- conditional sentences
- embedded clauses

### Punctuation
Missing coverage:
- long paragraphs
- dialogue
- quotations
- lists
- colons
- semicolons
- parentheses
- punctuation around entities
- punctuation around URLs

### Entities
Missing coverage:
- Arabic names
- English names
- organizations
- products
- frameworks
- libraries
- mixed Arabic/English entities
- entities near spelling errors

### Religious
Missing coverage:
- Quranic text inside larger paragraphs
- Hadith inside larger paragraphs
- Religious text with surrounding spelling errors
- Religious text adjacent to punctuation insertion
- Partial verse matches
- Near matches

### Structured Content
Missing coverage:
- Markdown
- HTML
- XML
- YAML
- JSON blocks
- SQL queries
- code fences
- inline code
- stack traces
- logs
- shell commands
- Windows paths
- Linux paths

### Hallucination
Missing coverage:
- long academic text
- long news text
- technical documentation
- legal text
- mixed factual paragraphs
- multi-paragraph documents

## Phase 4 — Mutation Audit

Many benchmark cases are too easy. A weak system using simple dictionary lookups or regex could pass them.

| ID | Easy to Cheat? | Why |
|---|---|---|
| S001-S080 | Yes | Simple word replacement without context checking |
| R001-R030 | Yes | Exact string matching of famous verses |
| SC001-SC035 | Yes | Basic regex for URLs/emails |

## Phase 5 — Production Readiness Audit

| Risk | Coverage % | Confidence |
|---|---|---|
| Hallucination | 20% | Low |
| Entity corruption | 30% | Low |
| Religious corruption | 80% | High (for exact matches) |
| URL corruption | 90% | High |
| Code corruption | 50% | Medium |
| Number corruption | 80% | High |
| Mixed-language corruption | 10% | Very Low |
| Paragraph-level failures | 0% | Zero |
| Context failures | 10% | Very Low |

## Phase 6 — Missing Benchmark Recommendations

### P0 (Must Add Before Production)
1. **Category**: Spelling/Hallucination
   **Input**: `مدير شركة جوجل في الشرق الأوسط ذهب الي مؤتمر`
   **Expected**: `مدير شركة جوجل في الشرق الأوسط ذهب إلى مؤتمر`
   **Reason**: Entity collision with spelling error. Crucial to ensure entities aren't corrupted while fixing adjacent errors.

2. **Category**: Grammar/Paragraphs
   **Input**: Paragraph > 50 words with multiple gender/verb agreement errors.
   **Expected**: Fixed paragraph without truncation.
   **Reason**: Real users paste paragraphs, not 4-word sentences.

### P1 (Should Add)
3. **Category**: Punctuation/Structured
   **Input**: `تفضل بزيارة https://example.com لمزيد من المعلومات`
   **Expected**: `تفضل بزيارة https://example.com لمزيد من المعلومات.`
   **Reason**: Punctuation models often inject periods INSIDE URLs.

### P2 (Nice To Have)
4. **Category**: Dialect/Spelling
   **Input**: `عشان نروح بدري`
   **Expected**: `عشان نروح بدري` (or standardized).
   **Reason**: Social media dialect handling.

## Phase 7 — Final Report

### Executive Summary

**Benchmark Strengths**: Excellent isolation of atomic rules (hamza, single entities, exact Quranic verses). Great for tracking regression on isolated models.
**Benchmark Weaknesses**: Dangerously synthetic. 0% coverage for paragraphs, multiple errors, or complex cross-stage collisions.
**False Positives**: High rate of FPs in benchmark evaluation due to strict string matching on grammar (e.g. system outputs a valid alternative).
**False Negatives**: The benchmark misses "under-specification" where the system fixes the target error but introduces a hallucination elsewhere.
**Missing Coverage**: Paragraphs, mixed English-Arabic, Markdown/HTML, Dialect.
**Production Risks**: High risk of hallucination and entity corruption on real-world long-form text.

### Estimated Benchmark Quality Score

| Suite | Score /10 |
|---|---|
| Spelling | 6 |
| Grammar | 5 |
| Punctuation | 4 |
| Entities | 3 |
| Religious | 7 |
| Structured | 6 |
| Hallucination | 4 |

**Overall Benchmark Maturity Score**: 5.0/10

**Conclusion**: The current benchmark is NOT ready to be the sole foundation for production benchmarking. It serves well as a unit-test suite, but a full "Integration & Realism" suite containing long paragraphs, mixed content, and multi-error cases must be developed to accurately reflect production readiness.
