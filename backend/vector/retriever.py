# backend/vector/retriever.py - Enhanced Retrieval System
from typing import Dict, Any, List, Optional
from backend.embedding.embedding import get_query_embedding
from backend.vector.vectorstore import vector_store
from backend.core.config import get_settings

settings = get_settings()

class EnhancedRetriever:
    """Enhanced retrieval system with context optimization"""
    
    def __init__(self):
        self.vector_store = vector_store
    
    def retrieve_context(self, query: str, session_id: str, 
                        top_k: int = None, filename_filter: Optional[str] = None,
                        use_hybrid_search: bool = True) -> Dict[str, Any]:
        """Retrieve relevant context with enhanced processing"""
        top_k = top_k or settings.RETRIEVAL_TOP_K
        
        if not query.strip():
            return {
                "context": "",
                "sources": [],
                "total_chunks": 0,
                "query_embedding_dim": 0
            }
        
        # Get query embedding
        query_embedding = get_query_embedding(query)
        
        # Perform search
        if use_hybrid_search:
            search_results = self.vector_store.query_with_hybrid_search(
                session_id=session_id,
                query_embedding=query_embedding,
                query_text=query,
                top_k=top_k
            )
        else:
            search_results = self.vector_store.query_session_documents(
                session_id=session_id,
                query_embedding=query_embedding,
                top_k=top_k,
                filename_filter=filename_filter
            )
        
        if not search_results["documents"]:
            return {
                "context": "",
                "sources": [],
                "total_chunks": 0,
                "query_embedding_dim": len(query_embedding)
            }
        
        # Process and format context
        context_info = self._format_context(search_results)
        
        return {
            "context": context_info["formatted_context"],
            "sources": context_info["sources"],
            "total_chunks": len(search_results["documents"]),
            "query_embedding_dim": len(query_embedding),
            "retrieval_scores": search_results.get("combined_scores", search_results["distances"])
        }
    
    def _format_context(self, search_results: Dict[str, Any]) -> Dict[str, Any]:
        """Format retrieved chunks into coherent context"""
        documents = search_results["documents"]
        metadatas = search_results["metadatas"]
        distances = search_results["distances"]
        
        if not documents:
            return {"formatted_context": "", "sources": []}
        
        # Group by file and section for better organization
        file_sections = {}
        sources = []
        
        for i, (doc, metadata, distance) in enumerate(zip(documents, metadatas, distances)):
            filename = metadata.get("filename", "Unknown")
            section_idx = metadata.get("section_idx", 0)
            chunk_idx = metadata.get("chunk_idx", i)
            
            key = f"{filename}_{section_idx}"
            
            if key not in file_sections:
                file_sections[key] = {
                    "filename": filename,
                    "section_idx": section_idx,
                    "chunks": []
                }
            
            file_sections[key]["chunks"].append({
                "text": doc,
                "chunk_idx": chunk_idx,
                "distance": distance,
                "relevance_score": max(0, 1 - distance)  # Convert distance to relevance
            })
            
            # Add to sources
            sources.append({
                "filename": filename,
                "section": section_idx,
                "chunk": chunk_idx,
                "relevance_score": max(0, 1 - distance),
                "char_count": metadata.get("char_count", len(doc))
            })
        
        # Format context with clear source attribution
        context_parts = []
        
        for file_section in file_sections.values():
            filename = file_section["filename"]
            section_idx = file_section["section_idx"]
            
            # Sort chunks by chunk index for coherent reading
            chunks = sorted(file_section["chunks"], key=lambda x: x["chunk_idx"])
            
            # Create section header
            section_header = f"\n=== {filename}"
            if section_idx > 0:
                section_header += f" (Section {section_idx + 1})"
            section_header += " ===\n"
            
            context_parts.append(section_header)
            
            # Add chunks with relevance indication
            for chunk in chunks:
                relevance = chunk["relevance_score"]
                relevance_indicator = ""
                if relevance > 0.8:
                    relevance_indicator = " [Highly Relevant]"
                elif relevance > 0.6:
                    relevance_indicator = " [Relevant]"
                
                context_parts.append(f"{chunk['text']}{relevance_indicator}\n")
        
        formatted_context = "\n".join(context_parts)
        
        # Ensure context doesn't exceed max length
        if len(formatted_context) > settings.MAX_CONTEXT_LENGTH:
            formatted_context = formatted_context[:settings.MAX_CONTEXT_LENGTH] + "\n\n[Context truncated...]"
        
        return {
            "formatted_context": formatted_context,
            "sources": sources
        }
    
    def get_file_specific_context(self, query: str, session_id: str, filename: str, top_k: int = 3) -> Dict[str, Any]:
        """Retrieve context from a specific file only"""
        return self.retrieve_context(
            query=query,
            session_id=session_id,
            top_k=top_k,
            filename_filter=filename,
            use_hybrid_search=True
        )
    
    def get_multi_file_context(self, query: str, session_id: str, filenames: List[str], top_k: int = 5) -> Dict[str, Any]:
        """Retrieve context from multiple specified files"""
        all_results = []
        
        for filename in filenames:
            file_result = self.get_file_specific_context(query, session_id, filename, top_k // len(filenames) + 1)
            if file_result["sources"]:
                all_results.append(file_result)
        
        if not all_results:
            return {
                "context": "",
                "sources": [],
                "total_chunks": 0,
                "query_embedding_dim": 0
            }
        
        # Combine results
        combined_context = "\n\n".join([result["context"] for result in all_results])
        combined_sources = []
        for result in all_results:
            combined_sources.extend(result["sources"])
        
        return {
            "context": combined_context,
            "sources": combined_sources,
            "total_chunks": sum(result["total_chunks"] for result in all_results),
            "query_embedding_dim": all_results[0]["query_embedding_dim"]
        }

# Global retriever instance
enhanced_retriever = EnhancedRetriever()

# Convenience function for backward compatibility
def retrieve_context(query: str, session_id: str, top_k: int = 5) -> Dict[str, Any]:
    """Legacy function"""
    return enhanced_retriever.retrieve_context(query, session_id, top_k)
