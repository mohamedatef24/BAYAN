# Bayan - Quick Start Guide

## 🚀 Quick Start

### 1. Install Dependencies
```bash
pip install -r requirements.txt
```

**Note:** If you have issues, install PyTorch separately:
- CPU: `pip install torch --index-url https://download.pytorch.org/whl/cpu`
- GPU: Visit https://pytorch.org/get-started/locally/

### 2. Run the Application
```bash
python run_app.py
```

### 3. Open in Browser
Navigate to: **http://localhost:5000**

## 📁 Project Structure

```
Bayan/
├── src/
│   ├── app.py              # Flask backend server
│   ├── model_loader.py     # Model loading and inference
│   └── index.html          # Web interface
├── models/
│   └── arabic_summarization_model/
│       └── content/drive/MyDrive/arabic_summarization_model/
│           ├── config.json
│           ├── model.safetensors
│           └── ... (other model files)
├── run_app.py              # Application launcher
├── requirements.txt         # Python dependencies
└── README_SETUP.md         # Detailed setup guide
```

## 🔧 Features

✅ **Robust Error Handling**
- Path validation for model files
- Graceful fallbacks if model loading fails
- Input validation and sanitization
- Clear error messages

✅ **Security**
- Input length limits (max 5000 characters)
- CORS enabled for web interface
- Safe model loading
- Error logging

✅ **User Experience**
- Loading indicators
- Real-time feedback
- Arabic language support
- Responsive design

## 🧪 Testing

### Test API Health
```bash
curl http://localhost:5000/api/health
```

### Test Summarization
```bash
curl -X POST http://localhost:5000/api/summarize \
  -H "Content-Type: application/json" \
  -d '{"text": "نص تجريبي للاختبار", "length": 2, "full_text": true}'
```

## 🐛 Troubleshooting

### Model Not Found
- Verify model path: `models/arabic_summarization_model/content/drive/MyDrive/arabic_summarization_model/`
- Check that `config.json` exists
- The app will search multiple possible locations automatically

### Dependencies Missing
```bash
python check_dependencies.py
pip install -r requirements.txt
```

### Port Already in Use
```bash
set PORT=5001
python run_app.py
```

## 📝 API Documentation

### POST /api/summarize
Summarize Arabic text.

**Request:**
```json
{
  "text": "النص العربي...",
  "length": 2,  // 1=short, 2=medium, 3=long
  "full_text": true
}
```

**Response:**
```json
{
  "status": "success",
  "summary": "الملخص...",
  "original_length": 500,
  "summary_length": 150
}
```

## 🎯 Next Steps

1. Install dependencies: `pip install -r requirements.txt`
2. Run the app: `python run_app.py`
3. Open browser: http://localhost:5000
4. Write Arabic text and click "توليد الملخص"

For detailed information, see `README_SETUP.md`.

