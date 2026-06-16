# ## 📦 Part 1: Imports & Setup


import re
import torch
import os
from transformers import AutoTokenizer, EncoderDecoderModel
import Levenshtein
import jellyfish  # NEW: For Damerau-Levenshtein (transpositions as 1 edit)

print("✅ All imports successful")
print(f"🔧 PyTorch version: {torch.__version__}")
print(f"🔧 CUDA available: {torch.cuda.is_available()}")
if torch.cuda.is_available():
    print(f"🔧 GPU: {torch.cuda.get_device_name(0)}")


# ═══════════════════════════════════════════════════════════════════════════════
# 🏆 PRODUCTION SPELL CHECKER - OPTIMIZED VERSION (Merged from src/)
# ═══════════════════════════════════════════════════════════════════════════════


# ═══════════════════════════════════════════════════════════════════════════════
# 🏆 PRODUCTION SPELL CHECKER - OPTIMIZED VERSION (Merged from src/)
# ═══════════════════════════════════════════════════════════════════════════════
# IMPROVEMENTS:
# 1. unified_collapse_repeated() - More conservative (3+ for Arabic)
# 2. fix_hamza_conservative() - Only fixes word endings
# 3. remove_hallucinations() - Removes duplicate words and trailing 'و'
# 4. Expanded PREPOSITIONS - 16 prepositions instead of 2
# 5. Better word splitting and joining
# ═══════════════════════════════════════════════════════════════════════════════

from enum import Enum
from typing import List, Tuple, Optional

# ─────────────────────────────────────────────────────────────────────────────
# ERROR TYPE ENUM
# ─────────────────────────────────────────────────────────────────────────────

class ErrorType(Enum):
    """Types of spelling errors"""
    CHAR_REPETITION = "char_repetition"
    WORD_MERGE = "word_merge"
    CHAR_SUBSTITUTION = "char_substitution"
    MIXED = "mixed"
    CLEAN = "clean"

# ═══════════════════════════════════════════════════════════════════════════════
# POST PROCESSOR (OPTIMIZED - Merged from src/)
# ═══════════════════════════════════════════════════════════════════════════════

class AraSpellPostProcessor:
    """Post-processing techniques (OPTIMIZED VERSION)"""
    
    ARABIC_HARAKAT = 'ًٌٍَُِّْ'
    TATWEEL = 'ـ'
    NORMALIZER_MAP = {
        'ﻹ': 'لإ', 'ﻷ': 'لأ', 'ﻵ': 'لآ', 'ﻻ': 'لا', 'ﷲ': 'الله'
    }
    ARABIC_CONSONANTS = set('بتثجحخدذرزسشصضطظعغفقكلمن')
    
    # ═══════════════════════════════════════════════════════════════════════════════
    # BASIC NORMALIZATION
    # ═══════════════════════════════════════════════════════════════════════════════
    
    @staticmethod
    def remove_harakat(text: str) -> str:
        """Remove Arabic diacritics"""
        return re.sub(r'[ً-ْ]', '', text)
    
    @staticmethod
    def remove_tatweel(text: str) -> str:
        """Remove Arabic kashida/tatweel"""
        return text.replace(AraSpellPostProcessor.TATWEEL, '')
    
    @staticmethod
    def normalize_special_chars(text: str) -> str:
        """Normalize special Arabic ligatures"""
        for old, new in AraSpellPostProcessor.NORMALIZER_MAP.items():
            text = text.replace(old, new)
        return text
    
    # ═══════════════════════════════════════════════════════════════════════════════
    # UNIFIED CORE FUNCTIONS (NEW from src/)
    # ═══════════════════════════════════════════════════════════════════════════════
    
    @staticmethod
    def unified_collapse_repeated(text: str) -> str:
        """
        UNIFIED repetition collapse (IMPROVED!)
        - Arabic: 3+ consecutive → 1 (more conservative!)
        - Latin: 2+ consecutive → 1
        """
        # Arabic characters: 3+ → 1
        text = re.sub(r"([\u0600-\u06FF])\1{2,}", r"\1", text)
        
        # Latin characters: 2+ → 1
        text = re.sub(r"([a-zA-Z])\1+", r"\1", text)
        
        return text
    

    
    @staticmethod
    def remove_duplicate_words(text: str) -> str:
        """
        Remove consecutive duplicate words (NEW from src/)
        Examples: كتاب كتاب → كتاب
        """
        words = text.split()
        if len(words) < 2:
            return text
        
        result = [words[0]]
        for i in range(1, len(words)):
            if words[i] != words[i-1]:
                result.append(words[i])
        
        return ' '.join(result)
    

    
    @staticmethod
    def normalize_spaces(text: str) -> str:
        """
        UNIFIED space normalization (NEW from src/)
        """
        # Multiple spaces → single
        text = re.sub(r' +', ' ', text)
        
        # Unicode spaces
        text = text.replace('\u00A0', ' ')  # Non-breaking space
        text = text.replace('\u200B', '')   # Zero-width space
        text = text.replace('\u200C', '')   # Zero-width non-joiner
        text = text.replace('\u200D', '')   # Zero-width joiner
        
        # Trim
        text = text.strip()
        
        # Punctuation spacing
        text = re.sub(r'\s*([،؛؟!.])\s*', r'\1 ', text)
        text = text.strip()
        
        return text
    
    @staticmethod
    def remove_word_repetition_with_wa(text: str) -> str:
        """Remove word و word → word"""
        words = text.split()
        result = []
        i = 0
        while i < len(words):
            if i + 2 < len(words) and words[i] == words[i+2] and words[i+1] == 'و':
                result.append(words[i])
                i += 3
            else:
                result.append(words[i])
                i += 1
        return ' '.join(result)
    
    # ═══════════════════════════════════════════════════════════════════════════════
    # HAMZA HANDLING (NEW from src/)
    # ═══════════════════════════════════════════════════════════════════════════════
    
    @staticmethod
    def fix_hamza_conservative(text: str) -> str:
        """
        CONSERVATIVE Hamza normalization (NEW!)
        Only normalizes at word END, not middle
        
        Examples:
        ✓ "المدرسه" → "المدرسة" (end of word)
        ✓ "سأل" → "سأل" (middle - KEEP IT!)
        """
        words = text.split()
        result = []
        
        for word in words:
            if len(word) >= 3:
                # Fix trailing أ → ا
                if word.endswith('أ'):
                    word = word[:-1] + 'ا'
                
                # Fix trailing إ → ا
                if word.endswith('إ'):
                    word = word[:-1] + 'ا'
            
            result.append(word)
        
        return ' '.join(result)
    
    @staticmethod
    def fix_ha_ta_marbuta(text: str) -> str:
        """
        Fix ه → ة at end of words (pattern-based)
        """
        words = text.split()
        result = []
        
        for word in words:
            if len(word) >= 4 and word.endswith('ه'):
                # Check if second-to-last char is a consonant
                if word[-2] in AraSpellPostProcessor.ARABIC_CONSONANTS:
                    result.append(word[:-1] + 'ة')
                    continue
            result.append(word)
        
        return ' '.join(result)
    
    # ═══════════════════════════════════════════════════════════════════════════════
    # HALLUCINATION REMOVAL (NEW from src/)
    # ═══════════════════════════════════════════════════════════════════════════════
    
    @staticmethod
    def remove_hallucinations(text: str) -> str:
        """
        Remove model hallucinations (NEW from src/):
        - Duplicate words
        - Trailing 'و' artifacts
        """
        words = text.split()
        if not words:
            return text
        
        result = []
        i = 0
        
        def normalize_word(w: str) -> str:
            """Normalize for comparison"""
            w = w.replace('ال', '').replace('ة', 'ه')
            w = re.sub(r'[أإآ]', 'ا', w)
            return w
        
        while i < len(words):
            word = words[i]
            
            # Remove trailing 'و' artifacts (الماضيةو → الماضية)
            if len(word) > 4 and word.endswith('و'):
                prev_char = word[-2]
                if prev_char in 'ةهاأإآء':
                    word = word[:-1]
            
            # Check for duplicate patterns
            if i + 1 < len(words):
                next_word = words[i + 1]
                if normalize_word(word) == normalize_word(next_word):
                    # Keep the one with 'ال' if possible
                    keep = next_word if next_word.startswith('ال') and not word.startswith('ال') else word
                    result.append(keep)
                    i += 2
                    continue
            
            result.append(word)
            i += 1
        
        return ' '.join(result)
    
    @staticmethod
    def remove_hallucinated_prefix(text: str, original: str) -> str:
        """Remove particles (و/في) added by model if not in original"""
        if not original:
            return text
        
        if text.startswith('و ') and not original.startswith('و'):
            rest = text[2:].strip()
            # Verify it matches original
            if AraSpellPostProcessor.normalize_special_chars(rest) == AraSpellPostProcessor.normalize_special_chars(original):
                return rest
        
        return text
    
    # ═══════════════════════════════════════════════════════════════════════════════
    # WORD SPLITTING & MERGING (NEW from src/)
    # ═══════════════════════════════════════════════════════════════════════════════
    
    @staticmethod
    def merge_separated_al(text: str) -> str:
        """Merge 'ال' separated by space: ال + كتاب → الكتاب"""
        return re.sub(r'\bال\s+(\w+)', r'ال\1', text)
    
    @staticmethod
    def join_fragments(text: str) -> str:
        """
        IMPROVED: Join short fragments with better validation (NEW from src/)
        الط + الب → الطالب
        
        FIXED: No longer joins valid separate words like "في من"
        """
        words = text.split()
        if len(words) < 2:
            return text
        
        # Common standalone words that should NOT be merged
        STANDALONE_WORDS = {
            'من', 'في', 'على', 'عن', 'مع', 'إلى', 'الى', 'حتى', 'منذ', 'خلال', 
            'بعد', 'قبل', 'ب', 'ل', 'ك', 'و', 'أو', 'لا', 'ما', 'لم', 'لن',
            'هو', 'هي', 'هم', 'أن', 'إن', 'كل', 'كان', 'قد', 'قال', 'ذلك',
            'هذا', 'هذه', 'تلك', 'التي', 'الذي', 'التى', 'اللذي'
        }
        
        result = []
        i = 0
        
        while i < len(words):
            word = words[i]
            
            if i + 1 < len(words):
                next_word = words[i + 1]
                
                # SAFETY: Don't merge if both are standalone words
                if word in STANDALONE_WORDS and next_word in STANDALONE_WORDS:
                    result.append(word)
                    i += 1
                    continue
                
                # Case 1: Single char fragment (safe to merge)
                if len(next_word) == 1:
                    result.append(word + next_word)
                    i += 2
                    continue
                
                # Case 2: Overlap (last char of word == first char of next)
                if len(word) >= 2 and len(next_word) >= 2 and word[-1] == next_word[0]:
                    if not (word in STANDALONE_WORDS and next_word in STANDALONE_WORDS):
                        result.append(word[:-1] + next_word)
                        i += 2
                        continue
                
                # Case 3: Short fragments (2-4 chars + 1-2 chars)
                if (2 <= len(word) <= 4 and 
                    1 <= len(next_word) <= 2 and
                    3 <= len(word) + len(next_word) <= 7):
                    if not (word in STANDALONE_WORDS and next_word in STANDALONE_WORDS):
                        result.append(word + next_word)
                        i += 2
                        continue
            
            result.append(word)
            i += 1
        
        return ' '.join(result)
    
    # ═══════════════════════════════════════════════════════════════════════════════
    # MAIN PIPELINES
    # ═══════════════════════════════════════════════════════════════════════════════
    
    @staticmethod
    def full_postprocess(text: str, original: str = "") -> str:
        """
        Apply all post-processing steps (OPTIMIZED ORDER!)
        """
        # 1. Remove hallucinated prefixes
        if original:
            text = AraSpellPostProcessor.remove_hallucinated_prefix(text, original)
        
        # 2. Basic normalization
        text = AraSpellPostProcessor.normalize_special_chars(text)
        
        # 3. Remove hallucinations
        text = AraSpellPostProcessor.remove_hallucinations(text)
        
        # 4. Collapse repetitions (UNIFIED!)
        text = AraSpellPostProcessor.unified_collapse_repeated(text)
        
        # 5. Fix Hamza (CONSERVATIVE!)
        text = AraSpellPostProcessor.fix_hamza_conservative(text)
        
        # 6. Fix Ta Marbuta
        text = AraSpellPostProcessor.fix_ha_ta_marbuta(text)
        
        # 7. Remove word repetition with 'و'
        text = AraSpellPostProcessor.remove_word_repetition_with_wa(text)
        
        # 8. Remove duplicate words
        text = AraSpellPostProcessor.remove_duplicate_words(text)
        
        # 9. Final space normalization
        text = AraSpellPostProcessor.normalize_spaces(text)
        
        return text


# ─────────────────────────────────────────────────────────────────────────────
# ERROR CLASSIFIER (Keep from original notebook)
# ─────────────────────────────────────────────────────────────────────────────

class ErrorClassifier:
    """Classify type of spelling error"""
    
    NON_ARABIC_KEYBOARD = set('پگچژکەڕڤڵڎےۀۃھیټډڼڑ')
    
    @staticmethod
    def has_char_substitution(text: str) -> bool:
        return any(c in ErrorClassifier.NON_ARABIC_KEYBOARD for c in text)
    
    @staticmethod
    def has_char_repetition(text: str, threshold: int = 3) -> bool:
        return bool(re.search(r"(.)\1{" + str(threshold - 1) + ",}", text))
    
    @staticmethod
    def has_word_merge(text: str, max_word_len: int = 8) -> bool:
        words = text.split()
        if any(len(w) > max_word_len for w in words):
            return True
        if len(words) == 1 and len(text) > 6:
            return True
        return False
    
    @staticmethod
    def classify(text: str) -> ErrorType:
        """Classify the error type"""
        has_rep = ErrorClassifier.has_char_repetition(text)
        has_merge = ErrorClassifier.has_word_merge(text)
        has_sub = ErrorClassifier.has_char_substitution(text)
        
        error_count = sum([has_rep, has_merge, has_sub])
        
        if error_count >= 2:
            return ErrorType.MIXED
        elif has_sub:
            return ErrorType.CHAR_SUBSTITUTION
        elif has_rep:
            return ErrorType.CHAR_REPETITION
        elif has_merge:
            return ErrorType.WORD_MERGE
        else:
            return ErrorType.CLEAN


# ═══════════════════════════════════════════════════════════════════════════════
# Part 3: Production Spell Checker Class
# This is the best pipeline based on extensive testing of 8+ different approaches
# ═══════════════════════════════════════════════════════════════════════════════

# ═══════════════════════════════════════════════════════════════════════════════
# RULES-BASED CORRECTOR (EXPANDED - Merged from src/)
# ═══════════════════════════════════════════════════════════════════════════════

class RulesBasedCorrector:
    """Rules-based correction (EXPANDED VERSION)"""
    
    # Persian/Urdu → Arabic mapping
    SUBSTITUTION_MAP = {
        'ک': 'ك', 'ی': 'ي', 'ے': 'ي',
        'پ': 'ب', 'چ': 'ج', 'ژ': 'ز',
        'گ': 'ك', 'ڤ': 'ف', 'ڵ': 'ل',
        'ڕ': 'ر', 'ڎ': 'د', 'ڼ': 'ن',
        'ټ': 'ت', 'ډ': 'د', 'ړ': 'ر',
        'ۀ': 'ه', 'ۃ': 'ة', 'ھ': 'ه',
        'ە': 'ه', 'ڑ': 'ر'
    }
    
    # EXPANDED: 16 prepositions instead of 2
    PREPOSITIONS = {
        'من', 'في', 'على', 'عن', 'مع', 'إلى', 'الى',
        'حتى', 'منذ', 'خلال', 'بعد', 'قبل',
        'ب', 'ل', 'ك',
        'لل'
    }
    
    @staticmethod
    def fix_char_substitution(text: str) -> str:
        """Replace Persian/Urdu characters with Arabic"""
        for old, new in RulesBasedCorrector.SUBSTITUTION_MAP.items():
            text = text.replace(old, new)
        return text
    
    @staticmethod
    def fix_char_repetition(text: str) -> str:
        """
        Remove excessive character repetition (IMPROVED!)
        Now: 3+ consecutive → 1 (more conservative)
        """
        # Only collapse 3+ repetitions (not 2+)
        text = re.sub(r'([^\d\s])\1{2,}', r'\1', text)
        return text
    
    @staticmethod
    def advanced_heuristic_repair(text: str) -> str:
        """
        Apply aggressive heuristic repairs to generate a strong baseline candidate.
        1. Unified Char Fixes (Persian/Urdu + Repetition)
        2. Aggressive Word Splitting (Iterative & Anchored)
        """
        # 1. Base Fixes
        text = RulesBasedCorrector.fix_char_substitution(text)
        text = RulesBasedCorrector.fix_char_repetition(text)
        
        # 2. Heuristic Split
        words = text.split()
        processed_words = []
        for word in words:
            processed_words.append(RulesBasedCorrector._recursive_split(word))
        
        return ' '.join(processed_words)

    @staticmethod
    def _recursive_split(word: str) -> str:
        """
        Recursively split merged words (Anchored to Start)
        Avoids splitting 'المنزل' -> 'ال من زل' (middle split)
        """
        if len(word) < 4:
            return word

        # 1. Separable Prepositions (Must be at START)
        # "فيالبيت" -> "في البيت"
        separables = sorted(['من', 'في', 'على', 'عن', 'مع', 'إلى', 'الى', 'حتى', 'منذ', 'خلال', 'بعد', 'قبل'], key=len, reverse=True)
        
        for sep in separables:
            # Check matches: exact match or prefix match
            if word == sep:
                return word
            
            if word.startswith(sep):
                remainder = word[len(sep):]
                # Condition: Remainder must be substantial (usually starts with al- or len > 2)
                if len(remainder) >= 3:
                     # Recursive call on remainder
                     return sep + " " + RulesBasedCorrector._recursive_split(remainder)

        # 2. Common typo merges (e.g. "يا" + Name)
        if word.startswith('يا') and len(word) > 4:
             return 'يا ' + RulesBasedCorrector._recursive_split(word[2:])

        # 3. Attached Particles (Only 'Wa' and 'Fa' are commonly mistakenly merged with non-al words in typos)
        # "وال" -> "و ال" is usually correct in tokenization but "و" is attached in script.
        # We only split if it looks like a HARD merge error.
        
        return word
    



# ═══════════════════════════════════════════════════════════════════════════════
# OUTPUT VALIDATOR (Hallucination Prevention)
# ═══════════════════════════════════════════════════════════════════════════════

class OutputValidator:
    """Validate model outputs to prevent hallucinations"""
    
    @staticmethod
    def calculate_edit_distance(s1: str, s2: str) -> int:
        """Calculate Levenshtein distance"""
        return Levenshtein.distance(s1, s2)
    
    @staticmethod
    def check_character_preservation(original: str, corrected: str) -> Tuple[bool, str]:
        """Check if characters are mostly preserved (Jaccard similarity)"""
        chars_original = set(original)
        chars_corrected = set(corrected)
        
        if not chars_original:
            return True, "valid"
        
        intersection = chars_original & chars_corrected
        union = chars_original | chars_corrected
        
        jaccard = len(intersection) / len(union) if union else 0
        
        if jaccard < 0.35:
            return False, "low_character_similarity"
        
        return True, "valid"

    @staticmethod
    def check_word_count(original: str, corrected: str) -> Tuple[bool, str]:
        """
        Check if word count is reasonable
        Relaxed: Allow splitting merged words (count can double)
        """
        len_orig = len(original.split())
        len_corr = len(corrected.split())
        
        # Allow expanding 1 word to up to 3 (e.g. "فيالمدرسة" -> "في المدرسة")
        if len_orig == 1:
            if len_corr <= 3:
                return True, "valid"
            # If original is very long, allow more splits (e.g. "هذاالولدذهبإلىالمدرسة")
            if len(original) > 12 and len_corr <= 6:
                return True, "valid"
             
        # For sentences, stricter ratio
        ratio = len_corr / len_orig if len_orig > 0 else 0
        if ratio > 2.0 or ratio < 0.5:
             return False, "word_count_mismatch"
             
        return True, "valid"

    def validate(self, original: str, corrected: str, error_type: str) -> Tuple[bool, str]:
        """
        Main validation logic
        """
        # 0. Sanity Check
        if not corrected or not corrected.strip():
            return False, "empty_output"
        
        # ═══════════════════════════════════════════════════════════════════════════
        # SPACE LENIENCY (Phase 1 - Solutions.md الفكرة 3)
        # ═══════════════════════════════════════════════════════════════════════════
        # If the ONLY difference is whitespace → accept if resulting words are valid
        # This fixes split/merge issues like "فيالمدرسة" → "في المدرسة"
        original_no_space = original.replace(' ', '').replace('\u200c', '')  # Also handle ZWNJ
        corrected_no_space = corrected.replace(' ', '').replace('\u200c', '')
        
        if original_no_space == corrected_no_space:
            # Only whitespace changed - accept immediately
            return True, "space_leniency_accept"
            
        # 1. Length Ratio Check
        len_orig = len(original)
        len_corr = len(corrected)
        
        # Allow expansion for word splitting
        if len_corr > len_orig * 2.5:
             return False, "too_long"
             
        # Allow shrinking (but not typically more than 50% unless removing repetition)
        if len_corr < len_orig * 0.5:
             # Exception: if original had excessive repetition
             if error_type == ErrorType.CHAR_REPETITION:
                 pass
             else:
                 return False, "too_short"
                 
        # 2. Check Word Count
        is_valid_count, reason = self.check_word_count(original, corrected)
        if not is_valid_count:
            return False, reason
            
        # 3. Check Character Preservation
        # Critical for avoiding hallucinations
        is_valid_chars, reason = self.check_character_preservation(original, corrected)
        if not is_valid_chars:
             # Exception: If input was garbage/keyboard mash, preservation might be low.
             # But for valid inputs, this prevents changing "كتاب" to "مكتبة" (if no roots match)
             return False, reason
             
        return True, "valid"


# ═══════════════════════════════════════════════════════════════════════════════
# VOCABULARY MANAGER (NEW - Phase 1)
# ═══════════════════════════════════════════════════════════════════════════════

class VocabularyManager:
    """
    Centralized vocabulary management for OOV/IV detection.
    Key for vocabulary-aware acceptance: OOV→IV = accept, IV→OOV = reject.
    """
    
    # Arabic character equivalence for normalization
    HAMZA_VARIANTS = {'أ', 'إ', 'آ', 'ء', 'ؤ', 'ئ', 'ا'}
    ALEF_NORMALIZED = 'ا'
    TA_MARBUTA = 'ة'
    HA = 'ه'
    YA_VARIANTS = {'ي', 'ى'}
    YA_NORMALIZED = 'ي'
    
    def __init__(self, tokenizer):
        self.tokenizer = tokenizer
        
        # Build vocabulary set from tokenizer (exclude subwords and short tokens)
        self.vocab = {
            w for w in tokenizer.get_vocab().keys()
            if w.isalpha() and not w.startswith('##') and len(w) > 1
        }
        
        # Frequency rank: lower index = more common (usually)
        self.vocab_rank = {w: i for w, i in tokenizer.get_vocab().items()}
        
        # Build normalized vocabulary for fuzzy matching
        self.normalized_vocab = {self.normalize_for_comparison(w): w for w in self.vocab}
        
        print(f"📚 VocabularyManager initialized: {len(self.vocab)} words")
    
    @classmethod
    def normalize_for_comparison(cls, word: str) -> str:
        """
        Normalize Arabic word for comparison (hamza, ta marbuta, etc.)
        Used for equivalence checking, not for final output.
        """
        result = []
        for i, char in enumerate(word):
            # Normalize Hamza variants to Alef
            if char in cls.HAMZA_VARIANTS:
                result.append(cls.ALEF_NORMALIZED)
            # Normalize Ta Marbuta to Ha at word end
            elif char == cls.TA_MARBUTA and i == len(word) - 1:
                result.append(cls.HA)
            # Normalize Ya variants
            elif char in cls.YA_VARIANTS:
                result.append(cls.YA_NORMALIZED)
            else:
                result.append(char)
        return ''.join(result)
    
    def is_iv(self, word: str) -> bool:
        """Check if word is In-Vocabulary (known word)."""
        clean = re.sub(r'[^\w]', '', word)
        if not clean:
            return True  # Empty/punctuation only = treat as valid
        
        # Direct check
        if clean in self.vocab:
            return True
        
        # Normalized check (handles hamza/ta marbuta variations)
        normalized = self.normalize_for_comparison(clean)
        if normalized in self.normalized_vocab:
            return True
            
        return False
    
    def is_oov(self, word: str) -> bool:
        """Check if word is Out-Of-Vocabulary (unknown word)."""
        return not self.is_iv(word)
    
    def get_frequency_rank(self, word: str) -> int:
        """Get frequency rank (lower = more common). Returns 999999 for OOV."""
        clean = re.sub(r'[^\w]', '', word)
        return self.vocab_rank.get(clean, 999999)
    
    def all_words_iv(self, text: str) -> bool:
        """Check if ALL words in text are In-Vocabulary."""
        words = text.split()
        return all(self.is_iv(w) for w in words)
    
    def count_oov_words(self, text: str) -> int:
        """Count number of OOV words in text."""
        words = text.split()
        return sum(1 for w in words if self.is_oov(w))
    
    def get_oov_words(self, text: str) -> List[str]:
        """Get list of OOV words in text."""
        words = text.split()
        return [w for w in words if self.is_oov(w)]
    
    def words_are_equivalent(self, word1: str, word2: str) -> bool:
        """
        Check if two words are equivalent (considering Arabic character variations).
        Useful for accepting corrections that only differ in hamza/ta marbuta.
        """
        norm1 = self.normalize_for_comparison(word1)
        norm2 = self.normalize_for_comparison(word2)
        return norm1 == norm2
    
    @staticmethod
    def damerau_levenshtein_distance(s1: str, s2: str) -> int:
        """
        Calculate Damerau-Levenshtein distance (transpositions count as 1 edit).
        This is better for Arabic typos like اقصتاديا→اقتصاديا (swap صت→تص).
        """
        return jellyfish.damerau_levenshtein_distance(s1, s2)
    
    def calculate_similarity(self, original: str, corrected: str) -> float:
        """
        Calculate similarity score using Damerau-Levenshtein distance.
        Returns value between 0 and 1 (1 = identical).
        """
        dist = self.damerau_levenshtein_distance(original, corrected)
        max_len = max(len(original), len(corrected), 1)
        return 1.0 - (dist / max_len)


# ═══════════════════════════════════════════════════════════════════════════════
# WORD ALIGNER (Phase 2 - Solutions.md الفكرة 5)
# ═══════════════════════════════════════════════════════════════════════════════

class WordAligner:
    """
    Aligns input and output words to create hybrid corrections.
    Helps when model fixes one word but breaks another (Raw Wins/Both Wrong cause).
    """
    
    def __init__(self, vocab_manager):
        """Initialize with VocabularyManager for IV checks."""
        self.vocab = vocab_manager
    
    def align_words(self, input_text: str, output_text: str) -> str:
        """
        Create hybrid by selecting best word from each position.
        Uses simple space-based alignment (works for most Arabic cases).
        """
        input_words = input_text.split()
        output_words = output_text.split()
        
        # If lengths differ significantly, alignment is risky -> fallback to output
        if abs(len(input_words) - len(output_words)) > 2:
            input_oov = self.vocab.count_oov_words(input_text)
            output_oov = self.vocab.count_oov_words(output_text)
            return output_text if output_oov < input_oov else input_text
        
        result = []
        
        # Simple position-based alignment (min length)
        min_len = min(len(input_words), len(output_words))
        
        for i in range(min_len):
            in_word = input_words[i]
            out_word = output_words[i]
            
            best_word = self._select_best_word(in_word, out_word)
            result.append(best_word)
            
        # Append remaining words from the longer sequence
        if len(output_words) > min_len:
            result.extend(output_words[min_len:])
        elif len(input_words) > min_len:
            # If input is longer, verify if trailing words are IV
            # If trailing input words are OOV, maybe model was right to remove them?
            # Safest is to keep them if they are IV, else drop.
            for w in input_words[min_len:]:
                 if self.vocab.is_iv(w):
                     result.append(w)
        
        return ' '.join(result)
    
    def _select_best_word(self, input_word: str, output_word: str) -> str:
        """
        Select best word between input and output version.
        
        Logic:
        1. Input OOV + Output IV → Take Output (Model fixed it)
        2. Input IV + Output OOV → Keep Input (Model broke it)
        3. Input IV + Output IV → Keep Input (Conservative) unless Output is much better?
           - For now, strict conservative: if input is valid, keep it.
        4. Both OOV → Take Output (Model likely closer)
        """
        if input_word == output_word:
            return input_word
            
        in_iv = self.vocab.is_iv(input_word)
        out_iv = self.vocab.is_iv(output_word)
        
        # Case 1: Correction worked (OOV -> IV)
        if not in_iv and out_iv:
            return output_word
            
        # Case 2: Correction broke it (IV -> OOV)
        if in_iv and not out_iv:
            return input_word
            
        # Case 3: Both IV (Semantic change or split/merge)
        # Conservative: Keep input to avoid semantic drift (Contextual errors are rare compared to typos)
        if in_iv and out_iv:
            return input_word 
            
        # Case 4: Both OOV
        # Take output, usually closer to target even if still OOV
        return output_word


# ═══════════════════════════════════════════════════════════════════════════════
# SPLIT/MERGE SPECIALIST (Phase 2 - Solutions.md الفكرة 4)
# ═══════════════════════════════════════════════════════════════════════════════

class SplitMergeSpecialist:
    """
    Handles word splitting and merging with vocabulary validation.
    
    Key patterns:
    1. SPLIT: OOV word that can be split into two IV words
       - فيالغالب → في الغالب
       - يقعبجماعة → يقع بجماعة
    2. MERGE: Adjacent OOV fragments that can merge to IV  
       - السوري ة → السورية (ta-marbuta attachment)
       - ال كتاب → الكتاب
    """
    
    # Common Arabic prefixes that can be detached
    SEPARABLE_PREFIXES = [
        # Prepositions (longer first for greedy matching)
        'من', 'في', 'على', 'عن', 'مع', 'إلى', 'الى', 'حتى', 'منذ', 'خلال', 
        'بعد', 'قبل', 'بين', 'حول', 'تحت', 'فوق', 'أمام', 'وراء', 'دون',
        # Particles
        'أن', 'لن', 'لم', 'قد', 'سوف', 'كي', 'إذا', 'لو', 'مثل', 'غير',
        # Call particle
        'يا',
    ]
    
    # Protected short words that shouldn't be split
    PROTECTED_WORDS = {
        'في', 'من', 'على', 'عن', 'مع', 'إلى', 'الى', 'ان', 'أن', 'لا', 'ما', 'هو', 'هي',
        'لم', 'لن', 'قد', 'كل', 'كان', 'ذلك', 'هذا', 'هذه', 'التي', 'الذي', 'بين',
    }
    
    def __init__(self, vocab_manager):
        """Initialize with VocabularyManager for IV checks."""
        self.vocab = vocab_manager
        self.separable_prefixes = sorted(
            self.SEPARABLE_PREFIXES, key=len, reverse=True
        )
    
    def split_word(self, word: str) -> str:
        """
        Try to split an OOV word into IV components.
        
        STRICT Strategy: Only split when BOTH parts are IV.
        This prevents over-splitting like معظم → مع ظم
        """
        # Short words: don't split
        if len(word) < 4:
            return word
        
        # Already IV: no need to split
        if self.vocab.is_iv(word):
            return word
        
        # Protected words: don't split
        if word in self.PROTECTED_WORDS:
            return word
        
        # 1. Try separable prefixes first (higher priority)
        for prefix in self.separable_prefixes:
            if word.startswith(prefix) and len(word) > len(prefix) + 1:
                remainder = word[len(prefix):]
                
                # Only accept if remainder is IV
                if self.vocab.is_iv(remainder):
                    return f"{prefix} {remainder}"
        
        # 2. Try all positions - STRICT: BOTH parts must be IV
        for i in range(2, len(word) - 1):
            left = word[:i]
            right = word[i:]
            
            if self.vocab.is_iv(left) and self.vocab.is_iv(right):
                return f"{left} {right}"
        
        # No valid split found
        return word
    
    def merge_fragments(self, text: str) -> str:
        """
        Try to merge adjacent OOV fragments into IV words.
        
        Key patterns:
        1. Ta-marbuta detachment: السوري ة → السورية (Safe even if السوري is IV)
        2. Al- detachment: ال كتاب → الكتاب
        3. General OOV+OOV merging: Only if both are OOV and result is IV
        """
        words = text.split()
        if len(words) < 2:
            return text
        
        result = []
        i = 0
        
        while i < len(words):
            word = words[i]
            
            # Try to merge with next word
            if i + 1 < len(words):
                next_word = words[i + 1]
                merged = word + next_word
                
                # Pattern 1: Detached suffix (ة، ه، ي، ك...)
                # Allow merging even if 'word' is IV because detached suffix is definitely wrong
                if len(next_word) == 1 and next_word in 'ةهاي':
                    if self.vocab.is_iv(merged):
                        result.append(merged)
                        i += 2
                        continue
                
                # Pattern 2: Detached 'Al-' prefix
                # ال كتاب → الكتاب (Safe to merge)
                if word == 'ال' and len(next_word) >= 2:
                    if self.vocab.is_iv(merged):
                        result.append(merged)
                        i += 2
                        continue
                
                # Pattern 3: General OOV + OOV → IV
                # STRICT: Both must be OOV to avoid merging valid words
                if self.vocab.is_oov(word) and self.vocab.is_oov(next_word):
                    if self.vocab.is_iv(merged):
                        result.append(merged)
                        i += 2
                        continue
                
                # Pattern 4: Short OOV fragment (1-2 chars) merge
                if len(word) <= 2 and self.vocab.is_oov(word):
                    if self.vocab.is_iv(merged):
                        result.append(merged)
                        i += 2
                        continue
            
            result.append(word)
            i += 1
        
        return ' '.join(result)
    
    def process_text(self, text: str) -> str:
        """
        Apply full split/merge processing to text.
        Order: First merge, then split.
        """
        # Step 1: Merge fragments
        text = self.merge_fragments(text)
        
        # Step 2: Split OOV words
        words = text.split()
        processed = []
        
        for word in words:
            if self.vocab.is_oov(word) and len(word) >= 4:
                split_result = self.split_word(word)
                processed.append(split_result)
            else:
                processed.append(word)
        
        return ' '.join(processed)


# ═══════════════════════════════════════════════════════════════════════════════
# EDIT DISTANCE CORRECTOR (NEW!)
# ═══════════════════════════════════════════════════════════════════════════════


class EditDistanceCorrector:
    """
    Generates candidates based on Levenshtein distance.
    Uses BERT Vocabulary to filter for valid words.
    """
    def __init__(self, tokenizer):
        self.tokenizer = tokenizer
        # Build strict vocabulary (ignore subwords starting with ## and punctuation)
        self.vocab = {
            w for w in tokenizer.get_vocab().keys() 
            if w.isalpha() and not w.startswith('##') and len(w) > 1
        }
        # Frequency rank heuristic: lower index = higher frequency (usually)
        self.vocab_rank = {w: i for w, i in tokenizer.get_vocab().items()}

    def edits1(self, word):
        """All edits that are one edit away from `word`."""
        letters    = 'أابتثجحخدذرزسشصضطظعغفقكلمنهويءآىةئؤ' # Arabic chars
        splits     = [(word[:i], word[i:])    for i in range(len(word) + 1)]
        deletes    = [L + R[1:]               for L, R in splits if R]
        transposes = [L + R[1] + R[0] + R[2:] for L, R in splits if len(R)>1]
        replaces   = [L + c + R[1:]           for L, R in splits if R for c in letters]
        inserts    = [L + c + R               for L, R in splits for c in letters]
        return set(deletes + transposes + replaces + inserts)

    def edits2(self, word):
        """All edits that are two edits away from `word`."""
        return (e2 for e1 in self.edits1(word) for e2 in self.edits1(e1))

    def known(self, words):
        """The subset of `words` that appear in the dictionary of known words."""
        return set(w for w in words if w in self.vocab)

    def generate_candidate(self, text: str) -> str:
        """
        Generate a candidate sentence by fixing OOV words using Edit Distance.
        """
        words = text.split()
        corrected_words = []
        
        for word in words:
            # Clean word for checking
            clean_word = re.sub(r'[^\w]', '', word)
            
            # If word is known, keep it
            if clean_word in self.vocab:
                corrected_words.append(word)
                continue
            
            # If OOV, try to find neighbor
            # 1. Edits 1
            candidates = self.known(self.edits1(clean_word))
            
            # 2. Edits 2 (if no Edits 1)
            if not candidates:
                # Optimize: Only check edits2 if word length is reasonable
                if len(clean_word) < 7: 
                    candidates = self.known(self.edits2(clean_word))
            
            if candidates:
                # Pick best candidate: Lowest vocab rank (most frequent)
                best_candidate = min(candidates, key=lambda w: self.vocab_rank.get(w, 999999))
                corrected_words.append(best_candidate)
            else:
                # No correction found, keep original
                corrected_words.append(word)
                
        return ' '.join(corrected_words)

    
    @staticmethod
    def check_word_count(original: str, corrected: str) -> Tuple[bool, str]:
        """Check if word count is reasonable"""
        words_original = original.split()
        words_corrected = corrected.split()
        
        # Allow more flexibility for merged words
        # If original has long words (>7 chars), allow more splits
        has_long_word = any(len(w) > 7 for w in words_original)
        max_expansion = 3 if has_long_word else 1
        
        if len(words_corrected) > len(words_original) + max_expansion:
            return False, "too_many_words"
        
        return True, "valid"
    
    @staticmethod
    def check_token_overlap(original: str, corrected: str) -> Tuple[bool, str]:
        """Check token overlap"""
        tokens_original = set(original.split())
        tokens_corrected = set(corrected.split())
        
        if not tokens_original:
            return True, "valid"
            
        # Skip for short sentences (1-2 words) where edit distance is better
        if len(tokens_original) <= 2:
            return True, "valid"
        
        overlap = len(tokens_original & tokens_corrected) / len(tokens_original)
        
        if overlap < 0.2:
            return False, "low_token_overlap"
        
        return True, "valid"
    
    @staticmethod
    def check_edit_distance_reasonable(original: str, corrected: str) -> Tuple[bool, str]:
        """Check if edit distance is reasonable"""
        distance = OutputValidator.calculate_edit_distance(original, corrected)
        threshold = len(original) * 0.5  # Adaptive threshold
        
        if distance > threshold:
            return False, "excessive_edit_distance"
        
        return True, "valid"
    
    @staticmethod
    def check_length(original: str, corrected: str) -> Tuple[bool, str]:
        """Check if length change is reasonable"""
        max_change = len(original) * 0.25 + 3
        
        if abs(len(corrected) - len(original)) > max_change:
            return False, "excessive_length_change"
        
        return True, "valid"
    
    @staticmethod
    def check_repetition(corrected: str) -> Tuple[bool, str]:
        """Check for suspicious repetitions"""
        # Check for 4+ consecutive identical chars
        if re.search(r'(.)\1{3,}', corrected):
            return False, "excessive_repetition"
        
        return True, "valid"
    
    @staticmethod
    def check_word_quality(corrected: str) -> Tuple[bool, str]:
        """Check for suspicious short words"""
        words = corrected.split()
        
        # Count 1-char words
        single_char_count = sum(1 for w in words if len(w) == 1)
        
        if single_char_count > 2:
            return False, "too_many_short_words"
        
        return True, "valid"
    
    @staticmethod
    def check_word_splitting_quality(corrected: str) -> Tuple[bool, str]:
        """Check if word splitting looks suspicious"""
        words = corrected.split()
        
        # Check for many 2-char words
        two_char_count = sum(1 for w in words if len(w) == 2)
        
        if len(words) > 3 and two_char_count > len(words) * 0.5:
            return False, "suspicious_word_splitting"
        
        return True, "valid"
    
    @staticmethod
    def check_single_chars(corrected: str) -> Tuple[bool, str]:
        """Check for suspicious single characters"""
        words = corrected.split()
        
        for word in words:
            if len(word) == 1 and word not in {'و', 'ب', 'ل', 'ك', 'ف'}:
                return False, "suspicious_short_word"
        
        return True, "valid"
    
    @staticmethod
    def check_word_preservation(original: str, corrected: str) -> Tuple[bool, str]:
        """Check if at least some words are preserved"""
        words_original = set(original.split())
        words_corrected = set(corrected.split())
        
        if len(words_original) <= 1:
            return True, "valid"
            
        # Skip if splitting a single merged word
        if len(words_original) == 1 and len(words_corrected) > 1:
            return True, "valid"
        
        preserved = len(words_original & words_corrected) / len(words_original)
        
        if preserved < 0.1:
            return False, "too_few_preserved_words"
        
        return True, "valid"
    
    @staticmethod
    def validate(original: str, corrected: str, error_type: str = "unknown") -> Tuple[bool, str]:
        """
        Validate model output
        Returns: (is_valid, reason)
        """
        # Run all checks
        checks = [
            OutputValidator.check_character_preservation(original, corrected),
            OutputValidator.check_word_count(original, corrected),
            OutputValidator.check_token_overlap(original, corrected),
            OutputValidator.check_edit_distance_reasonable(original, corrected),
            OutputValidator.check_length(original, corrected),
            OutputValidator.check_repetition(corrected),
            OutputValidator.check_word_quality(corrected),
            OutputValidator.check_word_splitting_quality(corrected),
            OutputValidator.check_single_chars(corrected),
            OutputValidator.check_word_preservation(original, corrected),
        ]
        
        for is_valid, reason in checks:
            if not is_valid:
                return False, reason
        
        return True, "valid"




# ═══════════════════════════════════════════════════════════════════════════════
# CONTEXTUAL CORRECTOR (MLM-based with Batch Scoring)
# ═══════════════════════════════════════════════════════════════════════════════

class ContextualCorrector:
    """MLM-based contextual correction for confusion pairs"""
    
    # Common confusion pairs in Arabic
    CONFUSION_PAIRS = [
        ('ض', 'ظ'), ('ذ', 'ز'), ('ث', 'س'), ('ص', 'س'),
        ('ط', 'ت'), ('ق', 'ك'), ('ه', 'ة'), ('ا', 'ى'),
        ('ت', 'د'), ('د', 'ض'), ('ك', 'ق'), ('غ', 'ق'),
        ('ج', 'ش'), ('س', 'ز'), ('ف', 'ب'), ('و', 'و'), # (و, و) placeholder, maybe (و, ؤ)?
        ('ؤ', 'و'), ('ئ', 'ي'), ('ء', 'أ'), ('إ', 'أ'),
    ]
    
    def __init__(self, model_name: str = 'aubmindlab/bert-base-arabertv02', cache_size: int = 10000):
        """Initialize with BERT MLM model and LRU cache"""
        from transformers import AutoTokenizer, AutoModelForMaskedLM
        from functools import lru_cache
        
        self.tokenizer = AutoTokenizer.from_pretrained(model_name)
        self.model = AutoModelForMaskedLM.from_pretrained(model_name)
        self.device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
        self.model = self.model.to(self.device)
        self.model.eval()
        
        # Build confusion map
        self.confusion_map = self._build_confusion_map()
        
        # Stats
        self.cache_hits = 0
        self.cache_misses = 0
        
        # Create LRU cache for scoring
        self._score_cache = {}
        self.cache_size = cache_size
        
        # Load vocabulary for filtering
        self.vocab = self.tokenizer.get_vocab()
    
    def _build_confusion_map(self):
        """Build bidirectional confusion map"""
        confusion_map = {}
        for char1, char2 in self.CONFUSION_PAIRS:
            if char1 not in confusion_map:
                confusion_map[char1] = []
            if char2 not in confusion_map:
                confusion_map[char2] = []
            confusion_map[char1].append(char2)
            confusion_map[char2].append(char1)
        return confusion_map
    
    def get_confusable_chars(self, char: str) -> List[str]:
        """Get confusable characters for a given char"""
        return self.confusion_map.get(char, [])
    
    def generate_candidates(self, word: str) -> List[str]:
        """Generate candidate corrections for a word"""
        candidates = [word]
        
        # 1. Substitute confusable chars
        for i, char in enumerate(word):
            confusables = self.get_confusable_chars(char)
            for conf_char in confusables:
                candidate = word[:i] + conf_char + word[i+1:]
                if candidate not in candidates:
                    candidates.append(candidate)
        
        # 2. 🆕 Remove repeated characters (deletion)
        # Fixes: مدررسة -> مدرسة, جميلل -> جميل
        for i in range(len(word) - 1):
            if word[i] == word[i+1]:
                # Remove one instance of the repeated char
                candidate = word[:i] + word[i+1:]
                if candidate not in candidates:
                    candidates.append(candidate)
        
        # 3. 🆕 Edit Distance 1 Candidates (Insertions, Substitutions, Transpositions)
        # Using a restricted set of characters to avoid explosion
        COMMON_CHARS = 'ابتثجحخدذرزسشصضطظعغفقكلمنهويأإآءئؤةى'
        
        # Filter candidates by vocabulary to prevent hallucinations and scoring errors
        # Only keep candidates that are valid single tokens in the vocabulary.
        
        # Insertions (missing char)
        for i in range(len(word) + 1):
            for char in COMMON_CHARS:
                candidate = word[:i] + char + word[i:]
                if candidate in self.vocab and candidate not in candidates:
                    candidates.append(candidate)
                    
        # Substitutions (wrong char)
        if len(word) < 7:
            for i in range(len(word)):
                for char in COMMON_CHARS:
                    if char != word[i]:
                        candidate = word[:i] + char + word[i+1:]
                        if candidate in self.vocab and candidate not in candidates:
                            candidates.append(candidate)
                            
        # Deletions (extra char) - General
        for i in range(len(word)):
            candidate = word[:i] + word[i+1:]
            if len(candidate) > 1:
                # For deletions, candidate might be a valid word even if not in vocab?
                # But to be safe and consistent with scoring, let's enforce vocab.
                # (Note: 'جميل' IS in vocab, so it works).
                if candidate in self.vocab and candidate not in candidates:
                    candidates.append(candidate)

        return candidates
    
    def score_with_mlm(self, text: str, position: int, word: str) -> float:
        """Score a word in context using BERT MLM"""
        # Check cache
        cache_key = f"{text}|{position}|{word}"
        if cache_key in self._score_cache:
            self.cache_hits += 1
            return self._score_cache[cache_key]
        
        self.cache_misses += 1
        
        # Create masked text
        words = text.split()
        if position >= len(words):
            return 0.0
        
        masked_words = words.copy()
        masked_words[position] = '[MASK]'
        masked_text = ' '.join(masked_words)
        
        # Tokenize
        inputs = self.tokenizer(masked_text, return_tensors='pt', padding=True, truncation=True)
        inputs = {k: v.to(self.device) for k, v in inputs.items()}
        
        # Get predictions
        with torch.no_grad():
            outputs = self.model(**inputs)
            predictions = outputs.logits
        
        # Find mask position
        mask_token_index = (inputs['input_ids'] == self.tokenizer.mask_token_id).nonzero(as_tuple=True)[1]
        
        if len(mask_token_index) == 0:
            return 0.0
        
        # Get probabilities for the word
        mask_token_logits = predictions[0, mask_token_index[0], :]
        probs = torch.softmax(mask_token_logits, dim=0)
        
        # Get word token id
        word_tokens = self.tokenizer.encode(word, add_special_tokens=False)
        if not word_tokens:
            return 0.0
        
        word_token_id = word_tokens[0]
        score = probs[word_token_id].item()
        
        # Update cache (with size limit)
        if len(self._score_cache) >= self.cache_size:
            # Remove oldest entry (simple FIFO)
            self._score_cache.pop(next(iter(self._score_cache)))
        
        self._score_cache[cache_key] = score
        
        return score
    
    def score_candidates_batch(self, text: str, position: int, candidates: List[str]) -> dict:
        """
        Batch score multiple candidates (NEW - more efficient!)
        Returns: {candidate: score}
        """
        scores = {}
        
        for candidate in candidates:
            scores[candidate] = self.score_with_mlm(text, position, candidate)
        
        return scores
    
    def correct_word_in_context(self, text: str, position: int, threshold: float = 0.05) -> Tuple[str, dict]:
        """
        Correct a word in context
        Returns: (corrected_word, metadata)
        """
        words = text.split()
        if position >= len(words):
            return words[position] if position < len(words) else "", {}
        
        original_word = words[position]
        
        # Generate candidates
        candidates = self.generate_candidates(original_word)
        
        if len(candidates) == 1:
            return original_word, {'candidates': 1, 'corrected': False}
        
        # Score candidates (batch)
        scores = self.score_candidates_batch(text, position, candidates)
        
        # Find best candidate
        best_word = max(scores, key=scores.get)
        best_score = scores[best_word]
        original_score = scores[original_word]
        
        # Check if original is in vocabulary (Single Token)
        # We need to know if original_score is reliable (IV) or just a prefix score (OOV)
        orig_tokens = self.tokenizer.encode(original_word, add_special_tokens=False)
        is_orig_iv = len(orig_tokens) == 1
        
        # Apply correction logic
        min_abs_improvement = 1e-4
        is_improvement = False
        
        if is_orig_iv:
            # Standard relative improvement for IV words
            if best_score > original_score * (1 + threshold) and \
               best_score > original_score + min_abs_improvement:
                is_improvement = True
        else:
            # Original is OOV/Multi-token (likely specific scoring issue with prefixes like 'ال')
            # If best_word is IV (Single Token), effectively compare its score against an absolute threshold
            # because original_score (prefix) is misleadingly high.
            # We use a stricter absolute threshold for this case to avoid over-correction of valid OOVs.
            oov_correction_threshold = 0.001 # 0.1% probability minimum (Lowered to catch 'الطقس')
            
            # Also ensure best_word is IV (which we forced in generation, but good to be sure)
            best_tokens = self.tokenizer.encode(best_word, add_special_tokens=False)
            is_best_iv = len(best_tokens) == 1
            
            if is_best_iv and best_score > oov_correction_threshold:
                # We ignore original_score here as it's likely just P(prefix)
                is_improvement = True
            elif best_score > original_score * (1 + threshold):
                # Fallback to relative check if both are OOV or logic allows
                is_improvement = True

        if best_word != original_word and is_improvement:
            return best_word, {
                'candidates': len(candidates),
                'corrected': True,
                'original_score': original_score,
                'best_score': best_score,
                'improvement': best_score - original_score,
                'is_orig_iv': is_orig_iv
            }
        
        return original_word, {
            'candidates': len(candidates),
            'corrected': False,
            'original_score': original_score
        }
    
    def predict_masked_token(self, text: str, position: int, top_k: int = 5) -> List[Tuple[str, float]]:
        """
        Predict words for a masked position.
        Returns: List of (word, score)
        """
        words = text.split()
        if position >= len(words):
            return []
            
        masked_words = words.copy()
        masked_words[position] = '[MASK]'
        masked_text = ' '.join(masked_words)
        
        inputs = self.tokenizer(masked_text, return_tensors='pt', padding=True, truncation=True).to(self.device)
        
        with torch.no_grad():
            outputs = self.model(**inputs)
            predictions = outputs.logits
            
        mask_token_index = (inputs['input_ids'] == self.tokenizer.mask_token_id).nonzero(as_tuple=True)[1]
        
        if len(mask_token_index) == 0:
            return []
            
        mask_token_logits = predictions[0, mask_token_index[0], :]
        probs = torch.softmax(mask_token_logits, dim=0)
        
        top_k_weights, top_k_indices = torch.topk(probs, top_k, sorted=True)
        
        results = []
        for i in range(top_k):
            token_id = top_k_indices[i].item()
            score = top_k_weights[i].item()
            token = self.tokenizer.decode([token_id]).strip()
            # Filter out subwords (starting with ##) and special tokens
            if not token.startswith("##") and token not in self.tokenizer.all_special_tokens:
                results.append((token, score))
                
        return results

    def refine_sentence_with_mask(self, text: str, threshold: float = 0.001) -> str:
        """
        Refine sentence by masking weak words and predicting replacements.
        Effectively uses BERT as a contextual dictionary.
        """
        words = text.split()
        refined_words = words.copy()
        
        for i, word in enumerate(words):
            # 1. Check confidence
            # We use score_with_mlm. If score is very low, it's a candidate for refinement.
            current_score = self.score_with_mlm(text, i, word)
            
            # If word is confident enough, skip
            # Threshold needs to be tuned. 0.001 implies 0.1% probability.
            if current_score > threshold:
                continue
                
            # 2. Mask and Predict
            predictions = self.predict_masked_token(text, i, top_k=10)
            
            # 3. Filter and Select
            for pred_word, pred_score in predictions:
                if pred_word == word:
                    continue

                # STRICTER CONSTRAINTS
                
                # 1. Length Check
                if abs(len(pred_word) - len(word)) > 2:
                     continue
                     
                # 2. Similarity Check (Edit Distance)
                # We want to fix TYPOS, not semantic hallucinations.
                # So the replacement MUST be structurally similar.
                # Exception: If original word is very short (<3 chars), strict check.
                
                dist = Levenshtein.distance(word, pred_word)
                max_len = max(len(word), len(pred_word))
                similarity = 1.0 - (dist / max_len)
                
                
                # Minimum similarity required: 0.7 (Much stricter to prevent semantic shift)
                # 'بسرعّة' -> 'بسرعة' (High sim)
                # 'الإسلامية' -> 'التطبيقية' (Low sim - rejected)
                if similarity < 0.7:
                    continue
                    
                # 3. Score Improvement
                # If current word is total garbage (score < 1e-5), take any reasonable predicted word.
                # If current word has some confidence, only replace if prediction is MUCH better.
                
                # Check if original word is IV and common
                is_original_common = current_score > 0.001
                
                if is_original_common:
                     # Very strict if original seems okay
                     if pred_score > current_score * 500:
                         refined_words[i] = pred_word
                         break
                else:
                    # Looser if original is weak
                    if pred_score > current_score * 10 or pred_score > 0.1:
                        refined_words[i] = pred_word
                        break # Take the top valid prediction
        
        return ' '.join(refined_words)
    
    def calculate_sentence_score(self, text: str) -> float:
        """
        Calculate a 'fluency' score for the sentence using BERT MLM.
        Returns the average probability of each word being predicted in its context.
        """
        words = text.split()
        if not words:
            return 0.0
            
        total_score = 0.0
        scored_words = 0
        
        for i, word in enumerate(words):
            # We skip scoring very common stopwords to focus on content/structure?
            # No, keep it simple for now: score everything.
            score = self.score_with_mlm(text, i, word)
            total_score += score
            scored_words += 1
            
        if scored_words == 0:
            return 0.0
            
        return total_score / scored_words

    def correct_sentence(self, text: str, threshold: float = 0.01) -> Tuple[str, dict]:
        """
        Correct all words in a sentence
        Returns: (corrected_text, metadata)
        """
        words = text.split()
        corrected_words = []
        corrections = []
        
        for i, word in enumerate(words):
            corrected_word, meta = self.correct_word_in_context(text, i, threshold)
            corrected_words.append(corrected_word)
            
            if meta.get('corrected'):
                corrections.append({
                    'position': i,
                    'original': word,
                    'corrected': corrected_word,
                    'confidence': meta.get('improvement', 0)
                })
        
        corrected_text = ' '.join(corrected_words)
        
        return corrected_text, {
            'corrections': corrections,
            'total_words': len(words)
        }




# ═══════════════════════════════════════════════════════════════════════════════
# MAIN SPELL CHECKER CLASS
# ═══════════════════════════════════════════════════════════════════════════════

class ArabicSpellChecker:
    """Main Arabic Spell Checker class"""
    
    def __init__(self, model, tokenizer, device, use_contextual: bool = True):
        """Initialize spell checker with model and components"""
        self.model = model
        self.tokenizer = tokenizer
        self.device = device
        
        # Initialize components
        self.postprocessor = AraSpellPostProcessor()
        self.classifier = ErrorClassifier()
        self.rules = RulesBasedCorrector()
        self.validator = OutputValidator()
        self.vocab_manager = VocabularyManager(tokenizer)  # Phase 1: Vocabulary Manager
        self.edit_corrector = EditDistanceCorrector(tokenizer)  # Edit Distance candidates
        self.split_merge = SplitMergeSpecialist(self.vocab_manager)  # Phase 2: Split/Merge
        
        # Phase 2: WordAligner for word-level hybrid corrections
        self.word_aligner = WordAligner(self.vocab_manager)
        
        # Initialize contextual corrector (optional)
        self.use_contextual = use_contextual
        if use_contextual:
            try:
                # Initialize ContextualCorrector
                self.contextual = ContextualCorrector()
                print("✅ Contextual correction enabled")
            except Exception as e:
                print(f"⚠️ Contextual correction disabled: {e}")
                self.contextual = None
                self.use_contextual = False
        else:
            self.contextual = None
    def _fix_repeated_end_chars(self, text: str) -> str:
        """
        🆕 Fix repeated characters at word endings
        
        Examples:
            اليومم → اليوم
            جميلل → جميل
            صباحح → صباح
        """
        # Remove repeated chars at word end (keep only one)
        text = re.sub(r'([ا-ي])\1+\b', r'\1', text)
        return text
    
    def _fix_merged_with_errors(self, text: str) -> str:
        """
        🆕 Fix merged words that contain errors
        
        Examples:
            الممدرسة → المدرسة
            الكتابب → الكتاب
            الططالب → الطالب
        """
        # Pattern 1: ال + repeated char + word
        text = re.sub(r'ال([ا-ي])\1+([ا-ي]{2,})', r'ال\2', text)
        
        # Pattern 2: word + repeated char at end
        text = re.sub(r'\b([ا-ي]{3,})([ا-ي])\2+\b', r'\1\2', text)
        
        return text
    

    def _split_merged_words_linguistic(self, text: str) -> str:
        """
        🆕 Split merged words using linguistic patterns
        
        Examples:
            كلصباح → كل صباح
            فيالطريق → في الطريق
            السلامعليكم → السلام عليكم
        """
        # Pattern 1: Prepositions + (article)? + word
        # Added: ك (like in كالكتاب) but careful not to split overlapping words
        text = re.sub(
            r'\b(في|من|إلى|الى|حتى|منذ|خلال|بعد|قبل)(ال)?([ا-ي]{3,})',
            r'\1 \2\3',
            text
        )
        
        # Pattern 2: كل + word
        text = re.sub(r'\b(كل)([ا-ي]{3,})', r'\1 \2', text)
        
        # Pattern 3: Article repetition
        text = re.sub(r'([ا-ي]{3,})(ال)([ا-ي]{3,})', r'\1 \2\3', text)
        
        # Pattern 4: Single-letter prepositions
        text = re.sub(r'\b([بلك])(ال)?([ا-ي]{3,})', r'\1 \2\3', text)
        
        # Pattern 5: Word + عليكم/عليك
        text = re.sub(r'([ا-ي]{4,})(عليكم|عليك|عليه|عليها)', r'\1 \2', text)
        
        # Pattern 6: على/عن in middle of (merged) words
        text = re.sub(r'([ا-ي]{3,})(على|عن)([ا-ي]{3,})', r'\1 \2 \3', text)

        # Pattern 7: بسم الله الرحمن الرحيم (common concatenation)
        text = re.sub(r'\bبسماللهالرحمنالرحيم\b', 'بسم الله الرحمن الرحيم', text)
        text = re.sub(r'\bبسمالله\b', 'بسم الله', text)
        text = re.sub(r'اللهالرحمن', 'الله الرحمن', text)
        text = re.sub(r'الرحمنالرحيم', 'الرحمن الرحيم', text)

        return text
    
    def _split_long_words_heuristic(self, text: str, max_length: int = 15) -> str:
        """
        🆕 Split suspiciously long words using heuristics
        """
        words = text.split()
        result = []
        
        for word in words:
            if len(word) <= max_length:
                result.append(word)
                continue
            
            # Check for embedded article
            if 'ال' in word[2:]:
                parts = word.split('ال', 1)
                if len(parts[0]) >= 2 and len(parts[1]) >= 3:
                    result.extend([parts[0], 'ال' + parts[1]])
                    continue
            
            # Check for common prefixes at start of long word
            if len(word) >= 8:
                split_found = False
                for split_pos in [2, 3]:
                    prefix = word[:split_pos]
                    suffix = word[split_pos:]
                    
                    if prefix in ['في', 'من', 'على', 'عن', 'مع', 'كل', 'ب', 'ل', 'ك']:
                        result.extend([prefix, suffix])
                        split_found = True
                        break
                
                if not split_found:
                    result.append(word)
            else:
                result.append(word)
        
        return ' '.join(result)
    
    def _normalize_tanween_patterns(self, text: str) -> str:
        """
        🆕 Normalize tanween patterns
        
        Examples:
            جدأ → جداً
            كثيرأ → كثيراً
        """
        # أ at word end → اً
        text = re.sub(r'([ا-ي]{2,})أ\b', r'\1اً', text)
        
        # Remove standalone أ
        text = re.sub(r'\s+أ\s+', ' ', text)
        
        # Fix accidental splits (e.g. ب + space + word)
        text = re.sub(r'\b([بلك])\s+([ا-ي])', r'\1\2', text)
        
        return text
    

    

    
    def preprocess(self, text: str) -> str:
        """Preprocessing pipeline (مع التحسينات المدمجة)"""
        # Basic normalization
        text = self.postprocessor.remove_harakat(text)
        text = self.postprocessor.remove_tatweel(text)
        text = self.postprocessor.normalize_special_chars(text)
        
        # 🆕 التحسينات المدمجة (IMPROVEMENTS INTEGRATED!)
        # Fix repeated chars and merged words with errors FIRST
        text = self._fix_repeated_end_chars(text)
        text = self._fix_merged_with_errors(text)
        
        # Then split merged words
        text = self._split_merged_words_linguistic(text)
        text = self._split_long_words_heuristic(text)
        text = self._normalize_tanween_patterns(text)
        
        # Merge separated 'ال'
        text = self.postprocessor.merge_separated_al(text)
        
        # Collapse repetitions
        text = self.postprocessor.unified_collapse_repeated(text)
        
        # Rules-based fixes
        text = self.rules.fix_char_substitution(text)
        text = self.rules.fix_char_repetition(text)
        
        # Normalize spaces
        text = self.postprocessor.normalize_spaces(text)
        
        return text
    
    def _fix_word_split(self, text: str) -> str:
        """Fix over-split words by joining fragments"""
        return self.postprocessor.join_fragments(text)
    
    def postprocess(self, text: str, original: str = "") -> str:
        """Postprocessing pipeline"""
        return self.postprocessor.full_postprocess(text, original)
    
    def model_inference(self, text: str, num_return_sequences: int = 5) -> List[str]:
        """Run seq2seq model inference and return top candidates"""
        # Tokenize
        inputs = self.tokenizer(text, return_tensors='pt', padding=True, truncation=True, max_length=128)
        inputs = {k: v.to(self.device) for k, v in inputs.items()}
        
        # Generate (encoder-decoder needs decoder_start_token_id / bos_token_id)
        decoder_start = getattr(
            self.model.config, 'decoder_start_token_id', None
        ) or getattr(self.model.config, 'bos_token_id', None) or self.tokenizer.cls_token_id
        pad_id = getattr(self.model.config, 'pad_token_id', None) or self.tokenizer.pad_token_id
        with torch.no_grad():
            outputs = self.model.generate(
                **inputs,
                max_length=128,
                num_beams=5,
                num_return_sequences=num_return_sequences,
                early_stopping=True,
                decoder_start_token_id=decoder_start,
                pad_token_id=pad_id,
            )
        
        # Decode
        candidates = self.tokenizer.batch_decode(outputs, skip_special_tokens=True)
        
        return candidates
    
    def correct(self, text: str) -> str:
        """
        Main correction pipeline (RERANKING APPROACH)
        
        Steps:
        1. Preprocess
        2. Generate Candidates (Model Beams + Baseline)
        3. Rerank Candidates (Validator + Fluency)
        4. Select Best
        5. Postprocess
        """
        if not text or not text.strip():
            return text
        
        original = text
        
        # 1. Preprocess
        # This provides a strong baseline candidate
        preprocessed_text = self.preprocess(text)
        
        # 2. Classify error type
        error_type = self.classifier.classify(preprocessed_text)
        
        # 3. Generate Candidates
        candidates = []
        
        # A. Baseline (Preprocessed)
        candidates.append(preprocessed_text)
        
        # B. Smart Rules Candidate (Aggressive Heuristic)
        # This helps when the model fails but the rule-based fix is obvious
        rules_candidate = self.rules.advanced_heuristic_repair(text)
        candidates.append(rules_candidate)
        
        # B2. Edit Distance Candidate (NEW!)
        # Tries to fix typos using simple edit distance (Norvig)
        edit_candidate = self.edit_corrector.generate_candidate(text)
        if edit_candidate != text and edit_candidate != rules_candidate:
            candidates.append(edit_candidate)
        
        # B3. Split/Merge Candidate (Phase 2)
        # NOTE: Disabled - caused regression (Hybrid Wins 144→134)
        # split_merge_candidate = self.split_merge.process_text(preprocessed_text)
        # if split_merge_candidate != preprocessed_text and split_merge_candidate not in candidates:
        #     candidates.append(split_merge_candidate)
        
        # C. Model Beams
        try:
            model_candidates = self.model_inference(preprocessed_text, num_return_sequences=5)
            candidates.extend(model_candidates)
            
            # D. Word-Aligned Hybrid Candidate (Phase 2 - Solution 5)
            # Creates a hybrid by selecting best word from each position
            # (OOV input + IV output → take output, IV input + OOV output → keep input)
            if model_candidates:
                hybrid_candidate = self.word_aligner.align_words(preprocessed_text, model_candidates[0])
                if hybrid_candidate not in candidates:
                    candidates.append(hybrid_candidate)
        except Exception as e:
            print(f"⚠️ Model inference failed: {e}")
        
        # Remove duplicates while preserving order
        unique_candidates = []
        seen = set()
        for c in candidates:
            if c not in seen:
                unique_candidates.append(c)
                seen.add(c)
        candidates = unique_candidates
        
        # 4. Rerank Candidates
        best_candidate = preprocessed_text
        best_score = -1.0
        
        # Debug info
        candidate_scores = []
        
        for cand in candidates:
            # A. Validation Score (Hard Penalty)
            # Check validity against strict original
            is_valid, reason = self.validator.validate(original, cand, error_type.value)
            
            # Additional check: If candidate is suspiciously shorter than original (and not just harakat removal)
            if len(cand) < len(original) * 0.5:
                is_valid = False
                reason = "too_short"

            # ═══════════════════════════════════════════════════════════════════════════
            # NEW: VOCABULARY-AWARE ACCEPTANCE (Phase 1 - Key Fix for Raw Wins)
            # ═══════════════════════════════════════════════════════════════════════════
            # Logic: OOV→IV = ACCEPT (boost), IV→OOV = REJECT (penalize)
            # This prevents over-conservative validation from rejecting correct corrections
            
            input_oov_count = self.vocab_manager.count_oov_words(original)
            cand_oov_count = self.vocab_manager.count_oov_words(cand)
            
            vocab_boost = 1.0
            
            # Case 1: OOV→IV (Correction fixed unknown words) → Accept more readily
            if input_oov_count > 0 and cand_oov_count < input_oov_count:
                # Significant boost for reducing OOV words
                oov_reduction = input_oov_count - cand_oov_count
                vocab_boost = 1.0 + (oov_reduction * 0.3)  # +30% per OOV fixed
                
                # If ALL words are now IV, accept even with higher edit distance
                if cand_oov_count == 0 and self.vocab_manager.all_words_iv(cand):
                    # Override validation rejection if OOV→IV
                    if not is_valid and reason not in ["empty_output"]:
                        is_valid = True
                        reason = "vocab_aware_accept"
            
            # Case 2: IV→OOV (Correction introduced unknown words) → Penalize
            elif cand_oov_count > input_oov_count:
                # Penalize for introducing new OOV words
                vocab_boost = 0.5  # 50% penalty
            
            # Case 3: All IV to begin with → Standard validation
            elif input_oov_count == 0 and cand_oov_count == 0:
                # Both are valid vocab, prefer minimal edits
                vocab_boost = 1.0
            
            # ═══════════════════════════════════════════════════════════════════════════

            
            # Penalty factor
            # Valid: 1.0
            # Invalid: 0.01 (Heavy penalty, essentially disqualified unless all are invalid)
            validity_factor = 1.0 if is_valid else 0.001
            
            # B. Fluency Score (BERT MLM)
            fluency_score = 0.0
            if self.use_contextual and self.contextual:
                try:
                    fluency_score = self.contextual.calculate_sentence_score(cand)
                except Exception as e:
                    print(f"⚠️ Scoring failed: {e}")
                    fluency_score = 0.5 # Default fallback
            else:
                fluency_score = 1.0 
            
            # C. Similarity Score (Damerau-Levenshtein Distance - Phase 1 improvement)
            # Penalize unnecessary changes. Using DL distance: transpositions = 1 edit (not 2)
            # This helps cases like اقصتاديا→اقتصاديا (swap صت→تص counts as 1)
            dist = VocabularyManager.damerau_levenshtein_distance(preprocessed_text, cand)
            # Using preprocessed_text as anchor because it has basic normalization.
            # Comparison with 'original' might penalize fixing harakat/spelling.
            
            max_len = max(len(preprocessed_text), len(cand), 1)
            similarity = 1.0 - (dist / max_len)
            
            # Boost matches
            if cand == preprocessed_text:
                similarity = 1.0
            
            # NEW: HIGH CONFIDENCE GATING (Phase 1/3 - Solution)
            # If model is extremely confident (high fluency) and words are valid, relax validation
            # This allows correcting severe corruptions that fail strict edit distance
            if fluency_score > 0.85 and cand_oov_count == 0:
                 if not is_valid and reason in ["too_short", "low_character_similarity", "word_count_mismatch"]:
                      # Check if it makes sense length-wise (don't allow completely empty or massive hallucinations)
                      if len(cand) >= len(original) * 0.4:
                          is_valid = True
                          reason = "high_confidence_override"
                          vocab_boost *= 1.2  # Bonus for high confidence
                          validity_factor = 1.0  # Reset validity factor
            
            # Final Score
            # Fluency is roughly [0, 1] (prob). Similarity [0, 1].
            # We want to balance staying close to original vs being fluent.
            # If fluency is very low, it's garbage.
            # If similarity is very low, it's hallucination.
            
            # Weighting:
            # We value Similarity highly to be conservative.
            # But we need Fluency to break ties or fix errors.
            
            # New Formula:
            # Score = (Fluency^0.3) * (Similarity^2.0) * Validity * VocabBoost
            # Using exponent to control trade-off. 
            # High sim power -> prefers closer matches.
            # Low fluency power -> flattens probability differences (since probs are small).
            # VocabBoost: rewards OOV→IV, penalizes IV→OOV
            
            final_score = (fluency_score ** 0.3) * (similarity ** 3.0) * validity_factor * vocab_boost
            
            candidate_scores.append({
                'text': cand,
                'is_valid': is_valid,
                'reason': reason,
                'fluency': fluency_score,
                'similarity': similarity,
                'vocab_boost': vocab_boost,  # NEW: Track vocab boost
                'input_oov': input_oov_count,
                'cand_oov': cand_oov_count,
                'final_score': final_score
            })
            
            if final_score > best_score:
                best_score = final_score
                best_candidate = cand
        
        # 5. Postprocess Winner
        result = self.postprocess(best_candidate, original)
        
        # 6. Contextual fine-tuning (BERT Masked Refinement)
        # Note: Applying to full sentence (OOV-only mode caused regression due to lack of context)
        if self.use_contextual and self.contextual:
             if len(result) > 3:
                 result = self.contextual.refine_sentence_with_mask(result)
        
        # 7. Phase 2: Safe Split/Merge Post-processing
        # Only apply merge_fragments (safe: only merges when result is IV)
        # This fixes ta-marbuta detachment like السوري ة → السورية
        result = self.split_merge.merge_fragments(result)
        
        return result


print("✅ All classes defined successfully!")
print("   - ErrorType")
print("   - AraSpellPostProcessor")
print("   - ErrorClassifier")
print("   - RulesBasedCorrector")
print("   - OutputValidator")
print("   - ContextualCorrector")
print("   - ArabicSpellChecker")


print("✅ AraSpell classes loaded successfully")

