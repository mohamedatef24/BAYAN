"""
Flask backend server for Arabic text summarization.
Provides API endpoints for the Bayan web application.
"""

import os
import logging
from flask import Flask, request, jsonify
from flask_cors import CORS
from pathlib import Path
import traceback

from model_loader import SummarizationModel

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Initialize Flask app
app = Flask(__name__, static_folder='.', static_url_path='')
CORS(app)  # Enable CORS for all routes

# Configuration
MAX_TEXT_LENGTH = 5000  # Maximum characters for input text
MAX_SUMMARY_LENGTH = 512  # Maximum tokens for summary
MIN_TEXT_LENGTH = 10  # Minimum characters for summarization

# Global model instance
model = None


def get_model_path():
    """Get the model path, handling different possible locations."""
    base_path = Path(__file__).parent.parent
    current_dir = Path.cwd()
    
    # Try different possible paths
    possible_paths = [
        base_path / "models" / "arabic_summarization_model" / "content" / "drive" / "MyDrive" / "arabic_summarization_model",
        base_path / "models" / "arabic_summarization_model",
        current_dir / "models" / "arabic_summarization_model" / "content" / "drive" / "MyDrive" / "arabic_summarization_model",
        current_dir / "models" / "arabic_summarization_model",
        Path("models") / "arabic_summarization_model" / "content" / "drive" / "MyDrive" / "arabic_summarization_model",
        Path("models") / "arabic_summarization_model",
    ]
    
    for path in possible_paths:
        path = path.resolve()  # Resolve to absolute path
        if path.exists() and (path / "config.json").exists():
            logger.info(f"Found model at: {path}")
            return str(path)
    
    # Provide helpful error message
    error_msg = f"Model not found. Searched in:\n"
    for p in possible_paths:
        error_msg += f"  - {p.resolve()}\n"
    error_msg += "\nPlease ensure the model files are in one of these locations."
    raise FileNotFoundError(error_msg)


def load_model():
    """Load the summarization model."""
    global model
    try:
        model_path = get_model_path()
        logger.info(f"Loading model from: {model_path}")
        model = SummarizationModel(model_path)
        logger.info("Model loaded successfully")
        return True
    except Exception as e:
        logger.error(f"Error loading model: {str(e)}")
        logger.error(traceback.format_exc())
        return False


@app.route('/')
def index():
    """Serve the main HTML file."""
    return app.send_static_file('index.html')


@app.route('/api/health', methods=['GET'])
def health_check():
    """Health check endpoint."""
    return jsonify({
        'status': 'healthy',
        'model_loaded': model is not None
    })


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
    if model is None:
        return jsonify({
            'error': 'Model not loaded. Please check server logs.',
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
        summary = model.summarize(text, max_length=max_length, min_length=max(10, max_length // 3))
        
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


if __name__ == '__main__':
    # Load model on startup
    logger.info("Starting Bayan server...")
    
    if not load_model():
        logger.error("Failed to load model. Server will start but summarization will not work.")
        logger.error("Please check that the model files are in the correct location.")
    
    # Run the app
    port = int(os.environ.get('PORT', 5000))
    debug = os.environ.get('DEBUG', 'False').lower() == 'true'
    
    logger.info(f"Starting server on port {port} (debug={debug})")
    app.run(host='0.0.0.0', port=port, debug=debug)

