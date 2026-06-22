# Grammar FN Root Cause Analysis

**Total Grammar FN: 17**

## By Category

| Category | Count | % |
|---|---|---|
| PATCH_FAILURE | 13 | 76% |
| FILTER_FAILURE | 2 | 12% |
| MODEL_FAILURE | 2 | 12% |

## Detail

### G001 — PATCH_FAILURE
- **Input**: `البنات ذهب إلى المدرسة`
- **Expected**: `ذهبن/ذهبت`
- **Pipeline output**: `البنات ذهبن إلى المدرسة`
- **Evidence**: Grammar patch accepted but final output doesn't match expected

### G002 — PATCH_FAILURE
- **Input**: `الطلاب يذهب إلى الجامعة`
- **Expected**: `يذهبون`
- **Pipeline output**: `الطلاب يذهبون إلى الجامعة`
- **Evidence**: Grammar patch accepted but final output doesn't match expected

### G003 — PATCH_FAILURE
- **Input**: `المهندسون حضر الاجتماع`
- **Expected**: `حضروا`
- **Pipeline output**: `المهندسون حضرون الاجتماع`
- **Evidence**: Grammar patch accepted but final output doesn't match expected

### G004 — PATCH_FAILURE
- **Input**: `الرجال يعمل في المصنع`
- **Expected**: `يعملون`
- **Pipeline output**: `الرجال يعملون في المصنع`
- **Evidence**: Grammar patch accepted but final output doesn't match expected

### G005 — PATCH_FAILURE
- **Input**: `النساء ذهب إلى السوق`
- **Expected**: `ذهبن`
- **Pipeline output**: `النساء ذهبن إلى السوق`
- **Evidence**: Grammar patch accepted but final output doesn't match expected

### G006 — FILTER_FAILURE
- **Input**: `الأولاد لعب في الحديقة`
- **Expected**: `لعبوا`
- **Pipeline output**: `الأولاد لعب في الحديقة`
- **Evidence**: Rejected by: IVtoOOV
- **Filters**: IVtoOOV

### G007 — PATCH_FAILURE
- **Input**: `المعلمات حضر الاجتماع`
- **Expected**: `حضرن`
- **Pipeline output**: `المعلمات حضرن الاجتماع`
- **Evidence**: Grammar patch accepted but final output doesn't match expected

### G008 — PATCH_FAILURE
- **Input**: `الأطباء يعالج المرضى`
- **Expected**: `يعالجون`
- **Pipeline output**: `الأطباء يعالجون المرضى`
- **Evidence**: Grammar patch accepted but final output doesn't match expected

### G009 — MODEL_FAILURE
- **Input**: `العمال بنى المبنى`
- **Expected**: `بنوا`
- **Pipeline output**: `العمال بنى المبنى`
- **Evidence**: Grammar model returned input unchanged

### G010 — PATCH_FAILURE
- **Input**: `الطالبات كتب الواجب`
- **Expected**: `كتبن`
- **Pipeline output**: `الطالبات كتبن الواجب`
- **Evidence**: Grammar patch accepted but final output doesn't match expected

### G011 — PATCH_FAILURE
- **Input**: `السيارة جميل جداً`
- **Expected**: `جميلة`
- **Pipeline output**: `السيارة جميلة جداً`
- **Evidence**: Grammar patch accepted but final output doesn't match expected

### G012 — PATCH_FAILURE
- **Input**: `البنت ذكي في المدرسة`
- **Expected**: `ذكية`
- **Pipeline output**: `البنت ذكية في المدرسة`
- **Evidence**: Grammar patch accepted but final output doesn't match expected

### G013 — PATCH_FAILURE
- **Input**: `الطالبة متفوق في دراسته`
- **Expected**: `متفوقة/دراستها`
- **Pipeline output**: `الطالب متفوق في دراسته`
- **Evidence**: Grammar patch accepted but final output doesn't match expected

### G014 — PATCH_FAILURE
- **Input**: `المدينة كبير وواسع`
- **Expected**: `كبيرة وواسعة`
- **Pipeline output**: `المدينة كبيرة وواسعة`
- **Evidence**: Grammar patch accepted but final output doesn't match expected

### G015 — PATCH_FAILURE
- **Input**: `الشمس مشرق اليوم`
- **Expected**: `مشرقة`
- **Pipeline output**: `الشمس مشرقة اليوم`
- **Evidence**: Grammar patch accepted but final output doesn't match expected

### G022 — MODEL_FAILURE
- **Input**: `رأيت أخوك في المسجد`
- **Expected**: `أخاك`
- **Pipeline output**: `رأيت أخوك في المسجد`
- **Evidence**: Grammar model returned input unchanged

### G028 — FILTER_FAILURE
- **Input**: `لم يفعلون الواجب بعد`
- **Expected**: `يفعلوا`
- **Pipeline output**: `لم يفعلون الواجب بعد`
- **Evidence**: Rejected by: IVtoOOV
- **Filters**: IVtoOOV

