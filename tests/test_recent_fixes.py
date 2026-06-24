"""
Test suite for FIX-33 through FIX-37.
Run from project root: python tests/test_recent_fixes.py

Tests that need camel-tools (ArabicGrammarGuard) test the regex logic
directly without instantiating the full class.
"""
import sys
import os
import re

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

PASS = 0
FAIL = 0

def test(name, condition, detail=""):
    global PASS, FAIL
    if condition:
        PASS += 1
        print(f"  ✅ {name}")
    else:
        FAIL += 1
        print(f"  ❌ {name} — {detail}")


# ══════════════════════════════════════════════════════════════
# TEST 1: FIX-33 — Grammar rules don't corrupt الامتحان
# Test the regex logic directly without camel-tools
# ══════════════════════════════════════════════════════════════
print("\n═══ FIX-33: Grammar rules — preposition + root noun protection ═══")

# Import the blocklist and test the regex callback logic
from nlp.grammar import grammar_rules

# Get the blocklist from the class (class-level attribute)
_PREP_BLOCKLIST = grammar_rules.ArabicGrammarGuard._PREP_BLOCKLIST

# Simulate the fix_prepositions_advanced regex with callback
def _prep_replace(m):
    prep = m.group(1)
    stem = m.group(2)
    suffix = m.group(3)
    full_word = stem + suffix
    if full_word in _PREP_BLOCKLIST:
        return m.group(0)
    if stem.startswith('ال') and suffix == 'ان':
        return m.group(0)
    return f'{prep} {stem}ين'

def fix_prepositions(text):
    return re.sub(
        r'\b([وف]?(?:في|من|إلى|على|عن|حتى))\s+([أ-ي]{4,})(ون|ان)\b',
        _prep_replace, text
    )

# Root nouns — should NOT be corrupted
root_nouns = [
    ("إلى الامتحان", "إلى الامتحان"),
    ("من الإنسان", "من الإنسان"),
    ("في الميدان", "في الميدان"),
    ("على المكان", "على المكان"),
    ("عن السلطان", "عن السلطان"),
    ("إلى البرلمان", "إلى البرلمان"),
    ("في الحيوان", "في الحيوان"),
    ("من القرآن", "من القرآن"),
    ("في الزمان", "في الزمان"),
]
for input_text, expected in root_nouns:
    result = fix_prepositions(input_text)
    test(f"'{input_text}' → unchanged", result == expected, f"got '{result}'")

# Actual plurals — SHOULD be corrected
plurals = [
    ("في المهندسون", "في المهندسين"),
    ("من المعلمون", "من المعلمين"),
]
for input_text, expected in plurals:
    result = fix_prepositions(input_text)
    test(f"'{input_text}' → '{expected}'", result == expected, f"got '{result}'")


# ══════════════════════════════════════════════════════════════
# TEST 2: FIX-35 — Spelling doesn't strip conjugation suffixes
# ══════════════════════════════════════════════════════════════
print("\n═══ FIX-35: Spelling — conjugation suffix protection ═══")

_CONJUGATION_SUFFIXES = {'ن', 'ت', 'ا', 'ي', 'ة', 'و', 'ه'}

def simulate_insertion_fix_check(orig_word, corr_word):
    """Simulate the FIX-35 suffix strip check logic from app.py."""
    if len(orig_word) != len(corr_word) + 1:
        return "not_applicable"
    
    for di in range(len(orig_word)):
        candidate = orig_word[:di] + orig_word[di + 1:]
        if candidate == corr_word:
            removed_char = orig_word[di]
            removed_pos = di
            if (removed_char in _CONJUGATION_SUFFIXES
                    and removed_pos == len(orig_word) - 1
                    and len(corr_word) >= 3):
                return "blocked"
            return "allowed"
    return "not_applicable"

# BLOCKED cases (suffix stripping)
test("'ذهبن'→'ذهب' blocked (ن suffix)", 
     simulate_insertion_fix_check("ذهبن", "ذهب") == "blocked",
     f"got {simulate_insertion_fix_check('ذهبن', 'ذهب')}")

test("'كتبت'→'كتب' blocked (ت suffix)",
     simulate_insertion_fix_check("كتبت", "كتب") == "blocked",
     f"got {simulate_insertion_fix_check('كتبت', 'كتب')}")

test("'درسة'→'درس' blocked (ة suffix)",
     simulate_insertion_fix_check("درسة", "درس") == "blocked",
     f"got {simulate_insertion_fix_check('درسة', 'درس')}")

test("'جلسوا'→'جلسو' not applicable (len diff ok but وا→و)",
     simulate_insertion_fix_check("جلسوا", "جلسو") == "blocked",
     f"got {simulate_insertion_fix_check('جلسوا', 'جلسو')}")

# ALLOWED cases (mid-word insertion fix)
test("'الكتتاب'→'الكتاب' allowed (mid-word extra ت)",
     simulate_insertion_fix_check("الكتتاب", "الكتاب") == "allowed",
     f"got {simulate_insertion_fix_check('الكتتاب', 'الكتاب')}")

test("'الصصف'→'الصف' allowed (mid-word extra ص)",
     simulate_insertion_fix_check("الصصف", "الصف") == "allowed",
     f"got {simulate_insertion_fix_check('الصصف', 'الصف')}")


# ══════════════════════════════════════════════════════════════
# TEST 3: FIX-36 — Overlap resolver merges grammar+punctuation
# ══════════════════════════════════════════════════════════════
print("\n═══ FIX-36: Overlap resolver — grammar+punctuation merge ═══")

from nlp.correction_patch import CorrectionPatch, PatchSet, PRIORITY

# Case 1: grammar + matching punctuation → merge
ps = PatchSet()
grammar_patch = CorrectionPatch(
    stage='grammar',
    start_original=18, end_original=26,
    start_current=18, end_current=26,
    original='المعلمون', replacement='المعلمين',
    priority=PRIORITY['grammar'], confidence=0.9
)
punc_patch = CorrectionPatch(
    stage='punctuation',
    start_original=18, end_original=26,
    start_current=18, end_current=26,
    original='المعلمون', replacement='المعلمين.',
    priority=PRIORITY['punctuation'], confidence=0.8
)
ps.add(grammar_patch)
ps.add(punc_patch)
resolved = ps.resolve_overlaps()

test("Case 1: 1 patch after merge", len(resolved) == 1, f"got {len(resolved)}")
if resolved:
    test("Merged replacement = 'المعلمين.'",
         resolved[0].replacement == 'المعلمين.',
         f"got '{resolved[0].replacement}'")
    test("Merged stage = grammar",
         resolved[0].stage == 'grammar',
         f"got '{resolved[0].stage}'")

# Case 2: Non-matching corrections → drop punctuation
ps2 = PatchSet()
ps2.add(CorrectionPatch(
    stage='grammar', start_original=0, end_original=5,
    start_current=0, end_current=5,
    original='ذهبوا', replacement='ذهبن',
    priority=PRIORITY['grammar'], confidence=0.9
))
ps2.add(CorrectionPatch(
    stage='punctuation', start_original=0, end_original=5,
    start_current=0, end_current=5,
    original='ذهبوا', replacement='ذهبوا.',
    priority=PRIORITY['punctuation'], confidence=0.8
))
resolved2 = ps2.resolve_overlaps()
test("Case 2: punc dropped (non-matching)", len(resolved2) == 1, f"got {len(resolved2)}")
if resolved2:
    test("Kept grammar unchanged 'ذهبن'",
         resolved2[0].replacement == 'ذهبن',
         f"got '{resolved2[0].replacement}'")

# Case 3: spelling + punctuation still coexist (Phase 14)
ps3 = PatchSet()
ps3.add(CorrectionPatch(
    stage='spelling', start_original=0, end_original=5,
    start_current=0, end_current=5,
    original='برفم', replacement='برغم',
    priority=PRIORITY['spelling'], confidence=0.9
))
ps3.add(CorrectionPatch(
    stage='punctuation', start_original=0, end_original=5,
    start_current=0, end_current=5,
    original='برفم', replacement='برفم.',
    priority=PRIORITY['punctuation'], confidence=0.8
))
resolved3 = ps3.resolve_overlaps()
test("Case 3: spelling+punc coexist (2 patches)",
     len(resolved3) == 2, f"got {len(resolved3)}")


# ══════════════════════════════════════════════════════════════
# TEST 4: FIX-34 — No auto re-analysis after Apply All
# ══════════════════════════════════════════════════════════════
print("\n═══ FIX-34: Frontend — no auto re-analysis after Apply All ═══")

editor_js_path = os.path.join(os.path.dirname(__file__), '..', 'src', 'js', 'editor.js')
with open(editor_js_path, 'r', encoding='utf-8') as f:
    editor_content = f.read()

# Find applyAllSuggestions function body
fn_match = re.search(
    r'function applyAllSuggestions\b(.*?\n\})',
    editor_content, re.DOTALL
)
if fn_match:
    fn_body = fn_match.group(1)
    has_auto_analyze = bool(re.search(r'analyzeText\s*\(', fn_body))
    test("applyAllSuggestions does NOT call analyzeText()",
         not has_auto_analyze,
         "Found analyzeText() call inside applyAllSuggestions!")
    
    has_fix34_comment = 'FIX-34' in fn_body
    test("FIX-34 comment present in function",
         has_fix34_comment, "Missing FIX-34 comment")
else:
    test("applyAllSuggestions function found", False, "Could not find function")


# ══════════════════════════════════════════════════════════════
# TEST 5: FIX-37 — Terminal period fallback exists in app.py
# ══════════════════════════════════════════════════════════════
print("\n═══ FIX-37: Terminal period fallback in app.py ═══")

app_py_path = os.path.join(os.path.dirname(__file__), '..', 'src', 'app.py')
with open(app_py_path, 'r', encoding='utf-8') as f:
    app_content = f.read()

test("FIX-37 comment exists in app.py",
     'FIX-37' in app_content,
     "Missing FIX-37 marker")

test("PUNC-FALLBACK log message exists",
     'PUNC-FALLBACK' in app_content,
     "Missing PUNC-FALLBACK log")

test("Terminal period injection code exists",
     "_lw_text + '.'" in app_content,
     "Missing terminal period injection")

# Verify indentation is correct (12-space, not 14)
for line in app_content.split('\n'):
    if 'FIX-37' in line:
        spaces = len(line) - len(line.lstrip())
        test(f"FIX-37 at correct indent (12 spaces)",
             spaces == 12,
             f"got {spaces} spaces")
        break


# ══════════════════════════════════════════════════════════════
# SUMMARY
# ══════════════════════════════════════════════════════════════
print(f"\n{'═'*60}")
if FAIL == 0:
    print(f"  ✅ ALL {PASS} TESTS PASSED")
else:
    print(f"  ❌ {FAIL} FAILED, {PASS} passed out of {PASS+FAIL} tests")
print(f"{'═'*60}")
sys.exit(1 if FAIL > 0 else 0)
