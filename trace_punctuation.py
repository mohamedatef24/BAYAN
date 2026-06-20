"""
BAYAN Punctuation Trace — Diagnose where punctuation marks get lost.

Compares:
  A) Raw PuncAra model output (no pipeline)
  B) After _strip_non_punctuation_changes (Fix P1)
  C) After get_word_diffs (diff algorithm)
  D) After StageLocker check
  E) After validate_punctuation_diff (safety layer)
  F) After overlap resolver + patch cap
"""

import sys, os, re, difflib
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

# Suppress model loading noise
import logging
logging.basicConfig(level=logging.WARNING)

# ─── Test Sentences ─────────────────────────────────────────────
TEST_SENTENCES = [
    {
        "input": "التزم الرياضي بتناول وجباته الصحية وحساب سعراته بدقة رغبة في بناء كتلة عضلية قوية ويا له من التزام حديدي يثير الإعجاب",
        "expected": "التزم الرياضي بتناول وجباته الصحية وحساب سعراته بدقة؛ رغبة في بناء كتلة عضلية قوية، ويا له من التزام حديدي يثير الإعجاب!",
    },
    {
        "input": "كانت الفتيات يلعبن في الحديقة وفجأة سقطت إحداهن وبدأت تبكي بشدة",
        "expected": "كانت الفتيات يلعبن في الحديقة، وفجأة سقطت إحداهن وبدأت تبكي بشدة.",
    },
    {
        "input": "إن الذكاء الاصطناعي يلعب دورا هاما لذلك يجب الاهتمام به",
        "expected": "إن الذكاء الاصطناعي يلعب دورا هاما؛ لذلك يجب الاهتمام به.",
    },
    {
        "input": "هل تعلم أن القاهرة هي عاصمة مصر وتقع على ضفاف نهر النيل",
        "expected": "هل تعلم أن القاهرة هي عاصمة مصر، وتقع على ضفاف نهر النيل؟",
    },
    {
        "input": "قال المعلم للطلاب ادرسوا جيدا فالامتحان قريب",
        "expected": "قال المعلم للطلاب: ادرسوا جيدا، فالامتحان قريب.",
    },
]

def count_punct(text):
    """Count punctuation marks in text."""
    marks = set('.,;:!?،؛؟')
    return sum(1 for c in text if c in marks)

def diff_punct(before, after):
    """Show what punctuation marks were added/removed."""
    marks = set('.,;:!?،؛؟')
    before_marks = [(i, c) for i, c in enumerate(before) if c in marks]
    after_marks = [(i, c) for i, c in enumerate(after) if c in marks]
    return before_marks, after_marks

def main():
    print("=" * 80)
    print("BAYAN PUNCTUATION TRACE — Where do punctuation marks get lost?")
    print("=" * 80)

    # Load model
    print("\n[1/2] Loading PuncAra-v1 model...")
    from nlp.punctuation.punctuation_service import get_punctuation_model, PunctuationChecker
    punc_checker = get_punctuation_model()
    print("  ✓ Model loaded\n")

    # Load pipeline tools
    print("[2/2] Loading pipeline tools...")
    from app import get_word_diffs
    from nlp.punctuation.punctuation_rules import validate_punctuation_diff
    print("  ✓ Tools loaded\n")

    for idx, test in enumerate(TEST_SENTENCES):
        inp = test["input"]
        expected = test["expected"]
        
        print("─" * 80)
        print(f"TEST {idx+1}")
        print(f"  INPUT:    {inp}")
        print(f"  EXPECTED: {expected}")
        print(f"  Expected marks: {count_punct(expected)}")
        print()

        # ─── Stage A: Raw model output (no post-processing) ────────
        raw_output = punc_checker._fix_punctuation(inp)
        print(f"  [A] RAW MODEL:     {raw_output}")
        print(f"      Marks added:   {count_punct(raw_output) - count_punct(inp)}")
        print()

        # ─── Stage B: After _strip_non_punctuation_changes ─────────
        stripped = punc_checker._strip_non_punctuation_changes(inp, raw_output)
        print(f"  [B] STRIP NON-PUNC: {stripped}")
        if stripped != raw_output:
            print(f"      ⚠ Changes stripped! Diff from raw:")
            for w1, w2 in zip(raw_output.split(), stripped.split()):
                if w1 != w2:
                    print(f"        '{w1}' → '{w2}'")
        print(f"      Marks added:   {count_punct(stripped) - count_punct(inp)}")
        print()

        # ─── Stage C: get_word_diffs ───────────────────────────────
        # This is what correct() returns after postprocessing
        from nlp.punctuation.punctuation_rules import arabic_postprocessing
        final_punc = arabic_postprocessing(stripped)
        
        print(f"  [C] FINAL PUNC OUT: {final_punc}")
        print(f"      Marks added:   {count_punct(final_punc) - count_punct(inp)}")
        print()

        # ─── Stage D: Word diffs ──────────────────────────────────
        if final_punc != inp:
            diffs = get_word_diffs(inp, final_punc)
            print(f"  [D] WORD DIFFS ({len(diffs)} found):")
            for d in diffs:
                orig = d.get('original', '')
                corr = d.get('correction', '')
                
                # Check validate_punctuation_diff
                is_valid = validate_punctuation_diff(d)
                
                # Check alpha match (lock bypass)
                orig_alpha = re.sub(r'[^\u0600-\u06FFa-zA-Z]', '', orig)
                corr_alpha = re.sub(r'[^\u0600-\u06FFa-zA-Z]', '', corr)
                alpha_match = orig_alpha == corr_alpha
                
                status_parts = []
                if not is_valid:
                    status_parts.append("❌ SAFETY-REJECTED")
                if not alpha_match:
                    status_parts.append("❌ LOCK-BLOCKED (alpha differs)")
                if is_valid and alpha_match:
                    status_parts.append("✅ WOULD PASS")
                elif is_valid:
                    status_parts.append("✅ valid-punc")
                
                status = " | ".join(status_parts)
                print(f"      [{d['start']}:{d['end']}] '{orig}' → '{corr}'  {status}")
        else:
            print(f"  [D] NO DIFFS — model returned same text as input!")
        
        print()

    # ─── Summary ───────────────────────────────────────────────────
    print("=" * 80)
    print("LOSS POINTS SUMMARY")
    print("=" * 80)
    print("""
Where punctuation marks can be lost:

  [A→B] _strip_non_punctuation_changes():
         If model changes a word's spelling AND adds punctuation,
         the punctuation transfer logic may fail.

  [B→C] arabic_postprocessing():
         Typographic cleanup may remove valid marks.

  [C→D] get_word_diffs():
         Word-level diff may merge/split changes incorrectly.

  [D→E] StageLocker:
         Locked ranges from spelling/grammar block nearby punctuation.
         (Now relaxed: pure-punc changes pass through)

  [D→E] validate_punctuation_diff():
         Safety layer rejects diffs that change Arabic text.

  [E→F] Overlap resolver:
         Grammar/spelling patches take priority over punctuation.

  [E→F] Patch cap:
         Max 3 punctuation patches per response.
""")


if __name__ == "__main__":
    main()
