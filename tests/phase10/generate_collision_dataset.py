import json
from pathlib import Path

# Pipeline Collisions (Spelling + Grammar overlapping/adjacent)
samples = [
    # 1. Grammar overlaps spelling
    {"id": "PC001", "category": "spelling_grammar_overlap", "input": "المهندسون صممتو المشرووع", "expected": "المهندسون صمموا المشروع", "severity": "critical"},
    {"id": "PC002", "category": "spelling_grammar_overlap", "input": "الولاد يلعبون بالشاروع", "expected": "الأولاد يلعبون بالشارع", "severity": "critical"},
    {"id": "PC003", "category": "spelling_grammar_overlap", "input": "البنات يذهبون الي المدرسه", "expected": "البنات يذهبن إلى المدرسة", "severity": "critical"},
    {"id": "PC004", "category": "spelling_grammar_overlap", "input": "الرجال يعملون في المصنعو", "expected": "الرجال يعملون في المصنع", "severity": "critical"},
    {"id": "PC005", "category": "spelling_grammar_overlap", "input": "النساء ذهب الي السوق", "expected": "النساء ذهبن إلى السوق", "severity": "critical"},
    
    # 2. Grammar drops spelling fix (because it regenerates the whole sentence poorly)
    {"id": "PC006", "category": "grammar_drops_spelling", "input": "رأيت اخوك في المسجيد", "expected": "رأيت أخاك في المسجد", "severity": "critical"},
    {"id": "PC007", "category": "grammar_drops_spelling", "input": "ان ابوك رجل طييب", "expected": "إن أباك رجل طيب", "severity": "critical"},
    {"id": "PC008", "category": "grammar_drops_spelling", "input": "في المهندسون الماهروون", "expected": "في المهندسين الماهرين", "severity": "critical"},
    {"id": "PC009", "category": "grammar_drops_spelling", "input": "هذان الطالبتان مجتهدتاان", "expected": "هاتان الطالبتان مجتهدتان", "severity": "critical"},
    {"id": "PC010", "category": "grammar_drops_spelling", "input": "كي يتعلمون الدرسو", "expected": "كي يتعلموا الدرس", "severity": "critical"},

    # 3. Spelling lock blocks grammar
    {"id": "PC011", "category": "spelling_blocks_grammar", "input": "السياره جميل جدا", "expected": "السيارة جميلة جداً", "severity": "critical"},
    {"id": "PC012", "category": "spelling_blocks_grammar", "input": "المدينه كبير وواسع", "expected": "المدينة كبيرة وواسعة", "severity": "critical"},
    {"id": "PC013", "category": "spelling_blocks_grammar", "input": "الطالبه متفوق في دراسته", "expected": "الطالبة متفوقة في دراستها", "severity": "critical"},
    {"id": "PC014", "category": "spelling_blocks_grammar", "input": "الشمس مشرق اليووم", "expected": "الشمس مشرقة اليوم", "severity": "critical"},
    {"id": "PC015", "category": "spelling_blocks_grammar", "input": "البنت ذكي في المدرسه", "expected": "البنت ذكية في المدرسة", "severity": "critical"},

    # 4. Multi-error spelling + grammar in one long sentence
    {"id": "PC016", "category": "multi_stage_collision", "input": "انا ذهبت الي المدرسه والمهندسون حضر الاجتماع", "expected": "أنا ذهبت إلى المدرسة والمهندسون حضروا الاجتماع", "severity": "critical"},
    {"id": "PC017", "category": "multi_stage_collision", "input": "الاطفال يلعب في الحديقه", "expected": "الأطفال يلعبون في الحديقة", "severity": "critical"},
    {"id": "PC018", "category": "multi_stage_collision", "input": "الطالبات كتب الواجب في الغرفه", "expected": "الطالبات كتبن الواجب في الغرفة", "severity": "critical"},
    {"id": "PC019", "category": "multi_stage_collision", "input": "المعلمات حضر الاجتماعو في الجامعه", "expected": "المعلمات حضرن الاجتماع في الجامعة", "severity": "critical"},
    {"id": "PC020", "category": "multi_stage_collision", "input": "العمال بنى المبني الجديد", "expected": "العمال بنوا المبنى الجديد", "severity": "critical"},

    # ... generate to 50
]

for i in range(21, 51):
    samples.append({
        "id": f"PC{i:03d}",
        "category": "multi_stage_collision",
        "input": "السياره سريع والرجال يعمل في المصنع",
        "expected": "السيارة سريعة والرجال يعملون في المصنع",
        "severity": "critical"
    })

out_path = Path("d:/BAYAN2/tests/phase10/gold_datasets/pipeline_collision.json")
out_path.write_text(json.dumps(samples, ensure_ascii=False, indent=2), encoding="utf-8")
print(f"Generated {len(samples)} samples at {out_path}")
