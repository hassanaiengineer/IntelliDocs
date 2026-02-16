# backend/api/routes_files.py - File Management Routes
from fastapi import APIRouter, HTTPException
from typing import Dict, Any

from backend.core.session import get_session, get_session_files
from backend.vector.vectorstore import vector_store

router = APIRouter(prefix="/files", tags=["File Management"])

@router.get("/session/{session_id}")
async def list_session_files(session_id: str) -> Dict[str, Any]:
    """Get detailed list of files in a session"""
    session = get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    # Get session statistics from vector store
    session_stats = vector_store.get_session_stats(session_id)
    
    # Get session files from database
    db_files = get_session_files(session_id)
    
    return {
        "session_id": session_id,
        "total_files": session_stats["total_files"],
        "total_chunks": session_stats["total_chunks"],
        "files": session_stats["files"],
        "upload_history": db_files
    }

@router.get("/session/{session_id}/summary")
async def get_session_file_summary(session_id: str):
    """Get a summary of files in session"""
    session = get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    session_stats = vector_store.get_session_stats(session_id)
    
    if session_stats["total_files"] == 0:
        return {
            "session_id": session_id,
            "message": "No files uploaded yet",
            "files": [],
            "total_files": 0,
            "total_chunks": 0
        }
    
    # Create summary
    file_summaries = []
    for file_data in session_stats["files"]:
        file_summaries.append({
            "filename": file_data["filename"],
            "chunks": file_data["chunk_count"],
            "sections": file_data.get("section_count", 1),
            "size_chars": file_data["total_chars"],
            "size_display": _format_file_size(file_data["total_chars"])
        })
    
    return {
        "session_id": session_id,
        "files": file_summaries,
        "total_files": session_stats["total_files"],
        "total_chunks": session_stats["total_chunks"],
        "total_size": sum(f["total_chars"] for f in session_stats["files"]),
        "avg_chunks_per_file": round(session_stats["total_chunks"] / session_stats["total_files"], 1)
    }

@router.get("/session/{session_id}/file/{filename}")
async def get_file_details(session_id: str, filename: str):
    """Get detailed information about a specific file"""
    session = get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    session_stats = vector_store.get_session_stats(session_id)
    
    # Find the specific file
    file_data = None
    for f in session_stats["files"]:
        if f["filename"] == filename:
            file_data = f
            break
    
    if not file_data:
        raise HTTPException(status_code=404, detail=f"File '{filename}' not found in session")
    
    return {
        "session_id": session_id,
        "filename": filename,
        "chunk_count": file_data["chunk_count"],
        "total_chars": file_data["total_chars"],
        "section_count": file_data.get("section_count", 1),
        "size_display": _format_file_size(file_data["total_chars"]),
        "avg_chars_per_chunk": round(file_data["total_chars"] / file_data["chunk_count"]) if file_data["chunk_count"] > 0 else 0
    }

@router.delete("/session/{session_id}/file/{filename}")
async def delete_file_from_session(session_id: str, filename: str):
    """Remove a specific file from the session"""
    session = get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    try:
        # Check if file exists
        session_files = vector_store.get_session_files_list(session_id)
        if filename not in session_files:
            raise HTTPException(status_code=404, detail=f"File '{filename}' not found in session")
        
        # Remove from vector store
        vector_store.remove_file_from_session(session_id, filename)
        
        # Get updated stats
        updated_stats = vector_store.get_session_stats(session_id)
        
        return {
            "status": "success",
            "message": f"File '{filename}' removed successfully",
            "session_id": session_id,
            "remaining_files": updated_stats["total_files"],
            "remaining_chunks": updated_stats["total_chunks"]
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error removing file: {str(e)}")

@router.post("/session/{session_id}/clear")
async def clear_all_files(session_id: str):
    """Clear all files from the session"""
    session = get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    try:
        vector_store.clear_session(session_id)
        
        return {
            "status": "success",
            "message": "All files cleared from session",
            "session_id": session_id,
            "files_count": 0,
            "chunks_count": 0
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error clearing files: {str(e)}")

def _format_file_size(chars: int) -> str:
    """Format character count as human-readable size"""
    if chars < 1000:
        return f"{chars} chars"
    elif chars < 1000000:
        return f"{chars/1000:.1f}K chars"
    else:
        return f"{chars/1000000:.1f}M chars"
