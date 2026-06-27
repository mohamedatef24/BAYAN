# ArabicGrammarGuard — Rule-based Arabic grammar post-processing
# Extracted from Grammer_Rules.py — uses camel-tools for morphological analysis.
# All classes are imported by grammar_service.py.

import re
import logging
from camel_tools.tokenizers.word import simple_word_tokenize
from camel_tools.disambig.mle import MLEDisambiguator

logger = logging.getLogger(__name__)

KNOWN_FEMININE_NOUNS = {
    'السيارة', 'سيارة', 'المدرسة', 'مدرسة', 'المدينة', 'مدينة',
    'البنت', 'الشمس', 'الأرض', 'الطالبة', 'طالبة',
    'الجامعة', 'جامعة', 'الشركة', 'شركة', 'الحكومة', 'حكومة',
    'الغرفة', 'غرفة', 'الحديقة', 'حديقة', 'المكتبة', 'مكتبة',
    'الدولة', 'دولة', 'الرحلة', 'رحلة', 'اللغة', 'لغة',
    'القصة', 'قصة', 'الفكرة', 'فكرة', 'النتيجة', 'نتيجة',
}

# Common adjectives that have masculine/feminine pairs
MASC_TO_FEM_ADJ = {
    'جميل': 'جميلة', 'كبير': 'كبيرة', 'صغير': 'صغيرة',
    'طويل': 'طويلة', 'قصير': 'قصيرة', 'جديد': 'جديدة',
    'قديم': 'قديمة', 'بعيد': 'بعيدة', 'قريب': 'قريبة',
    'سريع': 'سريعة', 'بطيء': 'بطيئة', 'واسع': 'واسعة',
    'ضيق': 'ضيقة', 'عميق': 'عميقة', 'خفيف': 'خفيفة',
    'ثقيل': 'ثقيلة', 'نظيف': 'نظيفة', 'مشرق': 'مشرقة',
    'ذكي': 'ذكية', 'غني': 'غنية', 'فقير': 'فقيرة',
    'متفوق': 'متفوقة', 'مجتهد': 'مجتهدة', 'ممتاز': 'ممتازة',
}


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

    def _apply_jazm_to_verb(self, word, token_info):
        # 1. Handle Af'al Khamsa using camel_tools analysis
        if token_info and token_info.analyses:
            analysis = token_info.analyses[0].analysis
            num = analysis.get('num', 's')
            per = analysis.get('per', '3')
            gen = analysis.get('gen', 'm')
            
            if num == 'p' and gen == 'm':
                if word.endswith('ون'):
                    return word[:-2] + 'وا'
            elif num == 'd':
                if word.endswith('ان'):
                    return word[:-2] + 'ا'
            elif num == 's' and per == '2' and gen == 'f':
                if word.endswith('ين'):
                    return word[:-2] + 'ي'

        # 2. Handle defective verbs in jazm context
        match = re.search(r'^(.*?)([يوىاَُِْ]?)$', word)
        if match:
            stem = match.group(1)
            ending = match.group(2)

            fatha_bases = ['سع', 'خش', 'رض', 'نس', 'بق', 'ر', 'نه', 'حظ', 'رع', 'أب', 'تمن', 'لق', 'هو', 'سل']
            damma_bases = ['دع', 'رج', 'شك', 'نم', 'غز', 'عف', 'سم', 'دن', 'بد', 'خل', 'عل']
            kasra_bases = ['مش', 'جر', 'قض', 'بك', 'هد', 'رم', 'أت', 'بن', 'ق', 'وف', 'شف', 'غن', 'عط', 'تق', 'شتر', 'عتن', 'ستدع', 'نته', 'رو']

            fatha_stems = {p + b for p in ['ي', 'ت', 'أ', 'ن'] for b in fatha_bases}
            damma_stems = {p + b for p in ['ي', 'ت', 'أ', 'ن'] for b in damma_bases}
            kasra_stems = {p + b for p in ['ي', 'ت', 'أ', 'ن'] for b in kasra_bases}

            if stem in fatha_stems:
                return stem + 'َ'
            elif stem in damma_stems:
                return stem + 'ُ'
            elif stem in kasra_stems:
                return stem + 'ِ'
            elif ending == 'و' and len(stem) >= 2:
                return stem + 'ُ'
            elif ending == 'ي' and len(stem) >= 2:
                return stem + 'ِ'
            elif (ending == 'ى' or ending == 'ا') and len(stem) >= 2:
                if not word.endswith('وا'):
                    return stem + 'َ'

        return word

    def _apply_nasb_to_verb(self, word, token_info):
        # 1. Handle Af'al Khamsa using camel_tools analysis
        if token_info and token_info.analyses:
            analysis = token_info.analyses[0].analysis
            num = analysis.get('num', 's')
            per = analysis.get('per', '3')
            gen = analysis.get('gen', 'm')
            
            if num == 'p' and gen == 'm':
                if word.endswith('ون'):
                    return word[:-2] + 'وا'
            elif num == 'd':
                if word.endswith('ان'):
                    return word[:-2] + 'ا'
            elif num == 's' and per == '2' and gen == 'f':
                if word.endswith('ين'):
                    return word[:-2] + 'ي'

        # 2. Handle defective verbs in nasb
        if word.endswith('و') and len(word) > 3:
            return word + 'َ'
        elif word.endswith('ي') and len(word) > 3:
            return word + 'َ'
            
        return word

    def fix_verbs_nasb_and_jazm(self, text):
        tokens = simple_word_tokenize(text)
        disambig_tokens = self.mle.disambiguate(tokens)

        nasb_particles = ['أن', 'ان', 'لن', 'كي', 'لكي', 'حتى', 'حتي', 'إذن', 'اذا']
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

            is_present_tense = word.startswith('ي') or word.startswith('ت') or word.startswith('ن') or word.startswith('أ')
            if (pos_tag == 'verb' or is_present_tense) and (is_nasb_context or is_jazm_context):
                if is_jazm_context:
                    word = self._apply_jazm_to_verb(word, token_info)
                elif is_nasb_context:
                    word = self._apply_nasb_to_verb(word, token_info)

            corrected_tokens.append(word)
        return " ".join(corrected_tokens)

    def fix_gender_agreement(self, text):

        text = re.sub(r'\bأحد عشر\s+([أ-ي]+ة)\b', r'إحدى عشرة \1', text)
        text = re.sub(r'\bأحد عشرة\s+([أ-ي]+ة)\b', r'إحدى عشرة \1', text)

        text = re.sub(r'\bإحدى عشرة\s+([أ-ي]+ا|رجل[اأ]|طالب[اأ]|مهندس[اأ])\b', r'أحد عشر \1', text)
        text = re.sub(r'\bإحدى عشر\s+([أ-ي]+ا|رجل[اأ]|طالب[اأ]|مهندس[اأ])\b', r'أحد عشر \1', text)

        # ── Batch 6: Noun-adjective gender agreement ──
        # When a feminine noun is followed by a masculine adjective, add ة
        # e.g. السيارة جميل → السيارة جميلة
        words = text.split()
        for i in range(len(words) - 1):
            noun = words[i]
            adj = words[i + 1]
            is_fem_noun = (noun in KNOWN_FEMININE_NOUNS or
                          (noun.endswith('ة') and len(noun) >= 3) or
                          (noun.startswith('ال') and noun.endswith('ة')))
            if is_fem_noun and adj in MASC_TO_FEM_ADJ:
                words[i + 1] = MASC_TO_FEM_ADJ[adj]
        text = ' '.join(words)

        return text

    # FIX-33: Words ending in ان that are root-form nouns, NOT duals/plurals.
    # These must never have ان→ين replacement.
    _PREP_BLOCKLIST = {
        'الامتحان', 'امتحان', 'الإنسان', 'إنسان', 'انسان', 'الانسان',
        'الميدان', 'ميدان', 'البرلمان', 'برلمان', 'السلطان', 'سلطان',
        'العنوان', 'عنوان', 'الديوان', 'ديوان', 'البستان', 'بستان',
        'البنيان', 'بنيان', 'الإيمان', 'إيمان', 'ايمان', 'الايمان',
        'الأمان', 'أمان', 'امان', 'الامان', 'العدوان', 'عدوان',
        'البيان', 'بيان', 'البرهان', 'برهان', 'الشيطان', 'شيطان',
        'الأذان', 'أذان', 'السودان', 'لبنان', 'عمان', 'الأردن',
        'الحيوان', 'حيوان', 'القرآن', 'قرآن', 'الدخان', 'دخان',
        'المكان', 'مكان', 'الزمان', 'زمان', 'الجدران', 'جدران',
        'النيران', 'نيران', 'الألوان', 'ألوان', 'البلدان', 'بلدان',
        'الأوطان', 'أوطان', 'الأبدان', 'أبدان', 'الأركان', 'أركان',
        'الفرسان', 'فرسان', 'الغزلان', 'غزلان', 'القضبان', 'قضبان',
    }

    def fix_prepositions_advanced(self, text):
        # Allow conjunctions (و، ف) before prepositions
        # (في المهندسون) -> (في المهندسين)
        # FIX-33: Use callback to skip root-form nouns ending in ان
        def _prep_replace(m):
            prep = m.group(1)
            stem = m.group(2)
            suffix = m.group(3)
            full_word = stem + suffix
            # Skip words in blocklist (root nouns, not duals)
            if full_word in self._PREP_BLOCKLIST:
                return m.group(0)  # return unchanged
            # Skip ال-prefixed words ending in ان — almost always root nouns
            if stem.startswith('ال') and suffix == 'ان':
                return m.group(0)  # return unchanged
            return f'{prep} {stem}ين'

        text = re.sub(r'\b([وف]?(?:في|من|إلى|على|عن|حتى))\s+([أ-ي]{4,})(ون|ان)\b', _prep_replace, text)

        # (وبالمبرمجون) -> (وبالمبرمجين)
        # FIX-33b: Same blocklist protection as first regex
        def _attached_prep_replace(m):
            prefix = m.group(1)  # وب، ب، فب، ول، ل، etc.
            stem = m.group(2)
            suffix = m.group(3)
            full_word = 'ال' + stem + suffix  # reconstruct with ال for blocklist check
            if full_word in self._PREP_BLOCKLIST:
                return m.group(0)
            # Words ending in ان with 4+ char stems are almost always root nouns
            if suffix == 'ان':
                return m.group(0)
            return f'{prefix}ال{stem}ين'

        text = re.sub(r'\b([وف]?[بلكف])ال([أ-ي]{4,})(ون|ان)\b', _attached_prep_replace, text)

        # (ولمهندسون) -> (ولمهندسين)
        # FIX-33b: Same protection — reconstruct full word for blocklist
        def _lam_prep_replace(m):
            prefix = m.group(1)  # ول، ل، فل
            stem = m.group(2)
            suffix = m.group(3)
            # Check blocklist with common prefixed forms
            if (stem + suffix) in self._PREP_BLOCKLIST:
                return m.group(0)
            if suffix == 'ان':
                return m.group(0)
            return f'{prefix}{stem}ين'

        text = re.sub(r'\b([وف]?ل)([أ-ي]{4,})(ون|ان)\b', _lam_prep_replace, text)
        return text

    def fix_kana_and_inna(self, text):
        """
        Fix cases (Nominative/Accusative) of nouns after Inna and Kana sisters.
        """
        tokens = simple_word_tokenize(text)
        disambig_tokens = self.mle.disambiguate(tokens)
        corrected_tokens = list(tokens)
        
        INNA_SISTERS = {'إن', 'أن', 'كأن', 'لكن', 'ليت', 'لعل', 'ان'}
        KANA_SISTERS = {'كان', 'أصبح', 'اصبح', 'أضحى', 'اضحى', 'ظل', 'أمسى', 'امسى', 'بات', 'صار', 'ليس'}
        
        def get_corrected_case(word, target_case, num):
            if target_case == 'a': # Mansoub
                if word == 'أبو': return 'أبا'
                if word == 'أخو': return 'أخا'
                if word == 'ذو': return 'ذا'
                if word == 'فو': return 'فا'
                if word == 'حمو': return 'حما'
                if word.endswith('ون'): return word[:-2] + 'ين'
                if word.endswith('ان'): return word[:-2] + 'ين'
            elif target_case == 'n': # Marfoo'
                if word in ('أبا', 'أبي'): return 'أبو'
                if word in ('أخا', 'أخي'): return 'أخو'
                if word in ('ذا', 'ذي'): return 'ذو'
                if word in ('فا', 'في'): return 'فو'
                if word in ('حما', 'حمي'): return 'حمو'
                if word.endswith('ين'):
                    if num == 'p': return word[:-2] + 'ون'
                    elif num == 'd': return word[:-2] + 'ان'
            return word

        state = None # 'inna' or 'kana'
        noun_count = 0
        subject_num = 's'
        
        for i, t in enumerate(disambig_tokens):
            word = corrected_tokens[i]
            
            if word in INNA_SISTERS:
                state = 'inna'
                noun_count = 0
                continue
            elif word in KANA_SISTERS:
                state = 'kana'
                noun_count = 0
                continue
                
            if state and t.analyses:
                analysis = t.analyses[0].analysis
                pos = analysis.get('pos')
                
                # Check for nouns/adjectives
                if pos in ('noun', 'adj', 'noun_prop'):
                    num = analysis.get('num', 's')
                    noun_count += 1
                    
                    new_word = word
                    if state == 'inna':
                        if noun_count == 1:
                            subject_num = num
                            new_word = get_corrected_case(word, 'a', num) # اسم إن منصوب
                        elif noun_count == 2:
                            new_word = get_corrected_case(word, 'n', subject_num) # خبر إن مرفوع
                            state = None
                    elif state == 'kana':
                        if noun_count == 1:
                            subject_num = num
                            new_word = get_corrected_case(word, 'n', num) # اسم كان مرفوع
                        elif noun_count == 2:
                            new_word = get_corrected_case(word, 'a', subject_num) # خبر كان منصوب
                            state = None
                            
                    if new_word != word:
                        pattern = r'(?<![أ-يa-zA-Z])' + re.escape(word) + r'(?![أ-يa-zA-Z])'
                        text = re.sub(pattern, new_word, text, count=1)
                        corrected_tokens[i] = new_word
                        
                elif pos == 'verb':
                    # Verb encountered, predicate might be a verbal sentence, reset to avoid false positives
                    state = None
            
            # Reset state on punctuation
            if word in {'.', '،', ':', '؟', '!', '؛'}:
                state = None
                
        return text

    def fix_subject_verb_agreement(self, text):
        """
        Fix G1: When a CONFIRMED plural noun PRECEDES a singular verb (SVO order),
        the verb must agree in number and gender.

        Arabic rule: In VSO order, verb can be singular even with plural subject.
        But in SVO order, subject-verb agreement is required.

        EXCLUSIONS:
        - Pronouns (أنا, أنت, هو, etc.) — these are NOT plural
        - Proper nouns — don't modify verbs after names
        - Words tagged as singular by the disambiguator
        """
        tokens = simple_word_tokenize(text)
        if len(tokens) < 2:
            return text
        disambig_tokens = self.mle.disambiguate(tokens)
        corrected_tokens = list(tokens)

        # Words that should NEVER trigger plural verb agreement
        EXCLUDED_WORDS = {
            # Pronouns (all singular/dual)
            'أنا', 'انا', 'أنت', 'انت', 'أنتِ', 'هو', 'هي',
            'نحن', 'أنتما', 'هما',
            # Common words that look like nouns but aren't plural
            'كان', 'وكان', 'كانت', 'وكانت', 'ليس', 'ليست',
            'هذا', 'هذه', 'ذلك', 'تلك', 'هناك',
        }

        for i in range(len(disambig_tokens) - 1):
            noun_info = disambig_tokens[i].analyses[0] if disambig_tokens[i].analyses else None
            verb_info = disambig_tokens[i+1].analyses[0] if disambig_tokens[i+1].analyses else None
            if not noun_info or not verb_info:
                continue

            noun_pos = noun_info.analysis.get('pos', 'unknown')
            verb_pos = verb_info.analysis.get('pos', 'unknown')
            noun_word = corrected_tokens[i]
            verb_word = corrected_tokens[i+1]

            # Skip excluded words
            if noun_word in EXCLUDED_WORDS:
                continue

            # Known verbs that are frequently mistagged as nouns by the tagger without diacritics
            KNOWN_VERBS = {'بنى', 'طبخ', 'صمم', 'لعب', 'كتب', 'شرح', 'حضر', 'تدرب', 'وافق', 'أصدر', 'اصدر', 'بني', 'عمل'}

            # Only process noun → verb patterns (SVO order)
            if noun_pos != 'noun' or (verb_pos != 'verb' and verb_word not in KNOWN_VERBS):
                continue

            noun_num = noun_info.analysis.get('num', 's')
            noun_gen = noun_info.analysis.get('gen', 'm')
            verb_num = verb_info.analysis.get('num', 's')

            # Skip if verb is already plural
            # Removed singular verb check to allow fixing gender mismatch on already plural verbs (e.g. البنات يذهبون -> يذهبن)
            
            # Only trigger on CONFIRMED plurals:
            # 1. Known broken plural nouns (hardcoded list)
            # 2. Sound masculine plural ending in ون/ين
            # 3. Sound feminine plural ending in ات
            # Do NOT rely on POS tagger alone — it misclassifies too many words

            is_plural_masc = False
            is_plural_fem = False

            KNOWN_PLURALS_MASC = {
                'الطلاب', 'طلاب', 'الرجال', 'رجال', 'الأولاد', 'أولاد',
                'الأطباء', 'أطباء', 'الاطباء', 'اطباء',
                'العمال', 'عمال', 'الشباب', 'الأبناء',
                'المهندسون', 'المعلمون', 'المهندسين', 'المعلمين',
                # FIX-08: Expanded plural lists
                'اللاعبون', 'اللاعبين', 'لاعبون', 'لاعبين',
                'المسلمون', 'المسلمين', 'مسلمون', 'مسلمين',
                'العرب', 'الناس', 'الأطفال', 'أطفال', 'اطفال',
                'الأصدقاء', 'أصدقاء', 'اصدقاء',
                'العلماء', 'علماء', 'الأعداء', 'أعداء',
                'الوزراء', 'وزراء', 'الأمراء', 'أمراء',
                'الكتّاب', 'كتّاب', 'الأدباء', 'أدباء',
                'السكان', 'سكان', 'الجنود', 'جنود',
                'الأساتذة', 'أساتذة', 'التلاميذ', 'تلاميذ',
                'المواطنون', 'المواطنين', 'المسؤولون', 'المسؤولين',
                'الطلبة', 'طلبة', 'الأقارب', 'أقارب',
            }
            KNOWN_PLURALS_FEM = {
                'الطالبات', 'طالبات', 'النساء', 'نساء', 'البنات', 'بنات',
                'المعلمات', 'معلمات', 'الأمهات', 'أمهات',
                # FIX-08: Expanded feminine plurals
                'المهندسات', 'مهندسات', 'الطبيبات', 'طبيبات',
                'اللاعبات', 'لاعبات', 'الممثلات', 'ممثلات',
                'الشركات', 'شركات', 'الجامعات', 'جامعات',
                'المدارس', 'مدارس', 'المستشفيات', 'مستشفيات',
                'الحكومات', 'حكومات', 'المنظمات', 'منظمات',
                'الطائرات', 'طائرات', 'السيارات', 'سيارات',
            }

            if noun_word in KNOWN_PLURALS_MASC:
                is_plural_masc = True
            elif noun_word in KNOWN_PLURALS_FEM:
                is_plural_fem = True
            elif noun_word.endswith('ون') or noun_word.endswith('ين'):
                # Sound masculine plural — but only if 4+ chars (avoid short words)
                if len(noun_word) >= 5:
                    is_plural_masc = True
            elif noun_word.endswith('ات') and len(noun_word) >= 5:
                is_plural_fem = True
            # FIX-08: Broken plural heuristic — common patterns
            elif noun_num == 'p':
                # Trust POS tagger when it says plural AND word is long enough
                if len(noun_word) >= 4:
                    if noun_gen == 'f':
                        is_plural_fem = True
                    else:
                        is_plural_masc = True
            
            is_singular_fem = False
            if not is_plural_masc and not is_plural_fem:
                if noun_gen == 'f' or noun_word.endswith('ة') or noun_word in KNOWN_FEMININE_NOUNS:
                    is_singular_fem = True
                else:
                    continue

            # Fix the verb to agree with the plural subject
            # Detect if verb is present tense (starts with ي/ت/ن/أ)
            _is_present = (verb_word.startswith('ي') or verb_word.startswith('ت')
                          or verb_word.startswith('ن') or verb_word.startswith('أ'))

            if _is_present:
                # Present tense: يذهب→يذهبون (masc) / يذهبن (fem)
                if is_plural_fem:
                    if verb_word.endswith('ون') or verb_word.endswith('ين'):
                        verb_word = verb_word[:-2]
                    if not verb_word.endswith('ن') and not verb_word.endswith('نَ'):
                        corrected_tokens[i+1] = verb_word + 'ن'
                elif is_plural_masc:
                    if verb_word.endswith('ن') and not verb_word.endswith('ون') and not verb_word.endswith('ين'):
                        verb_word = verb_word[:-1]
                    if (not verb_word.endswith('ون') and not verb_word.endswith('وا')
                            and not verb_word.endswith('ين')):
                        if verb_word.endswith('وَ'):
                            verb_word = verb_word[:-1]
                        corrected_tokens[i+1] = verb_word + 'ون'
                elif is_singular_fem:
                    if verb_word.startswith('ي'):
                        corrected_tokens[i+1] = 'ت' + verb_word[1:]
            else:
                # Past tense: ذهب→ذهبوا (masc) / ذهبن (fem)
                if is_plural_fem:
                    if verb_word.endswith('وا') or verb_word.endswith('ون'):
                        verb_word = verb_word[:-2]
                    elif verb_word.endswith('ت') or verb_word.endswith('تْ') or verb_word.endswith('تَ') or verb_word.endswith('و'):
                        verb_word = verb_word[:-1]
                    if not verb_word.endswith('ن') and not verb_word.endswith('نَ'):
                        if verb_word.endswith('ى') or verb_word.endswith('ا'):
                            verb_word = verb_word[:-1]
                        corrected_tokens[i+1] = verb_word + 'ن'
                elif is_plural_masc:
                    if verb_word.endswith('ت') or verb_word.endswith('تْ') or verb_word.endswith('تَ'):
                        verb_word = verb_word[:-1]
                    if verb_word.endswith('ن') and not verb_word.endswith('ون') and not verb_word.endswith('ين'):
                        verb_word = verb_word[:-1]
                    if (not verb_word.endswith('وا') and not verb_word.endswith('ون')
                            and not verb_word.endswith('ين')):
                        if verb_word.endswith('وَ'):
                            verb_word = verb_word[:-1]
                        elif verb_word.endswith('ى') or verb_word.endswith('ا'):
                            verb_word = verb_word[:-1]
                        corrected_tokens[i+1] = verb_word + 'وا'
                elif is_singular_fem:
                    if not verb_word.endswith('ت') and not verb_word.endswith('تْ') and not verb_word.endswith('تَ'):
                        if verb_word.endswith('ى'):
                            verb_word = verb_word[:-1] + 'ا'
                        corrected_tokens[i+1] = verb_word + 'ت'

        return " ".join(corrected_tokens)

    def regex_rules_fallback(self, text):
        def _add_hamza(word):
            if word.startswith('ا') and not word.startswith('ال'):
                return 'أ' + word[1:]
            return word

        # إن وأخواتها
        text = re.sub(r'\b(إن|أن|كأن|لكن|لعل|ليت|ان|كان)\s+(أبوك|ابوك|أخوك|اخوك|ذو|فوك)\b',
                      lambda m: f"{m.group(1)} {_add_hamza(m.group(2)).replace('و', 'ا')}", text)

        # الأفعال المتعدية (Object position)
        text = re.sub(r'\b(رأيت|شاهدت|قابلت|زرت|سمعت|عرفت|وجدت|أحب|أكرمت|صادفت)\s+(أبوك|ابوك|أخوك|اخوك|ذو|فوك)\b',
                      lambda m: f"{m.group(1)} {_add_hamza(m.group(2)).replace('و', 'ا')}", text)

        # حروف الجر المنفصلة بمسافة (في أخوك -> في أخيك)
        text = re.sub(r'\b([وف]?(?:في|من|إلى|الي|على|علي|عن))\s+(أبوك|ابوك|أباك|اباك|أخوك|اخوك|أخاك|اخاك|ذو|ذا)\b',
                      lambda m: f"{m.group(1)} {_add_hamza(m.group(2)).replace('و', 'ي').replace('ا', 'ي')}", text)

        # حروف الجر المتصلة بدون مسافة (بأخوك، لأبوك -> بأخيك، لأبيك)
        text = re.sub(r'\b([وف]?[بل])(أبوك|ابوك|أباك|اباك|أخوك|اخوك|أخاك|اخاك|ذو|ذا)\b',
                      lambda m: f"{m.group(1)}{m.group(2).replace('و', 'ي').replace('ا', 'ي')}", text)

        # NOTE: Broad preposition case (ون→ين) and nasb (ون→وا) regex rules
        # were REMOVED because they caused massive overcorrection on correct text.
        # These patterns are handled by CamelTools-based rules (fix_prepositions_advanced,
        # fix_verbs_nasb_and_jazm) which have POS-tag awareness.
        
        # FIX-PC010: Add targeted safe regex for Nasb/Jazm particles + verb
        # Only match clear present tense verbs starting with ي/ت/ن/أ and ending in ون
        text = re.sub(r'\b(أن|ان|لن|كي|حتى|لم|لما)\s+([يتا][\u0600-\u06FF]{2,})ون\b',
                      r'\1 \2وا', text)

        return text

    def fix_conditional_sentences(self, text):
        conditional_particles = {'إن', 'ان', 'من', 'ما', 'متى', 'متي', 'مهما', 'أينما', 'حيثما', 'أيان', 'ايان', 'كيفما', 'أنى', 'اني'}
        tokens = simple_word_tokenize(text)
        disambig_tokens = self.mle.disambiguate(tokens)
        corrected_tokens = list(tokens)
        
        # Lookahead for 2nd person context
        has_2nd_person_context = any(t.endswith('كم') or t.endswith('كمو') or t.startswith('ت') for t in tokens)
        
        in_cond = False
        verbs_jazmed = 0
        
        for i, token_info in enumerate(disambig_tokens):
            word = corrected_tokens[i]
            pos_tag = token_info.analyses[0].analysis.get('pos', 'unknown') if token_info.analyses else 'unknown'
            
            if word in conditional_particles:
                # To prevent overcorrection (e.g. 'إن الأطباء' treating 'إن' as conditional),
                # ensure the immediately following word is a verb.
                next_pos = 'unknown'
                if i + 1 < len(disambig_tokens):
                    if disambig_tokens[i+1].analyses:
                        next_pos = disambig_tokens[i+1].analyses[0].analysis.get('pos', 'unknown')
                
                if next_pos == 'verb':
                    in_cond = True
                    verbs_jazmed = 0
                continue
                
            if in_cond and pos_tag == 'verb':
                # Apply jazm using the comprehensive camel_tools helper
                word = self._apply_jazm_to_verb(word, token_info)
                    
                # Fix pronoun mismatch if 2nd person context exists
                if has_2nd_person_context and word.startswith('ي') and (word.endswith('وا') or word.endswith('ا') or word.endswith('ي')):
                    word = 'ت' + word[1:]
                    
                corrected_tokens[i] = word
                # Increment jazmed verbs counter (handles both فعل الشرط and جواب الشرط)
                verbs_jazmed += 1
                if verbs_jazmed >= 2:
                    in_cond = False
                    
        return " ".join(corrected_tokens)

    def fix_demonstrative_agreement(self, text):
        tokens = simple_word_tokenize(text)
        disambig_tokens = self.mle.disambiguate(tokens)
        corrected_tokens = list(tokens)
        
        for i in range(len(disambig_tokens) - 1):
            w1 = corrected_tokens[i]
            w2 = corrected_tokens[i+1]
            
            if w1 not in ['هذا', 'هذه', 'هذان', 'هاتان', 'هذين', 'هاتين', 'هؤلاء']:
                continue
                
            w2_info = disambig_tokens[i+1].analyses[0].analysis if disambig_tokens[i+1].analyses else {}
            w2_num = w2_info.get('num', 's')
            w2_gen = w2_info.get('gen', 'm')
            
            # Use heuristics to override or reinforce POS tags for duals
            if w2.endswith('تان') or w2.endswith('تين'):
                if w2_num == 'd':
                    w2_gen = 'f'
            
            if w2_num == 'd':
                is_nom = w2.endswith('ان') or w2.endswith('تان')
                if w2_gen == 'f':
                    corrected_tokens[i] = 'هاتان' if is_nom else 'هاتين'
                elif w2_gen == 'm':
                    corrected_tokens[i] = 'هذان' if is_nom else 'هذين'
                    
        return " ".join(corrected_tokens)

    def fix_noun_adjective_agreement_advanced(self, text):
        tokens = simple_word_tokenize(text)
        disambig_tokens = self.mle.disambiguate(tokens)
        corrected_tokens = list(tokens)
        
        for i in range(len(disambig_tokens) - 1):
            w1 = corrected_tokens[i]
            w2 = corrected_tokens[i+1]
            
            w1_info = disambig_tokens[i].analyses[0].analysis if disambig_tokens[i].analyses else {}
            w1_pos = w1_info.get('pos', 'unknown')
            w1_num = w1_info.get('num', 's')
            w1_gen = w1_info.get('gen', 'm')
            
            # Heuristic override for duals (camel_tools sometimes gets them wrong)
            if w1.endswith('تان') or w1.endswith('تين'):
                w1_gen = 'f'
                w1_num = 'd'
            elif w1.endswith('ان') or w1.endswith('ين'):
                if len(w1) > 4:
                    w1_num = 'd'
            
            # Dual Adjective Agreement
            if w1_num == 'd' and w1_pos in ['noun', 'unknown', 'noun_prop']:
                base_adj = None
                for suffix in ['ان', 'ين', 'تان', 'تين', 'ة', 'ون', 'ات', '']:
                    stem = w2[:-len(suffix)] if suffix else w2
                    if stem in MASC_TO_FEM_ADJ:
                        base_adj = stem
                        break
                
                if base_adj:
                    is_nom = w1.endswith('ان') or w1.endswith('تان')
                    if w1_gen == 'f':
                        corrected_tokens[i+1] = base_adj + ('تان' if is_nom else 'تين')
                    else:
                        corrected_tokens[i+1] = base_adj + ('ان' if is_nom else 'ين')
                        
            # Plural Human Adjective Agreement
            elif w1_num == 'p' and w1_pos in ['noun', 'unknown']:
                base_adj = None
                for suffix in ['ان', 'ين', 'تان', 'تين', 'ة', 'ون', 'ات', 'ين', '']:
                    stem = w2[:-len(suffix)] if suffix else w2
                    if stem in MASC_TO_FEM_ADJ:
                        base_adj = stem
                        break
                
                if base_adj:
                    if w1.endswith('ون') or w1.endswith('ين') or w1_gen == 'm':
                        is_nom = w1.endswith('ون')
                        corrected_tokens[i+1] = base_adj + ('ون' if is_nom else 'ين')
                    elif w1.endswith('ات') or w1_gen == 'f':
                        corrected_tokens[i+1] = base_adj + 'ات'

        return " ".join(corrected_tokens)


    def process(self, original_text, generated_text):
        """Apply all grammar rules to model output."""
        text = self.preserve_numbers(original_text, generated_text)
        
        # ── Fix Hallucinated Subject Gender ──
        # If model incorrectly changes female subject to male, restore it.
        orig_words = original_text.split()
        corr_words = text.split()
        if len(orig_words) == len(corr_words):
            for i, (o, c) in enumerate(zip(orig_words, corr_words)):
                o_clean = o.rstrip('.,،؛;:!؟?()[]{}«»"\'…')
                c_clean = c.rstrip('.,،؛;:!؟?()[]{}«»"\'…')
                # If model dropped 'ة' from a word of length >= 4
                if o_clean.endswith('ة') and not c_clean.endswith('ة') and o_clean[:-1] == c_clean:
                    corr_words[i] = o
            text = " ".join(corr_words)

        # Each rule is wrapped in try/except so that if camel-tools
        # functions fail, the regex-based rules still execute.
        for rule_name, rule_fn in [
            ('fix_demonstrative_agreement', self.fix_demonstrative_agreement),
            ('fix_number_and_gender_agreement', self.fix_number_and_gender_agreement),
            ('smart_asmaa_khamsa_fix', self.smart_asmaa_khamsa_fix),
            ('fix_verbs_nasb_and_jazm', self.fix_verbs_nasb_and_jazm),
            ('fix_gender_agreement', self.fix_gender_agreement),
            ('fix_noun_adjective_agreement_advanced', self.fix_noun_adjective_agreement_advanced),
            ('fix_prepositions_advanced', self.fix_prepositions_advanced),
            ('fix_subject_verb_agreement', self.fix_subject_verb_agreement),
            ('fix_kana_and_inna', self.fix_kana_and_inna),
            ('fix_conditional_sentences', self.fix_conditional_sentences),
            ('fix_tanween_fathah', self.fix_tanween_fathah),
            ('fix_initial_hamza', self.fix_initial_hamza),
            ('fix_suffix_hallucination', self.fix_suffix_hallucination),
            ('regex_rules_fallback', self.regex_rules_fallback),
        ]:
            try:
                text = rule_fn(text, original_text) if rule_name == 'fix_suffix_hallucination' else rule_fn(text)
            except Exception as e:
                logger.warning(f"[GRAMMAR-RULES] {rule_name} failed: {e}")

        text = re.sub(r'\s+', ' ', text).strip()
        return text

    def fix_suffix_hallucination(self, text, original_text):
        """
        Revert grammar hallucination where extra consonants are appended to pronoun suffixes.
        Example: شجعتهم → شجعتهمت
        """
        orig_words = original_text.split()
        curr_words = text.split()
        
        if len(orig_words) == len(curr_words):
            for i in range(len(orig_words)):
                ow = orig_words[i]
                cw = curr_words[i]
                # If the current word is just the original word + 1 consonant, and original ended in a suffix
                if len(cw) == len(ow) + 1 and cw.startswith(ow):
                    added_char = cw[-1]
                    if ow.endswith(('هم', 'هن', 'كم', 'كن', 'ها', 'نا')) and added_char in 'تمةنل':
                        curr_words[i] = ow
                        logger.info(f"[GRAMMAR-RULES] Reverted suffix hallucination: {cw} → {ow}")
            text = ' '.join(curr_words)
        return text

    def fix_tanween_fathah(self, text):
        """
        Add tanween fathah (ً) to indefinite accusative nouns ending in ا.
        
        Arabic rule: Words like جدا, كثيرا, قرارا should be جداً, كثيراً, قراراً.
        The trailing ا without tanween is a common orthographic error.
        
        From legacy AraSpell._normalize_tanween_patterns():
        Only apply to words >= 3 chars ending in ا where the ا is NOT part of
        the root (e.g. NOT ما، إلى، على، أنا، هذا).
        """
        # Common words ending in ا that should NOT get tanween
        _NO_TANWEEN = {
            'ما', 'إذا', 'هذا', 'أنا', 'إلى', 'على', 'حتى', 'متى', 'لما',
            'إلا', 'أما', 'كما', 'ربما', 'مهما',
            'عندما', 'بينما', 'حينما', 'كلما',
        }
        # Words that ALWAYS get tanween
        _ALWAYS_TANWEEN = {
            'جدا': 'جداً',
            'كثيرا': 'كثيراً',
            'شكرا': 'شكراً',
            'نظرا': 'نظراً',
            'قليلا': 'قليلاً',
            'أيضا': 'أيضاً',
            'فورا': 'فوراً',
            'سابقا': 'سابقاً',
            'لاحقا': 'لاحقاً',
            'حاليا': 'حالياً',
            'تقريبا': 'تقريباً',
            'خصوصا': 'خصوصاً',
            'عموما': 'عموماً',
            'دائما': 'دائماً',
            'مباشرا': 'مباشراً',
            'أبدا': 'أبداً',
            'غالبا': 'غالباً',
            'أحيانا': 'أحياناً',
            'مثلا': 'مثلاً',
            'قرارا': 'قراراً',
            'جديدا': 'جديداً',
            'كبيرا': 'كبيراً',
            'صغيرا': 'صغيراً',
            'طويلا': 'طويلاً',
            'قصيرا': 'قصيراً',
            'سريعا': 'سريعاً',
            'بطيئا': 'بطيئاً',
            'جيدا': 'جيداً',
            'سيئا': 'سيئاً',
            'عظيما': 'عظيماً',
            'قويا': 'قوياً',
            'ضعيفا': 'ضعيفاً',
            'صعبا': 'صعباً',
            'سهلا': 'سهلاً',
            'هاما': 'هاماً',
            'نهائيا': 'نهائياً',
            'رسميا': 'رسمياً',
            'تماما': 'تماماً',
            'عاجلا': 'عاجلاً',
            'أولا': 'أولاً',
            'ثانيا': 'ثانياً',
            'ثالثا': 'ثالثاً',
            'أخيرا': 'أخيراً',
            'حقا': 'حقاً',
            'حقيقيا': 'حقيقياً',
            'علميا': 'علمياً',
            'عمليا': 'عملياً',
        }
        words = text.split()
        for i, w in enumerate(words):
            if w in _ALWAYS_TANWEEN:
                words[i] = _ALWAYS_TANWEEN[w]
        return ' '.join(words)

    def fix_initial_hamza(self, text):
        """
        Fix missing hamza on initial alef for common verb/noun patterns.
        
        Arabic rule: أفعل-pattern verbs and certain nouns require hamza:
        - اعلن → أعلن (أَفْعَل form IV verb)
        - اصدر → أصدر
        - اسلم → أسلم
        """
        # Common words where initial ا should be أ
        _HAMZA_FIXES = {
            'اعلن': 'أعلن', 'اعلنت': 'أعلنت', 'اعلنوا': 'أعلنوا',
            'اصدر': 'أصدر', 'اصدرت': 'أصدرت', 'اصدروا': 'أصدروا',
            'اسلم': 'أسلم', 'اسلمت': 'أسلمت', 'اسلموا': 'أسلموا',
            'اكد': 'أكد', 'اكدت': 'أكدت', 'اكدوا': 'أكدوا',
            'اعطى': 'أعطى', 'اعطت': 'أعطت', 'اعطوا': 'أعطوا',
            'انجز': 'أنجز', 'انجزت': 'أنجزت', 'انجزوا': 'أنجزوا',
            'ارسل': 'أرسل', 'ارسلت': 'أرسلت', 'ارسلوا': 'أرسلوا',
            'اخرج': 'أخرج', 'اخرجت': 'أخرجت', 'اخرجوا': 'أخرجوا',
            'انشأ': 'أنشأ', 'انشأت': 'أنشأت', 'انشأوا': 'أنشأوا',
            'اضاف': 'أضاف', 'اضافت': 'أضافت', 'اضافوا': 'أضافوا',
            'احب': 'أحب', 'احبت': 'أحبت', 'احبوا': 'أحبوا',
            'افهم': 'أفهم', 'افهمت': 'أفهمت', 'افهموا': 'أفهموا',
            'اعجب': 'أعجب', 'اعجبت': 'أعجبت', 'اعجبوا': 'أعجبوا',
            'اكرم': 'أكرم', 'اكرمت': 'أكرمت', 'اكرموا': 'أكرموا',
            'انقذ': 'أنقذ', 'انقذت': 'أنقذت', 'انقذوا': 'أنقذوا',
            'الامهات': 'الأمهات', 'الاطفال': 'الأطفال',
            'الامة': 'الأمة', 'الاستاذ': 'الأستاذ',
        }
        _HAMZA_STEMS = {
            'احب': 'أحب', 'افهم': 'أفهم', 'اعلن': 'أعلن',
            'اصدر': 'أصدر', 'اسلم': 'أسلم', 'اكد': 'أكد',
            'انجز': 'أنجز', 'ارسل': 'أرسل', 'اخرج': 'أخرج',
            'اضاف': 'أضاف', 'اعجب': 'أعجب', 'اكرم': 'أكرم',
            'انقذ': 'أنقذ',
        }
        _PRONOUN_SUFFIXES = {'ه', 'ها', 'ك', 'كم', 'كن', 'هم', 'هن', 'ني', 'نا'}
        words = text.split()
        for i, w in enumerate(words):
            if w in _HAMZA_FIXES:
                words[i] = _HAMZA_FIXES[w]
                continue
            for stem, fixed in _HAMZA_STEMS.items():
                if w.startswith(stem) and len(w) > len(stem):
                    suffix = w[len(stem):]
                    if suffix in _PRONOUN_SUFFIXES:
                        words[i] = fixed + suffix
                        break
        return ' '.join(words)
