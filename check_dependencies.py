"""Check if all required dependencies are installed."""

import sys

required_packages = {
    'flask': 'Flask',
    'flask_cors': 'flask-cors',
    'transformers': 'transformers',
    'torch': 'torch',
    'sentencepiece': 'sentencepiece',
}

missing = []
for module, package in required_packages.items():
    try:
        __import__(module)
        print(f"✓ {package} is installed")
    except ImportError:
        print(f"✗ {package} is NOT installed")
        missing.append(package)

if missing:
    print(f"\nMissing packages: {', '.join(missing)}")
    print("Install them with: pip install -r requirements.txt")
    sys.exit(1)
else:
    print("\nAll dependencies are installed!")
    sys.exit(0)

