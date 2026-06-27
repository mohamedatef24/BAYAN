"""
Flask backend server for Arabic text analysis.
Provides API endpoints for the Bayan web application.

Routes are registered via Blueprints in routes/ package.
Analysis pipeline logic lives in services/ package.
"""

import os
import logging
import time
from flask import Flask
from flask_cors import CORS

from config import (
    _ALLOWED_ORIGINS, USE_HF_API, HUGGINGFACE_SUMMARIZATION_REPO,
)
from middleware.rate_limit import limiter
import state

from model_loader import (
    SummarizationModel,
    SUMMARIZATION_PATH,
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Initialize Flask app
app = Flask(__name__, static_folder='.', static_url_path='')

# CORS: restrict to known origins (website + extension)
CORS(app, resources={r"/api/*": {"origins": _ALLOWED_ORIGINS}})

# Rate limiting
limiter.init_app(app)

# Register Blueprints
from routes.core import core_bp
from routes.nlp import nlp_bp
app.register_blueprint(core_bp)
app.register_blueprint(nlp_bp)


def load_models():
    """Load summarization model. Other models use lazy-loading via their services."""
    if USE_HF_API:
        logger.info("HF_API_TOKEN is set — HF API mode enabled")
        logger.info("NOTE: HF Spaces free tier has NO outbound DNS. Loading summarization model locally.")
        logger.info("Spelling, punctuation, autocomplete will gracefully degrade (return input unchanged).")

    loaded = []
    failed = []

    try:
        logger.info(f"Loading summarization model from Hugging Face: {HUGGINGFACE_SUMMARIZATION_REPO}")
        try:
            state.summarization_model = SummarizationModel(HUGGINGFACE_SUMMARIZATION_REPO)
        except Exception as remote_error:
            logger.warning(f"Remote load failed, falling back to local model: {remote_error}")
            state._startup_errors.append(f"remote_load: {str(remote_error)[:200]}")
            logger.info(f"Loading summarization model from local path: {SUMMARIZATION_PATH}")
            state.summarization_model = SummarizationModel(SUMMARIZATION_PATH)
        loaded.append("summarization")
        logger.info("Summarization model loaded successfully")
    except Exception as e:
        import traceback
        err_detail = traceback.format_exc()
        failed.append(("summarization", str(e)))
        state._startup_errors.append(f"summarization_load_failed: {err_detail[-500:]}")
        logger.error(f"Failed to load summarization model: {str(e)}")

    logger.info(f"Models loaded: {loaded}")
    if failed:
        logger.warning(f"Models failed to load: {[f[0] for f in failed]}")

    return len(loaded) > 0


# ── Gunicorn startup hook ──
_models_loaded = False

def _ensure_models_loaded():
    """Load ALL models at startup — no lazy loading.

    Each model is wrapped in its own try/except so a single failure
    doesn't prevent the server from starting. Models that fail to load
    will gracefully degrade at request time.
    """
    global _models_loaded
    if _models_loaded:
        return
    _models_loaded = True

    total_t0 = time.time()
    logger.info("=" * 60)
    logger.info("BAYAN — Loading ALL models at startup (eager mode)...")
    logger.info("=" * 60)

    # 1. Summarization
    if not load_models():
        logger.error("Failed to load summarization model.")

    # 2. Spelling model
    try:
        t0 = time.time()
        from nlp.spelling.araspell_service import get_spelling_model
        get_spelling_model()
        logger.info(f"✓ Spelling model loaded in {time.time()-t0:.1f}s")
    except Exception as e:
        logger.error(f"✗ Spelling model failed to load: {e}")

    # 3. Grammar model (Gradio client + camel-tools rules)
    try:
        t0 = time.time()
        from nlp.grammar.grammar_service import get_grammar_model
        get_grammar_model()
        logger.info(f"✓ Grammar model loaded in {time.time()-t0:.1f}s")
    except Exception as e:
        logger.error(f"✗ Grammar model failed to load: {e}")

    # 4. Punctuation model
    try:
        t0 = time.time()
        from nlp.punctuation.punctuation_service import get_punctuation_model
        get_punctuation_model()
        logger.info(f"✓ Punctuation model loaded in {time.time()-t0:.1f}s")
    except Exception as e:
        logger.error(f"✗ Punctuation model failed to load: {e}")

    # 5. Autocomplete model
    try:
        t0 = time.time()
        from nlp.autocomplete.autocomplete_service import get_autocomplete_model
        get_autocomplete_model()
        logger.info(f"✓ Autocomplete model loaded in {time.time()-t0:.1f}s")
    except Exception as e:
        logger.error(f"✗ Autocomplete model failed to load: {e}")

    # 6. Dialect model
    try:
        t0 = time.time()
        from nlp.dialect.dialect_service import get_dialect_model
        get_dialect_model()
        logger.info(f"✓ Dialect model loaded in {time.time()-t0:.1f}s")
    except Exception as e:
        logger.error(f"✗ Dialect model failed to load: {e}")

    total_elapsed = time.time() - total_t0
    logger.info("=" * 60)
    logger.info(f"BAYAN — All models loaded in {total_elapsed:.1f}s")
    logger.info("=" * 60)

# Load models on import (gunicorn imports this module, __name__ != '__main__')
_ensure_models_loaded()


if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    debug = os.environ.get('DEBUG', 'False').lower() == 'true'

    logger.info(f"Starting server on port {port} (debug={debug})")
    app.run(host='0.0.0.0', port=port, debug=debug)
