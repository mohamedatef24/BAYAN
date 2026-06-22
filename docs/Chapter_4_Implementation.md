# Chapter 4: Implementation

## 4.1 Overview

This chapter details the implementation of each component of the Bayan system, covering the NLP pipeline, backend API, web application frontend, Chrome browser extension, and deployment infrastructure. For each component, we describe the implementation approach, key algorithms, data structures, and notable engineering decisions.

## 4.2 NLP Pipeline Implementation

### 4.2.1 AraSpell Spelling Correction

The AraSpell spelling correction system (`src/nlp/spelling/araspell_rules.py`, 1,507 lines) is the most complex NLP component in the system. It implements a multi-stage pipeline that processes text through nine distinct phases.

#### 4.2.1.1 Preprocessing (AraSpellPostProcessor)

The preprocessing stage normalizes input text to reduce noise before model inference:

```python
# Diacritics removal
text = re.sub(r'[ً-ْ]', '', text)

# Tatweel (kashida) removal
text = text.replace('ـ', '')

# Special character normalization (ligatures)
NORMALIZER_MAP = {'ﻹ': 'لإ', 'ﻷ': 'لأ', 'ﻵ': 'لآ', 'ﻻ': 'لا', 'ﷲ': 'الله'}

# Character repetition collapse (Arabic: 3+ → 1, Latin: 2+ → 1)
text = re.sub(r"([\u0600-\u06FF])\1{2,}", r"\1", text)
```

#### 4.2.1.2 Error Classification

The `ErrorClassifier` categorizes input text into one of five error types, which determines the correction strategy:

| Error Type | Detection Heuristic | Example |
|---|---|---|
| `CHAR_REPETITION` | 3+ consecutive identical Arabic characters | "كتاااااب" |
| `WORD_MERGE` | Words > 8 characters or single word > 6 chars | "فيالمدرسة" |
| `CHAR_SUBSTITUTION` | Non-Arabic keyboard characters (پ, گ, چ, etc.) | "پيت" (Persian ب) |
| `MIXED` | 2+ of the above | — |
| `CLEAN` | None of the above | "كتاب" |

#### 4.2.1.3 Rules-Based Correction

The `RulesBasedCorrector` applies deterministic corrections before model inference:

1. **Character Substitution Map**: Maps non-Arabic keyboard characters to their Arabic equivalents (40 mappings, e.g., 'ک' → 'ك', 'ی' → 'ي').

2. **Keyboard Proximity Map**: Maps 47 Arabic keyboard keys to their physical neighbors for error detection (e.g., 'ض' → ['ص', 'ق']).

3. **Recursive Word Splitting**: Detects merged prepositions using a longest-prefix-first algorithm:
```python
separables = sorted(['من', 'في', 'على', ...], key=len, reverse=True)
for sep in separables:
    if word.startswith(sep) and len(remainder) >= 3:
        return sep + " " + recursive_split(remainder)
```

#### 4.2.1.4 Neural Correction (AraBERT Encoder-Decoder)

The neural correction stage uses an AraBERT-based Encoder-Decoder model:

- **Encoder**: AraBERT (aubmindlab/bert-base-arabertv02), 12 layers, 768 hidden size, 12 attention heads, 64,000 vocabulary
- **Decoder**: AraBERT with cross-attention (is_decoder=True, add_cross_attention=True)
- **Training**: Fine-tuned on pairs of (misspelled, corrected) Arabic text
- **Inference**: Beam search with num_beams=5, max_length=128

Model weights are stored as a PyTorch checkpoint (`last_model.pt`) on HuggingFace Hub (`bayan10/AraSpell-Model`). At runtime, the model is assembled by:

```python
# Build architecture from config
config_encoder = BertConfig(vocab_size=64000, hidden_size=768, ...)
config_decoder = BertConfig(vocab_size=64000, ..., is_decoder=True, add_cross_attention=True)
model = EncoderDecoderModel(config=EncoderDecoderConfig.from_encoder_decoder_configs(...))

# Load trained weights
checkpoint = torch.load(model_path, map_location=device)
model.load_state_dict(checkpoint['model_state_dict'])
```

#### 4.2.1.5 Output Validation

The `OutputValidator` prevents hallucinated corrections from reaching the user:

```python
def validate(self, original, corrected, error_type):
    # Length check: corrected must be 0.5x–2.5x original length
    if len(corrected) > len(original) * 2.5: return False, "too_long"
    if len(corrected) < len(original) * 0.5: return False, "too_short"

    # Word count check: ratio must be 0.5–2.0
    ratio = len(corrected.split()) / max(1, len(original.split()))
    if ratio > 2.0 or ratio < 0.5: return False, "word_count_mismatch"

    # Character preservation: Jaccard similarity must be ≥ 0.35
    jaccard = len(chars_orig & chars_corr) / len(chars_orig | chars_corr)
    if jaccard < 0.35: return False, "low_character_similarity"
```

#### 4.2.1.6 Word Alignment (Hybrid Correction)

The `WordAligner` selects the best word from {input_word, output_word, hybrid} for each position:

```
if input_word == output_word → keep
if input is OOV, output is IV → use output (correct misspelling)
if input is IV, output is OOV → keep input (prevent corruption)
if both IV → keep input (prevent meaning change)
  EXCEPTION: if only difference is ه→ة at word end → use output (correct orthography)
```

#### 4.2.1.7 Contextual Refinement (BERT MLM)

For ambiguous corrections, the `ContextualCorrector` uses BERT's Masked Language Model to score candidate words in context:

```python
# Mask the target word and get top-k predictions
masked_text = text.replace(word, '[MASK]')
outputs = mlm_model(**tokenizer(masked_text, return_tensors='pt'))
top_k_tokens = torch.topk(outputs.logits[0, mask_pos], k=10)

# Select the candidate with highest contextual probability
for candidate in [original, correction]:
    if candidate in top_k_tokens:
        score = softmax_prob[candidate]
```

#### 4.2.1.8 Hamza Whitelist

The system maintains a curated whitelist of 60+ common hamza placement errors (`AraSpellPostProcessor.HAMZA_WHITELIST`):

```python
HAMZA_WHITELIST = {
    'الي': 'إلى', 'الى': 'إلى',
    'انت': 'أنت', 'انتم': 'أنتم',
    'لان': 'لأن', 'لانه': 'لأنه',
    'اذا': 'إذا', 'ايضا': 'أيضاً',
    # ... 50+ more entries
}
```

The whitelist also handles prefixed forms using `HAMZA_PREFIXES`:
```python
HAMZA_PREFIXES = ['وبال', 'فبال', 'وال', 'بال', 'فال', 'كال',
                  'ول', 'فل', 'وب', 'فب', 'وك', 'فك', 'و', 'ف', 'ب', 'ك', 'ل']
```

This allows corrections like "واصدقائي" → "وأصدقائي" (prefix "و" + whitelist word "اصدقائي" → "أصدقائي").

### 4.2.2 Grammar Correction

#### 4.2.2.1 Model Inference (Gradio Client)

The grammar model uses a fine-tuned Gemma 3 model hosted on Gradio Spaces:

```python
from gradio_client import Client
client = Client("mohammedahmedezz2004/bayan_arabic_grammarly_correction")
model_output = client.predict(text=text, api_name="/correct_grammar")
```

The Gradio connection includes retry logic with exponential backoff for rate limiting and sleeping Spaces:

```python
for attempt in range(1, max_retries + 1):
    try:
        client = Client(GRADIO_SPACE)
        break
    except Exception as conn_err:
        if is_retryable and attempt < max_retries:
            time.sleep(2 ** attempt)  # 2s, 4s, 8s
```

**Transient error handling**: Rate limiting, timeout, and connection errors are NOT cached — the next request retries loading. Only permanent failures are cached.

#### 4.2.2.2 Rule-Based Post-Processing (ArabicGrammarGuard)

The `ArabicGrammarGuard` class applies 8 rule categories using CAMeL Tools MLE Disambiguator:

**Rule 1: Number Preservation**
```python
def preserve_numbers(self, original_text, generated_text):
    orig_digits = re.findall(r'\d+', original_text)
    gen_digits = re.findall(r'\d+', generated_text)
    if orig_digits and gen_digits and orig_digits != gen_digits:
        return original_text  # Reject if digits changed
```

**Rule 2: Number-Gender Agreement**
Uses morphological analysis to detect agreement errors between nouns and their modifying verbs/adjectives.

**Rule 3: Five Nouns (الأسماء الخمسة)**
```python
asmaa_khamsa_roots = ['اب', 'اخ', 'حم', 'فو', 'ذو']
# After إنّ and sisters: nominative → accusative (و→ا)
# After prepositions: nominative → genitive (و→ي)
```

**Rule 4: Verb Nasb and Jazm**
```python
nasb_particles = ['أن', 'لن', 'كي', 'لكي', 'حتى', 'إذن']
jazm_particles = ['لم', 'لما', 'لا']
# After nasb/jazm: remove ون ending → وا, ان → ا, ين → ي
```

**Rule 5: Gender Agreement for Demonstratives and Numbers**
```python
# هذان + feminine dual → هاتان
text = re.sub(r'\bهذان\s+(ال[أ-ي]+تان)\b', r'هاتان \1', text)
```

**Rule 6: Preposition Case Marking**
```python
# في المهندسون → في المهندسين (nominative → genitive after preposition)
# Requires stem ≥ 4 chars to avoid false positives on roots ending in ان
text = re.sub(r'\b([وف]?(?:في|من|إلى|على|عن|حتى))\s+([أ-ي]{4,})(ون|ان)\b', r'\1 \2ين', text)
```

**Rule 7: Subject-Verb Agreement (SVO Order)**
Detects confirmed plural nouns followed by singular verbs in SVO word order:

```python
KNOWN_PLURALS_MASC = {'الطلاب', 'طلاب', 'الرجال', 'رجال', ...}
KNOWN_PLURALS_FEM = {'الطالبات', 'طالبات', 'النساء', 'نساء', ...}

# Also detects sound masculine plurals (ending in ون/ين, ≥5 chars)
# and sound feminine plurals (ending in ات, ≥5 chars)
```

### 4.2.3 Punctuation Restoration (PuncAra-v1)

#### 4.2.3.1 Model Architecture

PuncAra-v1 is an EncoderDecoderModel built from AraBERT, fine-tuned for punctuation restoration:

```python
model = EncoderDecoderModel.from_pretrained("bayan10/PuncAra-v1")
model.config.decoder_start_token_id = tokenizer.cls_token_id
model.config.eos_token_id = tokenizer.sep_token_id
```

**Inference parameters:**
- `max_length=128` per chunk
- `num_beams=3` (beam search for punctuation accuracy)
- `repetition_penalty=1.2`
- `early_stopping=True`

#### 4.2.3.2 Windowed Chunking

Long texts are processed in 50-word non-overlapping windows:

```python
window_size = 50
stride = 50  # Non-overlapping
for i in range(0, total_words, stride):
    chunk = words[i:i+window_size]
    processed = predict_chunk(" ".join(chunk))
    # Remove trailing punctuation from non-last segments
    if not is_last and processed[-1] in ".?!،؛:؟!":
        processed = processed[:-1]
```

#### 4.2.3.3 Non-Punctuation Change Stripping (Fix P1)

The PuncAra model was trained on data containing spelling/grammar corrections alongside punctuation. The `_strip_non_punctuation_changes()` method ensures only punctuation modifications are retained:

```python
for o_word, p_word in aligned_pairs:
    o_base = strip_punct(o_word)
    p_base = strip_punct(p_word)
    if o_base == p_base:
        result.append(p_word)  # Same base — keep model's punctuation
    else:
        # Model changed word content — revert to original, keep new punctuation
        result.append(o_word + new_punctuation_suffix)
```

### 4.2.4 Text Summarization (mBART)

The summarization model (`SummarizationModel` in `model_loader.py`) uses a fine-tuned mBART:

```python
generate_kwargs = dict(
    max_new_tokens=max(20, min(max_length, 160)),
    min_new_tokens=max(0, min_length),
    num_beams=1,           # Greedy decoding — empirically best for Arabic
    do_sample=False,
    early_stopping=False,
    no_repeat_ngram_size=3,
    repetition_penalty=1.1,
)
```

**Hallucination Detection and Extractive Fallback:**

```python
def _needs_fallback(self, source_text, summary_text):
    source_words = set(source_text.split())
    summary_words = summary_text.split()
    overlap = sum(1 for w in summary_words if w in source_words)
    overlap_ratio = overlap / max(1, len(summary_words))
    ratio = SequenceMatcher(None, source[:500], summary[:500]).ratio()
    return overlap_ratio < 0.35 or ratio < 0.22
```

When the model produces hallucinated output, the system falls back to an extractive approach that selects the opening sentences of the source text.

### 4.2.5 Dialect-to-MSA Conversion (mT5)

The dialect converter uses a fine-tuned mT5 model (`bayan10/dialect-to-msa-model`):

```python
class DialectConverter:
    PREFIX = "حوّل إلى الفصحى: "  # "Convert to MSA: "
    
    def convert(self, dialect_text, num_beams=4):
        input_text = self.PREFIX + dialect_text.strip()
        outputs = self.model.generate(
            **inputs,
            max_length=128,
            num_beams=num_beams,
            early_stopping=True,
            no_repeat_ngram_size=3,
        )
```

The task-specific prefix "حوّل إلى الفصحى: " instructs the model to perform dialect-to-MSA conversion, following the T5 text-to-text format.

### 4.2.6 Autocomplete (Hybrid Bigram + AraGPT2)

#### 4.2.6.1 Bigram Model

The statistical component uses a pre-trained bigram model (`bayan10/AutoComplete/bigram_model_v4.pkl`) stored as a pickle file containing:
- `unigrams`: `Dict[str, int]` — word → frequency count
- `bigrams`: `Dict[str, Dict[str, int]]` — context_word → {next_word → count}

#### 4.2.6.2 GPT-2 Component

The neural component uses AraGPT2-Base (`aubmindlab/aragpt2-base`) with a sampling-based prediction strategy:

```python
outputs = self.gpt2_model.generate(
    **inputs,
    max_new_tokens=5,
    do_sample=True,       # Sampling for diversity (beam search collapses)
    top_k=50,
    top_p=0.9,
    temperature=0.8,
    num_return_sequences=15,  # Generate 15 diverse sequences
)

# Extract first Arabic word from each sequence
for seq in outputs:
    match = re.search(r'[\u0600-\u06FF]{2,}', generated_text)
    word_counts[match.group(0)] += 1

# Score = frequency across samples
prob_dict = {w: count / total for w, count in word_counts.items()}
```

#### 4.2.6.3 Hybrid Scoring

```python
score = alpha * stat_prob + (1 - alpha) * neural_prob
# alpha = 0.4 → 40% bigram, 60% GPT-2
# threshold = 0.05 → minimum score to show
```

### 4.2.7 Quranic Text Verification

The Quran search engine (`quran.py`, 15,974 bytes) provides fuzzy search against a comprehensive SQLite database (`quran_master.db`, ~22MB). The database contains the complete Quran with:
- Arabic text (original and simplified)
- Verse metadata (Surah number, Ayah number, Surah name)
- Translations in multiple languages

The search function `search_bayan(text, target_type)` supports:
- **Verse verification**: Identifies if a given text is a Quranic quotation
- **Fuzzy matching**: Handles partial or slightly misspelled quotations
- **Translation lookup**: Returns translations alongside the Arabic text

## 4.3 Backend API Implementation

### 4.3.1 The `/api/analyze` Pipeline — Filtering and Safety

The `/api/analyze` endpoint implements extensive filtering at each pipeline stage to prevent over-correction and hallucination.

#### Spelling Stage Filtering

The `_is_small_spelling_change()` function implements a multi-layered filtering strategy:

1. **Numeral Protection**: Rejects any correction involving digits (Arabic or Latin).
2. **Directional Blocks**: Prevents known meaning-changing substitutions:
   ```python
   _DIRECTIONAL_BLOCKS = {
       'هذه': {'هذة'},          # Correct feminine → misspelling
       'كان': {'كأن'},          # "was" → "as if" (meaning change)
       'إلى': {'على', 'علي'},   # Different prepositions
   }
   ```
3. **Clitic-Aware Blocking**: Applies directional blocks with common prefixes stripped (و+كان→و+كأن).
4. **Feminine Marker Protection**: Rejects corrections that drop ه/ة endings.
5. **In-Vocabulary Guard**: When both words are valid Arabic words, only accepts:
   - Known ه→ة orthographic fixes (with pronoun suffix guard for ته patterns)
   - Hamza whitelist matches (exact target match required)
6. **Levenshtein Filter**: For OOV words, rejects edits with distance > 2 or ratio > 50%.
7. **Orthographic-Only Filter**: Only allows character changes within the orthographic pairs set (ه↔ة, ا↔أ↔إ↔آ, ي↔ى, ؤ↔و, ئ↔ي, ء↔أ).
8. **Confidence Dampening**: Returns 0.5 (instead of 0.9) for OOV→IV corrections and hamza-only changes.

#### Grammar Stage Filtering

1. **StageLocker Check**: Skips diffs overlapping with spelling-locked ranges.
2. **Hallucination Rejection**: Rejects corrections with Jaccard character similarity < 0.3.
3. **IV→OOV Corruption Guard**: Rejects corrections that change a valid word to a non-word.
4. **Spelling Re-labeling**: If a grammar correction is purely orthographic (ه→ة, hamza), re-labels it as 'spelling' for correct UI icons.
5. **Bracket Balance Guard**: Rejects grammar output if it breaks bracket balance.

#### Punctuation Stage Filtering

1. **StageLocker Check**: Blocks word changes in locked ranges but allows pure punctuation insertions.
2. **`validate_punctuation_diff()`**: Validates that each diff only adds/modifies punctuation characters.
3. **Aggregate Cap**: Maximum 3 punctuation patches per response.

### 4.3.2 Smart Text Processing Strategy

The pipeline adapts its behavior based on text length:

| Text Length | Strategy | Reason |
|---|---|---|
| 0–300 chars | Full pipeline (Spelling + Grammar + Punctuation) | Complete analysis |
| 300–1000 chars | Grammar + Punctuation only | AraSpell too slow |
| 1000+ chars | Grammar + Punctuation only | Performance |

### 4.3.3 Supabase Integration

The backend injects Supabase credentials into the frontend at serving time:

```python
@app.route('/')
def index():
    html = html_path.read_text(encoding='utf-8')
    html = html.replace('<meta name="supabase-url" content="">',
                        f'<meta name="supabase-url" content="{SUPABASE_URL}">')
    html = html.replace('<meta name="supabase-anon-key" content="">',
                        f'<meta name="supabase-anon-key" content="{SUPABASE_ANON_KEY}">')
```

## 4.4 Web Application Frontend

### 4.4.1 Editor Implementation

The WYSIWYG editor (`src/js/editor.js`, 30,022 bytes) provides:

- **ContentEditable-based editing**: Uses a `<div contenteditable="true">` element with custom event handlers for keyboard input, paste, and formatting commands.
- **RTL Default**: All text is right-to-left by default, appropriate for Arabic content.
- **Formatting Toolbar**: Bold (`document.execCommand('bold')`), italic, underline, font family, font size, text alignment, text color, and highlight color.
- **Real-time Analysis**: Debounced calls to `/api/analyze` on text change.
- **Inline Highlights**: Color-coded underlines beneath detected errors.

### 4.4.2 Theme System

The theme system (`src/js/theme.js`, 2,406 bytes) provides light and dark modes using CSS custom properties:

```css
:root {
    --bg-primary: #ffffff;
    --text-primary: #1a1a2e;
    --accent: #667eea;
}
[data-theme="dark"] {
    --bg-primary: #1a1a2e;
    --text-primary: #e0e0e0;
    --accent: #7c8cf8;
}
```

### 4.4.3 Document Management

Documents are stored in localStorage with the following operations:
- **Create**: Generates a new document with a unique ID and default title.
- **Save**: Serializes editor content to JSON and persists to localStorage.
- **Load**: Restores document content and metadata from localStorage.
- **Cloud Sync**: Optionally syncs documents to Supabase for cross-device access.

## 4.5 Chrome Extension Implementation

### 4.5.1 Background Service Worker

The background script (`extension/background.js`, 6,213 bytes) handles:

```javascript
chrome.runtime.onMessage.addListener((msg, sender, sendResponse) => {
    if (msg.type === 'BAYAN_ANALYZE') {
        fetch(API_URL + '/api/analyze', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({text: msg.text})
        })
        .then(r => r.json())
        .then(data => sendResponse(data))
        .catch(err => sendResponse({error: err.message}));
        return true; // async response
    }
    if (msg.type === 'OPEN_SIDE_PANEL') {
        chrome.sidePanel.open({tabId: sender.tab.id});
    }
});
```

### 4.5.2 Content Script — Inline Analysis

The content-inline.js script (20,208 bytes) implements the full Grammarly-style inline analysis:

**Editable Field Detection:**
```javascript
const EDITABLE_SELECTORS = [
    'textarea',
    '[contenteditable="true"]',
    '[contenteditable=""]',
    'input[type="text"]',
    'input:not([type])',
];

function detectEditableFields() {
    const fields = document.querySelectorAll(EDITABLE_SELECTORS.join(','));
    fields.forEach(field => {
        if (!field.__bayan_attached) {
            attachBayanAnalysis(field);
            field.__bayan_attached = true;
        }
    });
}

// MutationObserver for dynamically created fields
const observer = new MutationObserver(() => detectEditableFields());
observer.observe(document.body, {childList: true, subtree: true});
```

**Highlight Overlay Rendering:**
The overlay system creates positioned `<span>` elements with colored underlines beneath detected errors, aligned with the text in the editable field using `getComputedStyle()` and `getBoundingClientRect()`.

**Floating Action Button (FAB):**
A small circular button appears near editable fields, showing the count of detected issues. Clicking the FAB triggers analysis or opens the side panel.

### 4.5.3 Side Panel

The side panel (`extension/sidepanel/`) provides a persistent analysis interface alongside the browsing window:

- **Paste-and-Analyze**: Users paste text into a textarea and receive inline analysis results.
- **Result Display**: Uses `bayan-renderer.js` to display suggestions with accept/reject actions.
- **Shared Logic**: Reuses `analysis-controller.js`, `bayan-api.js`, and other shared modules.

### 4.5.4 Popup UI

The popup (`extension/popup.html`, 10,288 bytes; `popup.js`, 23,911 bytes; `popup.css`, 19,224 bytes) provides:

- **Quick Analysis**: Paste text and receive corrections.
- **Summarization**: Summarize pasted Arabic text.
- **Visual Parity**: Produces identical output to the side panel using shared rendering logic.

### 4.5.5 Internationalization

The extension supports Arabic and English locales via Chrome's i18n system:

```json
// _locales/ar/messages.json
{
    "extName": {"message": "بيان - مساعد الكتابة العربية"},
    "extDescription": {"message": "مساعد ذكي للكتابة العربية"}
}
```

## 4.6 Deployment Implementation

### 4.6.1 Dockerfile

The Dockerfile implements a two-phase strategy:

**Build Phase**: Downloads all model weights (5 models + CAMeL data) during `docker build`, caching them in the HuggingFace Hub local cache directory. This is necessary because the runtime container on HuggingFace Spaces free tier has no outbound DNS resolution.

**Runtime Phase**: Starts Gunicorn with a single worker, 300-second timeout, and binds to port 7860.

```dockerfile
# CPU-only PyTorch (saves ~1.5GB vs full torch with CUDA)
RUN pip install --no-cache-dir torch --index-url https://download.pytorch.org/whl/cpu

# Pre-download all models
RUN python -c "from transformers import MBartForConditionalGeneration, AutoTokenizer; ..."
RUN python -c "from huggingface_hub import hf_hub_download; ..."
RUN camel_data -i light
RUN python -c "from transformers import EncoderDecoderModel; ..."
RUN python -c "from transformers import AutoModelForSeq2SeqLM; ..."
```

### 4.6.2 Graceful Degradation

The system implements graceful degradation at multiple levels:

1. **Model loading failure**: If a model fails to load, the health endpoint reports it, but the server continues running with available models.
2. **Stage failure in `/api/analyze`**: Each pipeline stage is wrapped in try/except. If spelling fails, grammar and punctuation still run. The response includes a `'partial'` status and `'warnings'` field.
3. **Autocomplete**: Returns empty suggestions on failure (never fails the UI).
4. **HF API fallback**: When running in HF API mode without network, spelling/grammar/punctuation return input unchanged.

### 4.6.3 Health Monitoring

```python
@app.route('/api/health', methods=['GET'])
def health_check():
    health = {
        'status': 'healthy',
        'models': {
            'summarization': summarization_model is not None,
            'spelling': _spelling_available(),
            'grammar': _grammar_available(),
            'punctuation': _punctuation_available(),
            'dialect': _dialect_available()
        },
        'supabase': {'configured': bool(SUPABASE_URL and SUPABASE_ANON_KEY)},
    }
    status_code = 200 if health['models']['summarization'] else 503
```

### 4.6.4 Debug Endpoint

The `/api/debug-models` endpoint provides comprehensive diagnostics:
- Model loading status for all models
- Startup error traces
- Memory usage (`resource.getrusage`)
- System memory info (`/proc/meminfo`)
- HF API token configuration status

## 4.7 Implementation Statistics

| Component | File | Lines of Code |
|---|---|---|
| Flask API Server | `src/app.py` | 1,717 |
| Model Loader | `src/model_loader.py` | 904 |
| AraSpell Pipeline | `src/nlp/spelling/araspell_rules.py` | 1,507 |
| AraSpell Service | `src/nlp/spelling/araspell_service.py` | 106 |
| Grammar Rules | `src/nlp/grammar/grammar_rules.py` | 294 |
| Grammar Service | `src/nlp/grammar/grammar_service.py` | 164 |
| Punctuation Service | `src/nlp/punctuation/punctuation_service.py` | 282 |
| Punctuation Rules | `src/nlp/punctuation/punctuation_rules.py` | ~160 |
| Autocomplete Service | `src/nlp/autocomplete/autocomplete_service.py` | 373 |
| Dialect Service | `src/nlp/dialect/dialect_service.py` | 81 |
| Pipeline Context | `src/nlp/pipeline_context.py` | 117 |
| Correction Patch | `src/nlp/correction_patch.py` | 131 |
| Stage Locker | `src/nlp/stage_locker.py` | ~110 |
| HF Inference | `src/hf_inference.py` | 99 |
| Quran Search | `quran.py` | ~460 |
| Web App Frontend | `src/index.html` | ~4,000+ |
| Frontend JS (total) | `src/js/*.js` | ~3,000+ |
| Extension Background | `extension/background.js` | ~180 |
| Extension Content Script | `extension/content-inline.js` | ~600 |
| Extension Popup | `extension/popup.js` | ~700 |
| Extension CSS | `extension/*.css` | ~700 |
| Extension Shared | `extension/shared/*.js` | ~600 |
| Dockerfile | `Dockerfile` | 91 |
| **Estimated Total** | | **~16,000+** |
