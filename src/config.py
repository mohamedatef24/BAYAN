import os
from pathlib import Path

try:
    from dotenv import load_dotenv
    _env_path = Path(__file__).parent.parent / '.env'
    load_dotenv(dotenv_path=_env_path)
except ImportError:
    pass

SUPABASE_URL = os.environ.get('SUPABASE_URL', '')
SUPABASE_ANON_KEY = os.environ.get('SUPABASE_ANON_KEY', '')
HF_API_TOKEN = os.environ.get('HF_API_TOKEN', '')
USE_HF_API = bool(HF_API_TOKEN)
HUGGINGFACE_SUMMARIZATION_REPO = os.environ.get(
    "SUMMARIZATION_REPO_ID",
    "bayan10/summarization-model",
)
DEBUG_TRACE = os.environ.get('DEBUG_TRACE', '').lower() in ('1', 'true', 'yes')

MAX_TEXT_LENGTH = 5000
MAX_SUMMARY_LENGTH = 512
MIN_TEXT_LENGTH = 10

_ALLOWED_ORIGINS = [
    'https://bayan10-bayan-api.hf.space',
    'http://localhost:7860',
    'http://127.0.0.1:7860',
]
_ext_origin = os.environ.get('BAYAN_EXTENSION_ORIGIN', '')
if _ext_origin:
    _ALLOWED_ORIGINS.append(_ext_origin)
