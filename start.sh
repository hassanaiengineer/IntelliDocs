#!/bin/bash
# Enhanced RAG System Startup Script

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Print colored output
print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Configuration
HOST="${HOST:-0.0.0.0}"
PORT="${PORT:-8000}"
WORKERS="${WORKERS:-1}"
RELOAD="${RELOAD:-false}"

print_status "🚀 Starting Enhanced RAG System"
print_status "================================"

# Check Python version
python_version=$(python3 --version 2>&1 | grep -oP '\d+\.\d+')
required_version="3.8"

if [ "$(printf '%s\n' "$required_version" "$python_version" | sort -V | head -n1)" = "$required_version" ]; then
    print_success "Python version $python_version is compatible"
else
    print_error "Python 3.8+ required, found $python_version"
    exit 1
fi

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    print_status "Creating virtual environment..."
    python3 -m venv venv
    print_success "Virtual environment created"
fi

# Activate virtual environment
print_status "Activating virtual environment..."
source venv/bin/activate

# Install/update dependencies
if [ ! -f "venv/installed.flag" ] || [ "requirements.txt" -nt "venv/installed.flag" ]; then
    print_status "Installing/updating dependencies..."
    pip install --upgrade pip
    pip install -r requirements.txt
    touch venv/installed.flag
    print_success "Dependencies installed"
else
    print_status "Dependencies are up to date"
fi

# Create necessary directories
print_status "Creating data directories..."
mkdir -p chroma_store
mkdir -p logs
mkdir -p uploads

# Check if required environment variables are set
if [ ! -f ".env" ]; then
    print_status "Creating .env file from template..."
    cat > .env << EOF
# Enhanced RAG System Configuration

# Server Settings
HOST=0.0.0.0
PORT=8000
WORKERS=1
RELOAD=false

# File Upload Settings
MAX_FILES_PER_SESSION=4
MAX_FILE_SIZE_MB=20

# Vector Database
CHROMA_DIR=./chroma_store

# Session Settings
MAX_QUESTIONS_PER_SESSION=50
SESSION_TIMEOUT_HOURS=24

# Security (Optional - for production)
SECRET_KEY=your-secret-key-here
ALLOWED_ORIGINS=*

# Logging
LOG_LEVEL=info
LOG_FILE=logs/rag.log
EOF
    print_success ".env file created"
else
    print_status ".env file already exists"
fi

# Initialize database
print_status "Initializing databases..."
python3 -c "
from backend.core.session import init_session_db
from backend.embedding.embedding import embedding_service
from backend.vector.vectorstore import vector_store

print('✓ Session database initialized')
print('✓ Embedding service initialized')  
print('✓ Vector store initialized')
"

print_success "Database initialization complete"

# Start the server
print_status "Starting server..."
print_status "Host: $HOST"
print_status "Port: $PORT"
print_status "Workers: $WORKERS"

if [ "$RELOAD" = "true" ]; then
    print_warning "Development mode with auto-reload enabled"
    uvicorn main:app --host "$HOST" --port "$PORT" --reload
else
    print_status "Production mode"
    if [ "$WORKERS" -gt 1 ]; then
        gunicorn main:app -w "$WORKERS" -k uvicorn.workers.UvicornWorker --bind "$HOST:$PORT"
    else
        uvicorn main:app --host "$HOST" --port "$PORT"
    fi
fi
