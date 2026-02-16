# backend/api/routes_rag.py - Enhanced RAG Query Routes
from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel
from typing import Optional, List

from backend.core.config import get_settings
from backend.core.session import get_session, increment_question_count, validate_session_limits
from backend.vector.retriever import enhanced_retriever
from backend.llm.provider import LLMProvider

router = APIRouter(prefix="/rag", tags=["RAG"])
settings = get_settings()

class RAGQuery(BaseModel):
    question: str
    filename_filter: Optional[str] = None
    use_hybrid_search: bool = True
    top_k: int = 5

class FileSpecificQuery(BaseModel):
    question: str
    filenames: List[str]
    top_k: int = 5

@router.post("/ask")
async def ask_question(payload: RAGQuery, request: Request):
    """Ask a question against all uploaded documents"""
    question = payload.question.strip()
    if not question:
        raise HTTPException(status_code=400, detail="Question cannot be empty")
    
    # Extract headers
    headers = request.headers
    session_id = headers.get(settings.HEADER_SESSION_ID)
    api_key = headers.get(settings.HEADER_API_KEY)
    provider_raw = headers.get(settings.HEADER_PROVIDER, settings.DEFAULT_PROVIDER)
    
    if not session_id:
        raise HTTPException(
            status_code=400,
            detail=f"Missing header: {settings.HEADER_SESSION_ID}"
        )
    
    if not api_key:
        raise HTTPException(
            status_code=400,
            detail=f"Missing header: {settings.HEADER_API_KEY}"
        )
    
    # Validate session
    session = get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    # Check question limits
    limits_check = validate_session_limits(session_id)
    if not limits_check["valid"]:
        raise HTTPException(status_code=400, detail=limits_check["error"])
    
    # Normalize provider
    from backend.llm.provider import normalize_provider
    provider = normalize_provider(provider_raw)

    print("🚀 RAW provider from header:", provider_raw)
    print("🚀 Normalized provider:", provider)
    print("🚀 API Key received:", api_key[:10] + "...")
    
    # Increment question count
    question_count = increment_question_count(session_id)
    
    try:
        # Retrieve relevant context
        retrieval_result = enhanced_retriever.retrieve_context(
            query=question,
            session_id=session_id,
            top_k=payload.top_k,
            filename_filter=payload.filename_filter,
            use_hybrid_search=payload.use_hybrid_search
        )
        
        if not retrieval_result["context"]:
            return {
                "answer": "I couldn't find any relevant information in your uploaded documents to answer this question. Please make sure you've uploaded documents or try rephrasing your question.",
                "sources": [],
                "question_count": question_count,
                "context_found": False
            }
        
        # Generate answer
        answer = LLMProvider.generate_answer(
            provider=provider,
            api_key=api_key,
            question=question,
            context=retrieval_result["context"],
            sources_info=retrieval_result["sources"]
        )
        
        return {
            "answer": answer,
            "sources": retrieval_result["sources"],
            "question_count": question_count,
            "context_found": True,
            "retrieval_stats": {
                "total_chunks": retrieval_result["total_chunks"],
                "files_searched": len(set(source["filename"] for source in retrieval_result["sources"]))
            }
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error processing question: {str(e)}"
        )

@router.post("/ask-file-specific")
async def ask_file_specific(payload: FileSpecificQuery, request: Request):
    """Ask a question about specific files only"""
    question = payload.question.strip()
    if not question:
        raise HTTPException(status_code=400, detail="Question cannot be empty")
    
    if not payload.filenames:
        raise HTTPException(status_code=400, detail="At least one filename must be specified")
    
    # Extract headers
    headers = request.headers
    session_id = headers.get(settings.HEADER_SESSION_ID)
    api_key = headers.get(settings.HEADER_API_KEY)
    provider_raw = headers.get(settings.HEADER_PROVIDER, settings.DEFAULT_PROVIDER)
    
    if not session_id or not api_key:
        raise HTTPException(status_code=400, detail="Missing required headers")
    
    # Validate session
    session = get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    # Check question limits
    limits_check = validate_session_limits(session_id)
    if not limits_check["valid"]:
        raise HTTPException(status_code=400, detail=limits_check["error"])
    
    from backend.llm.provider import normalize_provider
    provider = normalize_provider(provider_raw)
    
    print("🚀 RAW provider from header:", provider_raw)
    print("🚀 Normalized provider:", provider)
    print("🚀 API Key received:", api_key[:10] + "...")

    question_count = increment_question_count(session_id)
    
    try:
        # Get context from specific files
        retrieval_result = enhanced_retriever.get_multi_file_context(
            query=question,
            session_id=session_id,
            filenames=payload.filenames,
            top_k=payload.top_k
        )
        
        if not retrieval_result["context"]:
            return {
                "answer": f"I couldn't find relevant information in the specified files: {', '.join(payload.filenames)}. Please check if these files contain information related to your question.",
                "sources": [],
                "question_count": question_count,
                "context_found": False,
                "files_searched": payload.filenames
            }
        
        # Generate answer
        answer = LLMProvider.generate_answer(
            provider=provider,
            api_key=api_key,
            question=question,
            context=retrieval_result["context"],
            sources_info=retrieval_result["sources"]
        )
        
        return {
            "answer": answer,
            "sources": retrieval_result["sources"],
            "question_count": question_count,
            "context_found": True,
            "files_searched": payload.filenames,
            "retrieval_stats": {
                "total_chunks": retrieval_result["total_chunks"],
                "files_with_results": len(set(source["filename"] for source in retrieval_result["sources"]))
            }
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error processing file-specific question: {str(e)}"
        )

@router.get("/session/{session_id}/stats")
async def get_session_stats(session_id: str):
    """Get comprehensive session statistics"""
    session = get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    # Get vector store stats
    from backend.vector.vectorstore import vector_store
    vector_stats = vector_store.get_session_stats(session_id)
    
    return {
        "session_id": session_id,
        "username": session.get("username"),
        "created_at": session.get("created_at"),
        "question_count": session.get("question_count", 0),
        "max_questions": settings.MAX_QUESTIONS_PER_SESSION,
        "file_count": session.get("file_count", 0),
        "max_files": settings.MAX_FILES_PER_SESSION,
        "vector_store_stats": vector_stats,
        "provider": session.get("provider", "Not set"),
        "api_key_set": bool(session.get("api_key"))
    }

@router.post("/test-connection")
async def test_llm_connection(request: Request):
    """Test LLM provider connection"""
    headers = request.headers
    api_key = headers.get(settings.HEADER_API_KEY)
    provider_raw = headers.get(settings.HEADER_PROVIDER, settings.DEFAULT_PROVIDER)
    
    if not api_key:
        raise HTTPException(status_code=400, detail="Missing API key")
    
    from backend.llm.provider import normalize_provider
    provider = normalize_provider(provider_raw)

    print("🚀 RAW provider from header:", provider_raw)
    print("🚀 Normalized provider:", provider)
    print("🚀 API Key received:", api_key[:10] + "...")
    
    # Test with a simple question
    try:
        test_answer = LLMProvider.generate_answer(
            provider=provider,
            api_key=api_key,
            question="What is 2+2?",
            context="The mathematical operation 2+2 equals 4."
        )
        
        return {
            "status": "success",
            "provider": provider,
            "test_response": test_answer,
            "message": f"{provider.title()} API connection successful"
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=400,
            detail=f"LLM connection test failed: {str(e)}"
        )
