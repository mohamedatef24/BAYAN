# Chapter 2: Literature Review

## 2.1 Overview

This chapter surveys the existing body of research and commercial tools relevant to the Bayan project. The review covers five major domains: Arabic Natural Language Processing (NLP) fundamentals, Arabic spell checking and grammar correction, Arabic text summarization, writing assistance tools, and browser extension technologies. For each domain, we examine the state of the art, identify key limitations, and position the contributions of the Bayan system within the broader landscape.

## 2.2 Arabic Natural Language Processing

### 2.2.1 Challenges of Arabic NLP

Arabic presents a unique constellation of challenges for NLP systems, documented extensively in the literature (Habash, 2010; Farghaly & Shaalan, 2009). These challenges include:

**Morphological Complexity**: Arabic is a morphologically rich language with a root-and-pattern system. A typical Arabic root consists of three consonants (triliteral root, e.g., ك-ت-ب) from which dozens of surface forms are derived through the insertion of vowel patterns, prefixes, suffixes, and infixes. Habash (2010) catalogued over 60 distinct morphological features that can be expressed through affixation and templatic morphology, producing an estimated 72 billion possible word forms from approximately 10,000 root entries.

**Orthographic Ambiguity**: The Arabic writing system omits short vowels (diacritics/tashkīl) in most contexts, creating pervasive lexical and syntactic ambiguity. Diab et al. (2007) demonstrated that a single Arabic word form may have an average of 12 possible analyses, compared to 2.4 for English. This ambiguity fundamentally impacts downstream NLP tasks including tokenization, part-of-speech tagging, and named entity recognition.

**Dialectal Variation**: Modern Standard Arabic (MSA) coexists with a spectrum of regional dialects (Egyptian, Gulf, Levantine, Maghrebi, and others) that differ substantially in vocabulary, phonology, and syntax. Bouamor et al. (2018) showed that inter-dialect intelligibility can be as low as 60% for geographically distant varieties. Most NLP tools are trained exclusively on MSA, leaving dialectal text inadequately served.

**Hamza and Ta Marbuta Confusion**: Two of the most frequent orthographic errors in Arabic involve hamza placement (أ/إ/آ/ء/ئ/ؤ) and the confusion between ta marbuta (ة) and ha (ه) at word endings. Zaghouani et al. (2014) found that these two error categories account for over 35% of all spelling errors in Arabic text.

### 2.2.2 Pre-trained Arabic Language Models

The development of pre-trained language models specifically for Arabic has been a critical enabler for downstream NLP tasks. Key models include:

**AraBERT** (Antoun et al., 2020): A BERT-based model pre-trained on 70 million Arabic sentences from news articles, Wikipedia, and OSCAR datasets. AraBERT introduced Arabic-specific preprocessing (Farasa segmentation, removing diacritics and tatweel) and achieved state-of-the-art results on several Arabic NLP benchmarks. The Bayan project uses AraBERT (aubmindlab/bert-base-arabertv02) as the encoder-decoder backbone for the AraSpell spelling correction model.

**AraGPT2** (Antoun et al., 2021): An Arabic adaptation of GPT-2, pre-trained on a large Arabic corpus for autoregressive language modeling. Available in base, medium, and large variants. The Bayan project uses AraGPT2-Base (aubmindlab/aragpt2-base) as the neural component of the hybrid autocomplete system.

**CAMeL Tools** (Obeid et al., 2020): A comprehensive Arabic NLP toolkit providing morphological analysis, disambiguation, and dialectal identification. The MLE (Maximum Likelihood Estimation) disambiguator from CAMeL Tools is used in Bayan's grammar post-processing rules to determine part-of-speech tags, number, and gender for agreement checking.

**mBART** (Liu et al., 2020): A multilingual denoising autoencoder pre-trained on 25 languages including Arabic. mBART's sequence-to-sequence architecture makes it suitable for text generation tasks. Bayan uses a fine-tuned mBART model (MBartForConditionalGeneration) for Arabic text summarization.

**mT5** (Xue et al., 2021): A multilingual variant of the Text-to-Text Transfer Transformer (T5) pre-trained on 101 languages. Bayan uses a fine-tuned mT5 model (AutoModelForSeq2SeqLM) for dialect-to-MSA conversion.

## 2.3 Arabic Spelling Correction

### 2.3.1 Traditional Approaches

Early Arabic spell checkers relied on dictionary lookup combined with edit distance metrics. Haddad and Yaseen (2007) proposed an Arabic spell checker using minimum edit distance with a dictionary of 9 million word forms. Ben Othmane Zribi and Ben Ahmed (2003) developed a morphological analyzer-based approach that decomposed words into roots, patterns, prefixes, and suffixes before dictionary validation.

These approaches suffer from two fundamental limitations: (1) the dictionary can never be complete due to Arabic's productive morphology, and (2) edit distance metrics designed for English do not account for Arabic-specific error patterns such as hamza misplacement, ta marbuta/ha confusion, and clitic attachment errors.

### 2.3.2 Neural Approaches

Recent work has applied sequence-to-sequence models to Arabic spell checking:

**Mohit et al. (2014)** proposed one of the first neural approaches to Arabic text correction, using statistical machine translation (SMT) techniques to "translate" erroneous text into correct text.

**Watson et al. (2019)** demonstrated that transformer-based models could achieve significant improvements over traditional approaches for Arabic grammatical error correction, particularly for hamza and morphological agreement errors.

**AraSpell (Bayan)**: The spelling correction system developed in this project represents a novel contribution: a full pipeline integrating rule-based preprocessing, neural correction (AraBERT Encoder-Decoder), hybrid word alignment, contextual refinement using masked language modeling (BERT MLM), and extensive post-processing with vocabulary validation. This multi-stage approach addresses the over-correction problem that plagues single-model approaches, where the model aggressively changes valid but rare words to more common alternatives.

### 2.3.3 Key Challenges in Arabic Spell Checking

The AraSpell development process identified and addressed several challenges not adequately covered in the literature:

1. **In-Vocabulary (IV) to In-Vocabulary (IV) Corruption**: When both the original and corrected words are valid Arabic words, the model may change the meaning (e.g., كان → كأن, "was" → "as if"). This requires vocabulary-aware filtering.

2. **Pronoun Suffix False Positives**: The ه→ة correction (ha to ta marbuta) is generally correct for feminine nouns but incorrect when ه is a pronoun suffix (e.g., فتأملته — "she contemplated him").

3. **Numeral Hallucination**: Neural models occasionally introduce or modify digits in the output, a complete-replacement failure mode.

4. **Word Split Validation**: Merged words (e.g., فيالمدرسة → في المدرسة) must be split carefully to avoid detaching pronoun suffixes (e.g., مستشفياتهم → "مستشفيات هم" is incorrect).

## 2.4 Arabic Grammar Correction

### 2.4.1 Rule-Based Approaches

Traditional Arabic grammar checking relies on morphological analysis and hand-crafted rules. Shaalan et al. (2012) developed a rule-based Arabic grammar checker that addressed subject-verb agreement, definiteness agreement, and case marking errors using a morphological analyzer. However, rule-based systems are inherently limited by the rules they encode and cannot generalize to unseen error patterns.

### 2.4.2 Neural Approaches

**Soliman et al. (2017)** applied sequence-to-sequence models to Arabic GEC (Grammatical Error Correction), achieving moderate improvements over rule-based baselines.

**Gemma (Google DeepMind, 2024)**: The Gemma family of language models, based on the research behind Google's Gemini models, provides instruction-following capabilities that can be adapted for GEC tasks through fine-tuning. Bayan uses a fine-tuned Gemma 3 model (AutoModelForCausalLM) deployed as a Gradio-hosted inference endpoint.

### 2.4.3 Hybrid Approaches

The Bayan grammar correction system employs a hybrid approach: neural model inference (Gemma 3 via Gradio) followed by rule-based post-processing using CAMeL Tools. The rule-based component addresses:

- **Number and Gender Agreement**: Ensuring adjectives, verbs, and demonstratives agree with their governing nouns in number (singular/dual/plural) and gender (masculine/feminine).
- **Case Marking with Prepositions**: Converting nominative endings to genitive after prepositions (e.g., المهندسون → المهندسين after في).
- **The Five Nouns (الأسماء الخمسة)**: Special declension rules for أب (father), أخ (brother), حم (father-in-law), فو (mouth), ذو (possessor of).
- **Nasb and Jazm of Verbs**: Correct verb endings after particles of subjunctive (أن, لن, كي) and jussive (لم, لا, لمّا).
- **Subject-Verb Agreement in SVO Order**: In Arabic, VSO (Verb-Subject-Object) order allows a singular verb with a plural subject, but SVO order requires number agreement.

## 2.5 Arabic Text Summarization

### 2.5.1 Extractive vs. Abstractive Summarization

Summarization techniques fall into two categories:

**Extractive summarization** selects and concatenates the most important sentences from the source text. Al-Sabahi et al. (2018) surveyed extractive methods for Arabic, including TF-IDF-based, graph-based (TextRank), and topic modeling approaches. While reliable, extractive methods produce summaries that lack coherence and may miss implicit information.

**Abstractive summarization** generates new text that captures the meaning of the source document. This is significantly more challenging as it requires natural language generation. Al-Maleh and Deris (2020) demonstrated that transformer-based models (mBART, mT5) could produce coherent Arabic summaries when fine-tuned on Arabic summarization datasets.

### 2.5.2 Bayan's Approach

Bayan's summarization system uses a fine-tuned mBART model with the following design decisions:

- **Greedy decoding** (num_beams=1, do_sample=False) was empirically found to produce more faithful summaries than beam search, which tended to generate generic or hallucinated content.
- **Extractive fallback**: When the model's output has low lexical overlap with the source (overlap ratio < 0.35 or SequenceMatcher ratio < 0.22), the system falls back to an extractive approach, selecting the opening sentences of the source text.
- **Configurable summary length**: Three tiers (short ~30%, medium ~50%, long ~70% of input length) allow users to control the compression ratio.

## 2.6 Arabic Punctuation Restoration

### 2.6.1 Background

Arabic text, particularly in informal digital communication, frequently lacks proper punctuation. Punctuation restoration (also called punctuation prediction) is the task of inserting appropriate punctuation marks into unpunctuated text. Che et al. (2016) formulated this as a sequence labeling problem, where each word is classified as having a punctuation mark after it (and which mark) or not.

### 2.6.2 Bayan's PuncAra Model

The PuncAra-v1 model developed for this project is a sequence-to-sequence EncoderDecoderModel fine-tuned on Arabic text with and without punctuation. Key design features include:

- **Windowed chunking**: Long texts are processed in 50-word non-overlapping windows, with trailing punctuation removed from non-final segments to avoid false sentence boundaries at chunk edges.
- **Non-punctuation change stripping**: The model was trained on data that included spelling/grammar corrections alongside punctuation. A post-processing step (Fix P1) strips any changes to word content, preserving only punctuation additions/modifications.
- **Punctuation-only diff validation**: A safety layer validates that each diff produced by the punctuation stage only adds or modifies punctuation characters, rejecting any diffs that alter Arabic word content.

## 2.7 Writing Assistance Tools

### 2.7.1 Grammarly

Grammarly (founded 2009) is the market leader in English writing assistance, with over 30 million daily active users. Its feature set includes:

- Real-time grammar, spelling, and punctuation checking
- Tone detection and style suggestions
- Plagiarism detection
- Clarity and engagement scoring
- Browser extension with inline highlighting and floating cards
- Desktop application and mobile keyboard

Grammarly's architecture combines rule-based NLP with deep learning models, running inference on cloud servers with edge-optimized client-side processing for low-latency suggestions. **Grammarly offers no Arabic language support.**

### 2.7.2 QuillBot

QuillBot (founded 2017) focuses on paraphrasing and writing assistance:

- Paraphraser with multiple modes (standard, fluency, creative, etc.)
- Grammar checker (English only)
- Summarizer
- Citation generator
- Co-Writer

QuillBot's Arabic support is limited to basic paraphrasing through machine translation proxies, with no grammar checking, spell checking, or punctuation restoration for Arabic.

### 2.7.3 Bayan's Position

Bayan occupies a unique position as the first comprehensive Arabic writing assistant that integrates all major NLP capabilities (spelling, grammar, punctuation, summarization, dialect conversion, autocomplete, and Quranic verification) within a unified platform accessible from both a web interface and a browser extension. The competitive gap analysis conducted during Phase 7 identified 47 features present in Grammarly or QuillBot, of which Bayan implements 22, with the remaining 25 representing future development opportunities.

## 2.8 Chrome Extension Technologies

### 2.8.1 Manifest V3

Google Chrome's Manifest V3 (MV3) extension platform, mandated for all new extensions since January 2023, introduced significant architectural changes from Manifest V2:

- **Service Workers** replace persistent background pages, requiring stateless message-passing architectures.
- **Host Permissions** replace broad `<all_urls>` access with explicit domain declarations.
- **Content Scripts** operate in an isolated world, communicating with the service worker via `chrome.runtime.sendMessage()`.
- **Side Panel API** (Chrome ≥ 114) provides a persistent panel alongside the browsing window.

### 2.8.2 Grammarly-Style Inline Analysis

The Grammarly browser extension pioneered the pattern of inline text analysis on arbitrary web pages, which Bayan's Phase 6 (inline analysis engine) implements. This pattern involves:

1. **Content script injection**: Detecting editable text fields (`<textarea>`, `contenteditable`, `<input>`) on any web page.
2. **Overlay rendering**: Creating a positioned overlay layer that renders colored underlines beneath detected errors, without modifying the underlying DOM content.
3. **Suggestion tooltips**: Displaying floating cards with correction options when the user hovers over or clicks an underlined error.
4. **Non-destructive correction**: Applying corrections by modifying the text content of the editable field, preserving cursor position and selection state.

### 2.8.3 Challenges of Content Script Architecture

Content scripts operating on arbitrary web pages face several challenges that the literature addresses only partially:

- **Shadow DOM isolation**: Modern web frameworks (React, Angular, Vue) use Shadow DOM boundaries that prevent content scripts from accessing internal elements.
- **Dynamic content**: Single-page applications (SPAs) dynamically create and destroy text fields, requiring MutationObserver-based detection.
- **Protected pages**: Browser-internal pages (`chrome://`, `chrome-extension://`), the Chrome Web Store, and certain Google properties block content script injection entirely.
- **Performance**: Real-time text analysis with network round-trips to a cloud API must be debounced and throttled to avoid degrading page responsiveness.

## 2.9 Summary of Literature Review

The literature review reveals a clear gap in the Arabic NLP landscape: while individual components (spell checking, grammar correction, summarization) have been studied in isolation, no existing system integrates these capabilities into a comprehensive, production-ready writing assistant platform. Commercial tools (Grammarly, QuillBot) either do not support Arabic at all or provide only superficial coverage. The Bayan project addresses this gap by combining custom-trained Arabic NLP models with a full-stack web application and a feature-rich Chrome browser extension, creating the first end-to-end Arabic writing assistance system of its kind.

| Capability | Grammarly | QuillBot | Bayan |
|---|---|---|---|
| Arabic Spelling Correction | ❌ | ❌ | ✅ |
| Arabic Grammar Checking | ❌ | ❌ | ✅ |
| Arabic Punctuation Restoration | ❌ | ❌ | ✅ |
| Arabic Summarization | ❌ | Partial | ✅ |
| Dialect-to-MSA Conversion | ❌ | ❌ | ✅ |
| Arabic Autocomplete | ❌ | ❌ | ✅ |
| Quranic Verification | ❌ | ❌ | ✅ |
| Browser Extension (Inline) | ✅ (English) | ✅ (English) | ✅ (Arabic) |
| Side Panel | ❌ | ❌ | ✅ |
| Web Application | ✅ (English) | ✅ (English) | ✅ (Arabic) |
