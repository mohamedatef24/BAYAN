"""
Simple script to run the Bayan application.
Usage: python run_app.py
"""

import sys
import os
from pathlib import Path

# Add src directory to path
src_path = Path(__file__).parent / 'src'
sys.path.insert(0, str(src_path))

# Change to src directory
os.chdir(src_path)

# Import and run the app
if __name__ == '__main__':
    from app import app, load_model
    import logging
    
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    logger = logging.getLogger(__name__)
    logger.info("Starting Bayan application...")
    
    # Load model
    if not load_model():
        logger.error("Failed to load model. Server will start but summarization will not work.")
        logger.error("Please check that the model files are in the correct location.")
    
    # Run the app
    port = int(os.environ.get('PORT', 5000))
    debug = os.environ.get('DEBUG', 'False').lower() == 'true'
    
    logger.info(f"Starting server on http://localhost:{port}")
    logger.info("Press Ctrl+C to stop the server")
    
    app.run(host='0.0.0.0', port=port, debug=debug)

