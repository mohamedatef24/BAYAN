import os
import logging
from pathlib import Path
from flask import Blueprint, jsonify, Response
from middleware.rate_limit import limiter
from config import SUPABASE_URL, SUPABASE_ANON_KEY, USE_HF_API, HF_API_TOKEN
import state

logger = logging.getLogger(__name__)

core_bp = Blueprint('core', __name__)


@core_bp.after_request
def add_security_headers(response):
    response.headers['Content-Security-Policy'] = (
        "default-src 'self'; "
        "script-src 'self' https://fonts.googleapis.com; "
        "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com https://fonts.gstatic.com; "
        "font-src 'self' https://fonts.gstatic.com; "
        "img-src 'self' data:; "
        "connect-src 'self' https://*.supabase.co; "
        "object-src 'none'; "
        "frame-ancestors 'self' https://huggingface.co https://*.huggingface.co"
    )
    response.headers['X-Content-Type-Options'] = 'nosniff'
    return response


def _spelling_available():
    try:
        from nlp.spelling.araspell_service import is_loaded
        return is_loaded()
    except Exception:
        return False


def _grammar_available():
    try:
        from nlp.grammar.grammar_service import is_loaded
        return is_loaded()
    except Exception:
        return False


def _punctuation_available():
    try:
        from nlp.punctuation.punctuation_service import is_loaded
        return is_loaded()
    except Exception:
        return False


def _autocomplete_available():
    try:
        from nlp.autocomplete.autocomplete_service import _instance
        return _instance is not None and _instance.is_ready()
    except Exception:
        return False


def _dialect_available():
    try:
        from nlp.dialect.dialect_service import is_loaded
        return is_loaded()
    except Exception:
        return False


@core_bp.route('/')
def index():
    html_path = Path(__file__).parent.parent / 'index.html'
    html = html_path.read_text(encoding='utf-8')

    import html as _html
    html = html.replace(
        '<meta name="supabase-url" content="">',
        f'<meta name="supabase-url" content="{_html.escape(SUPABASE_URL, quote=True)}">'
    )
    html = html.replace(
        '<meta name="supabase-anon-key" content="">',
        f'<meta name="supabase-anon-key" content="{_html.escape(SUPABASE_ANON_KEY, quote=True)}">'
    )

    return Response(html, mimetype='text/html')


@core_bp.route('/api/health', methods=['GET'])
def health_check():
    if USE_HF_API:
        health = {
            'status': 'healthy',
            'mode': 'hf_spaces_local',
            'models': {
                'summarization': state.summarization_model is not None,
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
        status_code = 200 if state.summarization_model is not None else 503
        return jsonify(health), status_code

    health = {
        'status': 'healthy',
        'mode': 'local_models',
        'models': {
            'summarization': state.summarization_model is not None,
            'spelling': state.spelling_model is not None,
            'autocomplete': state.autocomplete_model is not None,
            'grammar': state.grammar_model is not None,
            'punctuation': state.punctuation_model is not None,
            'dialect': _dialect_available()
        },
        'supabase': {
            'configured': bool(SUPABASE_URL and SUPABASE_ANON_KEY),
        },
        'environment': 'render' if os.environ.get('RENDER') else 'local',
    }
    status_code = 200 if health['models']['summarization'] else 503
    return jsonify(health), status_code


@core_bp.route('/api/config', methods=['GET'])
@limiter.limit("30 per minute")
def public_config():
    return jsonify({
        'supabase_url': SUPABASE_URL if SUPABASE_URL else '',
        'supabase_anon_key': SUPABASE_ANON_KEY if SUPABASE_ANON_KEY else '',
    })


@core_bp.route('/api/debug-models', methods=['GET'])
@limiter.limit("5 per minute")
def debug_models():
    from flask import current_app
    if not current_app.debug:
        return jsonify({'error': 'Debug endpoint disabled in production'}), 403
    results = {
        'spelling': {'loaded': state.spelling_model is not None},
        'grammar': {'loaded': state.grammar_model is not None},
        'punctuation': {'loaded': state.punctuation_model is not None},
        'summarization': {'loaded': state.summarization_model is not None},
        'autocomplete': {'loaded': state.autocomplete_model is not None},
    }

    import os
    try:
        import resource
        mem = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
        mem_info = f"{mem} KB"
    except Exception:
        mem_info = "N/A"

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
        'summarization_model_loaded': state.summarization_model is not None,
        'startup_errors': state._startup_errors,
        'memory': mem_info,
        'proc_meminfo': proc_mem,
        'models': results,
    }), 200


@core_bp.app_errorhandler(404)
def not_found(error):
    return jsonify({
        'error': 'Endpoint not found',
        'status': 'error'
    }), 404


@core_bp.app_errorhandler(500)
def internal_error(error):
    logger.error(f"Internal server error: {str(error)}")
    return jsonify({
        'error': 'Internal server error',
        'status': 'error'
    }), 500
