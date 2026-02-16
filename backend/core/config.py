# backend/core/config.py - Enhanced Configuration System
import os
from functools import lru_cache
try:
    from pydantic_settings import BaseSettings
except ImportError:
    from pydantic import BaseSettings

class Settings(BaseSettings):
    # File Upload Limits
    MAX_FILES_PER_SESSION: int = 4
    MAX_FILE_SIZE_MB: int = 20
    ALLOWED_EXTENSIONS: list = [".pdf", ".docx", ".doc"]
    
    # Vector Database
    CHROMA_DIR: str = "./chroma_store"
    EMBEDDING_MODEL: str = "all-MiniLM-L6-v2"
    
    # Text Processing
    CHUNK_SIZE: int = 1000
    CHUNK_OVERLAP: int = 200
    MAX_CHUNKS_PER_FILE: int = 500
    
    # RAG Parameters
    RETRIEVAL_TOP_K: int = 5
    SIMILARITY_THRESHOLD: float = 0.6
    MAX_CONTEXT_LENGTH: int = 4000
    
    # Session Management
    MAX_QUESTIONS_PER_SESSION: int = 50
    SESSION_TIMEOUT_HOURS: int = 24
    
    # Headers
    HEADER_SESSION_ID: str = "X-Session-ID"
    HEADER_API_KEY: str = "X-API-Key"
    HEADER_PROVIDER: str = "X-Provider"
    
    # Server Settings
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    WORKERS: int = 1
    RELOAD: bool = False
    
    # Supported LLM Providers
    SUPPORTED_PROVIDERS: list = ["openai", "gemini", "anthropic"]
    DEFAULT_PROVIDER: str = "openai"
    
    # Security & Logging
    SECRET_KEY: str = "your-secret-key-here"
    ALLOWED_ORIGINS: list = ["*"]
    LOG_LEVEL: str = "info"
    LOG_FILE: str = "logs/rag.log"
    DEBUG: bool = False
    
    class Config:
        env_file = ".env"
        case_sensitive = True
        extra = "ignore"

@lru_cache()
def get_settings():
    return Settings()
