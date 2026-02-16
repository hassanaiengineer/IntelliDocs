# backend/vector/vectorstore.py - Enhanced Vector Store with Progressive File Support
import uuid
import chromadb
import logging
from typing import List, Dict, Any, Optional
from backend.core.config import get_settings
from backend.core.session import add_session_file, get_session_files

logger = logging.getLogger(__name__)
settings = get_settings()

class EnhancedVectorStore:
    """Enhanced ChromaDB vector store with progressive file support and dimension validation"""
    
    def __init__(self):
        self.client = chromadb.PersistentClient(path=settings.CHROMA_DIR)
        self.collection = None
        self._expected_dimension = None
        self._init_collection()
    
    def _init_collection(self):
        """Initialize the collection with dimension validation"""
        try:
            self.collection = self.client.get_or_create_collection(
                name="enhanced_rag_docs",
                metadata={"hnsw:space": "cosine"}
            )
            logger.info("Vector store initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize vector store: {e}")
            raise
    
    def _validate_embedding_dimensions(self, embeddings: List[List[float]]) -> bool:
        """Validate embedding dimensions against existing collection"""
        if not embeddings:
            return True
        
        current_dimension = len(embeddings[0])
        
        # Get existing dimension from collection if available
        try:
            # Try to get one existing document to check dimension
            existing_data = self.collection.peek(limit=1)
            if existing_data['embeddings']:
                existing_dimension = len(existing_data['embeddings'][0])
                if current_dimension != existing_dimension:
                    logger.error(f"Dimension mismatch: Current={current_dimension}, Existing={existing_dimension}")
                    return False
            
            # Store the expected dimension for future validations
            self._expected_dimension = current_dimension
            return True
            
        except Exception as e:
            logger.warning(f"Could not validate dimensions: {e}")
            # If we can't validate, assume it's okay and let ChromaDB handle it
            return True
    
    def _reset_collection_if_needed(self, embeddings: List[List[float]]) -> bool:
        """Reset collection if there's a dimension mismatch"""
        if not self._validate_embedding_dimensions(embeddings):
            logger.warning("Dimension mismatch detected. This usually means:")
            logger.warning("1. The embedding model was changed")
            logger.warning("2. There are cached embeddings from a different model")
            logger.warning("3. Mixed embedding sources")
            
            # Don't auto-reset in production - this could lose data
            # Instead, raise an informative error
            current_dim = len(embeddings[0]) if embeddings else "unknown"
            existing_data = self.collection.peek(limit=1)
            existing_dim = len(existing_data['embeddings'][0]) if existing_data['embeddings'] else "unknown"
            
            raise ValueError(
                f"Embedding dimension mismatch detected!\n"
                f"Current embeddings: {current_dim} dimensions\n"
                f"Existing collection: {existing_dim} dimensions\n\n"
                f"This happens when:\n"
                f"1. The embedding model was changed in configuration\n"
                f"2. Cached embeddings from a different model are being used\n"
                f"3. Mixed embedding models in the same collection\n\n"
                f"Solutions:\n"
                f"1. Run the reset script: python reset_database.py\n"
                f"2. Clear embedding cache and restart\n"
                f"3. Use consistent embedding models"
            )
        
        return True
    
    def add_document_chunks(self, session_id: str, filename: str, file_hash: str,
                           chunks: List[Dict[str, Any]], embeddings: List[List[float]]) -> bool:
        """Add chunks from a new document (progressive addition) with dimension validation"""
        if len(chunks) != len(embeddings):
            raise ValueError("Chunks and embeddings length mismatch")
        
        # Validate dimensions before proceeding
        try:
            self._reset_collection_if_needed(embeddings)
        except ValueError as e:
            logger.error(f"Dimension validation failed: {e}")
            raise
        
        # Check if file already exists in this session
        existing_files = self.get_session_files_list(session_id)
        if filename in existing_files:
            logger.warning(f"File {filename} already exists in session {session_id}")
            return False  # File already processed
        
        # Prepare data for insertion
        ids = []
        documents = []
        metadatas = []
        
        for chunk in chunks:
            chunk_id = str(uuid.uuid4())
            ids.append(chunk_id)
            documents.append(chunk["text"])
            
            metadata = {
                "session_id": session_id,
                "filename": filename,
                "file_hash": file_hash,
                "section_idx": chunk["metadata"]["section_idx"],
                "chunk_idx": chunk["metadata"]["chunk_idx"],
                "char_count": chunk["metadata"]["char_count"],
                "word_count": chunk["metadata"]["word_count"]
            }
            metadatas.append(metadata)
        
        # Insert into vector database with better error handling
        try:
            self.collection.add(
                ids=ids,
                documents=documents,
                embeddings=embeddings,
                metadatas=metadatas
            )
            logger.info(f"Successfully added {len(chunks)} chunks for {filename}")
            
        except Exception as e:
            error_msg = str(e)
            if "dimension" in error_msg.lower():
                raise ValueError(
                    f"Embedding dimension error: {error_msg}\n\n"
                    f"This usually means the embedding model configuration changed.\n"
                    f"Run 'python reset_database.py' to fix this issue."
                )
            else:
                logger.error(f"Failed to add chunks to vector store: {e}")
                raise
        
        # Update session tracking
        try:
            add_session_file(
                session_id=session_id,
                filename=filename,
                file_hash=file_hash,
                chunk_count=len(chunks),
                file_size=sum(chunk["metadata"]["char_count"] for chunk in chunks)
            )
        except Exception as e:
            logger.error(f"Failed to update session tracking: {e}")
            # Don't fail the whole operation for session tracking errors
        
        return True
    
    def query_session_documents(self, session_id: str, query_embedding: List[float],
                               top_k: int = 5, filename_filter: Optional[str] = None) -> Dict[str, Any]:
        """Query documents in a session with optional file filtering"""
        where_clause = {"session_id": session_id}
        if filename_filter:
            where_clause["filename"] = filename_filter
        
        try:
            results = self.collection.query(
                query_embeddings=[query_embedding],
                n_results=top_k,
                where=where_clause,
                include=["documents", "metadatas", "distances"]
            )
            
            return self._format_query_results(results)
            
        except Exception as e:
            logger.error(f"Query failed: {e}")
            # Return empty results instead of failing
            return {
                "documents": [],
                "metadatas": [],
                "distances": []
            }
    
    def query_with_hybrid_search(self, session_id: str, query_embedding: List[float],
                                query_text: str, top_k: int = 5) -> Dict[str, Any]:
        """Perform hybrid search combining vector similarity and keyword matching"""
        try:
            # Vector search
            vector_results = self.query_session_documents(session_id, query_embedding, top_k * 2)
            
            if not vector_results["documents"]:
                return vector_results
            
            # Keyword filtering
            query_keywords = set(query_text.lower().split())
            scored_results = []
            
            for i, doc in enumerate(vector_results["documents"]):
                doc_keywords = set(doc.lower().split())
                keyword_score = len(query_keywords.intersection(doc_keywords)) / len(query_keywords) if query_keywords else 0
                
                combined_score = (1 - vector_results["distances"][i]) * 0.7 + keyword_score * 0.3
                
                scored_results.append({
                    "document": doc,
                    "metadata": vector_results["metadatas"][i],
                    "vector_distance": vector_results["distances"][i],
                    "keyword_score": keyword_score,
                    "combined_score": combined_score
                })
            
            # Sort by combined score and take top k
            scored_results.sort(key=lambda x: x["combined_score"], reverse=True)
            top_results = scored_results[:top_k]
            
            return {
                "documents": [r["document"] for r in top_results],
                "metadatas": [r["metadata"] for r in top_results],
                "distances": [r["vector_distance"] for r in top_results],
                "combined_scores": [r["combined_score"] for r in top_results]
            }
            
        except Exception as e:
            logger.error(f"Hybrid search failed: {e}")
            # Fallback to simple vector search
            return self.query_session_documents(session_id, query_embedding, top_k)
    
    def get_session_files_list(self, session_id: str) -> List[str]:
        """Get list of uploaded filenames for a session"""
        try:
            results = self.collection.get(
                where={"session_id": session_id},
                include=["metadatas"]
            )
            
            filenames = set()
            for metadata in results["metadatas"]:
                filenames.add(metadata["filename"])
            
            return list(filenames)
            
        except Exception as e:
            logger.error(f"Failed to get session files: {e}")
            return []
    
    def get_session_stats(self, session_id: str) -> Dict[str, Any]:
        """Get statistics for a session"""
        try:
            results = self.collection.get(
                where={"session_id": session_id},
                include=["metadatas"]
            )
            
            if not results["metadatas"]:
                return {
                    "total_chunks": 0,
                    "total_files": 0,
                    "files": []
                }
            
            file_stats = {}
            for metadata in results["metadatas"]:
                filename = metadata["filename"]
                if filename not in file_stats:
                    file_stats[filename] = {
                        "filename": filename,
                        "chunk_count": 0,
                        "total_chars": 0,
                        "sections": set()
                    }
                
                file_stats[filename]["chunk_count"] += 1
                file_stats[filename]["total_chars"] += metadata.get("char_count", 0)
                file_stats[filename]["sections"].add(metadata.get("section_idx", 0))
            
            # Convert sets to counts
            for file_data in file_stats.values():
                file_data["section_count"] = len(file_data["sections"])
                del file_data["sections"]
            
            return {
                "total_chunks": len(results["metadatas"]),
                "total_files": len(file_stats),
                "files": list(file_stats.values())
            }
            
        except Exception as e:
            logger.error(f"Failed to get session stats: {e}")
            return {
                "total_chunks": 0,
                "total_files": 0,
                "files": []
            }
    
    def remove_file_from_session(self, session_id: str, filename: str):
        """Remove a specific file from session"""
        try:
            self.collection.delete(
                where={"session_id": session_id, "filename": filename}
            )
            logger.info(f"Removed file {filename} from session {session_id}")
        except Exception as e:
            logger.error(f"Failed to remove file: {e}")
            raise
    
    def clear_session(self, session_id: str):
        """Clear all documents for a session"""
        try:
            self.collection.delete(where={"session_id": session_id})
            logger.info(f"Cleared all documents for session {session_id}")
        except Exception as e:
            logger.error(f"Failed to clear session: {e}")
            raise
    
    def health_check(self) -> Dict[str, Any]:
        """Perform a health check on the vector store"""
        try:
            # Check basic connectivity
            count = self.collection.count()
            
            # Check if we can peek at the collection
            sample = self.collection.peek(limit=1)
            
            dimension = None
            if sample['embeddings']:
                dimension = len(sample['embeddings'][0])
            
            return {
                "status": "healthy",
                "document_count": count,
                "embedding_dimension": dimension,
                "collection_name": self.collection.name
            }
            
        except Exception as e:
            return {
                "status": "error",
                "error": str(e)
            }
    
    def _format_query_results(self, results: Dict) -> Dict[str, Any]:
        """Format ChromaDB query results"""
        return {
            "documents": results["documents"][0] if results["documents"] else [],
            "metadatas": results["metadatas"][0] if results["metadatas"] else [],
            "distances": results["distances"][0] if results["distances"] else []
        }

# Global instance
vector_store = EnhancedVectorStore()

# Convenience functions for backward compatibility
def add_chunks(session_id: str, file_name: str, chunks: List[str], embeddings: List[List[float]]):
    """Legacy function - convert to new format"""
    chunk_dicts = []
    for i, chunk in enumerate(chunks):
        chunk_dicts.append({
            "text": chunk,
            "metadata": {
                "filename": file_name,
                "section_idx": 0,
                "chunk_idx": i,
                "char_count": len(chunk),
                "word_count": len(chunk.split())
            }
        })
    
    import hashlib
    file_hash = hashlib.md5(f"{session_id}_{file_name}".encode()).hexdigest()
    
    return vector_store.add_document_chunks(
        session_id=session_id,
        filename=file_name,
        file_hash=file_hash,
        chunks=chunk_dicts,
        embeddings=embeddings
    )

def query_session_chunks(session_id: str, query_embedding: List[float], k: int = 5):
    """Legacy function"""
    return vector_store.query_session_documents(session_id, query_embedding, k)

def clear_session(session_id: str):
    """Legacy function"""
    vector_store.clear_session(session_id)

def list_session_files(session_id: str):
    """Legacy function"""
    return vector_store.get_session_files_list(session_id)