import re
import time
import logging
import traceback
from flask import Blueprint, request, jsonify, current_app
from middleware.rate_limit import limiter
from config import MAX_TEXT_LENGTH, MAX_SUMMARY_LENGTH, MIN_TEXT_LENGTH
from nlp.pipeline_context import PipelineContext
from nlp.text_utils import OffsetMapper
from services.analysis_pipeline import (
    _run_spelling_stage,
    _run_grammar_stage,
    _run_punctuation_stage,
)
import state

logger = logging.getLogger(__name__)

nlp_bp = Blueprint('nlp', __name__)


@nlp_bp.route('/api/spelling', methods=['POST'])
@limiter.limit("30 per minute")
def spelling_correction():
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


@nlp_bp.route('/api/summarize', methods=['POST'])
@limiter.limit("10 per minute")
def summarize():
    if state.summarization_model is None:
        return jsonify({
            'error': 'Summarization model not loaded. Please check server logs.',
            'status': 'error'
        }), 503

    try:
        if not request.is_json:
            return jsonify({
                'error': 'Request must be JSON',
                'status': 'error'
            }), 400

        data = request.get_json()

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

        length = int(data.get('length', 2))
        length = max(1, min(3, length))

        full_text = data.get('full_text', True)

        input_length = len(text.split())
        length_multipliers = {1: 0.3, 2: 0.5, 3: 0.7}
        max_length = max(20, int(input_length * length_multipliers[length]))
        max_length = min(max_length, MAX_SUMMARY_LENGTH)

        logger.info(f"Generating summary: length={length}, max_length={max_length}, text_length={len(text)}")

        summary = state.summarization_model.summarize(text, max_length=max_length, min_length=max(10, max_length // 3))

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
            'details': str(e) if current_app.debug else None
        }), 500


@nlp_bp.route('/api/autocomplete', methods=['POST'])
@limiter.limit("60 per minute")
def autocomplete():
    try:
        if not request.is_json:
            return jsonify({'error': 'Request must be JSON', 'status': 'error'}), 400

        data = request.get_json()
        context = data.get('context', '').strip()
        n = min(int(data.get('n', 3)), 10)

        if not context or len(context) < 3:
            return jsonify({'suggestions': [], 'status': 'success'})

        from nlp.autocomplete.autocomplete_rules import extract_context
        context = extract_context(context, max_chars=200)

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
            'status': 'success'
        })


@nlp_bp.route('/api/grammar', methods=['POST'])
@limiter.limit("30 per minute")
def grammar_correction():
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
            'details': str(e) if current_app.debug else None
        }), 500


@nlp_bp.route('/api/punctuation', methods=['POST'])
@limiter.limit("30 per minute")
def add_punctuation():
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
            'details': str(e) if current_app.debug else None
        }), 500


@nlp_bp.route('/api/dialect', methods=['POST'])
@limiter.limit("10 per minute")
def convert_dialect():
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
            'details': str(e) if current_app.debug else None
        }), 500


@nlp_bp.route('/api/quran', methods=['POST'])
@limiter.limit("20 per minute")
def quran_verify():
    try:
        import os, sys
        _quran_root = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
        sys.path.insert(0, _quran_root)
        try:
            from quran import search_bayan
            _quran_ok = True
        except Exception:
            _quran_ok = False

        if not _quran_ok:
            return jsonify({'error': 'Quran search module not available'}), 503

        if not request.is_json:
            return jsonify({'status': 'error', 'error': 'Content-Type must be application/json'}), 415

        data = request.get_json()
        text = data.get('text', '').strip()
        language = data.get('language', 'تدقيق الايات').strip()

        if not text:
            return jsonify({'error': 'النص المُدخل فارغ'}), 400

        if len(text) > 2000:
            return jsonify({'error': 'النص طويل جداً (الحد الأقصى 2000 حرف)'}), 400

        logger.info(f'[QURAN] Query: "{text[:60]}..." lang={language}')
        start_time = time.time()

        result = search_bayan(text, target_type=language)

        elapsed = int((time.time() - start_time) * 1000)
        logger.info(f'[QURAN] Done in {elapsed}ms')

        if 'error' in result:
            return jsonify({'status': 'error', **result}), 404

        return jsonify({'status': 'success', **result})

    except Exception as e:
        logger.error(f'[QURAN] Error: {e}')
        logger.error(traceback.format_exc())
        return jsonify({'error': 'حدث خطأ أثناء البحث في القرآن الكريم'}), 500


@nlp_bp.route('/api/analyze', methods=['POST'])
@limiter.limit("30 per minute")
def analyze_text():
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

        text = re.sub(r'<[^>]*>', '', text).strip()
        if not text:
            return jsonify({'error': 'Text is required', 'status': 'error'}), 400

        arabic_chars = len(re.findall(r'[؀-ۿ]', text))
        alpha_chars = len(re.findall(r'[a-zA-Z؀-ۿ]', text))
        if alpha_chars > 0 and arabic_chars / alpha_chars < 0.3:
            return jsonify({
                'original': text, 'corrected': text,
                'suggestions': [], 'timing_ms': {},
                'status': 'success'
            })

        ctx = PipelineContext(text)
        current_text = text
        suggestions = []
        mappers = []

        _tel_events = []
        total_start = time.time()
        timing_ms = {'spelling_ms': 0, 'grammar_ms': 0, 'punctuation_ms': 0, 'total_ms': 0}

        text_len = len(current_text)
        run_spelling = text_len <= 1000
        if not run_spelling:
            logger.info(f"[ANALYZE] Text length {text_len} > 300 — skipping AraSpell for performance")

        _RELIGIOUS_PHRASES = [
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
            'المسلم من سلم المسلمون',
            'لا يؤمن أحدكم',
            'اهدنا الصراط',
        ]
        _is_religious_text = any(phrase in ctx.current_text for phrase in _RELIGIOUS_PHRASES)
        if _is_religious_text:
            logger.info(f"[ANALYZE] Religious text detected — skipping ALL stages")
            run_spelling = False

        _has_url = bool(re.search(r'https?://\S+', ctx.current_text))
        _has_email = bool(re.search(r'\S+@\S+\.\S+', ctx.current_text))
        _has_hashtag = bool(re.search(r'#[؀-ۿ\w]{2,}', ctx.current_text))
        _has_percent = bool(re.search(r'\d+\.\d+%', ctx.current_text))
        _has_latin_word = bool(re.search(r'\b[A-Za-z]{3,}\b', ctx.current_text))
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

        _run_spelling_stage(ctx, text, timing_ms, _tel_events, run_spelling, _is_religious_text)
        current_text = ctx.current_text

        _run_grammar_stage(ctx, timing_ms, _tel_events, _is_religious_text)
        current_text = ctx.current_text

        _run_punctuation_stage(ctx, timing_ms, _tel_events, _is_religious_text)
        current_text = ctx.current_text

        total_time = time.time() - total_start
        timing_ms['total_ms'] = int(total_time * 1000)

        suggestions = ctx.patches.to_list()

        def _apply_patches_to_original(original_text, suggestion_dicts):
            result = original_text
            for s in sorted(suggestion_dicts, key=lambda x: -x['start']):
                result = result[:s['start']] + s['correction'] + result[s['end']:]
            return result

        corrected = _apply_patches_to_original(text, suggestions)

        logger.info(f"[ANALYZE] Total: {timing_ms['total_ms']}ms | "
                    f"Spelling: {timing_ms['spelling_ms']}ms | "
                    f"Grammar: {timing_ms['grammar_ms']}ms | "
                    f"Punctuation: {timing_ms['punctuation_ms']}ms | "
                    f"Suggestions: {len(suggestions)}")

        stage_errors = {k: v for k, v in timing_ms.items() if k.endswith('_error')}
        response_status = 'partial' if stage_errors else 'success'

        response_data = {
            'original': text,
            'corrected': corrected,
            'suggestions': suggestions,
            'timing_ms': timing_ms,
            'status': response_status,
            'telemetry': _tel_events if current_app.debug else [],
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
            'details': str(e) if current_app.debug else None
        }), 500
