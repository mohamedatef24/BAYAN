"""
Model loader for all Arabic NLP models.
Handles loading and inference with error handling.
"""

import os
import logging
from pathlib import Path
import json
import pickle
import difflib
import torch
import importlib.util
from transformers import (
    MBartForConditionalGeneration, 
    AutoTokenizer, 
    AutoConfig,
    AutoModelForSeq2SeqLM,
    AutoModelForCausalLM,
    EncoderDecoderModel,
    BertConfig,
    EncoderDecoderConfig
)

# Imported lazily inside SpellingModel so summarization-only workflows do not
# require spelling dependencies at module import time.
ArabicSpellChecker = None

logger = logging.getLogger(__name__)

# Model paths
MODEL_BASE_PATH = Path(__file__).parent.parent / "models"
SUMMARIZATION_PATH = MODEL_BASE_PATH / "Summarization" / "Model"
SPELLING_PATH = MODEL_BASE_PATH / "Spelling" / "Model"
AUTOCOMPLETE_PATH = MODEL_BASE_PATH / "Autocomplete" / "Model"
GRAMMAR_PATH = MODEL_BASE_PATH / "Grammrar" / "Model"
PUNCTUATION_PATH = MODEL_BASE_PATH / "Punctuation" / "Model"


class SummarizationModel:
    """Wrapper class for the Arabic summarization model."""
    
    def __init__(self, model_path):
        """
        Initialize the model.
        
        Args:
            model_path: Path to the model directory
            
        Raises:
            FileNotFoundError: If model files are not found
            RuntimeError: If model loading fails
        """
        self.model_source = str(model_path)
        self._is_remote_source = self._looks_like_remote_source(self.model_source)
        self.model_path = None if self._is_remote_source else Path(model_path)
        self.model = None
        self.tokenizer = None
        self.device = None
        
        self._validate_path()
        self._load_model()

    @staticmethod
    def _looks_like_remote_source(source):
        """Detect Hugging Face repo ids or URLs."""
        source = str(source)
        return source.startswith(("http://", "https://")) or ("/" in source and not Path(source).exists())
    
    def _validate_path(self):
        """Validate that the model path exists and contains required files."""
        if self._is_remote_source:
            logger.info(f"Using remote model source: {self.model_source}")
            return

        if not self.model_path.exists():
            raise FileNotFoundError(f"Model path does not exist: {self.model_path}")
        
        required_files = ['config.json', 'tokenizer.json', 'model.safetensors']
        missing_files = []
        
        for file in required_files:
            if not (self.model_path / file).exists():
                missing_files.append(file)
        
        if missing_files:
            raise FileNotFoundError(
                f"Missing required model files: {', '.join(missing_files)}"
            )
        
        logger.info(f"Model path validated: {self.model_path}")
    
    def _fix_generation_config(self):
        """Fix generation_config.json and config.json if early_stopping is None/null."""
        if self._is_remote_source:
            return

        gen_config_path = self.model_path / "generation_config.json"
        config_path = self.model_path / "config.json"
        
        try:
            # Fix config.json first (this is the main issue)
            if config_path.exists():
                with open(config_path, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                
                # Check if early_stopping exists in config and is None
                if 'early_stopping' in config and config['early_stopping'] is None:
                    logger.info("Fixing early_stopping in config.json (was None)")
                    config['early_stopping'] = True
                    with open(config_path, 'w', encoding='utf-8') as f:
                        json.dump(config, f, indent=2, ensure_ascii=False)
                    logger.info("Fixed config.json - set early_stopping to True")
            
            # Fix generation_config.json
            if gen_config_path.exists():
                with open(gen_config_path, 'r', encoding='utf-8') as f:
                    gen_config = json.load(f)
                
                # Fix early_stopping if it's None/null
                if gen_config.get('early_stopping') is None:
                    logger.info("Fixing early_stopping in generation_config.json (was None)")
                    gen_config['early_stopping'] = True
                    with open(gen_config_path, 'w', encoding='utf-8') as f:
                        json.dump(gen_config, f, indent=2, ensure_ascii=False)
                    logger.info("Fixed generation_config.json - set early_stopping to True")
        
        except Exception as e:
            logger.warning(f"Could not fix generation config files: {str(e)}")
            # Continue anyway, we'll try to load with workaround
    
    def _load_model(self):
        """Load the model and tokenizer."""
        try:
            # Determine device
            if torch.cuda.is_available():
                self.device = torch.device('cuda')
                logger.info(f"Using CUDA device: {torch.cuda.get_device_name(0)}")
            else:
                self.device = torch.device('cpu')
                logger.info("Using CPU device")
            
            # Load tokenizer with error handling
            logger.info("Loading tokenizer...")
            try:
                self.tokenizer = AutoTokenizer.from_pretrained(
                    self.model_source,
                    local_files_only=True,
                    trust_remote_code=False
                )
                logger.info("Tokenizer loaded successfully")
            except Exception as e:
                logger.error(f"Failed to load tokenizer: {str(e)}")
                # Try without local_files_only as fallback
                logger.info("Retrying tokenizer load without local_files_only...")
                self.tokenizer = AutoTokenizer.from_pretrained(
                    self.model_source,
                    trust_remote_code=False
                )
                logger.info("Tokenizer loaded successfully (fallback method)")
            
            # Load model with error handling
            logger.info("Loading model (this may take a while)...")
            
            # Fix generation config files if needed
            self._fix_generation_config()
            
            # Load config and fix early_stopping if needed
            try:
                config = AutoConfig.from_pretrained(
                    self.model_source,
                    local_files_only=True,
                    trust_remote_code=False
                )
                
                # Fix early_stopping in config if it's None
                if hasattr(config, 'early_stopping') and config.early_stopping is None:
                    logger.info("Fixing early_stopping in loaded config (was None)")
                    config.early_stopping = True
                
                # Load model with fixed config
                try:
                    self.model = MBartForConditionalGeneration.from_pretrained(
                        self.model_source,
                        config=config,
                        local_files_only=True,
                        trust_remote_code=False,
                        torch_dtype=torch.float32
                    )
                except Exception as e:
                    logger.warning(f"Failed to load with config: {str(e)}")
                    # Try without explicit config
                    self.model = MBartForConditionalGeneration.from_pretrained(
                        self.model_source,
                        local_files_only=True,
                        trust_remote_code=False,
                        torch_dtype=torch.float32
                    )
            except Exception as e:
                logger.warning(f"Failed to load config: {str(e)}")
                logger.info("Retrying model load without config fix...")
                try:
                    self.model = MBartForConditionalGeneration.from_pretrained(
                        self.model_source,
                        local_files_only=True,
                        trust_remote_code=False,
                        torch_dtype=torch.float32
                    )
                except Exception as e2:
                    logger.warning(f"Failed to load with local_files_only: {str(e2)}")
                    logger.info("Retrying model load without local_files_only...")
                    self.model = MBartForConditionalGeneration.from_pretrained(
                        self.model_source,
                        trust_remote_code=False,
                        torch_dtype=torch.float32
                    )
            
            # Move model to device
            self.model.to(self.device)
            self.model.eval()  # Set to evaluation mode
            
            # Clear cache if using CUDA
            if torch.cuda.is_available():
                torch.cuda.empty_cache()
            
            logger.info(f"Model loaded successfully on {self.device}")
            
        except Exception as e:
            logger.error(f"Error loading model: {str(e)}")
            import traceback
            logger.error(traceback.format_exc())
            raise RuntimeError(f"Failed to load model: {str(e)}")
    
    def summarize(self, text, max_length=150, min_length=30, num_beams=1, **kwargs):
        """
        Summarize Arabic text.
        
        Args:
            text: Input Arabic text to summarize
            max_length: Maximum length of the summary
            min_length: Minimum length of the summary
            num_beams: Number of beams for beam search
            **kwargs: Additional generation parameters
            
        Returns:
            str: Summarized text
            
        Raises:
            RuntimeError: If summarization fails
        """
        if self.model is None or self.tokenizer is None:
            raise RuntimeError("Model not loaded")
        
        try:
            # Tokenize input
            inputs = self.tokenizer(
                text,
                max_length=1024,
                truncation=True,
                padding=True,
                return_tensors="pt"
            )
            
            # Move inputs to device
            inputs = {k: v.to(self.device) for k, v in inputs.items()}
            
            # Keep decoding conservative: this model performed best with greedy decoding
            # and became more generic/hallucinated with beam search or sampling.
            generate_kwargs = dict(
                max_new_tokens=max(20, min(max_length, 160)),
                min_new_tokens=max(0, min_length),
                num_beams=num_beams,
                do_sample=False,
                early_stopping=False,
                no_repeat_ngram_size=3,
                repetition_penalty=1.1,
            )
            generate_kwargs.update(kwargs)

            # Remove legacy max_length/min_length if caller supplied them; we prefer max_new_tokens.
            generate_kwargs.pop('max_length', None)
            generate_kwargs.pop('min_length', None)

            # Generate summary
            with torch.no_grad():
                outputs = self.model.generate(
                    **inputs,
                    **generate_kwargs,
                )
            
            # Decode output
            summary = self.tokenizer.decode(outputs[0], skip_special_tokens=True)

            summary = summary.strip()
            if self._needs_fallback(text, summary):
                return self._extractive_fallback(text, max_words=max(12, min(max_length, 80)))

            return summary
        
        except Exception as e:
            logger.error(f"Error during summarization: {str(e)}")
            raise RuntimeError(f"Summarization failed: {str(e)}")

    def _needs_fallback(self, source_text, summary_text):
        """Return True when generated summary appears too far from the source text."""
        if not summary_text:
            return True

        source_words = set(source_text.split())
        summary_words = summary_text.split()
        if not summary_words:
            return True

        overlap = sum(1 for word in summary_words if word in source_words)
        overlap_ratio = overlap / max(1, len(summary_words))

        # Also guard against summaries that are lexically too dissimilar.
        ratio = difflib.SequenceMatcher(None, source_text[:500], summary_text[:500]).ratio()

        return overlap_ratio < 0.35 or ratio < 0.22

    def _extractive_fallback(self, source_text, max_words=40):
        """Build a conservative summary from the opening sentences of the source text."""
        text = source_text.strip()
        if not text:
            return text

        sentence_endings = ['.', '!', '?', '؟', '۔', '،']
        sentences = []
        current = []
        for chunk in text.replace('\n', ' ').split(' '):
            current.append(chunk)
            if chunk and chunk[-1] in sentence_endings:
                sentence = ' '.join(current).strip()
                if sentence:
                    sentences.append(sentence)
                current = []

        if current:
            sentence = ' '.join(current).strip()
            if sentence:
                sentences.append(sentence)

        if not sentences:
            words = text.split()
            return ' '.join(words[:max_words]).strip()

        chosen = []
        total_words = 0
        for sentence in sentences:
            sentence_words = sentence.split()
            if not sentence_words:
                continue
            if total_words + len(sentence_words) > max_words and chosen:
                break
            chosen.append(sentence)
            total_words += len(sentence_words)
            if total_words >= max_words:
                break

        if not chosen:
            return ' '.join(text.split()[:max_words]).strip()

        return ' '.join(chosen).strip()
    
    def __del__(self):
        """Cleanup resources."""
        try:
            if getattr(self, 'model', None) is not None:
                del self.model
            # Guard torch.cuda access in case torch or cuda subsystems are unavailable
            if 'torch' in globals() and hasattr(torch, 'cuda'):
                try:
                    if torch.cuda.is_available():
                        torch.cuda.empty_cache()
                except Exception:
                    # Ignore any cuda-related errors during cleanup
                    pass
        except Exception:
            # Ensure destructor never raises
            pass



class SpellingModel:
    """Wrapper class for the Arabic spelling correction model."""
    
    def __init__(self, model_path=None):
        """
        Initialize the spelling model.
        
        Args:
            model_path: Path to the model directory (defaults to SPELLING_PATH)
        """
        self.model_path = Path(model_path) if model_path else SPELLING_PATH
        self.model = None
        self.device = None
        
        self._validate_path()
        self._load_model()
    
    def _validate_path(self):
        """Validate that the model path exists."""
        if not self.model_path.exists():
            raise FileNotFoundError(f"Model path does not exist: {self.model_path}")
        
        # Check for .pt file
        pt_files = list(self.model_path.glob("*.pt"))
        if not pt_files:
            raise FileNotFoundError(f"No .pt model file found in: {self.model_path}")
        
        logger.info(f"Spelling model path validated: {self.model_path}")
    
    def _load_model(self):
        """Load the spelling model."""
        try:
            global ArabicSpellChecker
            if ArabicSpellChecker is None:
                try:
                    from ara_spell import ArabicSpellChecker as _ArabicSpellChecker
                except ImportError:
                    try:
                        from src.ara_spell import ArabicSpellChecker as _ArabicSpellChecker
                    except ImportError:
                        from .ara_spell import ArabicSpellChecker as _ArabicSpellChecker
                ArabicSpellChecker = _ArabicSpellChecker

            self.device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
            logger.info(f"Loading spelling model on {self.device}...")
            
            # Load tokenizer (using AraBERT tokenizer as it matches the vocab size 64000)
            logger.info("Loading tokenizer for spelling model...")
            try:
                self.tokenizer = AutoTokenizer.from_pretrained("aubmindlab/bert-base-arabertv02")
            except Exception as e:
                logger.warning(f"Could not load aubmindlab/bert-base-arabertv02 tokenizer: {e}")
                # Fallback or error - strictly speaking we need this one
                raise RuntimeError(f"Tokenizer load failed: {e}")

            # Define the configuration for the EncoderDecoder model
            # Based on inspection, it uses BERT-like architecture with 64000 vocab
            # We'll create a generic config that matches what we found
            config_encoder = BertConfig(
                vocab_size=64000,
                hidden_size=768,
                num_hidden_layers=12,
                num_attention_heads=12,
                intermediate_size=3072
            )
            config_decoder = BertConfig(
                vocab_size=64000,
                hidden_size=768,
                num_hidden_layers=12,
                num_attention_heads=12,
                intermediate_size=3072,
                is_decoder=True,
                add_cross_attention=True
            )
            config = EncoderDecoderConfig.from_encoder_decoder_configs(config_encoder, config_decoder)
            
            # Initialize empty model
            self.model = EncoderDecoderModel(config=config)
            
            # Load state dict
            pt_file = list(self.model_path.glob("*.pt"))[0]
            logger.info(f"Loading weights from {pt_file}...")
            checkpoint = torch.load(pt_file, map_location=self.device)
            
            if "model_state_dict" in checkpoint:
                state_dict = checkpoint["model_state_dict"]
            else:
                state_dict = checkpoint
                
            # Load weights into model
            self.model.load_state_dict(state_dict)
            
            self.model.to(self.device)
            self.model.eval()
            
            # Set special tokens for generation
            # Usually strict encoder-decoder models need decoder_start_token_id
            self.model.config.decoder_start_token_id = self.tokenizer.cls_token_id
            self.model.config.eos_token_id = self.tokenizer.sep_token_id
            self.model.config.pad_token_id = self.tokenizer.pad_token_id
            self.model.config.vocab_size = self.model.config.encoder.vocab_size
            
            # Initialize the ArabicSpellChecker engine
            logger.info("Initializing ArabicSpellChecker engine...")
            self.engine = ArabicSpellChecker(self.model, self.tokenizer, self.device, use_contextual=True)
            logger.info("ArabicSpellChecker engine initialized successfully")

            logger.info("Spelling model loaded successfully")
            
        except Exception as e:
            logger.error(f"Error loading spelling model: {str(e)}")
            raise RuntimeError(f"Failed to load spelling model: {str(e)}")
    
    def correct(self, text):
        """
        Correct spelling in Arabic text.
        
        Args:
            text: Input Arabic text
            
        Returns:
            str: Corrected text
        """
        if not hasattr(self, 'engine'):
            # This should have happened in __init__ -> _load_model, but just in case
            logger.warning("Engine not found, reloading spelling model...")
            self._load_model()
        
        try:
            # Use the integrated AraSpell pipeline (Pre-process -> Generate -> Rerank -> Post-process)
            return self.engine.correct(text)
            
        except Exception as e:
            logger.error(f"Error during spelling correction: {str(e)}")
            # In case of error, return original text to avoid crashing the app flow
            logger.warning("Returning original text due to error.")
            return text


class AutocompleteModel:
    """Wrapper class for the Arabic autocomplete model."""
    
    def __init__(self, model_path=None, lazy=True):
        """
        Initialize the autocomplete model.
        
        Args:
            model_path: Path to the model directory (defaults to AUTOCOMPLETE_PATH)
            lazy: If True, models will be loaded on first use instead of initialization
        """
        self.model_path = Path(model_path) if model_path else AUTOCOMPLETE_PATH
        # GPT-2 only components (no bigram .pkl on this machine)
        self.bigram_model = None  # kept for backward compatibility (unused)
        self.ngram_model = None   # unused
        self.unigrams = None      # unused
        self.bigrams = None       # unused
        self._hybrid = None       # reference to hybrid_module (for GPT-2 helpers)
        self._gpt_tokenizer = None
        self._gpt_model = None
        self.lazy = lazy
        self.enabled = os.environ.get("LOAD_AUTOCOMPLETE", "false").lower() == "true"
        
        if not self.enabled:
            logger.info("Autocomplete model is disabled (LOAD_AUTOCOMPLETE=false)")
            return

        self._validate_path()
        if not self.lazy:
            self._load_model()
    
    def _validate_path(self):
        """Validate that the model path exists."""
        if not self.model_path.exists():
            raise FileNotFoundError(f"Model path does not exist: {self.model_path}")
        
        logger.info(f"Autocomplete model path validated: {self.model_path}")
    
    def _load_model(self):
        """Load GPT-2 autocomplete model using hybrid_module (GPT-2 only, no bigram .pkl)."""
        try:
            logger.info("Loading autocomplete models...")

            # Load hybrid_module.py dynamically from the model directory
            hybrid_path = self.model_path / "hybrid_module.py"
            if not hybrid_path.exists():
                raise FileNotFoundError(f"hybrid_module.py not found at: {hybrid_path}")

            spec = importlib.util.spec_from_file_location("autocomplete_hybrid", str(hybrid_path))
            if spec is None or spec.loader is None:
                raise ImportError(f"Could not load spec for hybrid_module from: {hybrid_path}")

            hybrid = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(hybrid)
            self._hybrid = hybrid
            logger.info("hybrid_module imported successfully")

            # Load GPT-2 model (on CPU) for autocomplete.
            if hasattr(hybrid, "load_gpt2"):
                try:
                    logger.info("Loading GPT-2 model for autocomplete (CPU, GPT-2 only mode)...")
                    tokenizer, model = hybrid.load_gpt2()
                    # Force CPU to avoid GPU OOM / kills
                    model.to(torch.device("cpu"))
                    self._gpt_tokenizer = tokenizer
                    self._gpt_model = model
                    logger.info("GPT-2 model loaded successfully for autocomplete (CPU)")
                except Exception as gpt_err:
                    logger.error(f"Failed to load GPT-2 for autocomplete: {gpt_err}")
                    raise
            else:
                raise RuntimeError("hybrid_module.load_gpt2 not found; cannot run GPT-2-only autocomplete")

            logger.info("Autocomplete GPT-2-only model loaded successfully")
        except Exception as e:
            logger.error(f"Error loading autocomplete models: {str(e)}")
            raise RuntimeError(f"Failed to load autocomplete models: {str(e)}")
    
    def predict(self, text, n=5):
        """
        Predict next words for autocomplete.
        
        Args:
            text: Input Arabic text
            n: Number of suggestions to return
            
        Returns:
            list: List of suggested completions
        """
        if not self.enabled:
            return []

        if self._hybrid is None or self._gpt_model is None or self._gpt_tokenizer is None:
            if self.lazy:
                try:
                    self._load_model()
                except Exception as e:
                    logger.error(f"Lazy loading of autocomplete failed: {str(e)}")
                    self.enabled = False
                    return []
            else:
                raise RuntimeError("Model not loaded and lazy loading is off")
        
        try:
            # GPT-2 only autocomplete using hybrid_module.gpt2_next_token_probs
            if not self._hybrid or self._gpt_model is None or self._gpt_tokenizer is None:
                raise RuntimeError("GPT-2 autocomplete components not loaded")

            logger.info(
                f"[Autocomplete] predict called | mode=gpt2-only | text_tail='{text[-50:]}'"
            )

            if not hasattr(self._hybrid, "gpt2_next_token_probs"):
                raise RuntimeError("hybrid_module.gpt2_next_token_probs not found")

            # Get token probability dict from GPT-2
            prob_dict = self._hybrid.gpt2_next_token_probs(
                text,
                self._gpt_tokenizer,
                self._gpt_model,
                top_k=max(n * 2, 10),  # grab a few extra for diversity
            )

            # Convert dict to sorted list of (token, prob)
            preds = sorted(prob_dict.items(), key=lambda x: x[1], reverse=True)
            logger.info(f"[Autocomplete] raw GPT-2 predictions (top 5): {preds[:5]}")

            # Extract top-n tokens as suggestions
            suggestions = [w for (w, _p) in preds[:n] if w]
            logger.info(f"[Autocomplete] suggestions returned to API: {suggestions}")
            return suggestions
        except Exception as e:
            logger.error(f"Error during autocomplete prediction: {str(e)}")
            raise RuntimeError(f"Autocomplete prediction failed: {str(e)}")


class GrammarModel:
    """Wrapper class for the Arabic grammar correction model."""
    
    def __init__(self, model_path=None):
        """
        Initialize the grammar model.
        
        Args:
            model_path: Path to the model directory (defaults to GRAMMAR_PATH)
        """
        self.model_path = Path(model_path) if model_path else GRAMMAR_PATH
        self.model = None
        self.tokenizer = None
        self.device = None
        
        self._validate_path()
        self._load_model()
    
    def _validate_path(self):
        """Validate that the model path exists and contains required files."""
        if not self.model_path.exists():
            raise FileNotFoundError(f"Model path does not exist: {self.model_path}")
        
        required_files = ['config.json', 'tokenizer.json', 'model.safetensors']
        missing_files = [f for f in required_files if not (self.model_path / f).exists()]
        
        if missing_files:
            raise FileNotFoundError(f"Missing required files: {', '.join(missing_files)}")
        
        logger.info(f"Grammar model path validated: {self.model_path}")
    
    def _load_model(self):
        """Load the grammar model and tokenizer."""
        try:
            # Force CPU-only to avoid GPU OOM / system freezes
            self.device = torch.device('cpu')
            logger.info("Loading grammar model on CPU (GPU disabled by design)...")
            
            self.tokenizer = AutoTokenizer.from_pretrained(
                str(self.model_path),
                local_files_only=True
            )
            
            self.model = AutoModelForCausalLM.from_pretrained(
                str(self.model_path),
                local_files_only=True,
                trust_remote_code=True,
                torch_dtype=torch.float32  # safe default for CPU inference
            )
            
            self.model.to(self.device)
            self.model.eval()
            
            logger.info("Grammar model loaded successfully")
        except Exception as e:
            logger.error(f"Error loading grammar model: {str(e)}")
            raise RuntimeError(f"Failed to load grammar model: {str(e)}")
    
    def correct(self, text):
        """
        Correct grammar in Arabic text with a timeout.
        
        Args:
            text: Input Arabic text
            
        Returns:
            str: Grammar-corrected text
        """
        if self.model is None or self.tokenizer is None:
            raise RuntimeError("Model not loaded")
        
        import threading
        result = [text]  # default to original
        error = [None]
        
        def _generate():
            try:
                # Use Gemma 3 chat template — pass text only (model is GEC-trained)
                messages = [{"role": "user", "content": text}]
                prompt = self.tokenizer.apply_chat_template(
                    messages,
                    tokenize=False,
                    add_generation_prompt=True,
                )
                
                inputs = self.tokenizer(
                    prompt,
                    max_length=256,
                    truncation=True,
                    padding=True,
                    return_tensors="pt",
                    add_special_tokens=False,
                )
                
                inputs = {k: v.to(self.device) for k, v in inputs.items()}
                input_length = inputs['input_ids'].shape[1]
                
                with torch.no_grad():
                    outputs = self.model.generate(
                        **inputs,
                        max_new_tokens=64,   # enough for corrected sentence
                        do_sample=False,
                    )
                
                # Decode only the NEW tokens (skip the prompt)
                new_tokens = outputs[0][input_length:]
                corrected = self.tokenizer.decode(new_tokens, skip_special_tokens=True).strip()
                
                # If model returned empty or nonsense, keep original
                if not corrected or len(corrected) < 2:
                    return
                
                # Reject generic instruction phrases (model fallback, not actual correction)
                generic_phrases = (
                    "أعد كتابتها", "أعد كتابته", "أعد كتابتها.", "أعد كتابته.",
                    "اعيد كتابتها", "اعيد كتابته", "أعد كتابة", "اعيد كتابة",
                    "أعد كتابتها فقط", "أعد كتابته فقط",
                )
                corrected_lower = corrected.strip()
                for phrase in generic_phrases:
                    if phrase in corrected_lower or corrected_lower.startswith(phrase):
                        return
                
                # Take only the first non-empty line as the corrected sentence
                corrected_lines = [l.strip() for l in corrected.split('\n') if l.strip()]
                if corrected_lines:
                    first = corrected_lines[0]
                    if first and len(first) >= 2 and first not in generic_phrases:
                        result[0] = first
            except Exception as e:
                error[0] = e
        
        # Run generation in a thread with a 30s timeout
        thread = threading.Thread(target=_generate)
        thread.start()
        thread.join(timeout=30)
        
        if thread.is_alive():
            logger.warning("[Grammar] Timed out after 30s — returning original text")
            return text
        
        if error[0]:
            logger.error(f"Error during grammar correction: {str(error[0])}")
            logger.warning("Returning original text due to grammar error.")
        
        return result[0]


class PunctuationModel:
    """Wrapper class for the Arabic punctuation model."""
    
    def __init__(self, model_path=None):
        """
        Initialize the punctuation model.
        
        Args:
            model_path: Path to the model directory (defaults to PUNCTUATION_PATH)
        """
        self.model_path = Path(model_path) if model_path else PUNCTUATION_PATH
        self.model = None
        self.tokenizer = None
        self.device = None
        
        self._validate_path()
        self._load_model()
    
    def _validate_path(self):
        """Validate that the model path exists and contains required files."""
        if not self.model_path.exists():
            raise FileNotFoundError(f"Model path does not exist: {self.model_path}")
        
        required_files = ['config.json', 'tokenizer.json', 'model.safetensors']
        missing_files = [f for f in required_files if not (self.model_path / f).exists()]
        
        if missing_files:
            raise FileNotFoundError(f"Missing required files: {', '.join(missing_files)}")
        
        logger.info(f"Punctuation model path validated: {self.model_path}")
    
    def _load_model(self):
        """Load the punctuation model and tokenizer."""
        try:
            self.device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
            logger.info(f"Loading punctuation model on {self.device}...")
            
            self.tokenizer = AutoTokenizer.from_pretrained(
                str(self.model_path),
                local_files_only=True
            )
            
            self.model = AutoModelForSeq2SeqLM.from_pretrained(
                str(self.model_path),
                local_files_only=True
            )
            
            self.model.to(self.device)
            self.model.eval()
            
            logger.info("Punctuation model loaded successfully")
        except Exception as e:
            logger.error(f"Error loading punctuation model: {str(e)}")
            raise RuntimeError(f"Failed to load punctuation model: {str(e)}")
    
    def add_punctuation(self, text):
        """
        Add punctuation to Arabic text.
        
        Args:
            text: Input Arabic text without punctuation
            
        Returns:
            str: Text with punctuation added
        """
        if self.model is None or self.tokenizer is None:
            raise RuntimeError("Model not loaded")
        
        try:
            inputs = self.tokenizer(
                text,
                max_length=512,
                truncation=True,
                padding=True,
                return_tensors="pt"
            )
            
            inputs = {k: v.to(self.device) for k, v in inputs.items()}
            
            # Since it's an EncoderDecoderModel, we use generate()
            with torch.no_grad():
                outputs = self.model.generate(
                    **inputs,
                    max_length=512,
                    decoder_start_token_id=self.tokenizer.cls_token_id,
                    eos_token_id=self.tokenizer.sep_token_id,
                    pad_token_id=self.tokenizer.pad_token_id
                )
            
            punctuated = self.tokenizer.decode(outputs[0], skip_special_tokens=True)
            return punctuated.strip()
        
        except Exception as e:
            logger.error(f"Error during punctuation: {str(e)}")
            logger.warning("Returning original text due to punctuation error.")
            return text
