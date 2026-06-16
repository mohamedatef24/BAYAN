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
    from app import app, load_models
    import logging
    
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    logger = logging.getLogger(__name__)
    logger.info("Starting Bayan application...")
    
    # Load models
    if not load_models():
        logger.error("Failed to load any models. Server will start but functionality will be limited.")
        logger.error("Please check that the model files are in the correct locations.")
    
    # Run the app
    port = int(os.environ.get('PORT', 5000))
    debug = os.environ.get('DEBUG', 'True').lower() == 'true'
    
    logger.info(f"Starting server on http://localhost:{port}")
    logger.info("Press Ctrl+C to stop the server")
    
    # Disable reloader to avoid loading models twice
    app.run(host='0.0.0.0', port=port, debug=debug, use_reloader=False)

