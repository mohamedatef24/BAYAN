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


def load_models():
    """Load models. In HF API mode, skip local loading entirely."""
    global summarization_model, spelling_model, autocomplete_model, grammar_model, punctuation_model
    
    if USE_HF_API:
        logger.info("HF_API_TOKEN is set — using HuggingFace Inference API (no local models loaded)")
        logger.info("Models will be called remotely: summarization, spelling, punctuation, autocomplete")
        return True
    
    loaded = []
    failed = []

    # Load only the Summarization model locally (dev mode).
    try:
        logger.info(f"Loading summarization model from Hugging Face: {HUGGINGFACE_SUMMARIZATION_REPO}")
        try:
            summarization_model = SummarizationModel(HUGGINGFACE_SUMMARIZATION_REPO)
        except Exception as remote_error:
            logger.warning(f"Remote load failed, falling back to local model: {remote_error}")
            logger.info(f"Loading summarization model from local path: {SUMMARIZATION_PATH}")
            summarization_model = SummarizationModel(SUMMARIZATION_PATH)
        loaded.append("summarization")
        logger.info("Summarization model loaded successfully")
    except Exception as e:
        failed.append(("summarization", str(e)))
        logger.error(f"Failed to load summarization model: {str(e)}")

    logger.info(f"Models loaded: {loaded}")
    if failed:
        logger.warning(f"Models failed to load: {[f[0] for f in failed]}")

    return len(loaded) > 0


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
            'mode': 'hf_inference_api',
            'models': {
                'summarization': True,
                'spelling': True,
                'autocomplete': True,
                'grammar': True,
                'punctuation': True
            },
            'supabase': {
                'configured': bool(SUPABASE_URL and SUPABASE_ANON_KEY),
            },
            'environment': 'huggingface_spaces',
        }
        return jsonify(health), 200
    
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
    """Debug endpoint: test all HF models and return actual errors."""
    if not USE_HF_API:
        return jsonify({'error': 'Not in HF API mode', 'mode': 'local'}), 400
    
    from hf_inference import debug_test_all_models
    results = debug_test_all_models()
    return jsonify({
        'status': 'debug',
        'hf_api_token_set': bool(HF_API_TOKEN),
        'hf_api_token_prefix': HF_API_TOKEN[:10] + '...' if HF_API_TOKEN else 'NOT SET',
        'models': results,
    }), 200


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
    if not USE_HF_API and summarization_model is None:
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
        
        if USE_HF_API:
            summary = hf_summarize(text, max_length=max_length, min_length=max(10, max_length // 3))
        else:
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


@app.route('/api/spelling', methods=['POST'])
def spelling_correction():
    """
    Correct spelling in Arabic text.
    
    Expected JSON payload:
    {
        "text": "Arabic text to correct"
    }
    """
    if not USE_HF_API and spelling_model is None:
        return jsonify({
            'error': 'Spelling model not loaded. Please check server logs.',
            'status': 'error'
        }), 503
    
    try:
        if not request.is_json:
            return jsonify({'error': 'Request must be JSON', 'status': 'error'}), 400
        
        data = request.get_json()
        text = data.get('text', '').strip()
        
        if not text:
            return jsonify({'error': 'Text is required', 'status': 'error'}), 400
        
        logger.info(f"Correcting spelling for text of length: {len(text)}")
        if USE_HF_API:
            corrected = hf_correct_spelling(text)
        else:
            corrected = spelling_model.correct(text)
        
        return jsonify({
            'corrected': corrected,
            'status': 'success',
            'original_length': len(text),
            'corrected_length': len(corrected)
        })
    
    except Exception as e:
        logger.error(f"Error during spelling correction: {str(e)}")
        logger.error(traceback.format_exc())
        return jsonify({
            'error': 'An error occurred during spelling correction.',
            'status': 'error',
            'details': str(e) if app.debug else None
        }), 500


@app.route('/api/autocomplete', methods=['POST'])
def autocomplete():
    """
    Get autocomplete suggestions for Arabic text.
    
    Expected JSON payload:
    {
        "text": "Arabic text prefix",
        "n": 5 (number of suggestions, optional)
    }
    """
    if not USE_HF_API and autocomplete_model is None:
        return jsonify({
            'error': 'Autocomplete model not loaded. Please check server logs.',
            'status': 'error'
        }), 503
    
    try:
        if not request.is_json:
            return jsonify({'error': 'Request must be JSON', 'status': 'error'}), 400
        
        data = request.get_json()
        text = data.get('text', '').strip()
        n = int(data.get('n', 5))
        
        if not text:
            return jsonify({'error': 'Text is required', 'status': 'error'}), 400
        
        logger.info(f"Getting autocomplete suggestions for: {text[:50]}...")
        if USE_HF_API:
            suggestions = hf_autocomplete(text, n=n)
        else:
            suggestions = autocomplete_model.predict(text, n=n)
        logger.info(f"Autocomplete suggestions (n={n}): {suggestions}")
        
        return jsonify({
            'suggestions': suggestions,
            'status': 'success'
        })
    
    except Exception as e:
        logger.error(f"Error during autocomplete: {str(e)}")
        logger.error(traceback.format_exc())
        return jsonify({
            'error': 'An error occurred during autocomplete.',
            'status': 'error',
            'details': str(e) if app.debug else None
        }), 500


@app.route('/api/grammar', methods=['POST'])
def grammar_correction():
    """
    Correct grammar in Arabic text.
    
    Expected JSON payload:
    {
        "text": "Arabic text to correct"
    }
    """
    if not USE_HF_API and grammar_model is None:
        return jsonify({
            'error': 'Grammar model not loaded. Please check server logs.',
            'status': 'error'
        }), 503
    
    try:
        if not request.is_json:
            return jsonify({'error': 'Request must be JSON', 'status': 'error'}), 400
        
        data = request.get_json()
        text = data.get('text', '').strip()
        
        if not text:
            return jsonify({'error': 'Text is required', 'status': 'error'}), 400
        
        logger.info(f"Correcting grammar for text of length: {len(text)}")
        if USE_HF_API:
            # Grammar uses spelling model as proxy (no dedicated grammar model yet)
            corrected = hf_correct_spelling(text)
        else:
            corrected = grammar_model.correct(text)
        
        return jsonify({
            'corrected': corrected,
            'status': 'success',
            'original_length': len(text),
            'corrected_length': len(corrected)
        })
    
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
    Add punctuation to Arabic text.
    
    Expected JSON payload:
    {
        "text": "Arabic text without punctuation"
    }
    """
    if not USE_HF_API and punctuation_model is None:
        return jsonify({
            'error': 'Punctuation model not loaded. Please check server logs.',
            'status': 'error'
        }), 503
    
    try:
        if not request.is_json:
            return jsonify({'error': 'Request must be JSON', 'status': 'error'}), 400
        
        data = request.get_json()
        text = data.get('text', '').strip()
        
        if not text:
            return jsonify({'error': 'Text is required', 'status': 'error'}), 400
        
        logger.info(f"Adding punctuation for text of length: {len(text)}")
        if USE_HF_API:
            punctuated = hf_add_punctuation(text)
        else:
            punctuated = punctuation_model.add_punctuation(text)
        
        return jsonify({
            'punctuated': punctuated,
            'status': 'success',
            'original_length': len(text),
            'punctuated_length': len(punctuated)
        })
    
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
    def __init__(self, original, modified):
        self.original = original
        self.modified = modified
        self.mapping = []  # list of (mod_start, mod_end, orig_start, orig_end)
        self._build_mapping()
        
    def _build_mapping(self):
        s = difflib.SequenceMatcher(None, self.original, self.modified)
        for tag, i1, i2, j1, j2 in s.get_opcodes():
            self.mapping.append((j1, j2, i1, i2))
            
    def map_offset(self, mod_offset):
        """
        Given a character offset in the modified text, return the corresponding
        character offset in the original text.
        """
        for j1, j2, i1, i2 in self.mapping:
            if j1 <= mod_offset <= j2:
                if j2 == j1:  # insertion point
                    return i1
                # Proportional mapping inside the block
                ratio = (mod_offset - j1) / (j2 - j1)
                return int(i1 + ratio * (i2 - i1))
        return len(self.original)


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


def _is_small_spelling_change(orig_word, corr_word):
    """
    Heuristic: only accept small spelling edits and ignore
    aggressive changes (to avoid over-editing).
    """
    if not orig_word or not corr_word:
        return False
    if orig_word == corr_word:
        return False

    # Ignore tokens that contain non-letters (numbers / punctuation)
    # Arabic letters range plus basic Latin letters.
    if re.search(r'[^ء-يآأإىa-zA-Z]', orig_word):
        return False
    if re.search(r'[^ء-يآأإىa-zA-Z]', corr_word):
        return False

    dist = _levenshtein(orig_word, corr_word)
    max_len = max(len(orig_word), len(corr_word))

    # Allow at most 2 character edits and at most 40% of the word
    return dist <= 2 and (dist / max_len) <= 0.4


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

        current_text = text
        suggestions = []
        mappers = []
        total_start = time.time()

        def map_range_to_original(start, end):
            curr_start, curr_end = start, end
            for mapper in reversed(mappers):
                curr_start = mapper.map_offset(curr_start)
                curr_end = mapper.map_offset(curr_end)
            return curr_start, curr_end

        # 1. Spelling (with conservative post-filtering to avoid over-editing)
        has_spelling = USE_HF_API or spelling_model
        if has_spelling:
            try:
                t0 = time.time()
                logger.info(f"[ANALYZE] Step 1: Spelling correction starting...")
                if USE_HF_API:
                    raw_corrected = hf_correct_spelling(current_text)
                else:
                    raw_corrected = spelling_model.correct(current_text)
                logger.info(f"[ANALYZE] Step 1: Spelling done in {time.time()-t0:.2f}s")

                if raw_corrected != current_text:
                    orig_word_positions = get_word_positions(current_text)
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
                                if _is_small_spelling_change(o_word, c_word):
                                    new_words.append(c_word)
                                    suggestions.append({
                                        'start': start_idx,
                                        'end': end_idx,
                                        'original': o_word,
                                        'correction': c_word,
                                        'type': 'spelling',
                                    })
                                else:
                                    new_words.append(current_text[start_idx:end_idx])
                            elif len(o_segment) == 1 and len(c_segment) > 1:
                                # 1-word → N words: accept when original is long (likely concatenated)
                                o_word = o_segment[0]
                                if len(o_word) >= 12 and ' ' not in o_word:
                                    corr_str = " ".join(c_segment)
                                    new_words.append(corr_str)
                                    suggestions.append({
                                        'start': start_idx,
                                        'end': end_idx,
                                        'original': o_word,
                                        'correction': corr_str,
                                        'type': 'spelling',
                                    })
                                else:
                                    new_words.append(current_text[start_idx:end_idx])
                            else:
                                new_words.extend([current_text[orig_word_positions[idx][1]:orig_word_positions[idx][2]] for idx in range(i1, i2)])
                        elif tag == 'delete':
                            for idx in range(i1, i2):
                                new_words.append(current_text[orig_word_positions[idx][1]:orig_word_positions[idx][2]])
                        elif tag == 'insert':
                            continue

                    safe_text = " ".join(new_words)
                    mappers.append(OffsetMapper(current_text, safe_text))
                    current_text = safe_text
            except Exception as e:
                logger.error(f"[ANALYZE] Spelling failed: {e}")

        # 2. Grammar (runs on spelling-corrected text)
        has_grammar = USE_HF_API or grammar_model
        if has_grammar:
            try:
                t0 = time.time()
                logger.info(f"[ANALYZE] Step 2: Grammar correction starting...")
                if USE_HF_API:
                    corrected_grammar = hf_correct_spelling(current_text)
                else:
                    corrected_grammar = grammar_model.correct(current_text)
                logger.info(f"[ANALYZE] Step 2: Grammar done in {time.time()-t0:.2f}s")
                if corrected_grammar != current_text:
                    diffs = get_word_diffs(current_text, corrected_grammar)
                    for d in diffs:
                        orig_start, orig_end = map_range_to_original(d['start'], d['end'])
                        suggestions.append({
                            'start': orig_start,
                            'end': orig_end,
                            'original': text[orig_start:orig_end],
                            'correction': d['correction'],
                            'type': 'grammar'
                        })
                    mappers.append(OffsetMapper(current_text, corrected_grammar))
                    current_text = corrected_grammar
            except Exception as e:
                logger.error(f"[ANALYZE] Grammar failed: {e}")

        # 3. Punctuation (runs on grammar-corrected text)
        has_punctuation = USE_HF_API or punctuation_model
        if has_punctuation:
            try:
                t0 = time.time()
                logger.info(f"[ANALYZE] Step 3: Punctuation starting...")
                if USE_HF_API:
                    corrected_punc = hf_add_punctuation(current_text)
                else:
                    corrected_punc = punctuation_model.add_punctuation(current_text)
                logger.info(f"[ANALYZE] Step 3: Punctuation done in {time.time()-t0:.2f}s")
                if corrected_punc != current_text:
                    diffs = get_word_diffs(current_text, corrected_punc)
                    for d in diffs:
                        orig_start, orig_end = map_range_to_original(d['start'], d['end'])
                        suggestions.append({
                            'start': orig_start,
                            'end': orig_end,
                            'original': text[orig_start:orig_end],
                            'correction': d['correction'],
                            'type': 'punctuation'
                        })
                    current_text = corrected_punc
            except Exception as e:
                logger.error(f"[ANALYZE] Punctuation failed: {e}")

        total_time = time.time() - total_start
        logger.info(f"[ANALYZE] Total analysis time: {total_time:.2f}s | Suggestions: {len(suggestions)}")

        return jsonify({
            'original': text,
            'corrected': current_text,
            'suggestions': suggestions,
            'status': 'success'
        })

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

# Load models on import (gunicorn) — guarded by flag to prevent double-load
if os.environ.get('RENDER') or os.environ.get('GUNICORN_LOADED'):
    _ensure_models_loaded()


if __name__ == '__main__':
    # Load models on startup (development)
    _ensure_models_loaded()
    
    # Run the app
    port = int(os.environ.get('PORT', 5000))
    debug = os.environ.get('DEBUG', 'False').lower() == 'true'
    
    logger.info(f"Starting server on port {port} (debug={debug})")
    app.run(host='0.0.0.0', port=port, debug=debug)
