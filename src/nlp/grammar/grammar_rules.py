# ArabicGrammarGuard — Rule-based Arabic grammar post-processing
# Extracted from Grammer_Rules.py — uses camel-tools for morphological analysis.
# All classes are imported by grammar_service.py.

import re
import logging
from camel_tools.tokenizers.word import simple_word_tokenize
from camel_tools.disambig.mle import MLEDisambiguator

logger = logging.getLogger(__name__)


class ArabicGrammarGuard:
    def __init__(self):
        self.mle = MLEDisambiguator.pretrained()

        self.number_words = ["واحد", "اثنان", "اثنين", "ثلاث", "أربع", "خمس", "ست", "سبع", "ثمان", "تسع", "عشر",
                             "عشرون", "عشرين", "ثلاثون", "ثلاثين", "أربعون", "أربعين", "خمسون", "خمسين",
                             "ستون", "ستين", "سبعون", "سبعين", "ثمانون", "ثمانين", "تسعون", "تسعين", "مائة", "ألف"]

        self.asmaa_khamsa_roots = ['اب', 'اخ', 'حم', 'فو', 'ذو']

    def preserve_numbers(self, original_text, generated_text):
        orig_digits = re.findall(r'\d+', original_text)
        gen_digits = re.findall(r'\d+', generated_text)
        if orig_digits and gen_digits and orig_digits != gen_digits:
            return original_text

        orig_words = [w for w in original_text.split() if any(num in w for num in self.number_words)]
        gen_words = [w for w in generated_text.split() if any(num in w for num in self.number_words)]
        if len(orig_words) > 0 and len(gen_words) > 0:
            if not any(orig[:3] in gen for orig in orig_words for gen in gen_words):
                 return original_text
        return generated_text

    def fix_number_and_gender_agreement(self, text):
        tokens = simple_word_tokenize(text)
        disambig_tokens = self.mle.disambiguate(tokens)
        corrected_tokens = list(tokens)

        for i in range(len(disambig_tokens) - 1):
            w1_info = disambig_tokens[i].analyses[0] if disambig_tokens[i].analyses else None
            w2_info = disambig_tokens[i+1].analyses[0] if disambig_tokens[i+1].analyses else None
            if not w1_info or not w2_info: continue

            w1_pos = w1_info.analysis.get('pos', 'unknown')
            w2_pos = w2_info.analysis.get('pos', 'unknown')
            w1_word = corrected_tokens[i]
            w2_word = corrected_tokens[i+1]

            if w1_pos == 'verb' and w2_pos == 'noun':
                if (w1_word.endswith('ون') or w1_word.endswith('وا')) and (w2_word.endswith('ون') or w2_word.endswith('ين')):
                    if w1_word.endswith('ون'): corrected_tokens[i] = w1_word[:-2]
                    elif w1_word.endswith('وا'): corrected_tokens[i] = w1_word[:-2]

            elif w1_pos == 'noun' and w2_pos == 'verb':
                if w1_word.endswith('ون') and not (w2_word.endswith('ون') or w2_word.endswith('وا') or w2_word.endswith('ين')):
                    if w2_info.analysis.get('num') == 's':
                        corrected_tokens[i+1] = w2_word + 'ون'

            # Match adjectives (adj) only; skip words starting with ب or ending with alef tanween
            elif w1_pos == 'noun' and w2_pos == 'adj':
                if w1_word.endswith('ون') and not w2_word.endswith('ون'):
                    if w2_info.analysis.get('num') == 's' and w2_info.analysis.get('gen') == 'm':
                        if len(w2_word) > 2 and not w2_word.endswith('ا') and not w2_word.startswith('ب'):
                            corrected_tokens[i+1] = w2_word + 'ون'

        return " ".join(corrected_tokens)

    def smart_asmaa_khamsa_fix(self, text):
        tokens = simple_word_tokenize(text)
        disambig_tokens = self.mle.disambiguate(tokens)
        corrected_tokens = []
        verb_seen = False

        for i, token_info in enumerate(disambig_tokens):
            word = tokens[i]

            pos_tag = token_info.analyses[0].analysis.get('pos', 'unknown') if token_info.analyses else 'unknown'

            if pos_tag == 'verb':
                verb_seen = True
                corrected_tokens.append(word)
                continue

            is_asmaa = any(word.startswith(root) or word.startswith('أ' + root[1:]) for root in self.asmaa_khamsa_roots if len(root)>1)

            if is_asmaa and len(word) >= 3:
                if verb_seen:
                    word = word.replace('ا', 'و').replace('ي', 'و')
                    verb_seen = False

            corrected_tokens.append(word)

        return " ".join(corrected_tokens)

    def fix_verbs_nasb_and_jazm(self, text):
        tokens = simple_word_tokenize(text)
        disambig_tokens = self.mle.disambiguate(tokens)

        nasb_particles = ['أن', 'لن', 'كي', 'لكي', 'حتى', 'إذن']
        jazm_particles = ['لم', 'لما', 'لا']

        corrected_tokens = []

        for i, token_info in enumerate(disambig_tokens):
            word = tokens[i]

            pos_tag = token_info.analyses[0].analysis.get('pos', 'unknown') if token_info.analyses else 'unknown'

            is_nasb_context = False
            is_jazm_context = False

            if i > 0:
                prev_word = tokens[i-1]
                if prev_word in nasb_particles or word.startswith('ل'):
                    is_nasb_context = True
                if prev_word in jazm_particles or word.startswith('ل') or word.startswith('ول'):
                    is_jazm_context = True

            if pos_tag == 'verb' and (is_nasb_context or is_jazm_context):
                if word.endswith('ون'):
                    word = word[:-2] + 'وا'
                elif word.endswith('ان'):
                    word = word[:-2] + 'ا'
                elif word.endswith('ين'):
                    word = word[:-2] + 'ي'
                elif is_jazm_context:
                    if word.endswith('و') and len(word) > 3:
                        word = word[:-1] + 'ُ'
                    elif (word.endswith('i') or word.endswith('ي')) and len(word) > 3:
                        if word.endswith('ي'): word = word[:-1] + 'ِ'
                    elif (word.endswith('ى') or word.endswith('ا')) and len(word) > 3:
                        word = word[:-1] + 'َ'

            corrected_tokens.append(word)
        return " ".join(corrected_tokens)

    def fix_gender_agreement(self, text):
        text = re.sub(r'\bهذان\s+(ال[أ-ي]+تان)\b', r'هاتان \1', text)
        text = re.sub(r'\bهاتان\s+(ال[أ-ي]+[^ت]ان)\b', r'هذان \1', text)
        text = re.sub(r'\bهذهن\b', 'هاتان', text)

        text = re.sub(r'\bأحد عشر\s+([أ-ي]+ة)\b', r'إحدى عشرة \1', text)
        text = re.sub(r'\bأحد عشرة\s+([أ-ي]+ة)\b', r'إحدى عشرة \1', text)

        text = re.sub(r'\bإحدى عشرة\s+([أ-ي]+ا|رجل[اأ]|طالب[اأ]|مهندس[اأ])\b', r'أحد عشر \1', text)
        text = re.sub(r'\bإحدى عشر\s+([أ-ي]+ا|رجل[اأ]|طالب[اأ]|مهندس[اأ])\b', r'أحد عشر \1', text)
        return text

    def fix_prepositions_advanced(self, text):
        # Allow conjunctions (و، ف) before prepositions
        # (في المهندسون) -> (في المهندسين)
        # Require stem >= 4 chars to avoid matching root-level ان endings (الامتحان, الإنسان, etc.)
        text = re.sub(r'\b([وف]?(?:في|من|إلى|على|عن|حتى))\s+([أ-ي]{4,})(ون|ان)\b', r'\1 \2ين', text)

        # (وبالمبرمجون) -> (وبالمبرمجين)
        text = re.sub(r'\b([وف]?[بلكف])ال([أ-ي]{4,})(ون|ان)\b', r'\1ال\2ين', text)

        # (ولمهندسون) -> (ولمهندسين)
        text = re.sub(r'\b([وف]?ل)([أ-ي]{4,})(ون|ان)\b', r'\1\2ين', text)
        return text

    def fix_subject_verb_agreement(self, text):
        """
        Fix G1: When a plural/dual noun PRECEDES a singular verb (SVO order),
        the verb must agree in number and gender.

        Arabic rule: In VSO order, verb can be singular even with plural subject.
        But in SVO order, subject-verb agreement is required.
        """
        tokens = simple_word_tokenize(text)
        if len(tokens) < 2:
            return text
        disambig_tokens = self.mle.disambiguate(tokens)
        corrected_tokens = list(tokens)

        # Common plural nouns (masculine sound plural) ending in ون/ين/ات
        # and their expected verb conjugation patterns
        for i in range(len(disambig_tokens) - 1):
            noun_info = disambig_tokens[i].analyses[0] if disambig_tokens[i].analyses else None
            verb_info = disambig_tokens[i+1].analyses[0] if disambig_tokens[i+1].analyses else None
            if not noun_info or not verb_info:
                continue

            noun_pos = noun_info.analysis.get('pos', 'unknown')
            verb_pos = verb_info.analysis.get('pos', 'unknown')
            noun_word = corrected_tokens[i]
            verb_word = corrected_tokens[i+1]

            # Only process noun → verb patterns (SVO order)
            if noun_pos != 'noun' or verb_pos != 'verb':
                continue

            noun_num = noun_info.analysis.get('num', 's')
            noun_gen = noun_info.analysis.get('gen', 'm')
            verb_num = verb_info.analysis.get('num', 's')

            # Skip if verb is already plural
            if verb_num != 's':
                continue

            # Detect plural nouns
            is_plural_masc = (noun_word.endswith('ون') or noun_word.endswith('ين')
                             or noun_num == 'p')
            is_plural_fem = (noun_word.endswith('ات') or
                            (noun_gen == 'f' and noun_num == 'p'))
            # Common broken plurals and collective nouns
            KNOWN_PLURALS_MASC = {
                'الطلاب', 'طلاب', 'الرجال', 'رجال', 'الأولاد', 'أولاد',
                'الأطباء', 'أطباء', 'الاطباء', 'اطباء',
                'العمال', 'عمال', 'الناس', 'الشباب', 'الأبناء',
            }
            KNOWN_PLURALS_FEM = {
                'الطالبات', 'طالبات', 'النساء', 'نساء', 'البنات', 'بنات',
                'المعلمات', 'معلمات', 'الأمهات', 'أمهات',
            }
            if noun_word in KNOWN_PLURALS_MASC:
                is_plural_masc = True
            if noun_word in KNOWN_PLURALS_FEM:
                is_plural_fem = True

            if not is_plural_masc and not is_plural_fem:
                continue

            # Fix the verb to agree with the plural subject
            # Past tense singular → plural
            if is_plural_fem:
                # Feminine plural: ذهب → ذهبن
                if not verb_word.endswith('ن') and not verb_word.endswith('نَ'):
                    # Check if it's a past tense verb (typically 3-5 chars, no prefix)
                    if len(verb_word) >= 3 and not verb_word.startswith('ي') and not verb_word.startswith('ت'):
                        corrected_tokens[i+1] = verb_word + 'ن'
            elif is_plural_masc:
                # Masculine plural: ذهب → ذهبوا
                if (not verb_word.endswith('وا') and not verb_word.endswith('ون')
                        and not verb_word.endswith('ين')):
                    if len(verb_word) >= 3 and not verb_word.startswith('ي') and not verb_word.startswith('ت'):
                        corrected_tokens[i+1] = verb_word + 'وا'

        return " ".join(corrected_tokens)

    def regex_rules_fallback(self, text):
        # إن وأخواتها
        text = re.sub(r'\b(إن|أن|كأن|لكن|لعل|ليت)\s+(أبوك|أخوك|ذو|فوك)\b',
                      lambda m: f"{m.group(1)} {m.group(2).replace('و', 'ا')}", text)

        # حروف الجر المنفصلة بمسافة (في أخوك -> في أخيك)
        text = re.sub(r'\b([وف]?(?:في|من|إلى|على|عن))\s+(أبوك|أباك|أخوك|أخاك|ذو|ذا)\b',
                      lambda m: f"{m.group(1)} {m.group(2).replace('و', 'ي').replace('ا', 'ي')}", text)

        # حروف الجر المتصلة بدون مسافة (بأخوك، لأبوك -> بأخيك، لأبيك)
        text = re.sub(r'\b([وف]?[بل])(أبوك|أباك|أخوك|أخاك|ذو|ذا)\b',
                      lambda m: f"{m.group(1)}{m.group(2).replace('و', 'ي').replace('ا', 'ي')}", text)
        return text

    def process(self, original_text, generated_text):
        """Apply all grammar rules to model output."""
        text = self.preserve_numbers(original_text, generated_text)
        text = self.fix_number_and_gender_agreement(text)
        text = self.smart_asmaa_khamsa_fix(text)
        text = self.fix_verbs_nasb_and_jazm(text)
        text = self.fix_gender_agreement(text)
        text = self.fix_prepositions_advanced(text)
        text = self.fix_subject_verb_agreement(text)  # Fix G1
        text = self.regex_rules_fallback(text)
        text = re.sub(r'\s+', ' ', text).strip()
        return text

