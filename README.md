# 🧠 Enhanced RAG System - IntelliDocs

A production-ready **Retrieval-Augmented Generation (RAG)** system that transforms your documents into intelligent conversations. Built with modern web technologies and AI capabilities for seamless document analysis.

![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)
![FastAPI](https://img.shields.io/badge/FastAPI-0.104+-green.svg)
![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)

## ✨ Features

### 🎯 **Core Capabilities**
- **Progressive File Upload**: Upload up to 4 documents (PDF/DOCX) without losing existing files
- **Intelligent Chat**: Ask questions and get answers based on your document content
- **Multi-Document Analysis**: Query across multiple documents simultaneously
- **Semantic Search**: Advanced retrieval with both vector similarity and keyword matching
- **Real-time Responses**: Instant AI-powered answers with source attribution

### 🔧 **Technical Features**
- **Multiple LLM Providers**: OpenAI, Anthropic Claude, Google Gemini support
- **Semantic Chunking**: Intelligent text segmentation preserving context
- **Vector Database**: ChromaDB for efficient similarity search
- **Session Management**: Secure, temporary sessions with no data persistence
- **Caching System**: Embedding caching for improved performance
- **Production Ready**: Built with FastAPI, proper error handling, and logging

### 🎨 **User Experience**
- **Beautiful UI**: Modern, responsive design with animations
- **Drag & Drop**: Intuitive file upload experience
- **Real-time Feedback**: Progress indicators and status updates
- **File Management**: Add, remove, and manage documents easily
- **Source Attribution**: See which documents provided each answer

## 🚀 Quick Start

### Prerequisites
- Python 3.8 or higher
- 4GB+ RAM recommended
- Modern web browser

### Installation

1. **Clone the repository**
```bash
git clone <repository-url>
cd enhanced_rag
```

2. **Make startup script executable**
```bash
chmod +x start.sh
```

3. **Run the application**
```bash
./start.sh
```

The script will:
- Create a virtual environment
- Install all dependencies
- Initialize databases
- Start the server on `http://localhost:8000`

### Manual Setup (Alternative)

If you prefer manual setup:

```bash
# Create virtual environment
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Start the server
uvicorn main:app --reload
```

## 🎮 Usage Guide

### 1. **Welcome & Setup**
1. Open `http://localhost:8000` in your browser
2. Enter your name to create a session
3. Choose an AI provider (OpenAI, Anthropic, or Gemini)
4. Enter your API key and test the connection

### 2. **Document Upload**
- **Drag & Drop**: Drop files onto the upload zone
- **Browse**: Click to select files from your computer
- **Progressive Upload**: Add new files without removing existing ones
- **Supported Formats**: PDF, DOCX, DOC (up to 20MB each)

### 3. **Chat Interface**
- **Ask Questions**: Type naturally about your documents
- **View Sources**: See which documents provided each answer
- **File Management**: Remove individual files or clear all
- **Session Limits**: Up to 50 questions per session

### 4. **Advanced Features**
- **Multi-file Queries**: Ask questions that span multiple documents
- **Contextual Answers**: Get responses that combine information from different sources
- **Real-time Processing**: See upload progress and typing indicators

## 🏗️ Architecture

### Backend Components

```
backend/
├── api/           # FastAPI routes
│   ├── routes_upload.py    # File upload handling
│   ├── routes_rag.py       # Chat and Q&A
│   ├── routes_validate.py  # Authentication
│   └── routes_files.py     # File management
├── core/          # Core system
│   ├── config.py           # Configuration management
│   └── session.py          # Session handling
├── ingestion/     # Document processing
│   ├── document_processor.py  # PDF/DOCX extraction
│   └── chunker.py             # Semantic chunking
├── embedding/     # Vector embeddings
│   └── embedding.py        # Sentence transformers
├── vector/        # Vector storage
│   ├── vectorstore.py      # ChromaDB interface
│   └── retriever.py        # Advanced retrieval
└── llm/           # LLM integration
    └── provider.py         # Multi-provider support
```

### Frontend Components

```
frontend/
├── welcome.html   # Landing page
├── auth.html      # API key setup
├── chat.html      # Main interface
└── static/
    ├── css/       # Styled components
    └── js/        # Interactive features
```

## 🔧 Configuration

### Environment Variables

Create a `.env` file or modify the generated one:

```bash
# Server Settings
HOST=0.0.0.0
PORT=8000
WORKERS=1

# File Upload Limits
MAX_FILES_PER_SESSION=4
MAX_FILE_SIZE_MB=20

# Session Management
MAX_QUESTIONS_PER_SESSION=50
SESSION_TIMEOUT_HOURS=24

# Vector Database
CHROMA_DIR=./chroma_store

# Embedding Model
EMBEDDING_MODEL=all-MiniLM-L6-v2

# Text Processing
CHUNK_SIZE=1000
CHUNK_OVERLAP=200
```

### Supported LLM Providers

#### OpenAI
- **Models**: GPT-3.5 Turbo, GPT-4
- **API Key Format**: `sk-...`
- **Get API Key**: [OpenAI Platform](https://platform.openai.com/api-keys)

#### Anthropic
- **Models**: Claude 3 Haiku, Claude 3 Sonnet
- **API Key Format**: `sk-ant-...`
- **Get API Key**: [Anthropic Console](https://console.anthropic.com/)

#### Google Gemini
- **Models**: Gemini Pro
- **API Key Format**: `AI...`
- **Get API Key**: [Google AI Studio](https://makersuite.google.com/app/apikey)

## 🚀 Production Deployment

### Using Docker (Recommended)

```dockerfile
FROM python:3.9-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .
EXPOSE 8000

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
```

### Using Gunicorn

```bash
gunicorn main:app -w 4 -k uvicorn.workers.UvicornWorker --bind 0.0.0.0:8000
```

### Environment-Specific Settings

#### Development
```bash
export RELOAD=true
export LOG_LEVEL=debug
```

#### Production
```bash
export WORKERS=4
export LOG_LEVEL=warning
export SECRET_KEY=your-production-secret
export ALLOWED_ORIGINS=https://yourdomain.com
```

## 🧪 Advanced Usage

### Custom Embedding Models

Modify `backend/core/config.py`:

```python
EMBEDDING_MODEL = "sentence-transformers/all-mpnet-base-v2"
# or
EMBEDDING_MODEL = "sentence-transformers/all-distilroberta-v1"
```

### Custom Chunking Strategy

Modify `backend/ingestion/chunker.py`:

```python
chunker = SemanticChunker(
    chunk_size=1500,      # Larger chunks
    overlap=300,          # More overlap
)
```

### API Integration

```python
import requests

# Upload files
files = {'files': open('document.pdf', 'rb')}
response = requests.post(
    'http://localhost:8000/api/upload/files',
    data={'session_id': 'your-session-id'},
    files=files
)

# Ask questions
response = requests.post(
    'http://localhost:8000/api/rag/ask',
    json={'question': 'What is the main topic?'},
    headers={
        'X-Session-ID': 'your-session-id',
        'X-API-Key': 'your-api-key',
        'X-Provider': 'openai'
    }
)
```

## 🛠️ Development

### Project Structure
- `main.py` - FastAPI application entry point
- `start.sh` - Development startup script
- `requirements.txt` - Python dependencies
- `backend/` - Server-side logic
- `frontend/` - Client-side interface

### Adding New Features

1. **Backend**: Add routes in `backend/api/`
2. **Frontend**: Modify HTML/CSS/JS in `frontend/`
3. **Database**: Update models in `backend/core/`

### Running Tests

```bash
pytest tests/ -v
```

## 📊 Performance

### Benchmarks
- **File Processing**: ~2-5 seconds per MB
- **Query Response**: ~1-3 seconds
- **Memory Usage**: ~500MB base + ~100MB per session
- **Concurrent Users**: 10+ (single worker)

### Optimization Tips
1. Use smaller embedding models for faster processing
2. Increase chunk overlap for better retrieval
3. Use multiple workers for production
4. Enable response caching for repeated queries

## 🔒 Security

### Data Privacy
- **No Persistent Storage**: Files and conversations are session-only
- **API Key Security**: Keys stored in browser session only
- **Encrypted Communication**: HTTPS recommended for production

### Security Headers
```python
# Add to main.py for production
from fastapi.middleware.trustedhost import TrustedHostMiddleware

app.add_middleware(TrustedHostMiddleware, allowed_hosts=["example.com"])
```

## 🐛 Troubleshooting

### Common Issues

#### 1. **Import Errors**
```bash
# Ensure virtual environment is activated
source venv/bin/activate
pip install -r requirements.txt
```

#### 2. **ChromaDB Issues**
```bash
# Clear vector database
rm -rf chroma_store/
# Restart application
```

#### 3. **Memory Issues**
```bash
# Reduce chunk size in config.py
CHUNK_SIZE = 500
# Use smaller embedding model
EMBEDDING_MODEL = "all-MiniLM-L6-v2"
```

#### 4. **File Upload Failures**
- Check file size limits (20MB max)
- Verify file format (PDF/DOCX only)
- Ensure sufficient disk space

### Debug Mode

```bash
export LOG_LEVEL=debug
export RELOAD=true
./start.sh
```

## 📝 API Documentation

Once running, visit:
- **Interactive Docs**: `http://localhost:8000/docs`
- **ReDoc**: `http://localhost:8000/redoc`
- **OpenAPI JSON**: `http://localhost:8000/openapi.json`

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests
5. Submit a pull request

### Code Style
```bash
black backend/ frontend/
flake8 backend/
```

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- **FastAPI** for the excellent web framework
- **ChromaDB** for vector storage
- **Sentence Transformers** for embeddings
- **Tailwind CSS** for beautiful styling
- **OpenAI/Anthropic/Google** for AI capabilities

---

**Built with ❤️ for intelligent document analysis**

For questions, issues, or contributions, please visit our [GitHub repository](https://github.com/your-repo/enhanced-rag).
