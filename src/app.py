"""
Flask backend server for Arabic text summarization.
Provides API endpoints for the Bayan web application.
"""

import os
import logging
import time
from flask import Flask, request, jsonify, Response
from flask_cors import CORS
from pathlib import Path
import traceback
import difflib
import re

# Quran search
import sys
_quran_root = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, _quran_root)
try:
    from quran import search_bayan
    logger_quran_ok = True
except Exception as _quran_err:
    logger_quran_ok = False
    import logging as _ql
    _ql.getLogger('app').warning(f'[QURAN] Failed to import quran module: {_quran_err}')
    _ql.getLogger('app').warning(f'[QURAN] Searched path: {_quran_root}')
    _ql.getLogger('app').warning(f'[QURAN] Files in root: {os.listdir(_quran_root) if os.path.isdir(_quran_root) else "DIR NOT FOUND"}')

# Pipeline hardening modules
from nlp.pipeline_context import PipelineContext
from nlp.punctuation.punctuation_rules import validate_punctuation_diff

# Load .env file from project root (one level up from src/)
try:
    from dotenv import load_dotenv
    _env_path = Path(__file__).parent.parent / '.env'
    load_dotenv(dotenv_path=_env_path)
except ImportError:
    pass  # python-dotenv not installed; rely on environment variables directly

SUPABASE_URL = os.environ.get('SUPABASE_URL', '')
SUPABASE_ANON_KEY = os.environ.get('SUPABASE_ANON_KEY', '')

from model_loader import (
    SummarizationModel,
    SpellingModel,
    AutocompleteModel,
    GrammarModel,
    PunctuationModel,
    SUMMARIZATION_PATH,
    SPELLING_PATH,
    AUTOCOMPLETE_PATH,
    GRAMMAR_PATH,
    PUNCTUATION_PATH
)

# HuggingFace Inference API — used in production to avoid RAM limits
from hf_inference import (
    hf_summarize,
    hf_correct_spelling,
    hf_add_punctuation,
    hf_autocomplete,
    check_hf_api_available,
)

HUGGINGFACE_SUMMARIZATION_REPO = os.environ.get(
    "SUMMARIZATION_REPO_ID",
    "bayan10/summarization-model",
)

# When HF_API_TOKEN is set, use remote HF Inference API instead of local models.
# This avoids loading 500MB+ models into RAM on the free tier.
HF_API_TOKEN = os.environ.get('HF_API_TOKEN', '')
USE_HF_API = bool(HF_API_TOKEN)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Initialize Flask app
app = Flask(__name__, static_folder='.', static_url_path='')
CORS(app, resources={r"/api/*": {"origins": "*"}})  # CORS for API routes only

# Configuration
MAX_TEXT_LENGTH = 5000  # Maximum characters for input text
MAX_SUMMARY_LENGTH = 512  # Maximum tokens for summary
MIN_TEXT_LENGTH = 10  # Minimum characters for summarization

# Global model instances
summarization_model = None
spelling_model = None
autocomplete_model = None
grammar_model = None
punctuation_model = None

# ── Directional Blocks: prevent meaning-changing substitutions ──
# Used by both spelling confidence filter and grammar diff filter.
_DIRECTIONAL_BLOCKS = {
    # Demonstratives: هذه (correct feminine) → هذة (misspelling) = ALWAYS wrong
    'هذه': {'هذة'},
    'هذا': {'هذة', 'هذه'},    # masculine → don't flip to feminine forms
    # Verb/particle confusion: كان (was) ↔ كأن (as if) = ALWAYS wrong
    'كان': {'كأن'},
    'كأن': {'كان'},
    'كانت': {'كأنت'},      # H016: كانت → كأنت = ALWAYS wrong
    'كانوا': {'كأنوا'},     # also block plural form
    # Preposition confusion: different meanings, both valid
    'إلى': {'على', 'علي'},
    'على': {'إلى', 'علي'},
    'علي': {'على'},           # proper name vs preposition
    # Conjunction: لكن (correct) ↔ لاكن (misspelling of لكن, never valid)
    'لكن': {'لاكن'},          # correct → misspelling = ALWAYS wrong
    # Demonstrative: ذلك (correct) ↔ ذالك (common misspelling)
    'ذلك': {'ذالك'},          # correct → misspelling = ALWAYS wrong
    # Pronoun suffix: ه→ة corruption (G037: عمله→عملة)
    'عمله': {'عملة'},          # عمله (his work) → عملة (currency) = WRONG
    'لسانه': {'لسانة'},        # his tongue
    'بيته': {'بيتة'},          # his house
    'كتابه': {'كتابة'},        # his book → writing
}


def load_models():
    """Load models. In HF API mode, load summarization locally; other models gracefully degrade."""
    global summarization_model, spelling_model, autocomplete_model, grammar_model, punctuation_model
    
    if USE_HF_API:
        logger.info("HF_API_TOKEN is set — HF API mode enabled")
        logger.info("NOTE: HF Spaces free tier has NO outbound DNS. Loading summarization model locally.")
        logger.info("Spelling, punctuation, autocomplete will gracefully degrade (return input unchanged).")
        # Fall through to load summarization model locally
    
    loaded = []
    failed = []
    
    # Store startup errors for diagnostics
    global _startup_errors
    _startup_errors = []

    # Load only the Summarization model locally.
    try:
        logger.info(f"Loading summarization model from Hugging Face: {HUGGINGFACE_SUMMARIZATION_REPO}")
        try:
            summarization_model = SummarizationModel(HUGGINGFACE_SUMMARIZATION_REPO)
        except Exception as remote_error:
            logger.warning(f"Remote load failed, falling back to local model: {remote_error}")
            _startup_errors.append(f"remote_load: {str(remote_error)[:200]}")
            logger.info(f"Loading summarization model from local path: {SUMMARIZATION_PATH}")
            summarization_model = SummarizationModel(SUMMARIZATION_PATH)
        loaded.append("summarization")
        logger.info("Summarization model loaded successfully")
    except Exception as e:
        import traceback
        err_detail = traceback.format_exc()
        failed.append(("summarization", str(e)))
        _startup_errors.append(f"summarization_load_failed: {err_detail[-500:]}")
        logger.error(f"Failed to load summarization model: {str(e)}")

    logger.info(f"Models loaded: {loaded}")
    if failed:
        logger.warning(f"Models failed to load: {[f[0] for f in failed]}")

    return len(loaded) > 0

_startup_errors = []


@app.route('/')
def index():
    """Serve the main HTML file with Supabase credentials injected."""
    html_path = Path(__file__).parent / 'index.html'
    html = html_path.read_text(encoding='utf-8')

    # Inject Supabase credentials into the meta tags
    html = html.replace(
        '<meta name="supabase-url" content="">',
        f'<meta name="supabase-url" content="{SUPABASE_URL}">'
    )
    html = html.replace(
        '<meta name="supabase-anon-key" content="">',
        f'<meta name="supabase-anon-key" content="{SUPABASE_ANON_KEY}">'
    )

    return Response(html, mimetype='text/html')


@app.route('/api/health', methods=['GET'])
def health_check():
    """Health check endpoint for production monitoring."""
    if USE_HF_API:
        health = {
            'status': 'healthy',
            'mode': 'hf_spaces_local',
            'models': {
                'summarization': summarization_model is not None,
                'spelling': _spelling_available(),
                'autocomplete': _autocomplete_available(),
                'grammar': _grammar_available(),
                'punctuation': _punctuation_available(),
                'dialect': _dialect_available()
            },
            'note': 'Free tier: summarization local, other models return input unchanged',
            'supabase': {
                'configured': bool(SUPABASE_URL and SUPABASE_ANON_KEY),
            },
            'environment': 'huggingface_spaces',
        }
        status_code = 200 if summarization_model is not None else 503
        return jsonify(health), status_code
    
    health = {
        'status': 'healthy',
        'mode': 'local_models',
        'models': {
            'summarization': summarization_model is not None,
            'spelling': spelling_model is not None,
            'autocomplete': autocomplete_model is not None,
            'grammar': grammar_model is not None,
            'punctuation': punctuation_model is not None,
            'dialect': _dialect_available()
        },
        'supabase': {
            'configured': bool(SUPABASE_URL and SUPABASE_ANON_KEY),
        },
        'environment': 'render' if os.environ.get('RENDER') else 'local',
    }
    status_code = 200 if health['models']['summarization'] else 503
    return jsonify(health), status_code


@app.route('/api/debug-models', methods=['GET'])
def debug_models():
    """Debug endpoint: report model status and startup errors."""
    from hf_inference import debug_test_all_models
    results = debug_test_all_models()
    
    # Memory info
    import os
    try:
        import resource
        mem = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
        mem_info = f"{mem} KB"
    except Exception:
        mem_info = "N/A"
    
    # /proc/meminfo on Linux
    proc_mem = {}
    try:
        with open('/proc/meminfo', 'r') as f:
            for line in f:
                if any(k in line for k in ['MemTotal', 'MemFree', 'MemAvailable', 'SwapTotal']):
                    parts = line.split()
                    proc_mem[parts[0].rstrip(':')] = parts[1] + ' ' + (parts[2] if len(parts) > 2 else '')
    except Exception:
        proc_mem = {"error": "cannot read /proc/meminfo"}
    
    return jsonify({
        'status': 'debug',
        'hf_api_token_set': bool(HF_API_TOKEN),
        'summarization_model_loaded': summarization_model is not None,
        'startup_errors': _startup_errors,
        'memory': mem_info,
        'proc_meminfo': proc_mem,
        'models': results,
    }), 200


def _spelling_available():
    """Check if spelling model is loaded (without triggering lazy load)."""
    try:
        from nlp.spelling.araspell_service import is_loaded
        return is_loaded()
    except Exception:
        return False


def _grammar_available():
    """Check if grammar model is loaded (without triggering lazy load)."""
    try:
        from nlp.grammar.grammar_service import is_loaded
        return is_loaded()
    except Exception:
        return False


def _punctuation_available():
    """Check if punctuation model is loaded (without triggering lazy load)."""
    try:
        from nlp.punctuation.punctuation_service import is_loaded
        return is_loaded()
    except Exception:
        return False


def _autocomplete_available():
    """Check if autocomplete model is loaded (without triggering lazy load)."""
    try:
        from nlp.autocomplete.autocomplete_service import _instance
        return _instance is not None and _instance.is_ready()
    except Exception:
        return False


def _dialect_available():
    """Check if dialect model is loaded (without triggering lazy load)."""
    try:
        from nlp.dialect.dialect_service import is_loaded
        return is_loaded()
    except Exception:
        return False


@app.route('/api/spelling', methods=['POST'])
def spelling_correction():
    """
    Correct spelling in Arabic text.
    
    Request JSON:
    {
        "text": "Arabic text with spelling errors"
    }
    
    Response JSON:
    {
        "original_text": "...",
        "corrected_text": "...",
        "status": "success"
    }
    """
    try:
        if not request.is_json:
            return jsonify({'error': 'Request must be JSON', 'status': 'error'}), 400
        
        data = request.get_json()
        text = data.get('text', '').strip()
        
        if not text:
            return jsonify({'error': 'Text is required', 'status': 'error'}), 400
        
        if len(text) > MAX_TEXT_LENGTH:
            return jsonify({
                'error': f'Text too long. Maximum {MAX_TEXT_LENGTH} characters.',
                'status': 'error'
            }), 400
        
        logger.info(f"Spelling correction request: text_length={len(text)}")
        
        from nlp.spelling.araspell_service import get_spelling_model
        checker = get_spelling_model()
        corrected = checker.correct(text)
        
        return jsonify({
            'original_text': text,
            'corrected_text': corrected,
            'status': 'success'
        }), 200
    
    except RuntimeError as e:
        logger.error(f"Spelling model error: {e}")
        return jsonify({
            'error': f'Spelling model unavailable: {str(e)[:200]}',
            'status': 'error'
        }), 503
    except Exception as e:
        logger.error(f"Spelling correction error: {e}")
        return jsonify({
            'error': f'Spelling correction failed: {str(e)[:200]}',
            'status': 'error'
        }), 500


@app.route('/api/summarize', methods=['POST'])
def summarize():
    """
    Summarize Arabic text.
    
    Expected JSON payload:
    {
        "text": "Arabic text to summarize",
        "length": 1-3 (1=short, 2=medium, 3=long),
        "full_text": true/false (whether to summarize full text or just first paragraph)
    }
    """
    if summarization_model is None:
        return jsonify({
            'error': 'Summarization model not loaded. Please check server logs.',
            'status': 'error'
        }), 503
    
    try:
        # Validate request
        if not request.is_json:
            return jsonify({
                'error': 'Request must be JSON',
                'status': 'error'
            }), 400
        
        data = request.get_json()
        
        # Validate input text
        text = data.get('text', '').strip()
        if not text:
            return jsonify({
                'error': 'Text is required',
                'status': 'error'
            }), 400
        
        if len(text) < MIN_TEXT_LENGTH:
            return jsonify({
                'error': f'Text must be at least {MIN_TEXT_LENGTH} characters',
                'status': 'error'
            }), 400
        
        if len(text) > MAX_TEXT_LENGTH:
            return jsonify({
                'error': f'Text must be at most {MAX_TEXT_LENGTH} characters',
                'status': 'error'
            }), 400
        
        # Get parameters
        length = int(data.get('length', 2))  # Default to medium
        length = max(1, min(3, length))  # Clamp between 1 and 3
        
        full_text = data.get('full_text', True)
        
        # Calculate max_length based on length parameter
        # Short: ~30% of input, Medium: ~50%, Long: ~70%
        input_length = len(text.split())
        length_multipliers = {1: 0.3, 2: 0.5, 3: 0.7}
        max_length = max(20, int(input_length * length_multipliers[length]))
        max_length = min(max_length, MAX_SUMMARY_LENGTH)
        
        # Generate summary
        logger.info(f"Generating summary: length={length}, max_length={max_length}, text_length={len(text)}")
        
        # Always use local model (HF Spaces free tier has no outbound DNS for API calls)
        summary = summarization_model.summarize(text, max_length=max_length, min_length=max(10, max_length // 3))
        
        return jsonify({
            'summary': summary,
            'status': 'success',
            'original_length': len(text),
            'summary_length': len(summary)
        })
    
    except ValueError as e:
        logger.error(f"Validation error: {str(e)}")
        return jsonify({
            'error': f'Invalid input: {str(e)}',
            'status': 'error'
        }), 400
    
    except Exception as e:
        logger.error(f"Error during summarization: {str(e)}")
        logger.error(traceback.format_exc())
        return jsonify({
            'error': 'An error occurred during summarization. Please try again.',
            'status': 'error',
            'details': str(e) if app.debug else None
        }), 500



@app.route('/api/autocomplete', methods=['POST'])
def autocomplete():
    """
    Get autocomplete suggestions for Arabic text.
    COMPLETELY INDEPENDENT — has zero interaction with /api/analyze.

    Request JSON:
    {
        "context": "<text before cursor>",
        "n": 5 (optional)
    }

    Response JSON:
    {
        "status": "success",
        "suggestions": ["word1", "word2", ...]
    }
    """
    try:
        if not request.is_json:
            return jsonify({'error': 'Request must be JSON', 'status': 'error'}), 400

        data = request.get_json()
        context = data.get('context', '').strip()
        n = int(data.get('n', 3))

        if not context or len(context) < 3:
            return jsonify({'suggestions': [], 'status': 'success'})

        # Extract last ~200 chars (trimmed to word boundary)
        from nlp.autocomplete.autocomplete_rules import extract_context
        context = extract_context(context, max_chars=200)

        # Lazy-load the model on first request
        from nlp.autocomplete.autocomplete_service import get_autocomplete_model
        ac_model = get_autocomplete_model()

        if not ac_model.is_ready():
            return jsonify({'suggestions': [], 'status': 'success'})

        t0 = time.time()
        suggestions = ac_model.predict(context, n=n)
        elapsed = int((time.time() - t0) * 1000)
        logger.info(f"[AUTOCOMPLETE] {elapsed}ms | mode={ac_model.get_mode()} | context='{context[:80]}' | suggestions={suggestions}")

        return jsonify({
            'suggestions': suggestions,
            'status': 'success'
        })

    except Exception as e:
        logger.error(f"Error during autocomplete: {str(e)}")
        logger.error(traceback.format_exc())
        return jsonify({
            'suggestions': [],
            'status': 'success'  # Graceful degradation — never fail the UI
        })


@app.route('/api/grammar', methods=['POST'])
def grammar_correction():
    """
    Correct grammar in Arabic text.
    
    Request JSON:
    {
        "text": "Arabic text with grammar errors"
    }
    
    Response JSON:
    {
        "original_text": "...",
        "corrected_text": "...",
        "status": "success"
    }
    """
    try:
        if not request.is_json:
            return jsonify({'error': 'Request must be JSON', 'status': 'error'}), 400
        
        data = request.get_json()
        text = data.get('text', '').strip()
        
        if not text:
            return jsonify({'error': 'Text is required', 'status': 'error'}), 400
        
        if len(text) > MAX_TEXT_LENGTH:
            return jsonify({
                'error': f'Text too long. Maximum {MAX_TEXT_LENGTH} characters.',
                'status': 'error'
            }), 400
        
        logger.info(f"Grammar correction request: text_length={len(text)}")
        
        from nlp.grammar.grammar_service import get_grammar_model
        checker = get_grammar_model()
        corrected = checker.correct(text)
        
        return jsonify({
            'original_text': text,
            'corrected_text': corrected,
            'status': 'success'
        }), 200
    
    except RuntimeError as e:
        logger.error(f"Grammar model error: {e}")
        return jsonify({
            'error': f'Grammar model unavailable: {str(e)[:200]}',
            'status': 'error'
        }), 503
    except Exception as e:
        logger.error(f"Error during grammar correction: {str(e)}")
        logger.error(traceback.format_exc())
        return jsonify({
            'error': 'An error occurred during grammar correction.',
            'status': 'error',
            'details': str(e) if app.debug else None
        }), 500


@app.route('/api/punctuation', methods=['POST'])
def add_punctuation():
    """
    Add punctuation to Arabic text using PuncAra-v1.

    Request JSON:
    {
        "text": "Arabic text without punctuation"
    }

    Response JSON:
    {
        "status": "success",
        "original_text": "...",
        "corrected_text": "..."
    }
    """
    try:
        if not request.is_json:
            return jsonify({'error': 'Request must be JSON', 'status': 'error'}), 400

        data = request.get_json()
        text = data.get('text', '').strip()

        if not text:
            return jsonify({'error': 'Text is required', 'status': 'error'}), 400

        logger.info(f"Adding punctuation for text of length: {len(text)}")
        from nlp.punctuation.punctuation_service import get_punctuation_model
        punc_checker = get_punctuation_model()
        punctuated = punc_checker.correct(text)

        return jsonify({
            'original_text': text,
            'corrected_text': punctuated,
            'status': 'success'
        })

    except RuntimeError as e:
        logger.error(f"Punctuation model error: {e}")
        return jsonify({
            'error': f'Punctuation model unavailable: {str(e)[:200]}',
            'status': 'error'
        }), 503
    except Exception as e:
        logger.error(f"Error during punctuation: {str(e)}")
        logger.error(traceback.format_exc())
        return jsonify({
            'error': 'An error occurred during punctuation.',
            'status': 'error',
            'details': str(e) if app.debug else None
        }), 500


def get_word_positions(text):
    """
    Returns a list of tuples (word, start_char_index, end_char_index)
    for all whitespace-separated words in the text.
    """
    positions = []
    for m in re.finditer(r'\S+', text):
        positions.append((m.group(), m.start(), m.end()))
    return positions


class OffsetMapper:
    """
    Single source of truth for coordinate transformations between
    two consecutive versions of CURRENT_TEXT.

    CONTRACT:
      Input:  text_before (str), text_after (str)
              — two consecutive states of CURRENT_TEXT
      Stores: Internal diff operations (PRIVATE)
      API:
        reverse_map_offset(pos)       → text_after pos → text_before pos
        forward_map_range(start, end) → text_before range → text_after range

    TERMINOLOGY:
      text_before = CURRENT_TEXT before this stage's mutation
      text_after  = CURRENT_TEXT after this stage's mutation
      forward     = text_before → text_after
      reverse     = text_after  → text_before

    RULES:
      All external code uses reverse_map_offset() or forward_map_range().
      ._opcodes is PRIVATE — no external access.
    """

    def __init__(self, text_before, text_after):
        self._text_before = text_before
        self._text_after = text_after
        self._opcodes = []  # PRIVATE — (i1, i2, j1, j2) tuples
        self._build()

    def _build(self):
        s = difflib.SequenceMatcher(None, self._text_before, self._text_after)
        for tag, i1, i2, j1, j2 in s.get_opcodes():
            self._opcodes.append((i1, i2, j1, j2))

    def reverse_map_offset(self, pos_in_after):
        """
        Map a single position from text_after → text_before.
        (CURRENT_TEXT after mutation → CURRENT_TEXT before mutation)

        Used by PipelineContext.map_to_original() to walk the mapper
        chain in reverse, ultimately reaching ORIGINAL_TEXT coordinates.
        """
        for i1, i2, j1, j2 in self._opcodes:
            if j1 <= pos_in_after <= j2:
                if j2 == j1:  # insertion point
                    return i1
                ratio = (pos_in_after - j1) / (j2 - j1)
                return round(i1 + ratio * (i2 - i1))  # FIX-12: round() instead of int() truncation
        return len(self._text_before)

    def forward_map_range(self, start_in_before, end_in_before):
        """
        Map a range from text_before → text_after.
        (CURRENT_TEXT before mutation → CURRENT_TEXT after mutation)

        Used ONLY by StageLocker.update_via_mapper() to shift locked
        spans after a text mutation.

        MONOTONICITY GUARD: If independent point mapping produces an
        inverted range (start > end) due to non-monotonic edits,
        the end is clamped to max(new_start, new_end).
        """
        new_start = self._forward_map_pos(start_in_before)
        new_end = self._forward_map_pos(end_in_before)
        # Monotonicity guard: prevent inverted ranges
        new_end = max(new_start, new_end)
        return new_start, new_end

    def _forward_map_pos(self, pos):
        """Map a single position text_before → text_after. PRIVATE."""
        for i1, i2, j1, j2 in self._opcodes:
            if i1 <= pos <= i2:
                if i2 == i1:
                    return j1
                ratio = (pos - i1) / (i2 - i1)
                return int(j1 + ratio * (j2 - j1))
        if self._opcodes:
            last = self._opcodes[-1]
            return last[3] + (pos - last[1])
        return pos



def get_word_diffs(original, corrected):
    """
    Identify differences between original and corrected text at the word level.
    Returns a list of suggestions with start and end character offsets.
    """
    orig_words = get_word_positions(original)
    corr_words = get_word_positions(corrected)
    s = difflib.SequenceMatcher(None, [w[0] for w in orig_words], [w[0] for w in corr_words])
    suggestions = []
    
    for tag, i1, i2, j1, j2 in s.get_opcodes():
        if tag == 'replace':
            if i1 < len(orig_words) and i2 - 1 < len(orig_words):
                start_char = orig_words[i1][1]
                end_char = orig_words[i2-1][2]
                suggestions.append({
                    'start': start_char,
                    'end': end_char,
                    'original': original[start_char:end_char],
                    'correction': " ".join([w[0] for w in corr_words[j1:j2]]),
                    'type': 'generic'
                })
        elif tag == 'delete':
            if i1 < len(orig_words) and i2 - 1 < len(orig_words):
                start_char = orig_words[i1][1]
                end_char = orig_words[i2-1][2]
                suggestions.append({
                    'start': start_char,
                    'end': end_char,
                    'original': original[start_char:end_char],
                    'correction': '',
                    'type': 'generic'
                })
        elif tag == 'insert':
            pos = orig_words[i1][1] if i1 < len(orig_words) else len(original)
            suggestions.append({
                'start': pos,
                'end': pos,
                'original': '',
                'correction': " ".join([w[0] for w in corr_words[j1:j2]]),
                'type': 'generic'
            })
            
    return suggestions


def _levenshtein(a, b):
    """Simple Levenshtein distance for short words."""
    m, n = len(a), len(b)
    if m == 0:
        return n
    if n == 0:
        return m
    dp = [[0] * (n + 1) for _ in range(m + 1)]
    for i in range(m + 1):
        dp[i][0] = i
    for j in range(n + 1):
        dp[0][j] = j
    for i in range(1, m + 1):
        for j in range(1, n + 1):
            cost = 0 if a[i - 1] == b[j - 1] else 1
            dp[i][j] = min(
                dp[i - 1][j] + 1,      # deletion
                dp[i][j - 1] + 1,      # insertion
                dp[i - 1][j - 1] + cost,  # substitution
            )
    return dp[m][n]


def _is_small_spelling_change(orig_word, corr_word, vocab_manager=None):
    """
    Heuristic: only accept small spelling edits and ignore
    aggressive changes (to avoid over-editing).

    CRITICAL: If both words are in-vocabulary (both are valid Arabic words),
    only accept known orthographic fixes (ه→ة, hamza whitelist).
    This prevents the model from corrupting correct words (e.g. وكان→وكأن).

    Returns:
        float: 0.0 = reject, 0.5 = dampened confidence (rare word risk),
               0.9 = normal confidence. Phase 2 (BUG-034/035/036/037/E8).
    """
    if not orig_word or not corr_word:
        return 0.0
    if orig_word == corr_word:
        return 0.0

    # ── GUARD 1: Numeral protection (Phase 1, BUG-011/012/E1) ──
    # Reject corrections that remove/change/introduce digits.
    # Numeral hallucination is a complete-replacement failure mode.
    _DIGITS = set('0123456789٠١٢٣٤٥٦٧٨٩')
    if any(c in _DIGITS for c in orig_word):
        return 0.0  # Never "correct" text containing numerals
    if any(c in _DIGITS for c in corr_word):
        return 0.0  # Never introduce digits that weren't in original

    # ── GUARD 2: Directional confusable-word rules (Phase 1, BUG-004/005/E4) ──
    # For known function words, only allow corrections TOWARD the valid form.
    # This prevents meaning-changing substitutions that pass orthographic checks.
    #
    # ── B5 KNOWN LIMITATION (BUG-025/026): Shadda Duplication ──
    # AraSpell duplicates shadda-bearing words in ISOLATION: إنّ→إن إن, أنّ→أن أن.
    # In sentence context (e.g., "إنّ العلم نور"), the model handles shadda correctly.
    # This is an isolation-only AraSpell quirk — no pipeline filter needed.
    # _DIRECTIONAL_BLOCKS is defined at module level (line ~100)
    if corr_word in _DIRECTIONAL_BLOCKS.get(orig_word, set()):
        return 0.0

    # Check with common prefixes stripped (و+كان→و+كأن etc.)
    _CLITIC_PREFIXES = ('و', 'ف', 'ب', 'ل', 'ك')
    for _pfx in _CLITIC_PREFIXES:
        if (orig_word.startswith(_pfx) and corr_word.startswith(_pfx)
                and len(orig_word) > len(_pfx) + 1):
            _orig_stem = orig_word[len(_pfx):]
            _corr_stem = corr_word[len(_pfx):]
            if _corr_stem in _DIRECTIONAL_BLOCKS.get(_orig_stem, set()):
                return 0.0

    # Ignore tokens that contain non-letters (numbers / punctuation)
    # Arabic letters range plus basic Latin letters.
    if re.search(r'[^ء-يآأإىa-zA-Z]', orig_word):
        return 0.0
    if re.search(r'[^ء-يآأإىa-zA-Z]', corr_word):
        return 0.0

    # Fix S2: Reject corrections that drop feminine marker (ه/ة)
    # e.g. بارده→بارد, منخفظه→منخفض — these are WORSE than no correction
    feminine_endings = ('ه', 'ة')
    if orig_word.endswith(feminine_endings) and not corr_word.endswith(feminine_endings):
        # Only reject if the correction is just the word minus the ending
        if corr_word == orig_word[:-1] or len(corr_word) < len(orig_word):
            return 0.0

    # CRITICAL: If both words are valid Arabic words, only accept known fixes.
    # This prevents the spelling model from changing one correct word to another
    # (e.g. وكان→وكأن, which changes "and was" to "as if" — a meaning change).
    if vocab_manager:
        orig_iv = vocab_manager.is_iv(orig_word)
        corr_iv = vocab_manager.is_iv(corr_word)
        if orig_iv and corr_iv:
             # Both are valid words — only accept known orthographic fixes:
            # 1. ه→ة at word end (feminine marker fix)
            #    B3 (BUG-014/015): EXCEPT when ه is a pronoun suffix (preceded by ت).
            #    Pattern: verb+ته = "verb + him/it", NOT ta marbuta.
            #    E.g., فتأملته (fataamaltahu) → فتأملتة is WRONG.
            if (orig_word.endswith('ه') and corr_word.endswith('ة')
                    and orig_word[:-1] == corr_word[:-1]):
                # Guard: if word ends in ته, the ه is likely a pronoun suffix
                # Pattern: verb+ته = "verb + him/it", NOT ta marbuta.
                # E.g., فتأملته → فتأملتة is WRONG.
                if len(orig_word) >= 3 and orig_word[-2] == 'ت':
                    logger.info(
                        f"[SPELLING] Blocked ه→ة at pronoun suffix: "
                        f"'{orig_word}'→'{corr_word}' (ته pattern = pronoun 'him/it')"
                    )
                    return 0.0
                return 0.9
            # 2. ة→ه at word end (less common but valid)
            if (orig_word.endswith('ة') and corr_word.endswith('ه')
                    and orig_word[:-1] == corr_word[:-1]):
                return 0.9
            # 3. Word is in the hamza whitelist (known common errors)
            #    CRITICAL (Phase 5 fix, BUG-016/027): only accept if the correction
            #    MATCHES the whitelist target — not any arbitrary correction.
            #    FIX-02: This check now ALWAYS accepts whitelist matches, bypassing IV-IV guard.
            from nlp.spelling.araspell_rules import AraSpellPostProcessor
            if orig_word in AraSpellPostProcessor.HAMZA_WHITELIST:
                expected = AraSpellPostProcessor.HAMZA_WHITELIST[orig_word]
                if corr_word == expected:
                    return 0.9
                else:
                    logger.info(
                        f"[SPELLING] Whitelist mismatch: '{orig_word}'→'{corr_word}' "
                        f"(expected '{expected}') — rejected"
                    )
                    return 0.0
            # 4. Check prefixed hamza (و+whitelist word, etc.)
            for prefix in AraSpellPostProcessor.HAMZA_PREFIXES:
                if orig_word.startswith(prefix) and len(orig_word) > len(prefix) + 1:
                    remainder = orig_word[len(prefix):]
                    if remainder in AraSpellPostProcessor.HAMZA_WHITELIST:
                        expected = prefix + AraSpellPostProcessor.HAMZA_WHITELIST[remainder]
                        if corr_word == expected:
                            return 0.9
                        else:
                            logger.info(
                                f"[SPELLING] Prefixed whitelist mismatch: '{orig_word}'→'{corr_word}' "
                                f"(expected '{expected}') — rejected"
                            )
                            return 0.0
            # 5. FIX-02: Alif maqsura fix (ي↔ى at end) — both IV but correction is valid
            if (orig_word.endswith('ي') and corr_word.endswith('ى')
                    and orig_word[:-1] == corr_word[:-1]):
                return 0.85
            if (orig_word.endswith('ى') and corr_word.endswith('ي')
                    and orig_word[:-1] == corr_word[:-1]):
                return 0.85
            # Both are valid words and change is NOT a known fix — REJECT
            # This prevents وكان→وكأن, etc.
            return 0.0

    dist = _levenshtein(orig_word, corr_word)
    max_len = max(len(orig_word), len(corr_word))

    # Tighter filter for OOV words: reject edits that change word roots
    # Allow max 2 edits at max 50% of word length
    if dist > 2 or (dist / max_len) > 0.5:
        return 0.0

    # CRITICAL: Only allow ORTHOGRAPHIC fixes (ه↔ة, ا↔أ↔إ↔آ, ي↔ى).
    # Any other letter change means the word's ROOT is different
    # (e.g. عضلية→عملية ض→م = completely different word!)
    ORTHO_PAIRS = {
        ('ه', 'ة'), ('ة', 'ه'),
        ('ا', 'أ'), ('أ', 'ا'), ('ا', 'إ'), ('إ', 'ا'), ('ا', 'آ'), ('آ', 'ا'),
        ('ي', 'ى'), ('ى', 'ي'),
        ('ؤ', 'و'), ('و', 'ؤ'),  # hamza on waw
        ('ئ', 'ي'), ('ي', 'ئ'),  # hamza on ya
        ('ء', 'أ'), ('أ', 'ء'),  # standalone hamza ↔ hamza on alef
        ('ء', 'ؤ'), ('ؤ', 'ء'),  # standalone hamza ↔ hamza on waw
        ('ء', 'ئ'), ('ئ', 'ء'),  # standalone hamza ↔ hamza on ya
    }
    # Check every character pair — reject if ANY non-orthographic change
    if len(orig_word) != len(corr_word):
        # Length change = structural change, not just orthographic
        # Exception: if diff is just adding/removing ا at start (hamza)
        if abs(len(orig_word) - len(corr_word)) > 1:
            return 0.0
    for a, b in zip(orig_word, corr_word):
        if a != b and (a, b) not in ORTHO_PAIRS:
            return 0.0

    # ── B3 (BUG-014/015): Pronoun suffix guard (OOV path) ──
    # Same guard as IV-IV path: block ه→ة when preceded by ت
    if (orig_word.endswith('ه') and corr_word.endswith('ة')
            and len(orig_word) >= 3 and orig_word[-2] == 'ت'
            and orig_word[:-1] == corr_word[:-1]):
        logger.info(
            f"[SPELLING] Blocked ه→ة at pronoun suffix (OOV path): "
            f"'{orig_word}'→'{corr_word}'"
        )
        return 0.0

    # ── Phase 2 (BUG-034/035/036/037/E8): Confidence dampening ──
    # If the original word might be a valid rare word (OOV in model but
    # potentially real Arabic), dampen confidence so users can reject easily.
    if vocab_manager:
        orig_iv = vocab_manager.is_iv(orig_word)
        corr_iv = vocab_manager.is_iv(corr_word)

        # Phase 2.2: Use frequency rank if available.
        # If the original word is a known word (even rare), require a
        # meaningfully higher confidence bar before replacing it.
        orig_rank = vocab_manager.get_frequency_rank(orig_word)  # 999999 if unknown
        corr_rank = vocab_manager.get_frequency_rank(corr_word)  # 999999 if unknown
        if orig_iv and corr_iv and orig_rank < 999999:
            # Original is a known ranked word — correction should be more common
            # If correction is rarer or similarly ranked, dampen confidence
            if corr_rank >= orig_rank:
                logger.info(
                    f"[SPELLING] Dampened (freq): '{orig_word}'(rank={orig_rank})"
                    f"→'{corr_word}'(rank={corr_rank}) — corr not more common"
                )
                return 0.5

        if not orig_iv and corr_iv:
            # OOV→IV: original might be a rare word being "corrected" to common
            # Dampen confidence to 0.5 (lower than normal 0.9)
            logger.info(
                f"[SPELLING] Dampened confidence: '{orig_word}'→'{corr_word}' "
                f"(OOV→IV, possible rare word)"
            )
            return 0.5

    # ── B2 (BUG-006/009/010/013): Hamza-removal dampening ──
    # Hamza changes (أ→ا, إ→ا, ء→ا, etc.) between same-length words are
    # ambiguous — could be a valid fix OR a corruption. Always dampen these
    # to 0.5 regardless of vocab_manager status. This prevents BUG-009
    # (قرأ→قرا) and BUG-013 (خطأ→خطا) from leaking at full confidence.
    _HAMZA_CHARS = set('أإآؤئء')
    if len(orig_word) == len(corr_word):
        has_hamza_diff = False
        for a, b in zip(orig_word, corr_word):
            if a != b:
                if a in _HAMZA_CHARS or b in _HAMZA_CHARS:
                    has_hamza_diff = True
                else:
                    has_hamza_diff = False
                    break  # Non-hamza difference, don't apply this guard
        if has_hamza_diff:
            logger.info(
                f"[SPELLING] Dampened (hamza-only): '{orig_word}'→'{corr_word}'"
            )
            return 0.5

    return 0.9


def _is_spelling_only_change(original: str, correction: str) -> bool:
    """
    Detect if a grammar model's correction is actually a spelling/orthographic fix
    (hamza, ه→ة, ا→أ, etc.) rather than a true grammar change.

    Used to re-label grammar patches as 'spelling' for correct UI icons.
    """
    if not original or not correction:
        return False

    # Normalize: strip diacritics for comparison
    import re as _re
    strip_diacritics = lambda t: _re.sub(r'[\u064B-\u065F\u0670]', '', t)
    o = strip_diacritics(original)
    c = strip_diacritics(correction)

    if o == c:
        return True  # Only diacritical difference

    # Check word-by-word for single-word changes
    o_words = o.split()
    c_words = c.split()

    if len(o_words) != len(c_words):
        return False  # Word count changed = grammar (word split/merge)

    all_spelling = True
    for ow, cw in zip(o_words, c_words):
        if ow == cw:
            continue
        if _is_orthographic_variant(ow, cw):
            continue
        all_spelling = False
        break

    return all_spelling


def _is_orthographic_variant(word1: str, word2: str) -> bool:
    """
    Check if two words differ only by common Arabic orthographic variations:
    - Hamza placement: ا↔أ↔إ↔آ, ى↔ي, ه↔ة
    - These are spelling differences, not grammar.
    """
    if len(word1) != len(word2):
        # Allow ه→ة at end (same length since both are 1 char)
        # But also allow small length diffs for hamza additions
        if abs(len(word1) - len(word2)) > 1:
            return False
        # Check if only difference is a trailing ة↔ه
        if (word1[:-1] == word2[:-1] and
                {word1[-1], word2[-1]} <= {'ه', 'ة'}):
            return True
        return False

    # Same length: check char-by-char
    SPELLING_EQUIVALENCES = {
        frozenset({'ا', 'أ'}), frozenset({'ا', 'إ'}), frozenset({'ا', 'آ'}),
        frozenset({'أ', 'إ'}), frozenset({'أ', 'آ'}), frozenset({'إ', 'آ'}),
        frozenset({'ى', 'ي'}), frozenset({'ه', 'ة'}),
        frozenset({'ؤ', 'و'}), frozenset({'ئ', 'ي'}), frozenset({'ئ', 'ء'}),
    }
    diff_count = 0
    for c1, c2 in zip(word1, word2):
        if c1 == c2:
            continue
        if frozenset({c1, c2}) in SPELLING_EQUIVALENCES:
            diff_count += 1
        else:
            return False  # Non-orthographic difference = grammar
    return diff_count > 0  # At least one orthographic difference


@app.route('/api/dialect', methods=['POST'])
def convert_dialect():
    """
    Convert dialect Arabic text to Modern Standard Arabic (MSA).

    Request JSON:
    {
        "text": "عايز اشتكي من موظف في فرعكم"
    }

    Response JSON:
    {
        "status": "success",
        "original_text": "...",
        "converted_text": "..."
    }
    """
    try:
        if not request.is_json:
            return jsonify({'error': 'Request must be JSON', 'status': 'error'}), 400

        data = request.get_json()
        text = data.get('text', '').strip()

        if not text:
            return jsonify({'error': 'Text is required', 'status': 'error'}), 400

        if len(text) > MAX_TEXT_LENGTH:
            return jsonify({
                'error': f'Text too long. Maximum {MAX_TEXT_LENGTH} characters.',
                'status': 'error'
            }), 400

        logger.info(f"[DIALECT] Conversion request: text_length={len(text)}")

        from nlp.dialect.dialect_service import get_dialect_model
        converter = get_dialect_model()
        t0 = time.time()
        result = converter.convert(text)
        elapsed = int((time.time() - t0) * 1000)

        logger.info(f"[DIALECT] {elapsed}ms | input='{text[:80]}' | output='{result[:80]}'")

        return jsonify({
            'original_text': text,
            'converted_text': result,
            'status': 'success'
        }), 200

    except RuntimeError as e:
        logger.error(f"Dialect model error: {e}")
        return jsonify({
            'error': f'Dialect model unavailable: {str(e)[:200]}',
            'status': 'error'
        }), 503
    except Exception as e:
        logger.error(f"Error during dialect conversion: {e}")
        logger.error(traceback.format_exc())
        return jsonify({
            'error': 'An error occurred during dialect conversion.',
            'status': 'error',
            'details': str(e) if app.debug else None
        }), 500


@app.route('/api/quran', methods=['POST'])
def quran_verify():
    """
    Quran text verification and translation.
    Accepts: {text: str, language: str (optional, default='تدقيق الايات')}
    Returns: {matched_segment, full_verse} or {error}
    """
    try:
        if not logger_quran_ok:
            return jsonify({'error': 'Quran search module not available'}), 503

        data = request.get_json(force=True)
        text = data.get('text', '').strip()
        language = data.get('language', 'تدقيق الايات').strip()

        if not text:
            return jsonify({'error': 'النص المُدخل فارغ'}), 400

        if len(text) > 2000:
            return jsonify({'error': 'النص طويل جداً (الحد الأقصى 2000 حرف)'}), 400

        app.logger.info(f'[QURAN] Query: "{text[:60]}..." lang={language}')
        start_time = time.time()

        result = search_bayan(text, target_type=language)

        elapsed = int((time.time() - start_time) * 1000)
        app.logger.info(f'[QURAN] Done in {elapsed}ms')

        if 'error' in result:
            return jsonify(result), 404

        return jsonify(result)

    except Exception as e:
        app.logger.error(f'[QURAN] Error: {e}')
        app.logger.error(traceback.format_exc())
        return jsonify({'error': 'حدث خطأ أثناء البحث في القرآن الكريم'}), 500


@app.route('/api/analyze', methods=['POST'])
def analyze_text():
    """
    Perform sequential analysis (Spelling -> Grammar -> Punctuation) 
    and return word-level suggestions with offsets.
    """
    try:
        if not request.is_json:
            return jsonify({'error': 'Request must be JSON', 'status': 'error'}), 400
        
        data = request.get_json()
        text = data.get('text', '').strip()
        
        if not text:
            return jsonify({'error': 'Text is required', 'status': 'error'}), 400

        # ── Input Sanitization (Fix 3: prevent pathological model inputs) ──
        # Strip HTML tags — prevents AraSpell from doing exhaustive edit-distance
        # on tag characters like <script>, </div>, etc.
        text = re.sub(r'<[^>]*>', '', text).strip()
        if not text:
            return jsonify({'error': 'Text is required', 'status': 'error'}), 400

        # Reject inputs that are predominantly non-Arabic (code, markup, etc.)
        arabic_chars = len(re.findall(r'[\u0600-\u06FF]', text))
        alpha_chars = len(re.findall(r'[a-zA-Z\u0600-\u06FF]', text))
        if alpha_chars > 0 and arabic_chars / alpha_chars < 0.3:
            return jsonify({
                'original': text, 'corrected': text,
                'suggestions': [], 'timing_ms': {},
                'status': 'success'
            })

        # Pipeline state — PipelineContext carries all shared state
        ctx = PipelineContext(text)
        current_text = text  # Local alias (updated alongside ctx.current_text)
        suggestions = []     # Legacy — will be replaced by ctx.patches at response time
        mappers = []         # Legacy — will be replaced by ctx._offset_mappers
        total_start = time.time()
        timing_ms = {'spelling_ms': 0, 'grammar_ms': 0, 'punctuation_ms': 0, 'total_ms': 0}

        def map_range_to_original(start, end):
            """Legacy wrapper — delegates to PipelineContext."""
            return ctx.map_to_original(start, end)

        def _get_spelling_alternatives(original_word, best_correction, spell_checker, max_alts=3):
            """Generate alternative spelling suggestions for a word."""
            alts = []
            seen = {best_correction, original_word}

            # 1. Try edit distance 1 candidates from the spell checker's vocabulary
            try:
                clean_w = re.sub(r'[^\w]', '', original_word)
                edit_cands = spell_checker.edit_corrector.known(spell_checker.edit_corrector.edits1(clean_w))
                if edit_cands:
                    ranked = sorted(list(edit_cands), key=lambda x: spell_checker.vocab_manager.get_frequency_rank(x))
                    for c in ranked:
                        if c not in seen and len(alts) < max_alts - 1:
                            alts.append(c)
                            seen.add(c)
            except Exception:
                pass

            # 2. Always include 'keep as-is' as the last alternative
            # Return: [best_correction, alt1, alt2, ..., original_word(keep)]
            result = [best_correction] + alts + [original_word]
            return result[:max_alts + 1]  # cap at max_alts + keep-as-is

        # ── Smart Text Processing Strategy ──
        # Short (0-300 chars): full pipeline (Spelling + Grammar + Punctuation)
        # Medium (300-1000 chars): Grammar + Punctuation only (skip AraSpell)
        # Large (1000+ chars): Grammar + Punctuation only
        #
        # ── B6/E3 ARCHITECTURAL NOTE ──
        # For texts >300 chars, AraSpell is skipped for performance. Grammar
        # still handles most orthographic errors (ه→ة, hamza normalization,
        # ي↔ى) using its own model. This means long-text orthographic fixes
        # come from grammar's correction "budget" rather than spelling's.
        # This is by design — grammar is faster on long text and catches the
        # most common orthographic patterns. However, rare/literary vocabulary
        # protection (the confidence dampening from Phase 2) only applies to
        # spelling, not grammar. For long texts, grammar may still produce
        # some false positives on rare words.
        text_len = len(current_text)
        run_spelling = text_len <= 1000  # FIX-10: Increased from 300 to 1000
        if not run_spelling:
            logger.info(f"[ANALYZE] Text length {text_len} > 300 — skipping AraSpell for performance")

        # ── Batch 2+5: Religious text detection (moved before spelling) ──
        # Religious text must skip ALL stages (spelling + grammar + punctuation)
        # to prevent ه→ة corruption (إله→إلة, لسانه→لسانة, etc.)
        _RELIGIOUS_PHRASES = [
            # Quran opening/common
            'بسم الله', 'الحمد لله', 'سبحان الله', 'لا إله إلا الله',
            'إياك نعبد', 'قل هو الله', 'قل أعوذ', 'إنا أنزلناه',
            'حسبنا الله', 'لا حول ولا قوة', 'أستغفر الله',
            'الله أكبر', 'إنا لله', 'اللهم صل', 'وإياك نستعين',
            'ذلك الكتاب لا ريب', 'مالك يوم الدين', 'لم يلد ولم يولد',
            'الله لا إله إلا هو', 'الرحمن الرحيم', 'رب العالمين',
            'إنما الأعمال بالنيات', 'السلام عليكم ورحمة الله',
            'صراط الذين أنعمت', 'من شر ما خلق', 'ملك الناس',
            'رب اشرح لي صدري', 'ربنا آتنا',
            'قل أعوذ برب الناس', 'الحي القيوم',
            'لا تأخذه سنة ولا نوم', 'أشهد أن لا إله',
            'أشهد أن محمد', 'إنما الأعمال',
            'من حسن إسلام المرء', 'سبحان الله وبحمده',
            'الله أكبر كبير', 'إله الناس', 'من شر الوسواس',
            'وأشهد أن', 'رسول الله', 'كرسيه السماوات',
            'وسع كرسيه', 'في السماوات وما في الأرض',
            'عليه وسلم', 'صلى الله عليه',
            'المسلم من سلم المسلمون',   # R016
            'لا يؤمن أحدكم',               # R017
            'اهدنا الصراط',                # R004 Fatiha
        ]
        _is_religious_text = any(phrase in ctx.current_text for phrase in _RELIGIOUS_PHRASES)
        if _is_religious_text:
            logger.info(f"[ANALYZE] Religious text detected — skipping ALL stages")
            # Skip ALL stages for religious text
            run_spelling = False

        # ── Batch 5: Skip spelling for text containing URLs/emails ──
        # The spelling model destroys URLs (https→htps, .com→. com)
        import re as _re_spell_guard
        _has_url = bool(_re_spell_guard.search(r'https?://\S+', ctx.current_text))
        _has_email = bool(_re_spell_guard.search(r'\S+@\S+\.\S+', ctx.current_text))
        _has_hashtag = bool(_re_spell_guard.search(r'#[\u0600-\u06FF\w]{2,}', ctx.current_text))
        _has_percent = bool(_re_spell_guard.search(r'\d+\.\d+%', ctx.current_text))
        _has_latin_word = bool(_re_spell_guard.search(r'\b[A-Za-z]{3,}\b', ctx.current_text))
        if _has_url or _has_email:
            logger.info(f"[ANALYZE] Text contains URLs/emails — skipping spelling")
            run_spelling = False
        elif _has_latin_word:
            logger.info(f"[ANALYZE] Text contains Latin words — skipping spelling")
            run_spelling = False
        elif _has_hashtag:
            logger.info(f"[ANALYZE] Text contains hashtags — skipping spelling")
            run_spelling = False
        elif _has_percent:
            logger.info(f"[ANALYZE] Text contains percentages — skipping spelling")
            run_spelling = False

        # 1. Spelling (with conservative post-filtering to avoid over-editing)
        if run_spelling:
            try:
                t0 = time.time()
                logger.info(f"[ANALYZE] Step 1: Spelling correction starting...")
                from nlp.spelling.araspell_service import get_spelling_model
                spell_checker = get_spelling_model()
                raw_corrected = spell_checker.correct(current_text)
                timing_ms['spelling_ms'] = int((time.time() - t0) * 1000)
                logger.info(f"[ANALYZE] Step 1: Spelling done in {timing_ms['spelling_ms']}ms")

                if raw_corrected != ctx.current_text:
                    orig_word_positions = get_word_positions(ctx.current_text)
                    corr_word_positions = get_word_positions(raw_corrected)

                    orig_word_strings = [w[0] for w in orig_word_positions]
                    corr_word_strings = [w[0] for w in corr_word_positions]

                    s = difflib.SequenceMatcher(None, orig_word_strings, corr_word_strings)
                    new_words = []

                    for tag, i1, i2, j1, j2 in s.get_opcodes():
                        if tag == 'equal':
                            start_idx = orig_word_positions[i1][1]
                            end_idx = orig_word_positions[i2-1][2]
                            new_words.append(current_text[start_idx:end_idx])
                        elif tag == 'replace':
                            o_segment = orig_word_strings[i1:i2]
                            c_segment = corr_word_strings[j1:j2]

                            start_idx = orig_word_positions[i1][1]
                            end_idx = orig_word_positions[i2-1][2]

                            if len(o_segment) == 1 and len(c_segment) == 1:
                                # 1-word → 1-word: accept only small edits (typos)
                                o_word = o_segment[0]
                                c_word = c_segment[0]
                                _spell_conf = _is_small_spelling_change(o_word, c_word, spell_checker.vocab_manager)
                                if _spell_conf:
                                    logger.info(f"[SPELLING] Accepted: '{o_word}'→'{c_word}' (conf={_spell_conf})")
                                    new_words.append(c_word)
                                    ctx.add_patch(
                                        'spelling', start_idx, end_idx,
                                        c_word, confidence=_spell_conf,
                                        alternatives=_get_spelling_alternatives(o_word, c_word, spell_checker),
                                    )
                                else:
                                    logger.info(f"[SPELLING] Rejected: '{o_word}'→'{c_word}' (filter blocked)")
                                    new_words.append(current_text[start_idx:end_idx])
                            elif len(o_segment) == 1 and len(c_segment) > 1:
                                # 1-word → N words: accept word splits (e.g. فيالمدرسة → في المدرسة)
                                o_word = o_segment[0]
                                if len(o_word) >= 5 and ' ' not in o_word:
                                    corr_str = " ".join(c_segment)
                                    # ── Phase 3 (BUG-021/028/029): validate split parts ──
                                    # Reject splits where any part is a dangling fragment
                                    _VALID_SINGLE_CHAR = {'و', 'ب', 'ل', 'ك', 'ف', 'أ'}
                                    _parts_ok = all(
                                        len(p) >= 2 or p in _VALID_SINGLE_CHAR
                                        for p in c_segment
                                    )
                                    # Phase 3.2: Reject splits that detach known pronoun suffixes
                                    # from nouns (e.g. مستشفياتهم → مستشفيات هم is WRONG)
                                    _ATTACHED_PRONOUNS = {
                                        'هم', 'هن', 'ها', 'هما', 'كم', 'كن', 'نا',
                                        'ه', 'ك',  # single-char pronouns
                                    }
                                    if _parts_ok and len(c_segment) == 2:
                                        last_part = c_segment[-1]
                                        if last_part in _ATTACHED_PRONOUNS:
                                            # Check if joined form ≈ original (pronoun was attached)
                                            joined_no_space = ''.join(c_segment)
                                            if _levenshtein(o_word, joined_no_space) <= 2:
                                                _parts_ok = False
                                                logger.info(
                                                    f"[SPELLING] Rejected split: '{o_word}'→'{corr_str}' "
                                                    f"(detached pronoun suffix '{last_part}')"
                                                )
                                    if _parts_ok:
                                        new_words.append(corr_str)
                                        ctx.add_patch(
                                            'spelling', start_idx, end_idx,
                                            corr_str, confidence=0.85,
                                            alternatives=[corr_str, o_word],
                                        )
                                    else:
                                        logger.info(
                                            f"[SPELLING] Rejected split: '{o_word}'→'{corr_str}' "
                                            f"(dangling fragment in parts: {c_segment})"
                                        )
                                        new_words.append(current_text[start_idx:end_idx])
                                else:
                                    new_words.append(current_text[start_idx:end_idx])
                            else:
                                # N→M replacement: process each original word individually
                                # Build a mapping by trying to match original words to corrected words
                                corr_joined = " ".join(c_segment)
                                ci = 0  # cursor into c_segment
                                for oi in range(i1, i2):
                                    o_word = orig_word_strings[oi]
                                    o_start = orig_word_positions[oi][1]
                                    o_end = orig_word_positions[oi][2]

                                    if ci < len(c_segment):
                                        c_word = c_segment[ci]
                                        # Check if this is a 1→1 small edit
                                        _spell_conf2 = _is_small_spelling_change(o_word, c_word, spell_checker.vocab_manager)
                                        if _spell_conf2:
                                            new_words.append(c_word)
                                            ctx.add_patch(
                                                'spelling', o_start, o_end,
                                                c_word, confidence=_spell_conf2,
                                                alternatives=_get_spelling_alternatives(o_word, c_word, spell_checker),
                                            )
                                            ci += 1
                                        # Check if this is a 1→N word split
                                        elif len(o_word) >= 5 and ci + 1 < len(c_segment):
                                            # Try to consume multiple corrected words for this one original word
                                            split_parts = [c_segment[ci]]
                                            temp_ci = ci + 1
                                            joined = c_segment[ci]
                                            while temp_ci < len(c_segment) and len(joined) < len(o_word) + 2:
                                                joined += c_segment[temp_ci]
                                                split_parts.append(c_segment[temp_ci])
                                                temp_ci += 1
                                            # Check if the joined parts roughly match the original
                                            corr_str = " ".join(split_parts)
                                            joined_no_space = "".join(split_parts)
                                            dist = _levenshtein(o_word, joined_no_space)
                                            # ── Phase 3 (BUG-021/028/029): validate split parts ──
                                            _VALID_SC = {'و', 'ب', 'ل', 'ك', 'ف', 'أ'}
                                            _parts_ok = all(
                                                len(p) >= 2 or p in _VALID_SC
                                                for p in split_parts
                                            )
                                            # Phase 3.2: Reject splits detaching pronoun suffixes
                                            _ATTACHED_PRON = {
                                                'هم', 'هن', 'ها', 'هما', 'كم', 'كن', 'نا',
                                                'ه', 'ك',
                                            }
                                            if _parts_ok and len(split_parts) == 2:
                                                if split_parts[-1] in _ATTACHED_PRON:
                                                    if _levenshtein(o_word, joined_no_space) <= 2:
                                                        _parts_ok = False
                                                        logger.info(
                                                            f"[SPELLING] Rejected N→M split: '{o_word}'→'{corr_str}' "
                                                            f"(detached pronoun suffix '{split_parts[-1]}')"
                                                        )
                                            if dist <= 3 and len(split_parts) > 1 and _parts_ok:
                                                new_words.append(corr_str)
                                                ctx.add_patch(
                                                    'spelling', o_start, o_end,
                                                    corr_str, confidence=0.85,
                                                    alternatives=[corr_str, o_word],
                                                )
                                                ci = temp_ci
                                            else:
                                                if not _parts_ok:
                                                    logger.info(
                                                        f"[SPELLING] Rejected N→M split: '{o_word}'→'{corr_str}' "
                                                        f"(dangling fragment)"
                                                    )
                                                new_words.append(current_text[o_start:o_end])
                                                ci += 1
                                        else:
                                            new_words.append(current_text[o_start:o_end])
                                            ci += 1
                                    else:
                                        new_words.append(current_text[o_start:o_end])
                        elif tag == 'delete':
                            for idx in range(i1, i2):
                                new_words.append(current_text[orig_word_positions[idx][1]:orig_word_positions[idx][2]])
                        elif tag == 'insert':
                            continue

                    safe_text = " ".join(new_words)
                    ctx.mutate_text(safe_text, OffsetMapper)
                    current_text = ctx.current_text
            except Exception as e:
                logger.error(f"[ANALYZE] Spelling failed: {type(e).__name__}: {e}")
                logger.error(traceback.format_exc())
                timing_ms['spelling_error'] = f"{type(e).__name__}: {str(e)[:200]}"

        # ── FIX-07: Religious text already detected above (before spelling) ──
        # _is_religious_text was set earlier to skip ALL stages for sacred text

        # ── FIX-03: Structured content protection ──
        # Protect URLs, emails, dates, code etc. from grammar model destruction
        _PROTECTED_PATTERNS = [
            r'https?://\S+',           # URLs
            r'\S+@\S+\.\S+',           # Emails
            r'\d{1,2}[/\-\.]\d{1,2}[/\-\.]\d{2,4}',  # Dates
            r'\d{1,2}:\d{2}',          # Times
            r'#[\u0600-\u06FF\w]+',     # Hashtags
            r'@[\w]+',                 # Mentions
            r'\+?\d{10,13}',           # Phone numbers
            r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}',  # IP addresses
            r'v\d+\.\d+\.\d+',         # Version numbers
        ]
        _structured_placeholders = []  # (start, end, original_text, label)
        _grammar_input_text = ctx.current_text
        if not _is_religious_text:
            import re as _re_struct
            for _pat in _PROTECTED_PATTERNS:
                for _m in _re_struct.finditer(_pat, _grammar_input_text):
                    _structured_placeholders.append((_m.start(), _m.end(), _m.group()))
            # Replace structured content with Arabic placeholder tokens
            if _structured_placeholders:
                _structured_placeholders.sort(key=lambda x: x[0], reverse=True)
                for _sp_start, _sp_end, _sp_text in _structured_placeholders:
                    _grammar_input_text = _grammar_input_text[:_sp_start] + 'بيان' + _grammar_input_text[_sp_end:]
                logger.info(f"[ANALYZE] Protected {len(_structured_placeholders)} structured elements")

        # 2. Grammar (runs on spelling-corrected text — word-level dependency)
        if not _is_religious_text:
          try:
            t0 = time.time()
            logger.info(f"[ANALYZE] Step 2: Grammar correction starting...")
            from nlp.grammar.grammar_service import get_grammar_model
            grammar_checker = get_grammar_model()
            corrected_grammar = grammar_checker.correct(_grammar_input_text)
            timing_ms['grammar_ms'] = int((time.time() - t0) * 1000)
            logger.info(f"[ANALYZE] Step 2: Grammar done in {timing_ms['grammar_ms']}ms")

            # FIX-03: Restore structured content in grammar output
            if _structured_placeholders:
                # Restore in forward order
                for _sp_start, _sp_end, _sp_text in reversed(_structured_placeholders):
                    corrected_grammar = corrected_grammar.replace('بيان', _sp_text, 1)

            if corrected_grammar != ctx.current_text:
                diffs = get_word_diffs(ctx.current_text, corrected_grammar)
                _grammar_accepted_diffs = []  # FIX-04: track accepted diffs
                for d in diffs:
                    # StageLocker: skip diffs that overlap with locked ranges
                    if ctx.stage_locker.is_locked(d['start'], d['end']):
                        logger.info(
                            f"[LOCK] Grammar blocked on [{d['start']}:{d['end']}] "
                            f"'{d.get('original','')}' — locked by previous stage"
                        )
                        continue

                    # Reject grammar hallucinations (e.g. جالس→جاكسون)
                    orig_text = d.get('original', '')
                    corr_text = d.get('correction', '')
                    if orig_text and corr_text:
                        orig_chars = set(orig_text.replace(' ', ''))
                        corr_chars = set(corr_text.replace(' ', ''))
                        if orig_chars and corr_chars:
                            jaccard = len(orig_chars & corr_chars) / len(orig_chars | corr_chars)
                            if jaccard < 0.3:
                                logger.info(
                                    f"[GRAMMAR] Rejected hallucination: '{orig_text}'→'{corr_text}' "
                                    f"(jaccard={jaccard:.2f})"
                                )
                                continue

                    # ── FIX-13: Named entity protection ──
                    # Reject grammar changes to words that look like proper nouns:
                    # - Title case Latin words (proper nouns in mixed text)
                    # - Single words where the grammar just adds/removes spaces
                    if orig_text and corr_text:
                        # If original has no spaces but correction does (grammar split a name)
                        _has_latin = any('A' <= c <= 'Z' or 'a' <= c <= 'z' for c in orig_text)
                        if _has_latin and orig_text != corr_text:
                            logger.info(
                                f"[GRAMMAR] Skipping entity (contains Latin): "
                                f"'{orig_text}'→'{corr_text}'"
                            )
                            continue

                    # ── FIX-22: Emoji protection ──
                    # Don't let grammar split/modify emoji sequences
                    import re as _re_emoji
                    if orig_text and _re_emoji.search(r'[\U0001F300-\U0001F9FF]', orig_text):
                        logger.info(
                            f"[GRAMMAR] Skipping emoji content: '{orig_text}'"
                        )
                        continue

                    # ── FIX-23: Tanween removal blocker ──
                    # The grammar model often strips tanween (ً/ٌ/ٍ) from correct text.
                    # Block diffs where the only change is tanween removal.
                    if orig_text and corr_text:
                        import re as _re_tnwn
                        _TANWEEN = '\u064B\u064C\u064D'  # ً ٌ ٍ
                        _orig_no_tnwn = _re_tnwn.sub(f'[{_TANWEEN}]', '', orig_text)
                        _corr_no_tnwn = _re_tnwn.sub(f'[{_TANWEEN}]', '', corr_text)
                        if _orig_no_tnwn == _corr_no_tnwn and orig_text != corr_text:
                            logger.info(
                                f"[GRAMMAR] Blocked tanween removal: "
                                f"'{orig_text}'→'{corr_text}'"
                            )
                            continue

                    # ── FIX-24: Grammar punctuation stripping blocker ──
                    # The grammar model removes periods/punctuation from end of text.
                    # e.g., 'البلاد.' → 'البلاد' — this is WRONG, the period is correct.
                    # Block diffs where the only change is punctuation removal/addition.
                    if orig_text and corr_text:
                        import re as _re_pstrip
                        _PUNCT_CHARS = '.,،؛;:!؟?()[]{}«»\"\'…'
                        _orig_stripped = orig_text.strip(_PUNCT_CHARS)
                        _corr_stripped = corr_text.strip(_PUNCT_CHARS)
                        if _orig_stripped == _corr_stripped and orig_text != corr_text:
                            logger.info(
                                f"[GRAMMAR] Blocked punct stripping: "
                                f"'{orig_text}'→'{corr_text}'"
                            )
                            continue
                        # Also block combined tanween + punct stripping
                        _TANWEEN2 = '\u064B\u064C\u064D'
                        _orig_clean = _re_pstrip.sub(f'[{_TANWEEN2}]', '', _orig_stripped)
                        _corr_clean = _re_pstrip.sub(f'[{_TANWEEN2}]', '', _corr_stripped)
                        if _orig_clean == _corr_clean and orig_text != corr_text:
                            logger.info(
                                f"[GRAMMAR] Blocked tanween+punct strip: "
                                f"'{orig_text}'→'{corr_text}'"
                            )
                            continue

                    # ── FIX-25: Grammar punctuation spacing blocker ──
                    # The grammar model inserts spaces around punctuation:
                    # e.g., 'حالك؟' → 'حالك ؟', 'المكتبة،' → 'المكتبة ،'
                    # Block diffs where the only change is spacing around punct.
                    if orig_text and corr_text:
                        import re as _re_psp
                        # Normalize: collapse spaces around common punct marks
                        def _norm_punct_spacing(t):
                            # Remove spaces before/after common punct
                            t = _re_psp.sub(r'\s+([.,:;!?\u060C\u061B\u061F\u0021%$)}\]>])', r'\1', t)
                            t = _re_psp.sub(r'([({\[<])\s+', r'\1', t)
                            return t
                        _orig_normed = _norm_punct_spacing(orig_text)
                        _corr_normed = _norm_punct_spacing(corr_text)
                        if _orig_normed == _corr_normed and orig_text != corr_text:
                            logger.info(
                                f"[GRAMMAR] Blocked punct spacing: "
                                f"'{orig_text}'\u2192'{corr_text}'"
                            )
                            continue

                    # ── FIX-27a: Grammar structured data protection ──
                    # Block grammar diffs where the original contains digits.
                    # The grammar model corrupts dates/numbers/times/percentages.
                    # e.g., '2026-06-22' → 'عشرين 26-06-22ا'
                    if orig_text and any(c.isdigit() for c in orig_text):
                        logger.info(
                            f"[GRAMMAR] Blocked digit-containing diff: "
                            f"'{orig_text}'\u2192'{corr_text}'"
                        )
                        continue

                    # ── FIX-27b: Grammar hallucination guard (Jaccard) ──
                    # Block grammar diffs where the correction is too different
                    # from the original (character-level Jaccard < 0.5).
                    # Catches: القانون→القانين, يعزف→يعزفون, للإنسان→للإنسين
                    if orig_text and corr_text and len(orig_text) > 2:
                        import re as _re_jac
                        # Strip punctuation/spaces for comparison
                        _o_chars = set(_re_jac.sub(r'[\s.,،؛؟!:;?]', '', orig_text))
                        _c_chars = set(_re_jac.sub(r'[\s.,،؛؟!:;?]', '', corr_text))
                        if _o_chars and _c_chars:
                            _jac = len(_o_chars & _c_chars) / len(_o_chars | _c_chars)
                            if _jac < 0.5:
                                logger.info(
                                    f"[GRAMMAR] Blocked low-Jaccard diff (j={_jac:.2f}): "
                                    f"'{orig_text}'\u2192'{corr_text}'"
                                )
                                continue

                    # ── FIX-06: Directional block protection for grammar ──
                    # Prevents meaning-changing substitutions (كان→كأن etc.)
                    # especially critical when spelling is skipped (>1000 chars).
                    if corr_text in _DIRECTIONAL_BLOCKS.get(orig_text, set()):
                        logger.info(
                            f"[GRAMMAR] Directional block: '{orig_text}'→'{corr_text}'"
                        )
                        continue
                    # Also check with clitic prefixes
                    _gram_dir_blocked = False
                    for _gpfx in ('و', 'ف', 'ب', 'ل', 'ك'):
                        if (orig_text.startswith(_gpfx) and corr_text.startswith(_gpfx)
                                and len(orig_text) > len(_gpfx) + 1):
                            _g_orig_stem = orig_text[len(_gpfx):]
                            _g_corr_stem = corr_text[len(_gpfx):]
                            if _g_corr_stem in _DIRECTIONAL_BLOCKS.get(_g_orig_stem, set()):
                                logger.info(
                                    f"[GRAMMAR] Directional block (prefixed): "
                                    f"'{orig_text}'→'{corr_text}'"
                                )
                                _gram_dir_blocked = True
                                break
                    if _gram_dir_blocked:
                        continue

                    # ── Phase 4 (BUG-033/E10): Grammar output sanity check ──
                    # Reject grammar corrections that produce a non-word when
                    # the original was already a valid word. Mirrors spelling filter.
                    # BUT: bypass for known grammar patterns (case endings, nasb, etc.)
                    _is_grammar_pattern = False
                    if orig_text and corr_text:
                        # Case: ون/ان → ين (sound masculine plural case)
                        if (orig_text.endswith('ون') and corr_text.endswith('ين') and
                                orig_text[:-2] == corr_text[:-2]):
                            _is_grammar_pattern = True
                        # Nasb/Jazm: ون → وا (verb mood)
                        elif (orig_text.endswith('ون') and corr_text.endswith('وا') and
                                orig_text[:-2] == corr_text[:-2]):
                            _is_grammar_pattern = True
                        # Five nouns: وك → اك/يك (أبوك→أباك, أخوك→أخيك)
                        elif (len(orig_text) >= 3 and len(corr_text) >= 3 and
                                orig_text[-2:] in ('وك', 'وه') and
                                corr_text[-2:] in ('اك', 'يك', 'اه', 'يه')):
                            _is_grammar_pattern = True
                        # Dual: ان → ين (dual oblique)
                        elif (orig_text.endswith('ان') and corr_text.endswith('ين') and
                                orig_text[:-2] == corr_text[:-2] and len(orig_text) >= 4):
                            _is_grammar_pattern = True
                        # Demonstrative: هذان→هاتان, هاتان→هذان
                        elif ({orig_text, corr_text} <= {'هذان', 'هاتان'}):
                            _is_grammar_pattern = True
                        # ── NEW: SV agreement suffix additions ──
                        # Past tense masc plural: verb→verb+وا (ذهب→ذهبوا, حضر→حضروا)
                        elif (corr_text.endswith('وا') and corr_text[:-2] == orig_text
                                and len(orig_text) >= 3):
                            _is_grammar_pattern = True
                        # Past tense fem plural: verb→verb+ن (ذهب→ذهبن, حضر→حضرن)
                        elif (corr_text.endswith('ن') and corr_text[:-1] == orig_text
                                and len(orig_text) >= 3):
                            _is_grammar_pattern = True
                        # Present tense masc plural: يفعل→يفعلون (adding ون)
                        elif (corr_text.endswith('ون') and corr_text[:-2] == orig_text
                                and len(orig_text) >= 3):
                            _is_grammar_pattern = True
                        # Gender: adjective→adjective+ة (جميل→جميلة, كبير→كبيرة)
                        elif (corr_text.endswith('ة') and corr_text[:-1] == orig_text
                                and len(orig_text) >= 3):
                            _is_grammar_pattern = True
                        # Gender with ي: ذكي→ذكية
                        elif (corr_text.endswith('ية') and corr_text[:-1] == orig_text[:-1] + 'ي'
                                and orig_text.endswith('ي') and len(orig_text) >= 3):
                            _is_grammar_pattern = True


                    if not _is_grammar_pattern:
                        if len(orig_text.split()) == 1 and len(corr_text.split()) == 1:
                            try:
                                from nlp.spelling.araspell_service import get_spelling_model
                                _vm = get_spelling_model().vocab_manager
                                if _vm and _vm.is_iv(orig_text) and _vm.is_oov(corr_text):
                                    logger.info(
                                        f"[GRAMMAR] Rejected corruption: '{orig_text}'→'{corr_text}' "
                                        f"(valid word → non-word)"
                                    )
                                    continue
                            except Exception:
                                pass

                    # FIX-22: Protect tanween (preserve ً ٌ ٍ from original)
                    _TANWEEN_CHARS = set('ًٌٍ')
                    if any(c in _TANWEEN_CHARS for c in orig_text) and not any(c in _TANWEEN_CHARS for c in corr_text):
                        # Grammar stripped tanween — reattach it
                        for _tc in _TANWEEN_CHARS:
                            if _tc in orig_text and _tc not in corr_text:
                                corr_text = corr_text + _tc
                                break

                    # Re-label: if grammar's change is purely orthographic
                    # (hamza, ه→ة, etc.), tag it as 'spelling' for correct UI icon
                    stage_label = 'grammar'
                    if _is_spelling_only_change(orig_text, corr_text):
                        stage_label = 'spelling'
                    _grammar_accepted_diffs.append(d)  # FIX-04: track accepted
                    ctx.add_patch(
                        stage_label, d['start'], d['end'],
                        corr_text, confidence=1.0
                    )

                # ── B7 (E6): Bracket-balance guard ──
                # If grammar's output lost brackets, reject the grammar correction.
                _OPEN_BRACKETS = set('([{')
                _CLOSE_BRACKETS = set(')]}')
                orig_opens = sum(1 for c in ctx.current_text if c in _OPEN_BRACKETS)
                orig_closes = sum(1 for c in ctx.current_text if c in _CLOSE_BRACKETS)
                corr_opens = sum(1 for c in corrected_grammar if c in _OPEN_BRACKETS)
                corr_closes = sum(1 for c in corrected_grammar if c in _CLOSE_BRACKETS)
                orig_balanced = (orig_opens == orig_closes)
                corr_balanced = (corr_opens == corr_closes)
                if orig_balanced and not corr_balanced:
                    logger.info(
                        f"[GRAMMAR] Rejected bracket-unbalanced output: "
                        f"orig=({orig_opens},{orig_closes}), corr=({corr_opens},{corr_closes})"
                    )
                    # Don't mutate text — keep pre-grammar text
                elif _grammar_accepted_diffs:
                    # FIX-04: Rebuild grammar text from ACCEPTED diffs only,
                    # not the full model output. Prevents phantom corrections.
                    _safe_grammar = ctx.current_text
                    # Apply accepted diffs in reverse order to build safe text
                    for _ad in sorted(_grammar_accepted_diffs, key=lambda x: x['start'], reverse=True):
                        _safe_grammar = (_safe_grammar[:_ad['start']] +
                                        _ad['correction'] +
                                        _safe_grammar[_ad['end']:])
                    ctx.mutate_text(_safe_grammar, OffsetMapper)
                current_text = ctx.current_text
          except Exception as e:
            logger.error(f"[ANALYZE] Grammar failed: {type(e).__name__}: {e}")
            logger.error(traceback.format_exc())
            timing_ms['grammar_error'] = f"{type(e).__name__}: {str(e)[:200]}"

        # 3. Punctuation (runs on grammar-corrected text — PuncAra-v1 local model)
        # FIX-07: Skip punctuation for religious text
        if not _is_religious_text:
          try:
            t0 = time.time()
            logger.info(f"[ANALYZE] Step 3: Punctuation starting...")
            from nlp.punctuation.punctuation_service import get_punctuation_model
            punc_checker = get_punctuation_model()
            corrected_punc = punc_checker.correct(ctx.current_text)
            timing_ms['punctuation_ms'] = int((time.time() - t0) * 1000)
            logger.info(f"[ANALYZE] Step 3: Punctuation done in {timing_ms['punctuation_ms']}ms")
            if corrected_punc != ctx.current_text:
                diffs = get_word_diffs(ctx.current_text, corrected_punc)
                for d in diffs:
                    # StageLocker: skip diffs that overlap with locked ranges
                    # BUT allow pure punctuation insertions near locked words
                    lock_info = ctx.stage_locker.is_locked_by(d['start'], d['end'])
                    if lock_info:
                        import re as _re
                        orig_alpha = _re.sub(r'[^\u0600-\u06FFa-zA-Z]', '', d.get('original', ''))
                        corr_alpha = _re.sub(r'[^\u0600-\u06FFa-zA-Z]', '', d.get('correction', ''))
                        ls, le, owner = lock_info
                        if orig_alpha != corr_alpha:
                            # Diff changes actual words — block it
                            logger.info(
                                f"[LOCK] Punctuation blocked on [{d['start']}:{d['end']}] "
                                f"'{d.get('original','')}' \u2014 locked by {owner}[{ls}:{le}]"
                            )
                            continue
                        # Arabic text unchanged — only punctuation added/moved. Allow through.
                        logger.info(
                            f"[LOCK] Punctuation ALLOWED through lock [{d['start']}:{d['end']}] "
                            f"'{d.get('original','')}' \u2192 '{d.get('correction','')}' "
                            f"(locked by {owner}[{ls}:{le}])"
                        )
                    # Punctuation safety layer: reject non-punctuation changes
                    if not validate_punctuation_diff(d):
                        logger.info(
                            f"[PUNC-SAFETY] Rejected diff [{d['start']}:{d['end']}] "
                            f"'{d.get('original','')}' → '{d.get('correction','')}' — not a safe punctuation change"
                        )
                        continue
                    ctx.add_patch(
                        'punctuation', d['start'], d['end'],
                        d['correction'], confidence=0.8
                    )

                # ── Aggregate punctuation cap (Fix 4): max 3 punctuation patches per response ──
                MAX_PUNC_PATCHES_PER_RESPONSE = 3
                punc_patches = [p for p in ctx.patches.patches if p.stage == 'punctuation']
                if len(punc_patches) > MAX_PUNC_PATCHES_PER_RESPONSE:
                    # Keep earliest patches (by start_original) — consistent with PatchSet sort
                    punc_patches_sorted = sorted(punc_patches, key=lambda p: p.start_original)
                    to_remove = set(id(p) for p in punc_patches_sorted[MAX_PUNC_PATCHES_PER_RESPONSE:])
                    # FIX-18: Also remove StageLocker locks for capped patches
                    for _capped_p in punc_patches_sorted[MAX_PUNC_PATCHES_PER_RESPONSE:]:
                        ctx.stage_locker.unlock(_capped_p.start_original, _capped_p.end_original)
                    ctx.patches.patches = [p for p in ctx.patches.patches if id(p) not in to_remove]
                    logger.info(
                        f"[PUNC-CAP] Capped punctuation patches: "
                        f"{len(punc_patches)} → {MAX_PUNC_PATCHES_PER_RESPONSE}"
                    )

                # FIX-05: Rebuild punctuation text from accepted diffs only
                _safe_punc = ctx.current_text
                _punc_accepted = [d for d in diffs if validate_punctuation_diff(d)]
                for _pd in sorted(_punc_accepted, key=lambda x: x['start'], reverse=True):
                    _safe_punc = (_safe_punc[:_pd['start']] +
                                 _pd['correction'] +
                                 _safe_punc[_pd['end']:])
                ctx.mutate_text(_safe_punc, OffsetMapper)
                current_text = ctx.current_text
          except Exception as e:
            logger.error(f"[ANALYZE] Punctuation failed: {type(e).__name__}: {e}")
            logger.error(traceback.format_exc())
            timing_ms['punctuation_error'] = f"{type(e).__name__}: {str(e)[:200]}"

        total_time = time.time() - total_start
        timing_ms['total_ms'] = int(total_time * 1000)

        # ══════════════════════════════════════════════════════════
        # OVERLAP RESOLUTION — Pipeline Hardening v3.3
        # ══════════════════════════════════════════════════════════
        # PatchSet handles deterministic overlap resolution:
        #   Sort: priority DESC → confidence DESC → start ASC → id ASC
        #   One range = one owner. No stacking.
        suggestions = ctx.patches.to_list()

        # ── Rebuild 'corrected' from original + accepted patches (Fix 2) ──
        # This ensures 'corrected' exactly matches what you'd get by applying
        # all suggestions to 'original'. ctx.current_text includes StageLocker-
        # blocked and safety-rejected mutations and must NOT be used.
        def _apply_patches_to_original(original_text, suggestion_dicts):
            """Apply patches in reverse offset order to produce corrected text."""
            result = original_text
            # Sort by start DESC so offset shifts don't invalidate later patches
            for s in sorted(suggestion_dicts, key=lambda x: -x['start']):
                result = result[:s['start']] + s['correction'] + result[s['end']:]
            return result

        corrected = _apply_patches_to_original(text, suggestions)

        logger.info(f"[ANALYZE] Total: {timing_ms['total_ms']}ms | "
                    f"Spelling: {timing_ms['spelling_ms']}ms | "
                    f"Grammar: {timing_ms['grammar_ms']}ms | "
                    f"Punctuation: {timing_ms['punctuation_ms']}ms | "
                    f"Suggestions: {len(suggestions)}")

        # ── Phase 6 (BUG-032/E9): Signal partial results if any stage failed ──
        stage_errors = {k: v for k, v in timing_ms.items() if k.endswith('_error')}
        response_status = 'partial' if stage_errors else 'success'

        response_data = {
            'original': text,
            'corrected': corrected,
            'suggestions': suggestions,
            'timing_ms': timing_ms,
            'status': response_status,
        }
        if stage_errors:
            response_data['warnings'] = stage_errors

        return jsonify(response_data)

    except Exception as e:
        logger.error(f"Error during analysis: {str(e)}")
        logger.error(traceback.format_exc())
        return jsonify({
            'error': 'An error occurred during text analysis.',
            'status': 'error',
            'details': str(e) if app.debug else None
        }), 500


@app.errorhandler(404)
def not_found(error):
    """Handle 404 errors."""
    return jsonify({
        'error': 'Endpoint not found',
        'status': 'error'
    }), 404


@app.errorhandler(500)
def internal_error(error):
    """Handle 500 errors."""
    logger.error(f"Internal server error: {str(error)}")
    return jsonify({
        'error': 'Internal server error',
        'status': 'error'
    }), 500


# ── Gunicorn startup hook ──
# When running under gunicorn, __name__ != '__main__', so we need
# to load models eagerly when the module is imported.
_models_loaded = False

def _ensure_models_loaded():
    global _models_loaded
    if _models_loaded:
        return
    _models_loaded = True
    logger.info("Loading models (production startup)...")
    if not load_models():
        logger.error("Failed to load any models. Server will start but functionality will be limited.")

# Load models on import (gunicorn imports this module, __name__ != '__main__')
_ensure_models_loaded()


if __name__ == '__main__':
    # Load models on startup (development)
    _ensure_models_loaded()
    
    # Run the app
    port = int(os.environ.get('PORT', 5000))
    debug = os.environ.get('DEBUG', 'False').lower() == 'true'
    
    logger.info(f"Starting server on port {port} (debug={debug})")
    app.run(host='0.0.0.0', port=port, debug=debug)
