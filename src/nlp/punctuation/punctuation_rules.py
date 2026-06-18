# PuncAra — Arabic Punctuation Restoration Rules
# Extracted from PuncAra.py — preprocessing + postprocessing + chunking logic.
# All classes are imported by punctuation_service.py.

import re
import logging

logger = logging.getLogger(__name__)


def arabic_preprocessing(text: str) -> str:
    """Remove Arabic diacritics to normalize input for the model."""
    arabic_diacritics = re.compile(r'[\u064B-\u0652]')
    return re.sub(arabic_diacritics, '', text).strip()


def arabic_postprocessing(text: str) -> str:
    """
    Typographic cleanup and punctuation normalization after model inference.
    Handles: bracket spacing, duplicate marks, chunk-join artifacts, etc.
    """
    if not text:
        return text

    # 1. Protect numbers/fractions/time from incorrect conversion
    text = re.sub(r'(?<=\d),(?=\d)', '٪TEMP_COMMA٪', text)
    text = re.sub(r'(?<=\d):(?=\d)', '٪TEMP_COLON٪', text)

    # 2. Arabize typographic marks
    text = text.replace(',', '،').replace(';', '؛').replace('?', '؟')

    # 3. Fix internal spacing for brackets and Arabic quotes
    text = re.sub(r'\(\s+', '(', text)
    text = re.sub(r'\s+\)', ')', text)
    text = re.sub(r'\[\s+', '[', text)
    text = re.sub(r'\s+\]', ']', text)
    text = re.sub(r'«\s+', '«', text)
    text = re.sub(r'\s+»', '»', text)

    # 4. Remove repeated emotional marks (except ellipsis)
    text = re.sub(r'([،؛:!؟])\1+', r'\1', text)
    text = re.sub(r'\.{4,}', '...', text)

    # 5. Fix chunk-join contradictions
    text = re.sub(r'[،؛:]+([.!؟])', r'\1', text)
    text = re.sub(r'،؛|؛،', '؛', text)
    text = re.sub(r'([!؟])\.', r'\1', text)

    # 6. Remove stray leading punctuation
    text = re.sub(r'^[،؛:!؟. \t]+', '', text)

    # 7. Ensure single space after punctuation before text
    text = re.sub(r'([،؛:!؟.])(?=\S)', r'\1 ', text)

    # 8. Restore protected numbers
    text = text.replace('٪TEMP_COMMA٪', ',').replace('٪TEMP_COLON٪', ':')

    # 9. Attach punctuation to preceding word
    text = re.sub(r'\s+([،؛:!؟.])', r'\1', text)

    # 10. Collapse horizontal spaces only
    text = re.sub(r'[ \t]+', ' ', text).strip()
    return text
