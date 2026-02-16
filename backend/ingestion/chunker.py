# backend/ingestion/chunker.py - Enhanced Semantic Chunking
import re
from typing import List, Dict, Any
from backend.core.config import get_settings

settings = get_settings()

class SemanticChunker:
    """Advanced semantic-aware text chunking"""
    
    def __init__(self, chunk_size: int = None, overlap: int = None):
        self.chunk_size = chunk_size or settings.CHUNK_SIZE
        self.overlap = overlap or settings.CHUNK_OVERLAP
        
        # Sentence boundary patterns
        self.sentence_endings = re.compile(r'[.!?]+\s+')
        self.paragraph_breaks = re.compile(r'\n\s*\n')
        self.section_breaks = re.compile(r'\n#{1,6}\s+|\n[A-Z][A-Z\s]+:|\n\d+\.\s+')
    
    def chunk_text(self, text: str, filename: str = "") -> List[Dict[str, Any]]:
        """Create semantically coherent chunks"""
        if not text.strip():
            return []
        
        # First, split into logical sections
        sections = self._split_into_sections(text)
        
        chunks = []
        for section_idx, section in enumerate(sections):
            section_chunks = self._chunk_section(section, section_idx, filename)
            chunks.extend(section_chunks)
        
        return chunks
    
    def _split_into_sections(self, text: str) -> List[str]:
        """Split text into logical sections"""
        # Find section breaks
        section_matches = list(self.section_breaks.finditer(text))
        
        if not section_matches:
            return [text]
        
        sections = []
        start = 0
        
        for match in section_matches:
            if start < match.start():
                section = text[start:match.start()].strip()
                if section:
                    sections.append(section)
            start = match.start()
        
        # Add final section
        final_section = text[start:].strip()
        if final_section:
            sections.append(final_section)
        
        return sections
    
    def _chunk_section(self, section: str, section_idx: int, filename: str) -> List[Dict[str, Any]]:
        """Chunk a section while preserving semantic boundaries"""
        if len(section) <= self.chunk_size:
            return [self._create_chunk(section, 0, section_idx, filename)]
        
        # Split into paragraphs first
        paragraphs = self.paragraph_breaks.split(section)
        
        chunks = []
        current_chunk = ""
        chunk_idx = 0
        
        for para in paragraphs:
            para = para.strip()
            if not para:
                continue
            
            # If paragraph fits in current chunk
            if len(current_chunk) + len(para) + 2 <= self.chunk_size:
                current_chunk = self._append_text(current_chunk, para)
            else:
                # Save current chunk if not empty
                if current_chunk:
                    chunks.append(self._create_chunk(current_chunk, chunk_idx, section_idx, filename))
                    chunk_idx += 1
                
                # If paragraph itself is too long, split by sentences
                if len(para) > self.chunk_size:
                    sentence_chunks = self._chunk_by_sentences(para, chunk_idx, section_idx, filename)
                    chunks.extend(sentence_chunks)
                    chunk_idx += len(sentence_chunks)
                    current_chunk = ""
                else:
                    current_chunk = para
        
        # Add final chunk
        if current_chunk:
            chunks.append(self._create_chunk(current_chunk, chunk_idx, section_idx, filename))
        
        # Add overlaps
        return self._add_overlaps(chunks)
    
    def _chunk_by_sentences(self, text: str, start_chunk_idx: int, section_idx: int, filename: str) -> List[Dict[str, Any]]:
        """Split long paragraph by sentences"""
        sentences = self.sentence_endings.split(text)
        
        chunks = []
        current_chunk = ""
        chunk_idx = start_chunk_idx
        
        for sentence in sentences:
            sentence = sentence.strip()
            if not sentence:
                continue
            
            # Add sentence ending back if it was removed
            if not sentence.endswith(('.', '!', '?')):
                sentence += '.'
            
            if len(current_chunk) + len(sentence) + 1 <= self.chunk_size:
                current_chunk = self._append_text(current_chunk, sentence)
            else:
                if current_chunk:
                    chunks.append(self._create_chunk(current_chunk, chunk_idx, section_idx, filename))
                    chunk_idx += 1
                
                # If single sentence is too long, force split
                if len(sentence) > self.chunk_size:
                    force_chunks = self._force_split(sentence, chunk_idx, section_idx, filename)
                    chunks.extend(force_chunks)
                    chunk_idx += len(force_chunks)
                    current_chunk = ""
                else:
                    current_chunk = sentence
        
        if current_chunk:
            chunks.append(self._create_chunk(current_chunk, chunk_idx, section_idx, filename))
        
        return chunks
    
    def _force_split(self, text: str, start_chunk_idx: int, section_idx: int, filename: str) -> List[Dict[str, Any]]:
        """Force split very long text"""
        chunks = []
        chunk_idx = start_chunk_idx
        
        for i in range(0, len(text), self.chunk_size - self.overlap):
            chunk_text = text[i:i + self.chunk_size]
            chunks.append(self._create_chunk(chunk_text, chunk_idx, section_idx, filename))
            chunk_idx += 1
        
        return chunks
    
    def _add_overlaps(self, chunks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Add overlapping content between chunks"""
        if len(chunks) <= 1:
            return chunks
        
        overlapped_chunks = [chunks[0]]
        
        for i in range(1, len(chunks)):
            prev_chunk = chunks[i-1]
            curr_chunk = chunks[i]
            
            # Get overlap from previous chunk
            prev_text = prev_chunk["text"]
            overlap_text = prev_text[-self.overlap:] if len(prev_text) > self.overlap else ""
            
            # Add overlap to current chunk
            if overlap_text:
                curr_chunk["text"] = overlap_text + " " + curr_chunk["text"]
            
            overlapped_chunks.append(curr_chunk)
        
        return overlapped_chunks
    
    def _create_chunk(self, text: str, chunk_idx: int, section_idx: int, filename: str) -> Dict[str, Any]:
        """Create chunk metadata"""
        return {
            "text": text.strip(),
            "metadata": {
                "filename": filename,
                "section_idx": section_idx,
                "chunk_idx": chunk_idx,
                "char_count": len(text),
                "word_count": len(text.split())
            }
        }
    
    def _append_text(self, current: str, new: str) -> str:
        """Append text with proper spacing"""
        if not current:
            return new
        return f"{current}\n\n{new}"

# Convenience function
def chunk_text(text: str, filename: str = "") -> List[Dict[str, Any]]:
    """Create semantic chunks from text"""
    chunker = SemanticChunker()
    return chunker.chunk_text(text, filename)
