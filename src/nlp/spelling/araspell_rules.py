# AraSpell — Arabic Spell Checker Pipeline (Rules & Classes)
# Extracted from AraSpell.py — NO global model loading, NO Gradio dependencies.
# All classes are imported by araspell_service.py.

import re
import math
import logging
import torch
from collections import Counter
from enum import Enum
from typing import List, Tuple, Optional

import Levenshtein
import jellyfish

logger = logging.getLogger(__name__)

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
# KEYBOARD PROXIMITY (Phase 12 — from original AraSpell.py L475-520)
# ═══════════════════════════════════════════════════════════════════════════════

class RulesBasedCorrector:
    """Arabic keyboard-proximity and character substitution rules."""

    # Arabic keyboard layout adjacency mapping
    KEYBOARD_NEIGHBORS = {
        'ض': ['ص', 'ق'],
        'ص': ['ض', 'ث', 'ق'],
        'ث': ['ص', 'ق'],
        'ق': ['ض', 'ص', 'ث', 'ف', 'غ'],
        'ف': ['ق', 'غ', 'ع', 'ب'],
        'غ': ['ق', 'ف', 'ع', 'ه'],
        'ع': ['ف', 'غ', 'ه', 'خ'],
        'ه': ['غ', 'ع', 'خ', 'ح'],
        'خ': ['ع', 'ه', 'ح', 'ج'],
        'ح': ['ه', 'خ', 'ج'],
        'ج': ['خ', 'ح', 'د'],
        'د': ['ج', 'ذ'],
        'ذ': ['د'],
        'ش': ['س', 'ي', 'ئ'],
        'س': ['ش', 'ي', 'ب'],
        'ي': ['ش', 'س', 'ب', 'ت'],
        'ب': ['ي', 'س', 'ف', 'ل', 'ن'],
        'ل': ['ب', 'ا', 'ن', 'م'],
        'ا': ['ل', 'ت', 'م'],
        'ت': ['ي', 'ا', 'ن'],
        'ن': ['ب', 'ل', 'ت', 'م', 'ك'],
        'م': ['ل', 'ا', 'ن', 'ك'],
        'ك': ['ن', 'م', 'ط'],
        'ط': ['ك', 'ظ'],
        'ظ': ['ط'],
        'ئ': ['ش', 'ء', 'ر'],
        'ء': ['ئ', 'ؤ'],
        'ؤ': ['ء', 'ر'],
        'ر': ['ئ', 'ؤ', 'لا', 'ى', 'ز'],
        'لا': ['ر', 'ى'],
        'ى': ['ر', 'لا', 'ة', 'ز'],
        'ة': ['ى', 'و', 'ز'],
        'و': ['ة', 'ز'],
        'ز': ['ر', 'ى', 'ة', 'و'],
        'أ': ['ا', 'إ', 'آ'],
        'إ': ['ا', 'أ'],
        'آ': ['ا', 'أ'],
    }

    @staticmethod
    def is_keyboard_neighbor(char1: str, char2: str) -> bool:
        """Check if two Arabic chars are adjacent on the keyboard."""
        neighbors = RulesBasedCorrector.KEYBOARD_NEIGHBORS.get(char1, [])
        return char2 in neighbors

# ═══════════════════════════════════════════════════════════════════════════════
# POST PROCESSOR
# ═══════════════════════════════════════════════════════════════════════════════

class AraSpellPostProcessor:
    """Arabic text post-processing techniques."""
    
    ARABIC_HARAKAT = 'ًٌٍَُِّْ'
    TATWEEL = 'ـ'
    NORMALIZER_MAP = {
        'ﻹ': 'لإ', 'ﻷ': 'لأ', 'ﻵ': 'لآ', 'ﻻ': 'لا', 'ﷲ': 'الله'
    }
    ARABIC_CONSONANTS = set('بتثجحخدذرزسشصضطظعغفقكلمن')
    
    # --- Basic Normalization ---
    
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
    
    # --- Core Functions ---
    
    @staticmethod
    def unified_collapse_repeated(text: str) -> str:
        """
        Collapse repeated characters.
        Arabic: 3+ consecutive → 1 | Latin: 2+ consecutive → 1
        """
        text = re.sub(r"([\u0600-\u06FF])\1{2,}", r"\1", text)
        text = re.sub(r"([a-zA-Z])\1+", r"\1", text)
        return text
    
    @staticmethod
    def remove_duplicate_words(text: str) -> str:
        """Remove consecutive duplicate words. e.g. كتاب كتاب → كتاب"""
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
        """Normalize whitespace: multiple spaces, unicode spaces, punctuation spacing."""
        text = re.sub(r' +', ' ', text)
        text = text.replace('\u00A0', ' ')
        text = text.replace('\u200B', '')
        text = text.replace('\u200C', '')
        text = text.replace('\u200D', '')
        text = text.strip()
        text = re.sub(r'\s*([،؛؟!.])\s*', r'\1 ', text)
        text = text.strip()
        return text
    
    @staticmethod
    def remove_word_repetition_with_wa(text: str) -> str:
        """Remove word و word → word"""
        # Bug 2.9: This deletes valid rhetorical repetition (التوكيد اللفظي) like "صنفا وصنفا"
        # Disabled as it is highly destructive to valid Arabic.
        return text
    
    # --- Hamza & Ta Marbuta Handling ---
    
    # Common Arabic words with hamza errors — covers the most frequent
    # spelling mistakes in informal Arabic writing
    HAMZA_WHITELIST = {
        'الي': 'إلى', 'الى': 'إلى',
        'انت': 'أنت', 'انتم': 'أنتم', 'انتي': 'أنتِ',
        'انتو': 'أنتم', 'انتن': 'أنتن',
        'انا': 'أنا',
        'امس': 'أمس',
        'لان': 'لأن', 'لانه': 'لأنه', 'لانها': 'لأنها',
        'لانهم': 'لأنهم', 'لانك': 'لأنك',
        'اذا': 'إذا', 'اذ': 'إذ',
        'اي': 'أي', 'اين': 'أين',
        'او': 'أو',
        
        'ان': 'أن', 'انه': 'أنه', 'انها': 'أنها', 'انهم': 'أنهم',
        'اخر': 'آخر', 'اخرى': 'أخرى',
        'الان': 'الآن',
        'اول': 'أول', 'اولى': 'أولى',
        'اصبح': 'أصبح', 'اصبحت': 'أصبحت',
        'اكثر': 'أكثر', 'اقل': 'أقل',
        'اعلى': 'أعلى', 'ادنى': 'أدنى',
        'اسرع': 'أسرع', 'ابطا': 'أبطأ',
        'اكبر': 'أكبر', 'اصغر': 'أصغر',
        'احسن': 'أحسن', 'اسوا': 'أسوأ',
        'امام': 'أمام',
        'اثناء': 'أثناء',
        'ايضا': 'أيضاً', 'ايض': 'أيضاً',
        'اساسي': 'أساسي', 'اساسية': 'أساسية',
        'اخي': 'أخي', 'اخت': 'أخت', 'اخو': 'أخو',
        'ابي': 'أبي', 'اب': 'أب', 'ابو': 'أبو',
        'اهل': 'أهل',
        'اطفال': 'أطفال',
        'اصدقاء': 'أصدقاء', 'اصدقائي': 'أصدقائي',
        'اريد': 'أريد', 'احب': 'أحب',
        'اعلم': 'أعلم',
        'اكل': 'أكل',
        'الايام': 'الأيام',
        'الاطفال': 'الأطفال',
        'الاسعار': 'الأسعار',
        'الاولى': 'الأولى',
        'الاخير': 'الأخير', 'الاخيرة': 'الأخيرة',
        'واصدقائي': 'وأصدقائي',
        # FIX-14: Additional hamza entries
        'ابناء': 'أبناء',
        'اجمل': 'أجمل', 'اجمع': 'أجمع',
        'اعلن': 'أعلن', 'اعلنت': 'أعلنت',
        'اكد': 'أكد', 'اكدت': 'أكدت',
        'اشار': 'أشار', 'اشارت': 'أشارت',
        'ارسل': 'أرسل', 'ارسلت': 'أرسلت',
        'اضاف': 'أضاف', 'اضافت': 'أضافت',
        'اخيرا': 'أخيراً', 'اخيراً': 'أخيراً',
        'اساسا': 'أساساً', 'اساساً': 'أساساً',
        'احيانا': 'أحياناً', 'احياناً': 'أحياناً',
        'ابدا': 'أبداً', 'ابداً': 'أبداً',
        'اصلا': 'أصلاً', 'اصلاً': 'أصلاً',
        'اخبار': 'أخبار', 'اخبر': 'أخبر',
        'امر': 'أمر', 'امور': 'أمور',
        'اهم': 'أهم', 'اهمية': 'أهمية',
        'اصبح': 'أصبح', 'اصل': 'أصل',
        'اثر': 'أثر', 'اثار': 'آثار',
        'اساء': 'أساء', 'اساس': 'أساس',
        'استاذ': 'أستاذ', 'اسلام': 'إسلام',
        # Batch 3: More hamza entries for remaining FN cases
        'اسرة': 'أسرة', 'اسر': 'أسر',
        'اعضاء': 'أعضاء', 'اعداد': 'أعداد',
        'اعمال': 'أعمال', 'اعمار': 'أعمار',
        'انجاز': 'إنجاز', 'انجازات': 'إنجازات',
        'انشاء': 'إنشاء', 'انتاج': 'إنتاج',
        'انتخابات': 'انتخابات', 'انتظار': 'انتظار',
        'اسلامي': 'إسلامي', 'اسلامية': 'إسلامية',
        'امكانية': 'إمكانية', 'امكان': 'إمكان',
        'اشكالية': 'إشكالية',
        'ادارة': 'إدارة', 'ادارية': 'إدارية',
        'اعلام': 'إعلام', 'اعلامي': 'إعلامي',
        'احتمال': 'احتمال', 'احتفال': 'احتفال',
        'اقرا': 'أقرأ', 'اقرأ': 'أقرأ',
        'اسافر': 'أسافر',
        'احبه': 'أحبه',
        'مسؤول': 'مسؤول', 'مسؤولية': 'مسؤولية',
        'رؤية': 'رؤية', 'رؤيا': 'رؤيا',
        'مؤسسة': 'مؤسسة', 'مؤتمر': 'مؤتمر',
        'تأثير': 'تأثير', 'تأكيد': 'تأكيد',
        'البنايه': 'البناية',
        'جدا': 'جداً', 'جداً': 'جداً',
        # FIX-14: Alif maqsura common errors
        'المستشفي': 'المستشفى',
        'مصطفي': 'مصطفى', 'موسي': 'موسى', 'عيسي': 'عيسى',
        'هدي': 'هدى', 'بني': 'بنى',
        'معني': 'معنى', 'مبني': 'مبنى',
        
        'الي': 'إلى',
        # FIX-47: Verb+pronoun hamza entries (احبه→أحبه)
        'احبه': 'أحبه', 'احبها': 'أحبها', 'احبك': 'أحبك',
        'احبكم': 'أحبكم', 'احببت': 'أحببت',
        'افهم': 'أفهم', 'افهمه': 'أفهمه', 'افهمها': 'أفهمها',
        'افهمك': 'أفهمك',
        'اعطي': 'أعطي', 'اعطاه': 'أعطاه', 'اعطاها': 'أعطاها',
        'اعطى': 'أعطى', 'اعطت': 'أعطت', 'اعطيت': 'أعطيت',
        'احتاج': 'أحتاج', 'احتاجه': 'أحتاجه',
        'استطيع': 'أستطيع', 'استطع': 'أستطع',
        'اتمنى': 'أتمنى', 'اتوقع': 'أتوقع',
        'اشعر': 'أشعر', 'اظن': 'أظن', 'افضل': 'أفضل',
        'اخاف': 'أخاف', 'اتذكر': 'أتذكر', 'اتعلم': 'أتعلم',
        'ارجو': 'أرجو', 'اتوقف': 'أتوقف', 'انصح': 'أنصح',
        'انسان': 'إنسان', 'انسانية': 'إنسانية',
    }
    
    @staticmethod
    def fix_hamza_conservative(text: str) -> str:
        """Conservative Hamza normalization — only at word END, not middle."""
        # Bug 2.5: Blindly changing أ at the end of word to ا corrupts valid orthography (قرأ -> قرا)
        # Disabled as it is highly destructive.
        return text
    
    # Attached prefixes that can precede hamza-whitelist words
    # Ordered longest-first so وال is tried before و
    HAMZA_PREFIXES = ['وبال', 'فبال', 'وال', 'بال', 'فال', 'كال', 'ول', 'فل',
                      'وب', 'فب', 'وك', 'فك', 'و', 'ف', 'ب', 'ك', 'ل']

    @staticmethod
    def fix_common_hamza(text: str) -> str:
        """
        Fix common hamza placement errors using a whitelist.
        Also handles prefixed words: و/ف/ب/ك/ل + whitelist word.
        Handles adjacent punctuation (e.g. واصدقائي، → وأصدقائي،)
        """
        words = text.split()
        result = []
        for word in words:
            # Separate leading/trailing punctuation from the core word
            match = re.match(r'^([\.,،؛؟!:;?\(\)\[\]«»"\'\s]*)(.*?)([\.,،؛؟!:;?\(\)\[\]«»"\'\s]*)$', word)
            if not match or not match.group(2):
                result.append(word)
                continue
                
            lead_punct = match.group(1)
            core_word = match.group(2)
            trail_punct = match.group(3)

            # Check exact match first
            if core_word in AraSpellPostProcessor.HAMZA_WHITELIST:
                result.append(lead_punct + AraSpellPostProcessor.HAMZA_WHITELIST[core_word] + trail_punct)
                continue

            # Try stripping common prefixes and looking up the remainder
            fixed = False
            for prefix in AraSpellPostProcessor.HAMZA_PREFIXES:
                if core_word.startswith(prefix) and len(core_word) > len(prefix) + 1:
                    remainder = core_word[len(prefix):]
                    if remainder in AraSpellPostProcessor.HAMZA_WHITELIST:
                        result.append(lead_punct + prefix + AraSpellPostProcessor.HAMZA_WHITELIST[remainder] + trail_punct)
                        fixed = True
                        break
            if not fixed:
                result.append(word)
        return ' '.join(result)
    
    @staticmethod
    def fix_ha_ta_marbuta(text: str, vocab_manager=None) -> str:
        """
        Smart ه → ة fix at end of words.
        Strategy: Always prefer ة when the previous char is a consonant,
        UNLESS the ه form is specifically a known word and the ة form is NOT.
        """
        PROTECTED_ENDINGS = ['لله']
        # Words that genuinely end in ه (not ة)
        PROTECTED_HA_WORDS = {
            'الله', 'لله', 'فيه', 'عليه', 'منه', 'به', 'له', 'إليه',
            'وجه', 'نزه', 'سفه', 'فقه', 'نبه', 'شبه', 'مكره', 'تنبه',
            'اتجه', 'توجه', 'تشابه',
        }
        words = text.split()
        result = []
        for word in words:
            if any(word.endswith(e) for e in PROTECTED_ENDINGS):
                result.append(word)
                continue
            if word in PROTECTED_HA_WORDS:
                result.append(word)
                continue
            if len(word) >= 3 and word.endswith('ه'):
                if word[-2] in AraSpellPostProcessor.ARABIC_CONSONANTS:
                    candidate_with_ta = word[:-1] + 'ة'
                    # Default: prefer ة (correct Arabic orthography for feminine nouns)
                    if vocab_manager:
                        ta_iv = vocab_manager.is_iv(candidate_with_ta)
                        ha_iv = vocab_manager.is_iv(word)
                        if ha_iv and ta_iv:
                            # Bug 2.2: Do not prefer ة if ه is also valid (possessive pronoun)
                            result.append(word)
                            continue
                        elif ta_iv:
                            # Prefer ة when ONLY the ة form is valid
                            result.append(candidate_with_ta)
                            continue
                        elif ha_iv:
                            result.append(word)
                            continue
                    # No vocab manager — default to ة
                    result.append(candidate_with_ta)
                    continue
            result.append(word)
        return ' '.join(result)
    
    # --- Hallucination Removal ---
    
    @staticmethod
    def remove_hallucinations(text: str) -> str:
        """Remove model hallucinations: duplicate words, trailing 'و' artifacts."""
        words = text.split()
        if not words:
            return text
        result = []
        i = 0
        
        def normalize_word(w: str) -> str:
            w = w.replace('ال', '').replace('ة', 'ه')
            w = re.sub(r'[أإآ]', 'ا', w)
            return w
        
        while i < len(words):
            word = words[i]
            if len(word) > 4 and word.endswith('و'):
                prev_char = word[-2]
                if prev_char in 'ةهاأإآء':
                    word = word[:-1]
            if i + 1 < len(words):
                next_word = words[i + 1]
                # Bug 2.11: Destroys Badal structures (الأستاذ أستاذ -> الأستاذ)
                if word == next_word: # Only remove exact duplicates, not normalized duplicates
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
            if AraSpellPostProcessor.normalize_special_chars(rest) == AraSpellPostProcessor.normalize_special_chars(original):
                return rest
        return text
    
    # --- Word Splitting & Merging ---
    
    @staticmethod
    def merge_separated_al(text: str) -> str:
        """Merge 'ال' separated by space: ال + كتاب → الكتاب"""
        return re.sub(r'\bال\s+(\w+)', r'ال\1', text)
    
    @staticmethod
    def join_fragments(text: str) -> str:
        """Join short fragments with validation."""
        words = text.split()
        if len(words) < 2:
            return text
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
                if word in STANDALONE_WORDS and next_word in STANDALONE_WORDS:
                    result.append(word)
                    i += 1
                    continue
                if len(next_word) == 1:
                    result.append(word + next_word)
                    i += 2
                    continue
                # Bug 2.3: Destructive word merging (يوم مشمس -> يومشمس)
                # Removed generic boundary letter merging.
            result.append(word)
            i += 1
        return ' '.join(result)
    
    # --- Main Pipelines ---
    
    @staticmethod
    def full_postprocess(text: str, original: str = "", vocab_manager=None) -> str:
        """Apply all post-processing steps."""
        if original:
            text = AraSpellPostProcessor.remove_hallucinated_prefix(text, original)
        text = AraSpellPostProcessor.normalize_special_chars(text)
        text = AraSpellPostProcessor.remove_hallucinations(text)
        text = AraSpellPostProcessor.unified_collapse_repeated(text)
        text = AraSpellPostProcessor.fix_hamza_conservative(text)
        text = AraSpellPostProcessor.fix_common_hamza(text)  # Fix S3: hamza whitelist
        text = AraSpellPostProcessor.fix_ha_ta_marbuta(text, vocab_manager=vocab_manager)
        text = AraSpellPostProcessor.remove_word_repetition_with_wa(text)
        text = AraSpellPostProcessor.remove_duplicate_words(text)
        text = AraSpellPostProcessor.normalize_spaces(text)
        return text


# ─────────────────────────────────────────────────────────────────────────────
# ERROR CLASSIFIER
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
# RULES-BASED CORRECTOR
# ═══════════════════════════════════════════════════════════════════════════════

class RulesBasedCorrector:
    """Rules-based correction with keyboard proximity mapping."""
    
    SUBSTITUTION_MAP = {
        'ک': 'ك', 'ی': 'ي', 'ے': 'ي',
        'پ': 'ب', 'چ': 'ج', 'ژ': 'ز',
        'گ': 'ك', 'ڤ': 'ف', 'ڵ': 'ل',
        'ڕ': 'ر', 'ڎ': 'د', 'ڼ': 'ن',
        'ټ': 'ت', 'ډ': 'د', 'ړ': 'ر',
        'ۀ': 'ه', 'ۃ': 'ة', 'ھ': 'ه',
        'ە': 'ه', 'ڑ': 'ر'
    }
    
    PREPOSITIONS = {
        'من', 'في', 'على', 'عن', 'مع', 'إلى', 'الى',
        'حتى', 'منذ', 'خلال', 'بعد', 'قبل',
        'ب', 'ل', 'ك', 'لل'
    }
    
    KEYBOARD_NEIGHBORS = {
        'ض': ['ص', 'ق'], 'ص': ['ض', 'ث', 'ق'], 'ث': ['ص', 'ق'],
        'ق': ['ض', 'ص', 'ث', 'ف', 'غ'], 'ف': ['ق', 'غ', 'ع', 'ب'],
        'غ': ['ق', 'ف', 'ع', 'ه'], 'ع': ['ف', 'غ', 'ه', 'خ'],
        'ه': ['غ', 'ع', 'خ', 'ح'], 'خ': ['ع', 'ه', 'ح', 'ج'],
        'ح': ['ه', 'خ', 'ج'], 'ج': ['خ', 'ح', 'د'],
        'د': ['ج', 'ذ'], 'ذ': ['د'],
        'ش': ['س', 'ي', 'ئ'], 'س': ['ش', 'ي', 'ب'],
        'ي': ['ش', 'س', 'ب', 'ت'], 'ب': ['ي', 'س', 'ف', 'ل', 'ن'],
        'ل': ['ب', 'ا', 'ن', 'م'], 'ا': ['ل', 'ت', 'م'],
        'ت': ['ي', 'ا', 'ن'], 'ن': ['ب', 'ل', 'ت', 'م', 'ك'],
        'م': ['ل', 'ا', 'ن', 'ك'], 'ك': ['ن', 'م', 'ط'],
        'ط': ['ك', 'ظ'], 'ظ': ['ط'],
        'ئ': ['ش', 'ء', 'ر'], 'ء': ['ئ', 'ؤ'], 'ؤ': ['ء', 'ر'],
        'ر': ['ئ', 'ؤ', 'لا', 'ى', 'ز'], 'لا': ['ر', 'ى'],
        'ى': ['ر', 'لا', 'ة', 'ز'], 'ة': ['ى', 'و', 'ز'],
        'و': ['ة', 'ز'], 'ز': ['ر', 'ى', 'ة', 'و'],
        'أ': ['ا', 'إ', 'آ'], 'إ': ['ا', 'أ'], 'آ': ['ا', 'أ'],
    }
    
    @staticmethod
    def is_keyboard_neighbor(char1: str, char2: str) -> bool:
        neighbors = RulesBasedCorrector.KEYBOARD_NEIGHBORS.get(char1, [])
        return char2 in neighbors
    
    @staticmethod
    def fix_char_substitution(text: str) -> str:
        for old, new in RulesBasedCorrector.SUBSTITUTION_MAP.items():
            text = text.replace(old, new)
        return text
    
    @staticmethod
    def fix_char_repetition(text: str) -> str:
        text = re.sub(r'([^\d\s])\1{2,}', r'\1', text)
        return text
    
    @staticmethod
    def advanced_heuristic_repair(text: str) -> str:
        text = RulesBasedCorrector.fix_char_substitution(text)
        text = RulesBasedCorrector.fix_char_repetition(text)
        words = text.split()
        processed_words = []
        for word in words:
            processed_words.append(RulesBasedCorrector._recursive_split(word))
        return ' '.join(processed_words)

    @staticmethod
    def _recursive_split(word: str) -> str:
        if len(word) < 4:
            return word
        separables = sorted(['من', 'في', 'على', 'عن', 'مع', 'إلى', 'الى', 'حتى', 'منذ', 'خلال', 'بعد', 'قبل'], key=len, reverse=True)
        for sep in separables:
            if word == sep:
                return word
            if word.startswith(sep):
                remainder = word[len(sep):]
                if len(remainder) >= 3:
                     return sep + " " + RulesBasedCorrector._recursive_split(remainder)
        if word.startswith('يا') and len(word) > 4:
             return 'يا ' + RulesBasedCorrector._recursive_split(word[2:])
        return word


# ═══════════════════════════════════════════════════════════════════════════════
# OUTPUT VALIDATOR (Hallucination Prevention)
# ═══════════════════════════════════════════════════════════════════════════════

class OutputValidator:
    """Validate model outputs to prevent hallucinations"""
    
    @staticmethod
    def calculate_edit_distance(s1: str, s2: str) -> int:
        return Levenshtein.distance(s1, s2)
    
    @staticmethod
    def check_character_preservation(original: str, corrected: str) -> Tuple[bool, str]:
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
        len_orig = len(original.split())
        len_corr = len(corrected.split())
        if len_orig == 1:
            if len_corr <= 3:
                return True, "valid"
            if len(original) > 12 and len_corr <= 6:
                return True, "valid"
        ratio = len_corr / len_orig if len_orig > 0 else 0
        if ratio > 2.0 or ratio < 0.5:
             return False, "word_count_mismatch"
        return True, "valid"

    def validate(self, original: str, corrected: str, error_type: str) -> Tuple[bool, str]:
        if not corrected or not corrected.strip():
            return False, "empty_output"
        original_no_space = original.replace(' ', '').replace('\u200c', '')
        corrected_no_space = corrected.replace(' ', '').replace('\u200c', '')
        if original_no_space == corrected_no_space:
            return True, "space_leniency_accept"
        len_orig = len(original)
        len_corr = len(corrected)
        if len_corr > len_orig * 2.5:
             return False, "too_long"
        if len_corr < len_orig * 0.5:
             if error_type == ErrorType.CHAR_REPETITION:
                 pass
             else:
                 return False, "too_short"
        is_valid_count, reason = self.check_word_count(original, corrected)
        if not is_valid_count:
            return False, reason
        is_valid_chars, reason = self.check_character_preservation(original, corrected)
        if not is_valid_chars:
             return False, reason
        return True, "valid"


# ═══════════════════════════════════════════════════════════════════════════════
# VOCABULARY MANAGER
# ═══════════════════════════════════════════════════════════════════════════════

class VocabularyManager:
    """Centralized vocabulary management for OOV/IV detection using CamelTools."""
    
    def __init__(self, tokenizer):
        self.tokenizer = tokenizer
        from camel_tools.morphology.database import MorphologyDB
        from camel_tools.morphology.analyzer import Analyzer
        self._db = MorphologyDB.builtin_db()
        self.analyzer = Analyzer(self._db)
        logger.info("VocabularyManager initialized with CamelTools Analyzer")
    
    def is_iv(self, word: str) -> bool:
        clean = re.sub(r'[^\w]', '', word)
        if not clean:
            return True
        return len(self.analyzer.analyze(clean)) > 0
    
    def is_oov(self, word: str) -> bool:
        return not self.is_iv(word)
    
    def get_frequency_rank(self, word: str) -> int:
        clean = re.sub(r'[^\w]', '', word)
        return self.vocab_rank.get(clean, 999999)
    
    def all_words_iv(self, text: str) -> bool:
        words = text.split()
        return all(self.is_iv(w) for w in words)
    
    def count_oov_words(self, text: str) -> int:
        words = text.split()
        return sum(1 for w in words if self.is_oov(w))
    
    def get_oov_words(self, text: str) -> List[str]:
        words = text.split()
        return [w for w in words if self.is_oov(w)]
    
    def words_are_equivalent(self, word1: str, word2: str) -> bool:
        norm1 = self.normalize_for_comparison(word1)
        norm2 = self.normalize_for_comparison(word2)
        return norm1 == norm2
    
    @staticmethod
    def damerau_levenshtein_distance(s1: str, s2: str) -> int:
        return jellyfish.damerau_levenshtein_distance(s1, s2)
    
    def calculate_similarity(self, original: str, corrected: str) -> float:
        dist = self.damerau_levenshtein_distance(original, corrected)
        max_len = max(len(original), len(corrected), 1)
        return 1.0 - (dist / max_len)


# ═══════════════════════════════════════════════════════════════════════════════
# WORD ALIGNER
# ═══════════════════════════════════════════════════════════════════════════════

class WordAligner:
    """Aligns input and output words to create hybrid corrections."""
    
    def __init__(self, vocab_manager):
        self.vocab = vocab_manager
    
    def align_words(self, input_text: str, output_text: str) -> str:
        input_words = input_text.split()
        output_words = output_text.split()
        if abs(len(input_words) - len(output_words)) > 2:
            input_oov = self.vocab.count_oov_words(input_text)
            output_oov = self.vocab.count_oov_words(output_text)
            return output_text if output_oov < input_oov else input_text
        result = []
        min_len = min(len(input_words), len(output_words))
        for i in range(min_len):
            in_word = input_words[i]
            out_word = output_words[i]
            best_word = self._select_best_word(in_word, out_word)
            result.append(best_word)
        if len(output_words) > min_len:
            result.extend(output_words[min_len:])
        elif len(input_words) > min_len:
            for w in input_words[min_len:]:
                 if self.vocab.is_iv(w):
                     result.append(w)
        return ' '.join(result)
    
    def _select_best_word(self, input_word: str, output_word: str) -> str:
        if input_word == output_word:
            return input_word
        in_iv = self.vocab.is_iv(input_word)
        out_iv = self.vocab.is_iv(output_word)
        if not in_iv and out_iv:
            return output_word
        if in_iv and not out_iv:
            return input_word
        if in_iv and out_iv:
            # Bug 2.2: Do not prefer ة over ه if both are IV, because ه is often a valid possessive pronoun.
            return input_word 
        if len(input_word) == len(output_word) and len(input_word) >= 3:
            for i in range(len(input_word)):
                if input_word[i] != output_word[i]:
                    hybrid = input_word[:i] + output_word[i] + input_word[i+1:]
                    if self.vocab.is_iv(hybrid):
                        return hybrid
                    hybrid2 = output_word[:i] + input_word[i] + output_word[i+1:]
                    if self.vocab.is_iv(hybrid2):
                        return hybrid2
        return output_word


# ═══════════════════════════════════════════════════════════════════════════════
# SPLIT/MERGE SPECIALIST
# ═══════════════════════════════════════════════════════════════════════════════

class SplitMergeSpecialist:
    """Handles word splitting and merging with vocabulary validation."""
    
    SEPARABLE_PREFIXES = [
        'من', 'في', 'على', 'عن', 'مع', 'إلى', 'الى', 'حتى', 'منذ', 'خلال', 
        'بعد', 'قبل', 'بين', 'حول', 'تحت', 'فوق', 'أمام', 'وراء', 'دون',
        'أن', 'لن', 'لم', 'قد', 'سوف', 'كي', 'إذا', 'لو', 'مثل', 'غير',
        'يا',
    ]
    
    PROTECTED_WORDS = {
        'في', 'من', 'على', 'عن', 'مع', 'إلى', 'الى', 'ان', 'أن', 'لا', 'ما', 'هو', 'هي',
        'لم', 'لن', 'قد', 'كل', 'كان', 'ذلك', 'هذا', 'هذه', 'التي', 'الذي', 'بين',
    }
    
    ATTACHED_PREFIXES = [
        'وال', 'بال', 'فال', 'كال', 'لل',
        'وب', 'وف', 'ول', 'وك', 'وم', 'ون',
        'فب', 'فل', 'فك', 'فم',
    ]
    
    PRONOUN_SUFFIXES = {'كم', 'هم', 'ها', 'هن', 'كن', 'نا', 'هما', 'كما', 'تم', 'تن'}
    
    def __init__(self, vocab_manager):
        self.vocab = vocab_manager
        self.separable_prefixes = sorted(
            self.SEPARABLE_PREFIXES, key=len, reverse=True
        )
    
    def split_word(self, word: str) -> str:
        if len(word) < 5:
            return word
        if self.vocab.is_iv(word):
            return word
        if word in self.PROTECTED_WORDS:
            return word
        for prefix in self.ATTACHED_PREFIXES:
            if word.startswith(prefix):
                remainder = word[len(prefix):]
                if self.vocab.is_iv(remainder):
                    return word
                if prefix.endswith('ال') and self.vocab.is_iv(remainder):
                    return word
        for prefix in self.separable_prefixes:
            if word.startswith(prefix) and len(word) > len(prefix) + 2:
                remainder = word[len(prefix):]
                if self.vocab.is_iv(remainder):
                    return f"{prefix} {remainder}"
        for i in range(3, len(word) - 2):
            left = word[:i]
            right = word[i:]
            if self.vocab.is_iv(left) and self.vocab.is_iv(right):
                return f"{left} {right}"
        return word
    
    def merge_fragments(self, text: str) -> str:
        words = text.split()
        if len(words) < 2:
            return text
        result = []
        i = 0
        while i < len(words):
            word = words[i]
            if i + 1 < len(words):
                next_word = words[i + 1]
                merged = word + next_word
                if len(next_word) == 1 and next_word in 'ةهاي':
                    if self.vocab.is_iv(merged):
                        result.append(merged)
                        i += 2
                        continue
                if word == 'ال' and len(next_word) >= 2:
                    if self.vocab.is_iv(merged):
                        result.append(merged)
                        i += 2
                        continue
                if self.vocab.is_oov(word) and self.vocab.is_oov(next_word):
                    if self.vocab.is_iv(merged):
                        result.append(merged)
                        i += 2
                        continue
                if len(word) <= 2 and self.vocab.is_oov(word):
                    if self.vocab.is_iv(merged):
                        result.append(merged)
                        i += 2
                        continue
                if next_word in self.PRONOUN_SUFFIXES:
                    if self.vocab.is_iv(merged) and not self.vocab.is_iv(word):
                        result.append(merged)
                        i += 2
                        continue
                if len(word) <= 3 and len(next_word) <= 3:
                    if len(merged) >= 5 and self.vocab.is_iv(merged):
                        result.append(merged)
                        i += 2
                        continue
            result.append(word)
            i += 1
        return ' '.join(result)
    
    def process_text(self, text: str) -> str:
        text = self.merge_fragments(text)
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
# EDIT DISTANCE CORRECTOR
# ═══════════════════════════════════════════════════════════════════════════════

class EditDistanceCorrector:
    """Generates candidates based on Levenshtein distance."""
    
    def __init__(self, tokenizer):
        self.tokenizer = tokenizer
        self.vocab = {
            w for w in tokenizer.get_vocab().keys() 
            if w.isalpha() and not w.startswith('##') and len(w) > 1
        }
        self.vocab_rank = {w: i for w, i in tokenizer.get_vocab().items()}

    def edits1(self, word):
        letters    = 'أابتثجحخدذرزسشصضطظعغفقكلمنهويءآىةئؤ'
        splits     = [(word[:i], word[i:])    for i in range(len(word) + 1)]
        deletes    = [L + R[1:]               for L, R in splits if R]
        transposes = [L + R[1] + R[0] + R[2:] for L, R in splits if len(R)>1]
        replaces   = [L + c + R[1:]           for L, R in splits if R for c in letters]
        inserts    = [L + c + R               for L, R in splits for c in letters]
        return set(deletes + transposes + replaces + inserts)

    def edits2(self, word):
        return (e2 for e1 in self.edits1(word) for e2 in self.edits1(e1))

    def known(self, words):
        return set(w for w in words if w in self.vocab)

    def generate_candidate(self, text: str) -> str:
        words = text.split()
        corrected_words = []
        for word in words:
            clean_word = re.sub(r'[^\w]', '', word)
            if clean_word in self.vocab:
                corrected_words.append(word)
                continue
            candidates = self.known(self.edits1(clean_word))
            if not candidates:
                if len(clean_word) < 7: 
                    candidates = self.known(self.edits2(clean_word))
            if candidates:
                best_candidate = min(candidates, key=lambda w: self.vocab_rank.get(w, 999999))
                corrected_words.append(best_candidate)
            else:
                corrected_words.append(word)
        return ' '.join(corrected_words)


# ═══════════════════════════════════════════════════════════════════════════════
# CONTEXTUAL CORRECTOR (MLM-based) — Optional, disabled by default to save RAM
# ═══════════════════════════════════════════════════════════════════════════════

class ContextualCorrector:
    """MLM-based contextual correction for confusion pairs"""
    
    CONFUSION_PAIRS = [
        ('ض', 'ظ'), ('ذ', 'ز'), ('ث', 'س'), ('ص', 'س'),
        ('ط', 'ت'), ('ق', 'ك'), ('ه', 'ة'), ('ا', 'ى'),
        ('ت', 'د'), ('د', 'ض'), ('ك', 'ق'), ('غ', 'ق'),
        ('ج', 'ش'), ('س', 'ز'), ('ف', 'ب'), ('و', 'و'),
        ('ؤ', 'و'), ('ئ', 'ي'), ('ء', 'أ'), ('إ', 'أ'),
    ]
    
    def __init__(self, model_name: str = 'aubmindlab/bert-base-arabertv02', cache_size: int = 10000):
        from transformers import AutoTokenizer, AutoModelForMaskedLM
        
        self.tokenizer = AutoTokenizer.from_pretrained(model_name)
        self.model = AutoModelForMaskedLM.from_pretrained(model_name)
        self.device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
        self.model = self.model.to(self.device)
        self.model.eval()
        self.confusion_map = self._build_confusion_map()
        self.cache_hits = 0
        self.cache_misses = 0
        self._score_cache = {}
        self.cache_size = cache_size
        self.vocab = self.tokenizer.get_vocab()
    
    def _build_confusion_map(self):
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
        return self.confusion_map.get(char, [])
    
    def generate_candidates(self, word: str) -> List[str]:
        candidates = [word]
        for i, char in enumerate(word):
            confusables = self.get_confusable_chars(char)
            for conf_char in confusables:
                candidate = word[:i] + conf_char + word[i+1:]
                if candidate not in candidates:
                    candidates.append(candidate)
        for i in range(len(word) - 1):
            if word[i] == word[i+1]:
                candidate = word[:i] + word[i+1:]
                if candidate not in candidates:
                    candidates.append(candidate)
        COMMON_CHARS = 'ابتثجحخدذرزسشصضطظعغفقكلمنهويأإآءئؤةى'
        for i in range(len(word) + 1):
            for char in COMMON_CHARS:
                candidate = word[:i] + char + word[i:]
                if candidate in self.vocab and candidate not in candidates:
                    candidates.append(candidate)
        if len(word) < 7:
            for i in range(len(word)):
                for char in COMMON_CHARS:
                    if char != word[i]:
                        candidate = word[:i] + char + word[i+1:]
                        if candidate in self.vocab and candidate not in candidates:
                            candidates.append(candidate)
        for i in range(len(word)):
            candidate = word[:i] + word[i+1:]
            if len(candidate) > 1:
                if candidate in self.vocab and candidate not in candidates:
                    candidates.append(candidate)
        return candidates
    
    def score_with_mlm(self, text: str, position: int, word: str) -> float:
        cache_key = f"{text}|{position}|{word}"
        if cache_key in self._score_cache:
            self.cache_hits += 1
            return self._score_cache[cache_key]
        self.cache_misses += 1
        words = text.split()
        if position >= len(words):
            return 0.0
        masked_words = words.copy()
        masked_words[position] = '[MASK]'
        masked_text = ' '.join(masked_words)
        inputs = self.tokenizer(masked_text, return_tensors='pt', padding=True, truncation=True)
        inputs = {k: v.to(self.device) for k, v in inputs.items()}
        with torch.no_grad():
            outputs = self.model(**inputs)
            predictions = outputs.logits
        mask_token_index = (inputs['input_ids'] == self.tokenizer.mask_token_id).nonzero(as_tuple=True)[1]
        if len(mask_token_index) == 0:
            return 0.0
        mask_token_logits = predictions[0, mask_token_index[0], :]
        probs = torch.softmax(mask_token_logits, dim=0)
        word_tokens = self.tokenizer.encode(word, add_special_tokens=False)
        if not word_tokens:
            return 0.0
        word_token_id = word_tokens[0]
        score = probs[word_token_id].item()
        if len(self._score_cache) >= self.cache_size:
            self._score_cache.pop(next(iter(self._score_cache)))
        self._score_cache[cache_key] = score
        return score
    
    def score_candidates_batch(self, text: str, position: int, candidates: List[str]) -> dict:
        scores = {}
        for candidate in candidates:
            scores[candidate] = self.score_with_mlm(text, position, candidate)
        return scores
    
    def predict_masked_token(self, text: str, position: int, top_k: int = 5) -> List[Tuple[str, float]]:
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
            if not token.startswith("##") and token not in self.tokenizer.all_special_tokens:
                results.append((token, score))
        return results

    def refine_sentence_with_mask(self, text: str, threshold: float = 0.001, vocab_manager=None, raw_model_output=None) -> str:
        words = text.split()
        refined_words = words.copy()
        raw_words = raw_model_output.split() if raw_model_output else []
        for i, word in enumerate(words):
            if vocab_manager and vocab_manager.is_iv(word):
                continue
            if i < len(raw_words) and word == raw_words[i]:
                continue
            if len(word) <= 2:
                continue
            current_score = self.score_with_mlm(text, i, word)
            if current_score > threshold:
                continue
            predictions = self.predict_masked_token(text, i, top_k=10)
            for pred_word, pred_score in predictions:
                if pred_word == word:
                    continue
                if abs(len(pred_word) - len(word)) > 1:
                     continue
                dist = Levenshtein.distance(word, pred_word)
                max_len = max(len(word), len(pred_word))
                similarity = 1.0 - (dist / max_len)
                if similarity < 0.90:
                    continue
                if vocab_manager and vocab_manager.is_oov(pred_word):
                    continue
                if pred_score < 0.12:
                    continue
                is_original_common = current_score > 0.001
                if is_original_common:
                     if pred_score > current_score * 1000:
                         refined_words[i] = pred_word
                         break
                else:
                    if pred_score > current_score * 50 and pred_score > 0.2:
                        refined_words[i] = pred_word
                        break
        return ' '.join(refined_words)
    
    def calculate_sentence_score(self, text: str) -> float:
        words = text.split()
        if not words:
            return 0.0
        total_score = 0.0
        scored_words = 0
        for i, word in enumerate(words):
            score = self.score_with_mlm(text, i, word)
            total_score += score
            scored_words += 1
        if scored_words == 0:
            return 0.0
        return total_score / scored_words


# ═══════════════════════════════════════════════════════════════════════════════
# MAIN SPELL CHECKER CLASS
# ═══════════════════════════════════════════════════════════════════════════════

class ArabicSpellChecker:
    """Main Arabic Spell Checker class"""
    
    def __init__(self, model, tokenizer, device, use_contextual: bool = True):
        self.model = model
        self.tokenizer = tokenizer
        self.device = device
        
        self.postprocessor = AraSpellPostProcessor()
        self.classifier = ErrorClassifier()
        self.rules = RulesBasedCorrector()
        self.validator = OutputValidator()
        self.vocab_manager = VocabularyManager(tokenizer)
        self.edit_corrector = EditDistanceCorrector(tokenizer)
        self.split_merge = SplitMergeSpecialist(self.vocab_manager)
        self.word_aligner = WordAligner(self.vocab_manager)
        
        self.use_contextual = use_contextual
        if use_contextual:
            try:
                logger.info("=" * 60)
                logger.info("[MLM/CONTEXTUAL] Loading AraBERT MLM model...")
                self.contextual = ContextualCorrector()
                logger.info("[MLM/CONTEXTUAL] ✅ LOADED SUCCESSFULLY")
                logger.info(f"[MLM/CONTEXTUAL] Device: {self.contextual.device}")
                logger.info(f"[MLM/CONTEXTUAL] Vocab size: {len(self.contextual.vocab)}")
                logger.info("=" * 60)
            except Exception as e:
                logger.warning("=" * 60)
                logger.warning(f"[MLM/CONTEXTUAL] ❌ FAILED TO LOAD: {e}")
                logger.warning("[MLM/CONTEXTUAL] Spelling will work without contextual validation")
                logger.warning("=" * 60)
                self.contextual = None
                self.use_contextual = False
        else:
            self.contextual = None
            logger.info("[MLM/CONTEXTUAL] Disabled by configuration (use_contextual=False)")

    def _fix_repeated_end_chars(self, text: str) -> str:
        text = re.sub(r'([ا-ي])\1+\b', r'\1', text)
        return text
    
    def _fix_merged_with_errors(self, text: str) -> str:
        # Bug 2.10: This regex was r'ال\2', deleting all instances of the character
        text = re.sub(r'ال([ا-ي])\1+([ا-ي]{2,})', r'ال\1\2', text)
        text = re.sub(r'\b([ا-ي]{3,})([ا-ي])\2+\b', r'\1\2', text)
        return text

    def _split_merged_words_linguistic(self, text: str) -> str:
        # Bug 2.7: Catastrophic preposition splitting (e.g. منطق -> من طق)
        # Disabled generic regex splitting as it is highly destructive to valid vocabulary.
        return text
    
    def _split_long_words_heuristic(self, text: str, max_length: int = 15) -> str:
        # Bug 2.8: Overzealous long word splitting (e.g. فيتامينات -> في تامينات)
        # Disabled as it creates more errors than it fixes.
        return text
    
    def _normalize_tanween_patterns(self, text: str) -> str:
        # Bug 2.6: Blind replacement of trailing أ with اً corrupts verbs and nominative cases (قرأ -> قراً)
        text = re.sub(r'\s+أ\s+', ' ', text)
        text = re.sub(r'\b([بلك])\s+([ا-ي])', r'\1\2', text)
        return text
    
    def preprocess(self, text: str) -> str:
        """Preprocessing pipeline"""
        text = self.postprocessor.remove_harakat(text)
        text = self.postprocessor.remove_tatweel(text)
        text = self.postprocessor.normalize_special_chars(text)
        text = self._fix_repeated_end_chars(text)
        text = self._fix_merged_with_errors(text)
        text = self._split_merged_words_linguistic(text)
        text = self._split_long_words_heuristic(text)
        text = self._normalize_tanween_patterns(text)
        text = self.postprocessor.merge_separated_al(text)
        text = self.postprocessor.unified_collapse_repeated(text)
        text = self.rules.fix_char_substitution(text)
        text = self.rules.fix_char_repetition(text)
        text = self.postprocessor.normalize_spaces(text)
        return text
    
    def postprocess(self, text: str, original: str = "") -> str:
        """Postprocessing pipeline"""
        return self.postprocessor.full_postprocess(text, original, vocab_manager=self.vocab_manager)
    
    def model_inference(self, text: str, num_return_sequences: int = 5) -> List[str]:
        """Run seq2seq model inference and return top candidates."""
        inputs = self.tokenizer(text, return_tensors='pt', padding=True, truncation=True, max_length=128)
        inputs = {k: v.to(self.device) for k, v in inputs.items()}
        with torch.no_grad():
            outputs = self.model.generate(
                **inputs,
                num_beams=5,
                num_return_sequences=num_return_sequences,
                early_stopping=True,
                return_dict_in_generate=True,
                output_scores=True
            )
        candidates = self.tokenizer.batch_decode(outputs.sequences, skip_special_tokens=True)
        self._last_beam_scores = {}
        if hasattr(outputs, 'sequences_scores') and outputs.sequences_scores is not None:
            scores = outputs.sequences_scores.tolist()
            for cand, score in zip(candidates, scores):
                self._last_beam_scores[cand] = score
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
        preprocessed_text = self.preprocess(text)
        
        # 2. Classify error type
        error_type = self.classifier.classify(preprocessed_text)
        
        # 3. Generate Candidates
        candidates = []
        candidates.append(preprocessed_text)
        
        rules_candidate = self.rules.advanced_heuristic_repair(text)
        candidates.append(rules_candidate)
        
        edit_candidate = self.edit_corrector.generate_candidate(text)
        if edit_candidate != text and edit_candidate != rules_candidate:
            candidates.append(edit_candidate)
        
        raw_model_output = None
        try:
            model_candidates = self.model_inference(preprocessed_text, num_return_sequences=5)
            raw_model_output = model_candidates[0] if model_candidates else None
            candidates.extend(model_candidates)
            
            if model_candidates:
                hybrid_candidate = self.word_aligner.align_words(preprocessed_text, model_candidates[0])
                if hybrid_candidate not in candidates:
                    candidates.append(hybrid_candidate)
                for beam in model_candidates[1:3]:
                    hybrid_beam = self.word_aligner.align_words(preprocessed_text, beam)
                    if hybrid_beam not in candidates:
                        candidates.append(hybrid_beam)
            
            if model_candidates and len(model_candidates) >= 3:
                try:
                    beam_word_lists = [c.split() for c in model_candidates]
                    max_words = max(len(wl) for wl in beam_word_lists)
                    voted_words = []
                    for pos in range(max_words):
                        words_at_pos = []
                        for wl in beam_word_lists:
                            if pos < len(wl):
                                words_at_pos.append(wl[pos])
                        if words_at_pos:
                            most_common = Counter(words_at_pos).most_common(1)[0][0]
                            voted_words.append(most_common)
                    voted_candidate = ' '.join(voted_words)
                    if voted_candidate not in candidates:
                        candidates.append(voted_candidate)
                except Exception:
                    pass
        except Exception as e:
            logger.warning(f"Model inference failed: {e}")
        
        # Remove duplicates
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
        candidate_scores = []
        
        for cand in candidates:
            is_valid, reason = self.validator.validate(original, cand, error_type.value)
            if len(cand) < len(original) * 0.5:
                is_valid = False
                reason = "too_short"

            input_oov_count = self.vocab_manager.count_oov_words(original)
            cand_oov_count = self.vocab_manager.count_oov_words(cand)
            vocab_boost = 1.0
            
            if input_oov_count > 0 and cand_oov_count < input_oov_count:
                oov_reduction = input_oov_count - cand_oov_count
                vocab_boost = 1.0 + (oov_reduction * 0.3)
                if cand_oov_count == 0 and self.vocab_manager.all_words_iv(cand):
                    if not is_valid and reason not in ["empty_output"]:
                        is_valid = True
                        reason = "vocab_aware_accept"
            elif cand_oov_count > input_oov_count:
                vocab_boost = 0.5
            elif input_oov_count == 0 and cand_oov_count == 0:
                vocab_boost = 1.0
            
            validity_factor = 1.0 if is_valid else 0.001
            
            fluency_score = 0.0
            if self.use_contextual and self.contextual:
                try:
                    fluency_score = self.contextual.calculate_sentence_score(cand)
                except Exception as e:
                    logger.warning(f"Scoring failed: {e}")
                    fluency_score = 0.5
            else:
                fluency_score = 1.0 
            
            dist = VocabularyManager.damerau_levenshtein_distance(preprocessed_text, cand)
            max_len = max(len(preprocessed_text), len(cand), 1)
            similarity = 1.0 - (dist / max_len)
            if cand == preprocessed_text:
                similarity = 1.0
            
            keyboard_bonus = 1.0
            input_words = preprocessed_text.split()
            cand_words = cand.split()
            if len(input_words) == len(cand_words):
                for iw, cw in zip(input_words, cand_words):
                    if iw != cw and len(iw) == len(cw):
                        for ic, cc in zip(iw, cw):
                            if ic != cc and RulesBasedCorrector.is_keyboard_neighbor(ic, cc):
                                keyboard_bonus *= 1.05
            
            if fluency_score > 0.85 and cand_oov_count == 0:
                 if not is_valid and reason in ["too_short", "low_character_similarity", "word_count_mismatch"]:
                      if len(cand) >= len(original) * 0.4:
                          is_valid = True
                          reason = "high_confidence_override"
                          vocab_boost *= 1.2
                          validity_factor = 1.0
            
            fluency_exp = 0.3
            similarity_exp = 3.0
            beam_boost = 1.0
            if raw_model_output and cand == raw_model_output:
                beam_boost = 1.15
            
            final_score = (fluency_score ** fluency_exp) * (similarity ** similarity_exp) * validity_factor * vocab_boost * keyboard_bonus * beam_boost
            
            candidate_scores.append({
                'text': cand, 'is_valid': is_valid, 'reason': reason,
                'fluency': fluency_score, 'similarity': similarity,
                'vocab_boost': vocab_boost, 'input_oov': input_oov_count,
                'cand_oov': cand_oov_count, 'final_score': final_score
            })
            
            if final_score > best_score:
                best_score = final_score
                best_candidate = cand
        
        # Output Quality Scoring
        if best_candidate != preprocessed_text:
            preprocessed_score = 0.0
            for cs in candidate_scores:
                if cs['text'] == preprocessed_text:
                    preprocessed_score = cs['final_score']
                    break
            if preprocessed_score > 0 and best_score < preprocessed_score * 1.05:
                best_oov = self.vocab_manager.count_oov_words(best_candidate)
                prep_oov = self.vocab_manager.count_oov_words(preprocessed_text)
                if best_oov > prep_oov:
                    best_candidate = preprocessed_text
                    best_score = preprocessed_score
        
        # Contextual Validation Layer
        if best_candidate != preprocessed_text and self.use_contextual and self.contextual:
            try:
                input_fluency = self.contextual.calculate_sentence_score(preprocessed_text)
                best_fluency = 0.0
                for cs in candidate_scores:
                    if cs['text'] == best_candidate:
                        best_fluency = cs['fluency']
                        break
                if input_fluency > 0 and best_fluency > 0:
                    if input_fluency > best_fluency * 1.5:
                        input_oov = self.vocab_manager.count_oov_words(preprocessed_text)
                        best_oov = self.vocab_manager.count_oov_words(best_candidate)
                        if input_oov <= best_oov:
                            best_candidate = preprocessed_text
            except Exception:
                pass
        
        # 5. Postprocess Winner
        result = self.postprocess(best_candidate, original)
        
        # IV-Safe Postprocessing Check
        if result != best_candidate:
            result_words = result.split()
            best_words = best_candidate.split()
            if len(result_words) == len(best_words):
                fixed_words = []
                for idx_fw, (rw, bw) in enumerate(zip(result_words, best_words)):
                    if rw != bw:
                        bw_iv = self.vocab_manager.is_iv(bw)
                        rw_iv = self.vocab_manager.is_iv(rw)
                        if bw_iv and not rw_iv:
                            fixed_words.append(bw)
                        else:
                            fixed_words.append(rw)
                    else:
                        fixed_words.append(rw)
                result = ' '.join(fixed_words)
        
        # 6. Contextual fine-tuning
        if self.use_contextual and self.contextual:
             if len(result) > 3:
                 result = self.contextual.refine_sentence_with_mask(
                     result, vocab_manager=self.vocab_manager,
                     raw_model_output=raw_model_output
                 )
        
        # 7. Safe Split/Merge Post-processing
        result = self.split_merge.merge_fragments(result)
        
        # 8. Output Stability Test
        if result != preprocessed_text and raw_model_output:
            try:
                re_preprocessed = self.preprocess(result)
                stability_dist = VocabularyManager.damerau_levenshtein_distance(result, re_preprocessed)
                result_len = max(len(result), 1)
                if stability_dist > 0:
                    stability_ratio = stability_dist / result_len
                    if stability_ratio > 0.15:
                        raw_re = self.preprocess(raw_model_output)
                        raw_stability = VocabularyManager.damerau_levenshtein_distance(
                            raw_model_output, raw_re
                        ) / max(len(raw_model_output), 1)
                        if raw_stability < stability_ratio:
                            raw_oov = self.vocab_manager.count_oov_words(raw_model_output)
                            our_oov = self.vocab_manager.count_oov_words(result)
                            if raw_oov <= our_oov:
                                result = raw_model_output
            except Exception:
                pass
        
        # 9. Bidirectional Word-Level Validation
        if raw_model_output and result != raw_model_output:
            result_words = result.split()
            raw_words = raw_model_output.split()
            if len(result_words) == len(raw_words):
                corrected_words = []
                changed = False
                for rw, raw_w in zip(result_words, raw_words):
                    if rw != raw_w:
                        rw_iv = self.vocab_manager.is_iv(rw)
                        raw_iv = self.vocab_manager.is_iv(raw_w)
                        if not rw_iv and raw_iv:
                            corrected_words.append(raw_w)
                            changed = True
                        elif rw_iv and raw_iv:
                            input_words_list = preprocessed_text.split()
                            idx = len(corrected_words)
                            if idx < len(input_words_list):
                                input_w = input_words_list[idx]
                                rw_dist = Levenshtein.distance(input_w, rw)
                                raw_dist = Levenshtein.distance(input_w, raw_w)
                                if raw_dist < rw_dist:
                                    corrected_words.append(raw_w)
                                    changed = True
                                else:
                                    corrected_words.append(rw)
                            else:
                                corrected_words.append(rw)
                        else:
                            corrected_words.append(rw)
                    else:
                        corrected_words.append(rw)
                if changed:
                    new_result = ' '.join(corrected_words)
                    new_oov = self.vocab_manager.count_oov_words(new_result)
                    old_oov = self.vocab_manager.count_oov_words(result)
                    if new_oov <= old_oov:
                        result = new_result
        
        # 10. SAFETY NET
        if raw_model_output and raw_model_output != result:
            raw_oov = self.vocab_manager.count_oov_words(raw_model_output)
            our_oov = self.vocab_manager.count_oov_words(result)
            if raw_oov == 0 and our_oov > 0:
                is_valid, reason = self.validator.validate(original, raw_model_output, "mixed")
                if is_valid or reason == "space_leniency_accept":
                    result = raw_model_output
            elif raw_oov == 0 and our_oov == 0:
                raw_dist = VocabularyManager.damerau_levenshtein_distance(original, raw_model_output)
                our_dist = VocabularyManager.damerau_levenshtein_distance(original, result)
                result_vs_raw_dist = VocabularyManager.damerau_levenshtein_distance(result, raw_model_output)
                if raw_dist < our_dist and result_vs_raw_dist <= 3:
                    raw_valid, _ = self.validator.validate(original, raw_model_output, "mixed")
                    if raw_valid:
                        result = raw_model_output
            elif raw_oov == 0:
                raw_wc = len(raw_model_output.split())
                our_wc = len(result.split())
                if raw_wc != our_wc:
                    raw_dist = VocabularyManager.damerau_levenshtein_distance(original, raw_model_output)
                    our_dist = VocabularyManager.damerau_levenshtein_distance(original, result)
                    if raw_dist < our_dist:
                        raw_valid, _ = self.validator.validate(original, raw_model_output, "mixed")
                        if raw_valid:
                            result = raw_model_output
        # ── FINAL PASS: Hamza whitelist + Ta Marbuta fixes (unrevertable) ──
        # These are applied AFTER all validation/safety steps so they can't
        # be undone by Steps 8-10 which compare against raw_model_output.
        # The root issue: Steps 8-10 use edit distance to INPUT (which has errors)
        # so they revert corrections back to the erroneous form.
        result = AraSpellPostProcessor.fix_common_hamza(result)
        result = AraSpellPostProcessor.fix_ha_ta_marbuta(result, vocab_manager=self.vocab_manager)

        # 11. DESTRUCTIVE TOKENIZATION GUARD
        # Arabic orthography does not use standalone 1-letter words except prepositions.
        # If the model creates a standalone 1-letter word that was not in the original,
        # check if it's a legitimate prefix separation (e.g. بالشاروع→ب الشارع).
        orig_standalone = set(w for w in original.split() if len(w) == 1)
        orig_words = original.split()
        res_words_list = result.split()
        for idx, w in enumerate(res_words_list):
            if len(w) == 1 and w not in orig_standalone:
                if w in 'واتيبلفك':
                    # Check if this is a legitimate prefix separation:
                    # The original word should have started with this letter as a prefix
                    is_prefix_separation = False
                    if w in 'وفبلك' and idx + 1 < len(res_words_list):
                        next_word = res_words_list[idx + 1]
                        combined = w + next_word
                        # If any original word started with the prefix letter and
                        # the remainder matches the next word, it's legitimate
                        for ow in orig_words:
                            if ow.startswith(w) and len(ow) > 2:
                                is_prefix_separation = True
                                break
                    
                    if not is_prefix_separation:
                        logger.info(f"[SPELLING] Blocked destructive tokenization (hallucinated standalone '{w}'): '{original}' -> '{result}'")
                        result = original
                        break

        # 12. MORPHOLOGICAL MUTATION GUARD (Verb -> Noun)
        # Prevents spelling from changing a plural verb (e.g. صممو) to a noun (e.g. مصممو) by prepending م
        if len(orig_words) == len(res_words_list):
            for idx in range(len(orig_words)):
                ow = orig_words[idx]
                rw = res_words_list[idx]
                # If the word didn't start with م but the correction does, and it looks like a plural verb
                if not ow.startswith('م') and rw.startswith('م') and rw[1:] == ow and ow.endswith('و'):
                    logger.info(f"[SPELLING] Blocked morphological mutation (verb→noun '{ow}'→'{rw}')")
                    res_words_list[idx] = ow
            result = ' '.join(res_words_list)

        return result

