# backend/embedding/embedding.py - Enhanced Embedding System with Dimension Validation
import hashlib
import sqlite3
import numpy as np
import logging
from typing import List, Dict, Any, Optional
from sentence_transformers import SentenceTransformer
from backend.core.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

class EmbeddingService:
    """Enhanced embedding service with caching, batch processing, and dimension validation"""
    
    def __init__(self):
        self.model = None
        self.model_name = settings.EMBEDDING_MODEL
        self.cache_db = "embeddings_cache.db"
        self._current_dimension = None
        self._init_model()
        self._init_cache_db()
    
    def _init_model(self):
        """Initialize the embedding model with error handling"""
        try:
            logger.info(f"Loading embedding model: {self.model_name}")
            self.model = SentenceTransformer(self.model_name)
            self._current_dimension = self.model.get_sentence_embedding_dimension()
            logger.info(f"Model loaded successfully. Dimension: {self._current_dimension}")
        except Exception as e:
            logger.error(f"Failed to load embedding model {self.model_name}: {e}")
            raise RuntimeError(f"Cannot initialize embedding model: {e}")
    
    def _init_cache_db(self):
        """Initialize embedding cache database with improved schema"""
        conn = sqlite3.connect(self.cache_db)
        cursor = conn.cursor()
        
        # Create table with dimension tracking
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS embeddings_cache (
                text_hash TEXT PRIMARY KEY,
                embedding BLOB NOT NULL,
                model_name TEXT NOT NULL,
                dimension INTEGER NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Add dimension column if it doesn't exist (for existing databases)
        try:
            cursor.execute("ALTER TABLE embeddings_cache ADD COLUMN dimension INTEGER")
        except sqlite3.OperationalError:
            # Column already exists
            pass
        
        conn.commit()
        conn.close()
        
        # Clean up inconsistent cache entries
        self._validate_cache()
    
    def _validate_cache(self):
        """Validate and clean cache entries that don't match current model"""
        try:
            conn = sqlite3.connect(self.cache_db)
            cursor = conn.cursor()
            
            # Count total entries
            cursor.execute("SELECT COUNT(*) FROM embeddings_cache")
            total_count = cursor.fetchone()[0]
            
            if total_count == 0:
                conn.close()
                return
            
            # Count entries for current model with correct dimension
            cursor.execute("""
                SELECT COUNT(*) FROM embeddings_cache 
                WHERE model_name = ? AND dimension = ?
            """, (self.model_name, self._current_dimension))
            valid_count = cursor.fetchone()[0]
            
            # If there are mismatched entries, clean them up
            invalid_count = total_count - valid_count
            if invalid_count > 0:
                logger.warning(f"Found {invalid_count} cached embeddings with incorrect model/dimension")
                
                # Remove entries that don't match current model and dimension
                cursor.execute("""
                    DELETE FROM embeddings_cache 
                    WHERE model_name != ? OR dimension != ? OR dimension IS NULL
                """, (self.model_name, self._current_dimension))
                
                conn.commit()
                logger.info(f"Cleaned up {invalid_count} inconsistent cache entries")
            
            conn.close()
            
        except Exception as e:
            logger.warning(f"Cache validation failed: {e}")
    
    def _get_text_hash(self, text: str) -> str:
        """Generate hash for text caching"""
        return hashlib.sha256(text.encode()).hexdigest()
    
    def _cache_embedding(self, text_hash: str, embedding: List[float]):
        """Cache embedding to database with dimension tracking"""
        try:
            conn = sqlite3.connect(self.cache_db)
            cursor = conn.cursor()
            
            # Convert embedding to binary
            embedding_bytes = np.array(embedding, dtype=np.float32).tobytes()
            
            cursor.execute("""
                INSERT OR REPLACE INTO embeddings_cache 
                (text_hash, embedding, model_name, dimension)
                VALUES (?, ?, ?, ?)
            """, (text_hash, embedding_bytes, self.model_name, len(embedding)))
            
            conn.commit()
            conn.close()
            
        except Exception as e:
            logger.warning(f"Failed to cache embedding: {e}")
    
    def _get_cached_embedding(self, text_hash: str) -> Optional[List[float]]:
        """Retrieve cached embedding with model and dimension validation"""
        try:
            conn = sqlite3.connect(self.cache_db)
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT embedding, dimension FROM embeddings_cache 
                WHERE text_hash = ? AND model_name = ? AND dimension = ?
            """, (text_hash, self.model_name, self._current_dimension))
            
            result = cursor.fetchone()
            conn.close()
            
            if result:
                embedding_bytes, cached_dimension = result
                
                # Double-check dimension consistency
                if cached_dimension != self._current_dimension:
                    logger.warning(f"Cached dimension mismatch: {cached_dimension} vs {self._current_dimension}")
                    return None
                
                # Convert binary back to list
                embedding_array = np.frombuffer(embedding_bytes, dtype=np.float32)
                
                # Validate array dimension
                if len(embedding_array) != self._current_dimension:
                    logger.warning(f"Embedding array size mismatch: {len(embedding_array)} vs {self._current_dimension}")
                    return None
                
                return embedding_array.tolist()
            
            return None
            
        except Exception as e:
            logger.warning(f"Failed to retrieve cached embedding: {e}")
            return None
    
    def get_embedding(self, text: str) -> List[float]:
        """Get embedding for single text with caching and validation"""
        if not text.strip():
            return [0.0] * self._current_dimension
        
        text_hash = self._get_text_hash(text)
        
        # Try cache first
        cached_embedding = self._get_cached_embedding(text_hash)
        if cached_embedding is not None:
            return cached_embedding
        
        # Generate new embedding
        try:
            embedding = self.model.encode(text, convert_to_tensor=False)
            embedding_list = embedding.tolist()
            
            # Validate dimension
            if len(embedding_list) != self._current_dimension:
                raise ValueError(f"Model returned unexpected dimension: {len(embedding_list)} vs {self._current_dimension}")
            
            # Cache result
            self._cache_embedding(text_hash, embedding_list)
            
            return embedding_list
            
        except Exception as e:
            logger.error(f"Failed to generate embedding: {e}")
            raise RuntimeError(f"Embedding generation failed: {e}")
    
    def get_batch_embeddings(self, texts: List[str], batch_size: int = 32) -> List[List[float]]:
        """Get embeddings for multiple texts with batching, caching, and validation"""
        if not texts:
            return []
        
        embeddings = []
        uncached_texts = []
        uncached_indices = []
        
        # Check cache first
        for i, text in enumerate(texts):
            if not text.strip():
                embeddings.append([0.0] * self._current_dimension)
                continue
            
            text_hash = self._get_text_hash(text)
            cached_embedding = self._get_cached_embedding(text_hash)
            
            if cached_embedding is not None:
                embeddings.append(cached_embedding)
            else:
                embeddings.append(None)  # Placeholder
                uncached_texts.append(text)
                uncached_indices.append(i)
        
        # Generate embeddings for uncached texts
        if uncached_texts:
            try:
                # Process in batches
                new_embeddings = []
                for i in range(0, len(uncached_texts), batch_size):
                    batch = uncached_texts[i:i + batch_size]
                    batch_embeddings = self.model.encode(
                        batch, 
                        convert_to_tensor=False,
                        show_progress_bar=len(uncached_texts) > 50
                    )
                    
                    # Convert to list and validate dimensions
                    for embedding in batch_embeddings:
                        embedding_list = embedding.tolist()
                        if len(embedding_list) != self._current_dimension:
                            raise ValueError(f"Batch embedding dimension mismatch: {len(embedding_list)} vs {self._current_dimension}")
                        new_embeddings.append(embedding_list)
                
                # Cache new embeddings and fill placeholders
                for i, (text, embedding) in enumerate(zip(uncached_texts, new_embeddings)):
                    text_hash = self._get_text_hash(text)
                    self._cache_embedding(text_hash, embedding)
                    
                    original_index = uncached_indices[i]
                    embeddings[original_index] = embedding
                
            except Exception as e:
                logger.error(f"Batch embedding generation failed: {e}")
                raise RuntimeError(f"Batch embedding generation failed: {e}")
        
        # Final validation
        for i, embedding in enumerate(embeddings):
            if embedding is None:
                raise RuntimeError(f"Failed to generate embedding for text at index {i}")
            if len(embedding) != self._current_dimension:
                raise RuntimeError(f"Embedding dimension mismatch at index {i}: {len(embedding)} vs {self._current_dimension}")
        
        return embeddings
    
    def get_query_embedding(self, query: str) -> List[float]:
        """Get embedding for search query (no caching for queries for privacy)"""
        if not query.strip():
            return [0.0] * self._current_dimension
        
        try:
            embedding = self.model.encode(query, convert_to_tensor=False)
            embedding_list = embedding.tolist()
            
            # Validate dimension
            if len(embedding_list) != self._current_dimension:
                raise ValueError(f"Query embedding dimension mismatch: {len(embedding_list)} vs {self._current_dimension}")
            
            return embedding_list
            
        except Exception as e:
            logger.error(f"Failed to generate query embedding: {e}")
            raise RuntimeError(f"Query embedding generation failed: {e}")
    
    def compute_similarity(self, embedding1: List[float], embedding2: List[float]) -> float:
        """Compute cosine similarity between embeddings"""
        try:
            # Validate dimensions
            if len(embedding1) != len(embedding2):
                raise ValueError(f"Embedding dimension mismatch: {len(embedding1)} vs {len(embedding2)}")
            
            arr1 = np.array(embedding1)
            arr2 = np.array(embedding2)
            
            # Cosine similarity
            dot_product = np.dot(arr1, arr2)
            norm1 = np.linalg.norm(arr1)
            norm2 = np.linalg.norm(arr2)
            
            if norm1 == 0 or norm2 == 0:
                return 0.0
            
            return float(dot_product / (norm1 * norm2))
            
        except Exception as e:
            logger.error(f"Similarity computation failed: {e}")
            return 0.0
    
    def get_embedding_dimension(self) -> int:
        """Get embedding dimension"""
        return self._current_dimension
    
    def get_model_info(self) -> Dict[str, Any]:
        """Get information about the current model"""
        return {
            "model_name": self.model_name,
            "dimension": self._current_dimension,
            "cache_db": self.cache_db
        }
    
    def health_check(self) -> Dict[str, Any]:
        """Perform a health check on the embedding service"""
        try:
            # Test basic embedding generation
            test_text = "This is a test sentence for health check."
            test_embedding = self.get_embedding(test_text)
            
            # Check cache database
            cache_status = self._check_cache_health()
            
            return {
                "status": "healthy",
                "model_name": self.model_name,
                "dimension": self._current_dimension,
                "test_embedding_length": len(test_embedding),
                "cache_status": cache_status
            }
            
        except Exception as e:
            return {
                "status": "error",
                "error": str(e)
            }
    
    def _check_cache_health(self) -> Dict[str, Any]:
        """Check the health of the embedding cache"""
        try:
            conn = sqlite3.connect(self.cache_db)
            cursor = conn.cursor()
            
            # Count total entries
            cursor.execute("SELECT COUNT(*) FROM embeddings_cache")
            total_count = cursor.fetchone()[0]
            
            # Count entries for current model
            cursor.execute("SELECT COUNT(*) FROM embeddings_cache WHERE model_name = ?", (self.model_name,))
            current_model_count = cursor.fetchone()[0]
            
            conn.close()
            
            return {
                "status": "healthy",
                "total_entries": total_count,
                "current_model_entries": current_model_count
            }
            
        except Exception as e:
            return {
                "status": "error",
                "error": str(e)
            }

# Global embedding service instance
embedding_service = EmbeddingService()

# Convenience functions for backward compatibility
def get_batch_embeddings(texts: List[str]) -> List[List[float]]:
    """Legacy function"""
    return embedding_service.get_batch_embeddings(texts)

def get_embedding(text: str) -> List[float]:
    """Legacy function"""
    return embedding_service.get_embedding(text)

def get_query_embedding(query: str) -> List[float]:
    """Get embedding for query"""
    return embedding_service.get_query_embedding(query)

def get_embedding_dimension() -> int:
    """Get embedding dimension"""
    return embedding_service.get_embedding_dimension()