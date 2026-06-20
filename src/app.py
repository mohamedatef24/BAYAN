"""
Flask backend server for Arabic text summarization.
Provides API endpoints for the Bayan web application.
"""

import os
import logging
import time
import hashlib
from collections import OrderedDict
from functools import wraps
from flask import Flask, request, jsonify, Response
from flask_cors import CORS
from pathlib import Path
import traceback
import difflib
import re

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

# ── Response Cache (P3) ──
# LRU cache for /api/analyze: hash(text) → (response_dict, timestamp)
_ANALYZE_CACHE_MAX = 500
_ANALYZE_CACHE_TTL = 300  # 5 minutes
_analyze_cache = OrderedDict()

# ── Rate Limiter (P3) ──
_RATE_LIMIT_MAX = 30  # requests per window
_RATE_LIMIT_WINDOW = 60  # seconds
_rate_limit_store = {}  # ip → [(timestamp, ...)]

# ── Ta Marbuta Dictionary (P2) ──
# Common words where ه at the end should be ة
_TA_MARBUTA_DICT = {
    'المدرسه': 'المدرسة', 'الجامعه': 'الجامعة', 'المكتبه': 'المكتبة',
    'الحياه': 'الحياة', 'الصلاه': 'الصلاة', 'الزكاه': 'الزكاة',
    'القراءه': 'القراءة', 'الكتابه': 'الكتابة', 'المعرفه': 'المعرفة',
    'الثقافه': 'الثقافة', 'السياسه': 'السياسة', 'الاقتصاديه': 'الاقتصادية',
    'العربيه': 'العربية', 'الاسلاميه': 'الإسلامية', 'التربيه': 'التربية',
    'الشريعه': 'الشريعة', 'الدوله': 'الدولة', 'الحكومه': 'الحكومة',
    'المدينه': 'المدينة', 'القريه': 'القرية', 'الغرفه': 'الغرفة',
    'السياره': 'السيارة', 'الطاوله': 'الطاولة', 'الرساله': 'الرسالة',
    'المقاله': 'المقالة', 'الصحيفه': 'الصحيفة', 'الجريده': 'الجريدة',
    'القصه': 'القصة', 'الروايه': 'الرواية', 'اللغه': 'اللغة',
    'الفكره': 'الفكرة', 'الخطوه': 'الخطوة', 'المرحله': 'المرحلة',
    'النتيجه': 'النتيجة', 'المشكله': 'المشكلة', 'الطريقه': 'الطريقة',
    'الحاله': 'الحالة', 'الصوره': 'الصورة', 'القوه': 'القوة',
    'الوحده': 'الوحدة', 'العلاقه': 'العلاقة', 'التجربه': 'التجربة',
    'الحركه': 'الحركة', 'السلطه': 'السلطة', 'المنطقه': 'المنطقة',
    'الساعه': 'الساعة', 'اللحظه': 'اللحظة', 'الفتره': 'الفترة',
    'الاداره': 'الإدارة', 'البيئه': 'البيئة', 'الماده': 'المادة',
    'الاسره': 'الأسرة', 'العائله': 'العائلة', 'الشركه': 'الشركة',
    'المؤسسه': 'المؤسسة', 'المنظمه': 'المنظمة', 'الجمعيه': 'الجمعية',
    'الوزاره': 'الوزارة', 'السفاره': 'السفارة', 'القياده': 'القيادة',
    'الزياره': 'الزيارة', 'المحاوله': 'المحاولة', 'الدراسه': 'الدراسة',
    'الممارسه': 'الممارسة', 'المتابعه': 'المتابعة', 'الخدمه': 'الخدمة',
    'التقنيه': 'التقنية', 'الهندسه': 'الهندسة', 'الفلسفه': 'الفلسفة',
    'مدرسه': 'مدرسة', 'جامعه': 'جامعة', 'مكتبه': 'مكتبة',
    'حياه': 'حياة', 'صلاه': 'صلاة', 'زكاه': 'زكاة',
    'لغه': 'لغة', 'قصه': 'قصة', 'فكره': 'فكرة',
    'خطوه': 'خطوة', 'صوره': 'صورة', 'قوه': 'قوة',
    'سياره': 'سيارة', 'رساله': 'رسالة', 'ساعه': 'ساعة',
    'غرفه': 'غرفة', 'شركه': 'شركة', 'دوله': 'دولة',
}


def _fix_ta_marbuta(text):
    """Fix common ه→ة errors at pipeline level using dictionary lookup."""
    words = text.split()
    fixed_words = []
    changes = []
    pos = 0
    for word in words:
        start = text.find(word, pos)
        end = start + len(word)
        # Check bare word
        if word in _TA_MARBUTA_DICT:
            fixed_words.append(_TA_MARBUTA_DICT[word])
            changes.append({'start': start, 'end': end, 'original': word, 'correction': _TA_MARBUTA_DICT[word]})
        # Check word ending in ه that should be ة (pattern match)
        elif word.endswith('ه') and len(word) >= 3:
            candidate = word[:-1] + 'ة'
            if candidate in _TA_MARBUTA_DICT.values():
                fixed_words.append(candidate)
                changes.append({'start': start, 'end': end, 'original': word, 'correction': candidate})
            else:
                fixed_words.append(word)
        else:
            fixed_words.append(word)
        pos = end
    return ' '.join(fixed_words), changes


def _check_rate_limit(ip):
    """Check if IP has exceeded rate limit. Returns True if allowed."""
    now = time.time()
    if ip not in _rate_limit_store:
        _rate_limit_store[ip] = []
    # Clean old entries
    _rate_limit_store[ip] = [t for t in _rate_limit_store[ip] if now - t < _RATE_LIMIT_WINDOW]
    if len(_rate_limit_store[ip]) >= _RATE_LIMIT_MAX:
        return False
    _rate_limit_store[ip].append(now)
    return True


def _get_cache_key(text):
    """Generate cache key from text."""
    return hashlib.md5(text.encode('utf-8')).hexdigest()


def _get_cached_response(text):
    """Get cached response if exists and not expired."""
    key = _get_cache_key(text)
    if key in _analyze_cache:
        data, ts = _analyze_cache[key]
        if time.time() - ts < _ANALYZE_CACHE_TTL:
            _analyze_cache.move_to_end(key)
            return data
        else:
            del _analyze_cache[key]
    return None


def _set_cached_response(text, response_data):
    """Store response in cache."""
    key = _get_cache_key(text)
    _analyze_cache[key] = (response_data, time.time())
    # Evict oldest if over limit
    while len(_analyze_cache) > _ANALYZE_CACHE_MAX:
        _analyze_cache.popitem(last=False)


# Global model instances
summarization_model = None
spelling_model = None
autocomplete_model = None
grammar_model = None
punctuation_model = None


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
                'punctuation': _punctuation_available()
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
            'punctuation': punctuation_model is not None
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
                return int(i1 + ratio * (i2 - i1))
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
    _DIRECTIONAL_BLOCKS = {
        # Demonstratives: هذه (correct feminine) → هذة (misspelling) = ALWAYS wrong
        'هذه': {'هذة'},
        'هذا': {'هذة', 'هذه'},    # masculine → don't flip to feminine forms
        # Verb/particle confusion: كان (was) ↔ كأن (as if) = ALWAYS wrong
        'كان': {'كأن'},
        'كأن': {'كان'},
        # Preposition confusion: different meanings, both valid
        'إلى': {'على', 'علي'},
        'على': {'إلى', 'علي'},
        'علي': {'على'},           # proper name vs preposition
        # Conjunction: لكن (correct) ↔ لاكن (misspelling of لكن, never valid)
        'لكن': {'لاكن'},          # correct → misspelling = ALWAYS wrong
        # Demonstrative: ذلك (correct) ↔ ذالك (common misspelling)
        'ذلك': {'ذالك'},          # correct → misspelling = ALWAYS wrong
    }
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

    # ── GUARD 3: Word truncation protection (Phase 4, P3) ──
    # Reject corrections that significantly shorten a valid word.
    # E.g. الدمث→الدم (rare word truncated to different word).
    if vocab_manager and len(orig_word) - len(corr_word) >= 2:
        if vocab_manager.is_iv(orig_word):
            logger.info(f"[SPELLING] Blocked truncation: '{orig_word}'→'{corr_word}' (valid word shortened by {len(orig_word) - len(corr_word)} chars)")
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


@app.route('/api/analyze', methods=['POST'])
def analyze_text():
    # ── Rate Limiting (P3) ──
    client_ip = request.headers.get('X-Forwarded-For', request.remote_addr)
    if not _check_rate_limit(client_ip):
        return jsonify({
            'error': 'Rate limit exceeded. Please wait before making more requests.',
            'status': 'error'
        }), 429

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

        # ── Cache Check (P3) ──
        cached = _get_cached_response(text)
        if cached:
            logger.info(f"[ANALYZE] Cache hit for text (len={len(text)})")
            return jsonify(cached)

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
        run_spelling = text_len <= 300
        if not run_spelling:
            logger.info(f"[ANALYZE] Text length {text_len} > 300 — skipping AraSpell for performance")

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

        # ── Standalone hamza-fix pass (P1/P2) ──
        # fix_common_hamza handles common hamza errors that AraSpell missed
        # in sentence context: انت→أنت, الان→الآن, ام→أم, انا→أنا, etc.
        # This runs on the FULL text regardless of whether AraSpell ran.
        try:
            from nlp.spelling.araspell_rules import AraSpellPostProcessor
            hamza_fixed = AraSpellPostProcessor.fix_common_hamza(current_text)
            if hamza_fixed != current_text:
                hamza_diffs = get_word_diffs(current_text, hamza_fixed)
                for hd in hamza_diffs:
                    ctx.add_patch(
                        'spelling', hd['start'], hd['end'],
                        hd['correction'], confidence=0.95,
                    )
                    logger.info(f"[HAMZA-FIX] '{hd.get('original','')}' → '{hd.get('correction','')}'")
                ctx.mutate_text(hamza_fixed, OffsetMapper)
                current_text = ctx.current_text
        except Exception as e:
            logger.error(f"[ANALYZE] Hamza fix failed: {type(e).__name__}: {e}")

        # ── Ta Marbuta fix pass (P2) ──
        # Catches common ه→ة errors like المدرسه→المدرسة at pipeline level.
        try:
            ta_fixed, ta_changes = _fix_ta_marbuta(current_text)
            if ta_fixed != current_text:
                for tc in ta_changes:
                    ctx.add_patch(
                        'spelling', tc['start'], tc['end'],
                        tc['correction'], confidence=0.95,
                    )
                    logger.info(f"[TA-MARBUTA] '{tc['original']}' → '{tc['correction']}'")
                ctx.mutate_text(ta_fixed, OffsetMapper)
                current_text = ctx.current_text
        except Exception as e:
            logger.error(f"[ANALYZE] Ta Marbuta fix failed: {type(e).__name__}: {e}")

        # 2. Grammar (runs on spelling-corrected text — word-level dependency)
        try:
            t0 = time.time()
            logger.info(f"[ANALYZE] Step 2: Grammar correction starting...")
            from nlp.grammar.grammar_service import get_grammar_model
            grammar_checker = get_grammar_model()
            corrected_grammar = grammar_checker.correct(ctx.current_text)
            timing_ms['grammar_ms'] = int((time.time() - t0) * 1000)
            logger.info(f"[ANALYZE] Step 2: Grammar done in {timing_ms['grammar_ms']}ms")
            if corrected_grammar != ctx.current_text:
                diffs = get_word_diffs(ctx.current_text, corrected_grammar)

                # ── Phase 2 (P1): Split multi-word grammar diffs ──
                # Break merged diffs like "الي المدرسه الاستاذ"→"إلى المدرسة الأستاذ"
                # into individual word-level suggestions.
                expanded_diffs = []
                for d in diffs:
                    orig_text = d.get('original', '')
                    corr_text = d.get('correction', '')
                    orig_words_list = orig_text.split()
                    corr_words_list = corr_text.split()
                    # Only split if same word count and multiple words
                    if (len(orig_words_list) > 1
                            and len(orig_words_list) == len(corr_words_list)):
                        # Split into per-word diffs
                        search_from = d['start']
                        for ow, cw in zip(orig_words_list, corr_words_list):
                            if ow != cw:
                                w_start = ctx.current_text.find(ow, search_from)
                                if w_start >= 0:
                                    w_end = w_start + len(ow)
                                    expanded_diffs.append({
                                        'start': w_start, 'end': w_end,
                                        'original': ow, 'correction': cw,
                                        'type': 'generic'
                                    })
                                    search_from = w_end
                                else:
                                    search_from += len(ow) + 1
                            else:
                                search_from += len(ow) + 1
                    else:
                        expanded_diffs.append(d)

                for d in expanded_diffs:
                    # StageLocker: skip diffs that overlap with locked ranges
                    if ctx.stage_locker.is_locked(d['start'], d['end']):
                        logger.info(
                            f"[LOCK] Grammar blocked on [{d['start']}:{d['end']}] "
                            f"'{d.get('original','')}' — locked by previous stage"
                        )
                        continue

                    # ── Punctuation-protection guard ──
                    # Grammar model sometimes strips/normalizes punctuation
                    # (removes full stops, commas, etc.). Reject grammar diffs
                    # that only differ in punctuation marks — grammar should
                    # only fix grammar, not touch punctuation.
                    _orig_t = d.get('original', '')
                    _corr_t = d.get('correction', '')
                    _PUNC_CHARS = set('.,;:!?؟،؛。·…•–—\u200f\u200e')
                    _orig_no_punc = ''.join(c for c in _orig_t if c not in _PUNC_CHARS)
                    _corr_no_punc = ''.join(c for c in _corr_t if c not in _PUNC_CHARS)
                    if _orig_no_punc == _corr_no_punc:
                        # Only punctuation was changed — block it
                        if _orig_t != _corr_t:
                            logger.info(
                                f"[GRAMMAR] Blocked punctuation change: "
                                f"'{_orig_t}' → '{_corr_t}' (grammar must not alter punctuation)"
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

                    # ── Phase 4 (BUG-033/E10): Grammar output sanity check ──
                    # Reject grammar corrections that produce a non-word when
                    # the original was already a valid word. Mirrors spelling filter.
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

                    # Re-label: if grammar's change is purely orthographic
                    # (hamza, ه→ة, etc.), tag it as 'spelling' for correct UI icon
                    stage_label = 'grammar'
                    if _is_spelling_only_change(orig_text, corr_text):
                        stage_label = 'spelling'
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
                else:
                    ctx.mutate_text(corrected_grammar, OffsetMapper)
                current_text = ctx.current_text
        except Exception as e:
            logger.error(f"[ANALYZE] Grammar failed: {type(e).__name__}: {e}")
            logger.error(traceback.format_exc())
            timing_ms['grammar_error'] = f"{type(e).__name__}: {str(e)[:200]}"

        # 3. Punctuation (runs on grammar-corrected text — PuncAra-v1 local model)
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
                    ctx.patches.patches = [p for p in ctx.patches.patches if id(p) not in to_remove]
                    logger.info(
                        f"[PUNC-CAP] Capped punctuation patches: "
                        f"{len(punc_patches)} → {MAX_PUNC_PATCHES_PER_RESPONSE}"
                    )

                ctx.mutate_text(corrected_punc, OffsetMapper)
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

        # ── Cache Store (P3) ──
        if response_status == 'success':
            _set_cached_response(text, response_data)

        return jsonify(response_data)

    except Exception as e:
        logger.error(f"Error during analysis: {str(e)}")
        logger.error(traceback.format_exc())
        return jsonify({
            'error': 'An error occurred during text analysis.',
            'status': 'error',
            'details': str(e) if app.debug else None
        }), 500


@app.route('/api/feedback', methods=['POST'])
def submit_feedback():
    """Accept user feedback on correction suggestions."""
    try:
        if not request.is_json:
            return jsonify({'error': 'Request must be JSON', 'status': 'error'}), 400

        data = request.get_json()
        suggestion_id = data.get('suggestion_id', '')
        helpful = data.get('helpful', None)
        text = data.get('text', '')[:200]  # Truncate for safety
        original = data.get('original', '')[:100]
        correction = data.get('correction', '')[:100]

        if helpful is None:
            return jsonify({'error': 'helpful field is required', 'status': 'error'}), 400

        # Log feedback (simple file-based for now)
        feedback_entry = {
            'timestamp': time.strftime('%Y-%m-%d %H:%M:%S'),
            'suggestion_id': suggestion_id,
            'helpful': helpful,
            'original': original,
            'correction': correction,
            'text_snippet': text,
            'ip': request.headers.get('X-Forwarded-For', request.remote_addr),
        }
        logger.info(f"[FEEDBACK] {feedback_entry}")

        # Append to feedback log file
        try:
            feedback_dir = Path(__file__).parent.parent / 'logs'
            feedback_dir.mkdir(exist_ok=True)
            with open(feedback_dir / 'feedback.jsonl', 'a', encoding='utf-8') as f:
                import json
                f.write(json.dumps(feedback_entry, ensure_ascii=False) + '\n')
        except Exception as log_err:
            logger.warning(f"[FEEDBACK] Could not write to file: {log_err}")

        return jsonify({'status': 'success', 'message': 'شكراً لملاحظاتك!'})

    except Exception as e:
        logger.error(f"[FEEDBACK] Error: {e}")
        return jsonify({'error': 'Failed to submit feedback', 'status': 'error'}), 500


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
