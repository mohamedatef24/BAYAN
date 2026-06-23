"""
Phase 5 — BUG-016/027 Text Duplication Investigation

Reproduce exact case: ان الطالبات ذهبو الى الجامعه
Log every patch produced by spelling and grammar with full ORIGINAL coordinates.
Determine: overlapping coords (PatchSet bug) vs non-overlapping (coord computation bug).
Also check: does الى get silently dropped?
"""
import sys, os, json, time, requests

API_BASE = "https://bayan10-bayan-api.hf.space"
TIMEOUT = 60

def api_call(endpoint, text):
    url = f"{API_BASE}{endpoint}"
    try:
        t0 = time.time()
        resp = requests.post(url, json={"text": text}, timeout=TIMEOUT)
        elapsed = int((time.time() - t0) * 1000)
        if resp.status_code == 200:
            data = resp.json()
            data['_elapsed_ms'] = elapsed
            return data
        return {"error": f"HTTP {resp.status_code}", "_elapsed_ms": elapsed}
    except Exception as e:
        return {"error": f"{type(e).__name__}: {e}"}


def investigate_bug_016():
    """Full coordinate investigation for BUG-016."""
    print("=" * 70)
    print("PHASE 5 — BUG-016/027 Text Duplication Investigation")
    print("=" * 70)

    test_input = "ان الطالبات ذهبو الى الجامعه"
    print(f"\nInput: '{test_input}'")
    print(f"Words: {test_input.split()}")
    for i, w in enumerate(test_input.split()):
        # Compute char offsets
        start = test_input.index(w) if i == 0 else test_input.index(w, sum(len(x) + 1 for x in test_input.split()[:i]))
        end = start + len(w)
        print(f"  Word {i}: '{w}' chars [{start}:{end}]")

    # Track A: Raw model outputs
    print("\n--- Track A: Raw Spelling ---")
    a_spell = api_call("/api/spelling", test_input)
    a_spell_out = a_spell.get("corrected_text", test_input)
    print(f"  Input:  '{test_input}'")
    print(f"  Output: '{a_spell_out}'")
    print(f"  Changed: {a_spell_out != test_input}")

    # Character-level diff
    if a_spell_out != test_input:
        print("\n  Character-level changes (spelling):")
        from difflib import SequenceMatcher
        s = SequenceMatcher(None, test_input.split(), a_spell_out.split())
        for tag, i1, i2, j1, j2 in s.get_opcodes():
            if tag != 'equal':
                orig_words = test_input.split()[i1:i2]
                corr_words = a_spell_out.split()[j1:j2]
                print(f"    {tag}: [{i1}:{i2}] {orig_words} → [{j1}:{j2}] {corr_words}")

    print("\n--- Track A: Raw Grammar ---")
    a_gram = api_call("/api/grammar", test_input)
    a_gram_out = a_gram.get("corrected_text", test_input)
    print(f"  Input:  '{test_input}'")
    print(f"  Output: '{a_gram_out}'")
    print(f"  Changed: {a_gram_out != test_input}")

    if a_gram_out != test_input:
        print("\n  Character-level changes (grammar):")
        from difflib import SequenceMatcher
        s = SequenceMatcher(None, test_input.split(), a_gram_out.split())
        for tag, i1, i2, j1, j2 in s.get_opcodes():
            if tag != 'equal':
                orig_words = test_input.split()[i1:i2]
                corr_words = a_gram_out.split()[j1:j2]
                print(f"    {tag}: [{i1}:{i2}] {orig_words} → [{j1}:{j2}] {corr_words}")

    # Track B: Full pipeline
    print("\n--- Track B: Full Pipeline ---")
    b = api_call("/api/analyze", test_input)
    b_corrected = b.get("corrected", test_input)
    b_suggestions = b.get("suggestions", [])
    print(f"  Input:      '{test_input}'")
    print(f"  Corrected:  '{b_corrected}'")
    print(f"  Suggestions: {len(b_suggestions)}")

    for s in b_suggestions:
        print(f"\n    Suggestion [{s.get('start')}:{s.get('end')}]:")
        print(f"      Type: {s.get('type')}")
        print(f"      Original: '{s.get('original', '')}'")
        print(f"      Correction: '{s.get('correction', '')}'")
        if 'confidence' in s:
            print(f"      Confidence: {s.get('confidence')}")

    # Check for duplicates
    print("\n--- Duplicate / Drop Analysis ---")
    output_words = b_corrected.split()
    input_words = test_input.split()
    print(f"  Input words:  {input_words}")
    print(f"  Output words: {output_words}")

    # Check for duplicated words
    for i, w in enumerate(output_words):
        if i > 0 and w == output_words[i-1]:
            print(f"  ⚠ DUPLICATE: '{w}' at positions {i-1} and {i}")

    # Check for dropped words (الى should appear as الى or إلى)
    for w in input_words:
        # Check if word or a known correction of it appears in output
        found = w in b_corrected
        if not found:
            # Check common corrections
            corrections = {
                'ان': ['أن', 'إن', 'ان'],
                'الى': ['إلى', 'الى'],
                'الجامعه': ['الجامعة', 'الجامعه'],
                'ذهبو': ['ذهبوا', 'ذهبن', 'ذهبو'],
                'الطالبات': ['الطالبات'],
            }
            alts = corrections.get(w, [w])
            found = any(a in b_corrected for a in alts)
        if not found:
            print(f"  ⚠ DROPPED: '{w}' not found in corrected output!")
        else:
            print(f"  ✓ '{w}' present (or corrected variant)")

    # Overlap analysis between suggestions
    print("\n--- Overlap Analysis ---")
    for i, s1 in enumerate(b_suggestions):
        for j, s2 in enumerate(b_suggestions):
            if j <= i:
                continue
            s1_start, s1_end = s1.get('start', 0), s1.get('end', 0)
            s2_start, s2_end = s2.get('start', 0), s2.get('end', 0)
            if s1_start < s2_end and s2_start < s1_end:
                print(f"  ⚠ OVERLAP: suggestion {i} [{s1_start}:{s1_end}] and suggestion {j} [{s2_start}:{s2_end}]")
                print(f"    S{i}: '{s1.get('original','')}' → '{s1.get('correction','')}' ({s1.get('type')})")
                print(f"    S{j}: '{s2.get('original','')}' → '{s2.get('correction','')}' ({s2.get('type')})")
    if not any(
        s1.get('start', 0) < s2.get('end', 0) and s2.get('start', 0) < s1.get('end', 0)
        for i, s1 in enumerate(b_suggestions) for j, s2 in enumerate(b_suggestions) if j > i
    ):
        print("  ✓ No overlapping suggestions found")

    return {
        "input": test_input,
        "raw_spelling": a_spell_out,
        "raw_grammar": a_gram_out,
        "pipeline_corrected": b_corrected,
        "suggestions": b_suggestions,
    }


if __name__ == "__main__":
    result = investigate_bug_016()
    output_path = os.path.join(os.path.dirname(__file__), 'phase5_results.json')
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    print(f"\nResults saved to {output_path}")
