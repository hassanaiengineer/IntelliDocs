# backend/api/routes_upload.py - Enhanced Upload Routes with Progressive Support
from fastapi import APIRouter, UploadFile, File, Form, HTTPException
from typing import List, Dict, Any
import hashlib
import logging
import traceback
from datetime import datetime

from backend.core.config import get_settings
from backend.core.session import get_session, validate_session_limits, add_session_file
from backend.ingestion.document_processor import extract_text_with_metadata, DocumentProcessor
from backend.ingestion.chunker import chunk_text
from backend.embedding.embedding import embedding_service
from backend.vector.vectorstore import vector_store

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/upload", tags=["Upload"])
settings = get_settings()

@router.post("/files")
async def upload_files_progressive(
    session_id: str = Form(...),
    files: List[UploadFile] = File(...)
):
    """
    Progressive file upload - adds new files without removing existing ones
    Enhanced with better error handling for dimension mismatches
    """
    logger.info(f"Starting upload for session {session_id} with {len(files)} files")
    
    if not session_id:
        raise HTTPException(status_code=400, detail={
            "error": "Missing session_id",
            "error_code": "MISSING_SESSION_ID"
        })
    
    if not files:
        raise HTTPException(status_code=400, detail={
            "error": "No files uploaded",
            "error_code": "NO_FILES"
        })
    
    # Validate session
    try:
        session = get_session(session_id)
        if not session:
            raise HTTPException(status_code=404, detail={
                "error": "Session not found",
                "error_code": "SESSION_NOT_FOUND",
                "session_id": session_id
            })
    except Exception as e:
        logger.error(f"Session validation failed: {e}")
        raise HTTPException(status_code=500, detail={
            "error": "Session validation failed",
            "error_code": "SESSION_VALIDATION_ERROR",
            "details": str(e)
        })
    
    # Check session limits
    try:
        limits_check = validate_session_limits(session_id)
        if not limits_check["valid"]:
            raise HTTPException(status_code=400, detail={
                "error": limits_check["error"],
                "error_code": "SESSION_LIMITS_EXCEEDED"
            })
    except Exception as e:
        logger.error(f"Session limits check failed: {e}")
        raise HTTPException(status_code=500, detail={
            "error": "Session limits validation failed",
            "error_code": "LIMITS_CHECK_ERROR",
            "details": str(e)
        })
    
    # Check file count limits (current + new files)
    try:
        current_files = vector_store.get_session_files_list(session_id)
        if len(current_files) + len(files) > settings.MAX_FILES_PER_SESSION:
            raise HTTPException(
                status_code=400, 
                detail={
                    "error": f"Cannot upload {len(files)} files. Maximum {settings.MAX_FILES_PER_SESSION} files per session. Currently have {len(current_files)} files.",
                    "error_code": "FILE_COUNT_EXCEEDED",
                    "current_files": len(current_files),
                    "new_files": len(files),
                    "max_allowed": settings.MAX_FILES_PER_SESSION
                }
            )
    except HTTPException:
        raise
    except Exception as e:
        logger.warning(f"Could not check existing files: {e}")
        # Continue anyway, let the upload process handle it
    
    successful_uploads = []
    failed_uploads = []
    
    logger.info(f"Processing {len(files)} files for session {session_id}")
    
    # Process each file
    for i, file in enumerate(files):
        logger.info(f"Processing file {i+1}/{len(files)}: {file.filename}")
        try:
            upload_result = await _process_single_file(session_id, file)
            if upload_result["success"]:
                successful_uploads.append(upload_result)
                logger.info(f"Successfully processed: {file.filename}")
            else:
                failed_uploads.append({
                    "filename": file.filename,
                    "error": upload_result["error"],
                    "error_code": upload_result.get("error_code", "PROCESSING_FAILED"),
                    "details": upload_result.get("details", {})
                })
                logger.warning(f"Failed to process {file.filename}: {upload_result['error']}")
                
        except Exception as e:
            error_msg = str(e)
            logger.error(f"Unexpected error processing {file.filename}: {error_msg}")
            
            # Check for dimension mismatch errors specifically
            if "dimension" in error_msg.lower():
                failed_uploads.append({
                    "filename": file.filename,
                    "error": "Embedding dimension mismatch detected",
                    "error_code": "DIMENSION_MISMATCH",
                    "details": {
                        "original_error": error_msg,
                        "solution": "Run 'python reset_database.py' to fix this issue",
                        "cause": "The embedding model configuration may have changed"
                    }
                })
            else:
                failed_uploads.append({
                    "filename": file.filename,
                    "error": error_msg,
                    "error_code": "UNEXPECTED_ERROR",
                    "details": {"exception": error_msg}
                })
    
    # Check if any files were processed successfully
    if not successful_uploads and failed_uploads:
        logger.error(f"No files successfully processed for session {session_id}")
        
        # Provide specific error guidance for dimension mismatches
        dimension_errors = [f for f in failed_uploads if f.get("error_code") == "DIMENSION_MISMATCH"]
        if dimension_errors:
            raise HTTPException(
                status_code=400,
                detail={
                    "error": "Embedding dimension mismatch detected",
                    "error_code": "DIMENSION_MISMATCH",
                    "message": "The vector database has embeddings with different dimensions than your current model configuration.",
                    "solution": "Run 'python reset_database.py' to reset the database and clear inconsistent embeddings.",
                    "failed_files": failed_uploads,
                    "cause": "This usually happens when the embedding model configuration changes after documents have already been uploaded."
                }
            )
        
        # General failure
        failure_analysis = _analyze_upload_failures(failed_uploads)
        raise HTTPException(
            status_code=400,
            detail={
                "error": "No files were successfully processed",
                "error_code": "ALL_FILES_FAILED",
                "failed_files": failed_uploads,
                "failure_analysis": failure_analysis
            }
        )
    
    # Get updated session stats
    try:
        session_stats = vector_store.get_session_stats(session_id)
    except Exception as e:
        logger.warning(f"Could not get session stats: {e}")
        session_stats = {
            "total_files": len(successful_uploads),
            "total_chunks": sum(f["chunks_created"] for f in successful_uploads),
            "files": []
        }
    
    logger.info(f"Upload completed for session {session_id}: {len(successful_uploads)}/{len(files)} files successful")
    
    response = {
        "status": "success",
        "session_id": session_id,
        "successful_uploads": len(successful_uploads),
        "failed_uploads": len(failed_uploads),
        "files_processed": successful_uploads,
        "session_stats": session_stats,
        "message": f"Successfully processed {len(successful_uploads)} out of {len(files)} files"
    }
    
    # Include failed files if any (but don't fail the request if some succeeded)
    if failed_uploads:
        response["failed_files"] = failed_uploads
        response["failure_analysis"] = _analyze_upload_failures(failed_uploads)
        response["message"] += f" ({len(failed_uploads)} failed)"
    
    return response

async def _process_single_file(session_id: str, file: UploadFile) -> Dict[str, Any]:
    """
    Process a single file upload with comprehensive error handling
    """
    try:
        filename = file.filename or "unnamed_file"
        logger.info(f"Processing file: {filename}")
        
        # Validate file type
        ext = filename.lower().split('.')[-1] if '.' in filename else ''
        if f".{ext}" not in settings.ALLOWED_EXTENSIONS:
            return {
                "success": False,
                "error": f"Unsupported file type: {ext}. Allowed: {', '.join(settings.ALLOWED_EXTENSIONS)}",
                "error_code": "UNSUPPORTED_FILE_TYPE",
                "details": {
                    "extension": ext,
                    "allowed_extensions": settings.ALLOWED_EXTENSIONS
                }
            }
        
        # Read file content
        try:
            file_bytes = await file.read()
        except Exception as e:
            return {
                "success": False,
                "error": f"Failed to read file: {str(e)}",
                "error_code": "FILE_READ_ERROR",
                "details": {"read_error": str(e)}
            }
        
        # Check file size
        file_size_mb = len(file_bytes) / (1024 * 1024)
        if file_size_mb > settings.MAX_FILE_SIZE_MB:
            return {
                "success": False,
                "error": f"File too large: {file_size_mb:.1f}MB (max: {settings.MAX_FILE_SIZE_MB}MB)",
                "error_code": "FILE_TOO_LARGE",
                "details": {
                    "file_size_mb": round(file_size_mb, 2),
                    "max_size_mb": settings.MAX_FILE_SIZE_MB
                }
            }
        
        # Generate file hash for deduplication
        try:
            file_hash = DocumentProcessor.get_file_hash(file_bytes)
        except Exception as e:
            return {
                "success": False,
                "error": f"Failed to generate file hash: {str(e)}",
                "error_code": "HASH_GENERATION_ERROR",
                "details": {"hash_error": str(e)}
            }
        
        # Check if file already exists in session
        try:
            existing_files = vector_store.get_session_files_list(session_id)
            if filename in existing_files:
                return {
                    "success": False,
                    "error": "File with this name already exists in session",
                    "error_code": "DUPLICATE_FILENAME",
                    "details": {
                        "filename": filename,
                        "existing_files": existing_files
                    }
                }
        except Exception as e:
            logger.warning(f"Could not check existing files: {e}")
            # Continue anyway
        
        # Extract text and metadata
        try:
            text, metadata = extract_text_with_metadata(file_bytes, filename)
        except Exception as e:
            return {
                "success": False,
                "error": f"Text extraction failed: {str(e)}",
                "error_code": "TEXT_EXTRACTION_ERROR",
                "details": {
                    "extraction_error": str(e),
                    "filename": filename,
                    "file_size": len(file_bytes)
                }
            }
        
        if not text.strip():
            return {
                "success": False,
                "error": "No readable text found in file",
                "error_code": "NO_TEXT_CONTENT",
                "details": {
                    "text_length": len(text),
                    "metadata": metadata
                }
            }
        
        # Create semantic chunks
        try:
            chunks = chunk_text(text, filename)
        except Exception as e:
            return {
                "success": False,
                "error": f"Text chunking failed: {str(e)}",
                "error_code": "CHUNKING_ERROR",
                "details": {
                    "chunking_error": str(e),
                    "text_length": len(text)
                }
            }
        
        if not chunks:
            return {
                "success": False,
                "error": "Failed to create text chunks",
                "error_code": "NO_CHUNKS_CREATED",
                "details": {
                    "text_length": len(text),
                    "chunk_count": len(chunks)
                }
            }
        
        # Limit chunks per file
        original_chunk_count = len(chunks)
        if len(chunks) > settings.MAX_CHUNKS_PER_FILE:
            chunks = chunks[:settings.MAX_CHUNKS_PER_FILE]
            logger.warning(f"Truncated chunks for {filename}: {original_chunk_count} -> {len(chunks)}")
        
        # Generate embeddings
        try:
            chunk_texts = [chunk["text"] for chunk in chunks]
            embeddings = embedding_service.get_batch_embeddings(chunk_texts)
        except Exception as e:
            error_msg = str(e)
            if "dimension" in error_msg.lower():
                return {
                    "success": False,
                    "error": "Embedding dimension mismatch detected",
                    "error_code": "EMBEDDING_DIMENSION_MISMATCH",
                    "details": {
                        "original_error": error_msg,
                        "solution": "Run 'python reset_database.py' to fix this issue",
                        "cause": "Vector database has different embedding dimensions than current model"
                    }
                }
            else:
                return {
                    "success": False,
                    "error": f"Embedding generation failed: {error_msg}",
                    "error_code": "EMBEDDING_GENERATION_ERROR",
                    "details": {
                        "embedding_error": error_msg,
                        "chunk_count": len(chunks)
                    }
                }
        
        # Add to vector store
        try:
            success = vector_store.add_document_chunks(
                session_id=session_id,
                filename=filename,
                file_hash=file_hash,
                chunks=chunks,
                embeddings=embeddings
            )
            
            if not success:
                return {
                    "success": False,
                    "error": "Failed to add file to vector store",
                    "error_code": "VECTOR_STORE_ERROR",
                    "details": {"possible_cause": "duplicate content or storage error"}
                }
                
        except ValueError as e:
            # This is likely a dimension mismatch error
            error_msg = str(e)
            if "dimension" in error_msg.lower():
                return {
                    "success": False,
                    "error": "Vector database dimension mismatch",
                    "error_code": "VECTOR_DIMENSION_MISMATCH",
                    "details": {
                        "error_message": error_msg,
                        "solution": "Run 'python reset_database.py' to reset the database",
                        "explanation": "The vector database contains embeddings with different dimensions than your current embedding model"
                    }
                }
            else:
                return {
                    "success": False,
                    "error": f"Vector store validation error: {error_msg}",
                    "error_code": "VECTOR_STORE_VALIDATION_ERROR",
                    "details": {"validation_error": error_msg}
                }
                
        except Exception as e:
            return {
                "success": False,
                "error": f"Vector store error: {str(e)}",
                "error_code": "VECTOR_STORE_EXCEPTION",
                "details": {"store_error": str(e)}
            }

        # Success response
        return {
            "success": True,
            "filename": filename,
            "chunks_created": len(chunks),
            "total_characters": len(text),
            "metadata": metadata,
            "file_size_mb": round(file_size_mb, 2),
            "file_hash": file_hash,
            "chunks_truncated": original_chunk_count > settings.MAX_CHUNKS_PER_FILE,
            "original_chunk_count": original_chunk_count
        }

    except Exception as e:
        logger.error(f"Unexpected error in _process_single_file: {str(e)}")
        logger.error(f"Traceback: {traceback.format_exc()}")
        return {
            "success": False,
            "error": f"Unexpected processing error: {str(e)}",
            "error_code": "UNEXPECTED_PROCESSING_ERROR",
            "details": {
                "exception": str(e),
                "traceback": traceback.format_exc()
            }
        }

def _analyze_upload_failures(failed_uploads: List[Dict]) -> Dict[str, Any]:
    """Analyze failed uploads to provide helpful error summary and suggestions"""
    if not failed_uploads:
        return {}
    
    error_counts = {}
    common_errors = []
    
    for failure in failed_uploads:
        error_code = failure.get("error_code", "UNKNOWN")
        error_counts[error_code] = error_counts.get(error_code, 0) + 1
    
    # Identify most common errors and provide suggestions
    sorted_errors = sorted(error_counts.items(), key=lambda x: x[1], reverse=True)
    
    suggestions = []
    for error_code, count in sorted_errors:
        if error_code == "UNSUPPORTED_FILE_TYPE":
            suggestions.append(f"Check file types - {count} files have unsupported extensions")
        elif error_code == "FILE_TOO_LARGE":
            suggestions.append(f"Reduce file sizes - {count} files exceed {settings.MAX_FILE_SIZE_MB}MB limit")
        elif error_code == "NO_TEXT_CONTENT":
            suggestions.append(f"Ensure files contain readable text - {count} files have no extractable text")
        elif error_code == "TEXT_EXTRACTION_ERROR":
            suggestions.append(f"File format issues - {count} files couldn't be processed (may be corrupted or password-protected)")
        elif error_code == "DUPLICATE_FILENAME":
            suggestions.append(f"Rename files - {count} files have duplicate names in this session")
        elif error_code in ["DIMENSION_MISMATCH", "EMBEDDING_DIMENSION_MISMATCH", "VECTOR_DIMENSION_MISMATCH"]:
            suggestions.append(f"Embedding dimension conflict - run 'python reset_database.py' to fix")
        elif error_code == "EMBEDDING_GENERATION_ERROR":
            suggestions.append(f"Embedding generation failed - check if embedding model is properly configured")
        elif error_code == "VECTOR_STORE_ERROR":
            suggestions.append(f"Vector database issues - may need database reset or restart")
    
    # Add general guidance
    if any(code in ["DIMENSION_MISMATCH", "EMBEDDING_DIMENSION_MISMATCH", "VECTOR_DIMENSION_MISMATCH"] 
           for code, _ in sorted_errors):
        suggestions.insert(0, "🔧 DIMENSION MISMATCH DETECTED - Run 'python reset_database.py' to fix this issue")
    
    return {
        "total_failures": len(failed_uploads),
        "error_breakdown": error_counts,
        "most_common_error": sorted_errors[0] if sorted_errors else None,
        "suggestions": suggestions,
        "needs_database_reset": any(code in ["DIMENSION_MISMATCH", "EMBEDDING_DIMENSION_MISMATCH", "VECTOR_DIMENSION_MISMATCH"] 
                                   for code, _ in sorted_errors)
    }

# Health check endpoint for debugging
@router.get("/health")
async def upload_health_check():
    """Health check for upload system dependencies"""
    health = {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "checks": {}
    }
    
    try:
        # Check settings
        health["checks"]["settings"] = {
            "status": "ok" if settings else "error",
            "max_files": getattr(settings, 'MAX_FILES_PER_SESSION', 'not_set'),
            "max_file_size": getattr(settings, 'MAX_FILE_SIZE_MB', 'not_set'),
            "allowed_extensions": getattr(settings, 'ALLOWED_EXTENSIONS', 'not_set'),
            "embedding_model": getattr(settings, 'EMBEDDING_MODEL', 'not_set')
        }
    except Exception as e:
        health["checks"]["settings"] = {"status": "error", "error": str(e)}
        health["status"] = "degraded"
    
    try:
        # Check vector store
        vector_health = vector_store.health_check()
        health["checks"]["vector_store"] = vector_health
        if vector_health.get("status") == "error":
            health["status"] = "degraded"
    except Exception as e:
        health["checks"]["vector_store"] = {"status": "error", "error": str(e)}
        health["status"] = "degraded"
    
    try:
        # Check embedding service
        embedding_health = embedding_service.health_check()
        health["checks"]["embedding_service"] = embedding_health
        if embedding_health.get("status") == "error":
            health["status"] = "degraded"
    except Exception as e:
        health["checks"]["embedding_service"] = {"status": "error", "error": str(e)}
        health["status"] = "degraded"
    
    return health

@router.get("/session/{session_id}/files")
async def get_session_files(session_id: str):
    """Get list of files uploaded in a session with enhanced error handling"""
    try:
        session = get_session(session_id)
        if not session:
            raise HTTPException(status_code=404, detail={
                "error": "Session not found",
                "error_code": "SESSION_NOT_FOUND",
                "session_id": session_id
            })
        
        session_stats = vector_store.get_session_stats(session_id)
        return {
            "session_id": session_id,
            "files": session_stats["files"],
            "total_files": session_stats["total_files"],
            "total_chunks": session_stats["total_chunks"],
            "status": "success"
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting session files: {str(e)}")
        raise HTTPException(status_code=500, detail={
            "error": "Failed to retrieve session files",
            "error_code": "SESSION_FILES_ERROR",
            "details": str(e)
        })

@router.delete("/session/{session_id}/file/{filename}")
async def remove_file_from_session(session_id: str, filename: str):
    """Remove a specific file from session with enhanced error handling"""
    try:
        session = get_session(session_id)
        if not session:
            raise HTTPException(status_code=404, detail={
                "error": "Session not found",
                "error_code": "SESSION_NOT_FOUND",
                "session_id": session_id
            })
        
        vector_store.remove_file_from_session(session_id, filename)
        return {
            "status": "success",
            "message": f"File '{filename}' removed from session",
            "session_id": session_id,
            "filename": filename
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error removing file: {str(e)}")
        raise HTTPException(status_code=500, detail={
            "error": f"Failed to remove file '{filename}'",
            "error_code": "FILE_REMOVAL_ERROR",
            "details": str(e)
        })

@router.delete("/session/{session_id}/files")
async def clear_session_files(session_id: str):
    """Clear all files from session with enhanced error handling"""
    try:
        session = get_session(session_id)
        if not session:
            raise HTTPException(status_code=404, detail={
                "error": "Session not found",
                "error_code": "SESSION_NOT_FOUND",
                "session_id": session_id
            })
        
        vector_store.clear_session(session_id)
        return {
            "status": "success",
            "message": "All files removed from session",
            "session_id": session_id
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error clearing session: {str(e)}")
        raise HTTPException(status_code=500, detail={
            "error": "Failed to clear session files",
            "error_code": "SESSION_CLEAR_ERROR",
            "details": str(e)
        })