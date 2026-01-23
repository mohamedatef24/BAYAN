# Bayan - Arabic Text Summarization Setup Guide

## Overview
Bayan is an Arabic text summarization application with a web interface. This guide will help you set up and run the application.

## Prerequisites
- Python 3.8 or higher
- pip (Python package manager)
- At least 4GB RAM (8GB+ recommended for better performance)
- Model files in the correct location (see below)

## Installation Steps

### 1. Install Dependencies
```bash
pip install -r requirements.txt
```

**Note:** If you encounter issues installing PyTorch, you may need to install it separately:
- For CPU: `pip install torch --index-url https://download.pytorch.org/whl/cpu`
- For CUDA: Visit https://pytorch.org/get-started/locally/ for the appropriate command

### 2. Verify Model Location
The model should be located at:
```
models/arabic_summarization_model/content/drive/MyDrive/arabic_summarization_model/
```

Required files:
- `config.json`
- `tokenizer.json`
- `model.safetensors`
- `sentencepiece.bpe.model`
- Other tokenizer/model files

### 3. Run the Application

#### Option A: Using the run script (Recommended)
```bash
python run_app.py
```

#### Option B: Direct Flask run
```bash
cd src
python app.py
```

#### Option C: Using Flask CLI
```bash
cd src
export FLASK_APP=app.py
flask run
```

### 4. Access the Application
Open your browser and navigate to:
```
http://localhost:5000
```

## Configuration

### Environment Variables
- `PORT`: Server port (default: 5000)
- `DEBUG`: Enable debug mode (default: False)
  ```bash
  export DEBUG=True
  export PORT=8080
  ```

## Troubleshooting

### Model Not Found Error
If you see "Model not found" error:
1. Verify the model path exists
2. Check that all required files are present
3. The application will search multiple possible paths automatically

### Out of Memory Error
If you encounter memory issues:
1. Close other applications
2. Use CPU mode (it will automatically use CPU if CUDA is not available)
3. Reduce the `MAX_TEXT_LENGTH` in `src/app.py` if needed

### Port Already in Use
If port 5000 is already in use:
```bash
export PORT=5001
python run_app.py
```

### Slow Performance
- First run will be slower as the model loads
- Subsequent requests will be faster
- Using GPU (CUDA) significantly improves performance

## API Endpoints

### Health Check
```
GET /api/health
```
Returns server status and model loading state.

### Summarize Text
```
POST /api/summarize
Content-Type: application/json

{
  "text": "النص العربي المراد تلخيصه...",
  "length": 2,  // 1=short, 2=medium, 3=long
  "full_text": true
}
```

Response:
```json
{
  "status": "success",
  "summary": "الملخص المولد...",
  "original_length": 500,
  "summary_length": 150
}
```

## Security Features

- Input validation (text length limits)
- CORS enabled for web interface
- Error handling and logging
- Path validation for model files
- Safe model loading with fallbacks

## Development

### Running in Debug Mode
```bash
export DEBUG=True
python run_app.py
```

### Testing the API
```bash
curl -X POST http://localhost:5000/api/summarize \
  -H "Content-Type: application/json" \
  -d '{"text": "نص تجريبي للاختبار", "length": 2, "full_text": true}'
```

## Support

For issues or questions:
1. Check the logs in the terminal
2. Verify model files are correct
3. Ensure all dependencies are installed
4. Check Python version compatibility

