"""
Model loader for Arabic summarization model.
Handles loading and inference with error handling.
"""

import os
import logging
from pathlib import Path
import json
import torch
from transformers import MBartForConditionalGeneration, AutoTokenizer, AutoConfig

logger = logging.getLogger(__name__)


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
        self.model_path = Path(model_path)
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
                    str(self.model_path),
                    local_files_only=True,
                    trust_remote_code=False
                )
                logger.info("Tokenizer loaded successfully")
            except Exception as e:
                logger.error(f"Failed to load tokenizer: {str(e)}")
                # Try without local_files_only as fallback
                logger.info("Retrying tokenizer load without local_files_only...")
                self.tokenizer = AutoTokenizer.from_pretrained(
                    str(self.model_path),
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
                    str(self.model_path),
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
                        str(self.model_path),
                        config=config,
                        local_files_only=True,
                        trust_remote_code=False,
                        torch_dtype=torch.float32
                    )
                except Exception as e:
                    logger.warning(f"Failed to load with config: {str(e)}")
                    # Try without explicit config
                    self.model = MBartForConditionalGeneration.from_pretrained(
                        str(self.model_path),
                        local_files_only=True,
                        trust_remote_code=False,
                        torch_dtype=torch.float32
                    )
            except Exception as e:
                logger.warning(f"Failed to load config: {str(e)}")
                logger.info("Retrying model load without config fix...")
                try:
                    self.model = MBartForConditionalGeneration.from_pretrained(
                        str(self.model_path),
                        local_files_only=True,
                        trust_remote_code=False,
                        torch_dtype=torch.float32
                    )
                except Exception as e2:
                    logger.warning(f"Failed to load with local_files_only: {str(e2)}")
                    logger.info("Retrying model load without local_files_only...")
                    self.model = MBartForConditionalGeneration.from_pretrained(
                        str(self.model_path),
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
    
    def summarize(self, text, max_length=150, min_length=30, num_beams=4, **kwargs):
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
            
            # Generate summary
            with torch.no_grad():
                outputs = self.model.generate(
                    **inputs,
                    max_length=max_length,
                    min_length=min_length,
                    num_beams=num_beams,
                    early_stopping=True,
                    no_repeat_ngram_size=3,
                    **kwargs
                )
            
            # Decode output
            summary = self.tokenizer.decode(outputs[0], skip_special_tokens=True)
            
            return summary.strip()
        
        except Exception as e:
            logger.error(f"Error during summarization: {str(e)}")
            raise RuntimeError(f"Summarization failed: {str(e)}")
    
    def __del__(self):
        """Cleanup resources."""
        if self.model is not None:
            del self.model
        if torch.cuda.is_available():
            torch.cuda.empty_cache()

