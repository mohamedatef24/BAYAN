"""
Unit tests for the Dialect-to-MSA feature.
Tests Flask route validation, service layer, and edge cases.
All tests mock the model so NO actual model loading happens.

Run: python -m pytest test_dialect.py -v
"""

import sys
import os
import pytest
from unittest.mock import patch, MagicMock

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))
os.chdir(os.path.join(os.path.dirname(__file__), 'src'))


# ═══════════════════════════════════════════════════════════════
#  FIXTURE: Flask test client (no model loading)
# ═══════════════════════════════════════════════════════════════

@pytest.fixture
def client():
    """Create Flask test client without loading any models."""
    with patch('app.load_models', return_value=True):
        from app import app
        app.config['TESTING'] = True
        with app.test_client() as c:
            yield c


def _mock_dialect():
    """Create a mock DialectConverter that returns predictable output."""
    mock = MagicMock()
    mock.convert.side_effect = lambda text, **kw: f"[MSA] {text}"
    mock.is_ready.return_value = True
    return mock


@pytest.fixture
def mock_model():
    """Patch dialect model globally so no real model loading happens."""
    m = _mock_dialect()
    with patch('nlp.dialect.dialect_service._instance', m):
        with patch('nlp.dialect.dialect_service.get_dialect_model', return_value=m):
            yield m


# ═══════════════════════════════════════════════════════════════
#  GROUP 1: Input Validation (no model needed)
# ═══════════════════════════════════════════════════════════════

class TestDialectInputValidation:
    """Tests that verify input validation BEFORE the model is called."""

    def test_empty_text_returns_400(self, client):
        r = client.post('/api/dialect', json={'text': ''})
        assert r.status_code == 400
        assert r.get_json()['status'] == 'error'

    def test_whitespace_only_returns_400(self, client):
        r = client.post('/api/dialect', json={'text': '   '})
        assert r.status_code == 400
        assert r.get_json()['status'] == 'error'

    def test_missing_text_field_returns_400(self, client):
        r = client.post('/api/dialect', json={})
        assert r.status_code == 400

    def test_text_too_long_returns_400(self, client):
        r = client.post('/api/dialect', json={'text': 'ا' * 5001})
        assert r.status_code == 400
        assert '5000' in r.get_json()['error']

    def test_non_json_returns_400(self, client):
        r = client.post('/api/dialect', data='plain text',
                        content_type='text/plain')
        assert r.status_code == 400

    def test_get_method_not_allowed(self, client):
        r = client.get('/api/dialect')
        assert r.status_code in [404, 405]  # Flask static_folder returns 404

    def test_put_method_not_allowed(self, client):
        r = client.put('/api/dialect', json={'text': 'test'})
        assert r.status_code == 405

    def test_null_text_handled(self, client):
        r = client.post('/api/dialect', json={'text': None})
        assert r.status_code in [400, 500]
        assert r.get_json()['status'] == 'error'


# ═══════════════════════════════════════════════════════════════
#  GROUP 2: Successful Conversion (mocked model)
# ═══════════════════════════════════════════════════════════════

class TestDialectConversion:
    """Tests with mocked model to verify route logic."""

    def test_success_response_format(self, client, mock_model):
        r = client.post('/api/dialect', json={'text': 'عايز اروح البيت'})
        assert r.status_code == 200
        data = r.get_json()
        assert data['status'] == 'success'
        assert 'original_text' in data
        assert 'converted_text' in data

    def test_original_text_preserved(self, client, mock_model):
        r = client.post('/api/dialect', json={'text': 'عايز اروح البيت'})
        data = r.get_json()
        assert data['original_text'] == 'عايز اروح البيت'

    def test_converted_text_from_model(self, client, mock_model):
        r = client.post('/api/dialect', json={'text': 'عايز اروح البيت'})
        data = r.get_json()
        assert data['converted_text'] == '[MSA] عايز اروح البيت'

    def test_text_gets_stripped(self, client, mock_model):
        r = client.post('/api/dialect', json={'text': '  عايز اروح  '})
        data = r.get_json()
        assert data['original_text'] == 'عايز اروح'

    def test_text_exactly_5000_passes(self, client, mock_model):
        text = 'ا' * 5000
        r = client.post('/api/dialect', json={'text': text})
        assert r.status_code == 200

    def test_special_chars_dont_crash(self, client, mock_model):
        r = client.post('/api/dialect',
                        json={'text': '<script>alert(1)</script>'})
        assert r.status_code == 200

    def test_sql_injection_safe(self, client, mock_model):
        r = client.post('/api/dialect',
                        json={'text': "'; DROP TABLE users; --"})
        assert r.status_code == 200

    def test_unicode_bidi_safe(self, client, mock_model):
        r = client.post('/api/dialect',
                        json={'text': '\u200e\u200f\u202a عايز'})
        assert r.status_code == 200

    def test_emoji_safe(self, client, mock_model):
        r = client.post('/api/dialect',
                        json={'text': 'عايز اروح 🏠 دلوقتي'})
        assert r.status_code == 200

    def test_newlines_safe(self, client, mock_model):
        r = client.post('/api/dialect',
                        json={'text': 'عايز\nاروح\nالبيت'})
        assert r.status_code == 200

    def test_numbers_safe(self, client, mock_model):
        r = client.post('/api/dialect',
                        json={'text': 'عايز 5 كيلو و 3 كيلو'})
        assert r.status_code == 200

    def test_english_mixed_safe(self, client, mock_model):
        r = client.post('/api/dialect',
                        json={'text': 'عايز اعمل login في ال app'})
        assert r.status_code == 200

    def test_extra_json_fields_ignored(self, client, mock_model):
        r = client.post('/api/dialect',
                        json={'text': 'عايز', 'extra': 'field', 'hack': True})
        assert r.status_code == 200


# ═══════════════════════════════════════════════════════════════
#  GROUP 3: Model Error Handling
# ═══════════════════════════════════════════════════════════════

class TestDialectErrorHandling:
    """Tests for when the model throws errors."""

    def test_runtime_error_returns_503(self, client):
        mock = MagicMock()
        mock.convert.side_effect = RuntimeError("Model OOM")
        with patch('nlp.dialect.dialect_service._instance', mock):
            with patch('nlp.dialect.dialect_service.get_dialect_model', return_value=mock):
                r = client.post('/api/dialect', json={'text': 'عايز'})
                assert r.status_code == 503
                assert r.get_json()['status'] == 'error'

    def test_generic_exception_returns_500(self, client):
        mock = MagicMock()
        mock.convert.side_effect = ValueError("Bad tensor")
        with patch('nlp.dialect.dialect_service._instance', mock):
            with patch('nlp.dialect.dialect_service.get_dialect_model', return_value=mock):
                r = client.post('/api/dialect', json={'text': 'عايز'})
                assert r.status_code == 500
                assert r.get_json()['status'] == 'error'


# ═══════════════════════════════════════════════════════════════
#  GROUP 4: DialectConverter Service Unit Tests
# ═══════════════════════════════════════════════════════════════

class TestDialectService:
    """Tests for the DialectConverter class directly."""

    def test_singleton_pattern(self):
        from nlp.dialect import dialect_service
        dialect_service._instance = None
        with patch.object(dialect_service.DialectConverter, '__init__', return_value=None):
            with patch.object(dialect_service.DialectConverter, 'is_ready', return_value=True):
                m1 = dialect_service.get_dialect_model()
                m2 = dialect_service.get_dialect_model()
                assert m1 is m2
        dialect_service._instance = None

    def test_is_loaded_false_initially(self):
        from nlp.dialect import dialect_service
        dialect_service._instance = None
        assert dialect_service.is_loaded() is False

    def test_is_loaded_true_after_init(self):
        from nlp.dialect import dialect_service
        mock = MagicMock()
        mock.is_ready.return_value = True
        dialect_service._instance = mock
        assert dialect_service.is_loaded() is True
        dialect_service._instance = None

    def test_convert_empty_passthrough(self):
        from nlp.dialect.dialect_service import DialectConverter
        c = DialectConverter.__new__(DialectConverter)
        c.model = MagicMock()
        c.tokenizer = MagicMock()
        c.device = "cpu"
        assert c.convert("") == ""
        c.model.generate.assert_not_called()

    def test_convert_whitespace_passthrough(self):
        from nlp.dialect.dialect_service import DialectConverter
        c = DialectConverter.__new__(DialectConverter)
        c.model = MagicMock()
        c.tokenizer = MagicMock()
        c.device = "cpu"
        assert c.convert("   ") == "   "
        c.model.generate.assert_not_called()

    def test_convert_none_passthrough(self):
        from nlp.dialect.dialect_service import DialectConverter
        c = DialectConverter.__new__(DialectConverter)
        c.model = MagicMock()
        c.tokenizer = MagicMock()
        c.device = "cpu"
        assert c.convert(None) is None
        c.model.generate.assert_not_called()

    def test_prefix_correct(self):
        from nlp.dialect.dialect_service import DialectConverter
        assert DialectConverter.PREFIX == "حوّل إلى الفصحى: "

    def test_repo_id_correct(self):
        from nlp.dialect.dialect_service import DialectConverter
        assert DialectConverter.REPO_ID == "bayan10/dialect-to-msa-model"

    def test_max_lengths(self):
        from nlp.dialect.dialect_service import DialectConverter
        assert DialectConverter.MAX_INPUT_LENGTH == 128
        assert DialectConverter.MAX_OUTPUT_LENGTH == 128

    def test_is_ready_both_required(self):
        from nlp.dialect.dialect_service import DialectConverter
        c = DialectConverter.__new__(DialectConverter)
        c.model = None; c.tokenizer = MagicMock()
        assert c.is_ready() is False
        c.model = MagicMock(); c.tokenizer = None
        assert c.is_ready() is False
        c.model = MagicMock(); c.tokenizer = MagicMock()
        assert c.is_ready() is True


# ═══════════════════════════════════════════════════════════════
#  GROUP 5: Health Check Integration
# ═══════════════════════════════════════════════════════════════

class TestDialectHealthCheck:

    def test_health_includes_dialect(self, client):
        r = client.get('/api/health')
        data = r.get_json()
        assert 'dialect' in data['models']

    def test_dialect_false_when_not_loaded(self, client):
        from nlp.dialect import dialect_service
        dialect_service._instance = None
        r = client.get('/api/health')
        assert r.get_json()['models']['dialect'] is False

    def test_dialect_true_when_loaded(self, client):
        from nlp.dialect import dialect_service
        mock = MagicMock(); mock.is_ready.return_value = True
        dialect_service._instance = mock
        r = client.get('/api/health')
        assert r.get_json()['models']['dialect'] is True
        dialect_service._instance = None
