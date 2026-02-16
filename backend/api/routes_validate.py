# backend/api/routes_validate.py - Enhanced Validation Routes
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional

from backend.llm.provider import LLMProvider, normalize_provider
from backend.core.session import create_session, get_session, update_session_credentials

router = APIRouter(prefix="/auth", tags=["Authentication"])

class CreateSessionRequest(BaseModel):
    username: str

class ValidateCredentialsRequest(BaseModel):
    session_id: str
    provider: str
    api_key: str

class SessionResponse(BaseModel):
    session_id: str
    username: str
    message: str

@router.post("/create-session", response_model=SessionResponse)
async def create_user_session(payload: CreateSessionRequest):
    """Create a new user session"""
    username = payload.username.strip()
    
    if not username:
        raise HTTPException(status_code=400, detail="Username is required")
    
    if len(username) < 2:
        raise HTTPException(status_code=400, detail="Username must be at least 2 characters long")
    
    if len(username) > 50:
        raise HTTPException(status_code=400, detail="Username must be less than 50 characters")
    
    # Create new session
    session_id = create_session(username)
    
    return SessionResponse(
        session_id=session_id,
        username=username,
        message="Session created successfully"
    )

@router.post("/validate-credentials")
async def validate_credentials(payload: ValidateCredentialsRequest):
    """Validate API credentials and update session"""
    # Validate session exists
    session = get_session(payload.session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    # Normalize provider
    provider = normalize_provider(payload.provider)
    
    # Validate API key
    is_valid, message = LLMProvider.validate_api_key(provider, payload.api_key)
    
    if not is_valid:
        raise HTTPException(status_code=400, detail=message)
    
    # Update session with credentials
    update_session_credentials(payload.session_id, payload.api_key, provider)
    
    return {
        "status": "success",
        "provider": provider,
        "message": message,
        "session_id": payload.session_id
    }

@router.get("/session/{session_id}")
async def get_session_info(session_id: str):
    """Get session information"""
    session = get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    # Don't return sensitive information like API key
    return {
        "session_id": session_id,
        "username": session["username"],
        "provider": session.get("provider"),
        "has_api_key": bool(session.get("api_key")),
        "created_at": session["created_at"],
        "question_count": session["question_count"],
        "file_count": session["file_count"],
        "is_active": session["is_active"]
    }

@router.get("/providers")
async def get_supported_providers():
    """Get list of supported LLM providers"""
    from backend.core.config import get_settings
    settings = get_settings()
    
    return {
        "providers": [
            {
                "id": "openai",
                "name": "OpenAI",
                "description": "GPT-3.5 Turbo and GPT-4 models",
                "key_format": "sk-...",
                "website": "https://openai.com"
            },
            {
                "id": "anthropic",
                "name": "Anthropic",
                "description": "Claude models",
                "key_format": "sk-ant-...",
                "website": "https://anthropic.com"
            },
            {
                "id": "gemini",
                "name": "Google Gemini",
                "description": "Gemini Pro model",
                "key_format": "AI...",
                "website": "https://makersuite.google.com"
            }
        ],
        "default_provider": settings.DEFAULT_PROVIDER
    }

@router.post("/test-key")
async def test_api_key(payload: ValidateCredentialsRequest):
    """Test API key without saving to session"""
    provider = normalize_provider(payload.provider)
    
    is_valid, message = LLMProvider.validate_api_key(provider, payload.api_key)
    
    if not is_valid:
        raise HTTPException(status_code=400, detail=message)
    
    return {
        "status": "valid",
        "provider": provider,
        "message": message
    }
