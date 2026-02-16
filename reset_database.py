#!/usr/bin/env python3
"""
Database Reset Script - Fix Embedding Dimension Mismatch
========================================================

This script resolves the embedding dimension mismatch error by:
1. Resetting the ChromaDB collection
2. Clearing the embedding cache
3. Ensuring consistent embedding dimensions

Run this script when you encounter:
"Embedding dimension 768 does not match collection dimensionality 384"
"""

import os
import shutil
import sqlite3
import chromadb
from pathlib import Path

def reset_chroma_database(chroma_dir="./chroma_store"):
    """Reset ChromaDB by removing the entire directory"""
    print(f"🔄 Resetting ChromaDB at {chroma_dir}")
    
    if os.path.exists(chroma_dir):
        try:
            shutil.rmtree(chroma_dir)
            print(f"✅ Removed existing ChromaDB directory: {chroma_dir}")
        except Exception as e:
            print(f"❌ Error removing ChromaDB directory: {e}")
            return False
    else:
        print(f"ℹ️  ChromaDB directory doesn't exist: {chroma_dir}")
    
    # Create fresh ChromaDB instance
    try:
        client = chromadb.PersistentClient(path=chroma_dir)
        collection = client.get_or_create_collection(
            name="enhanced_rag_docs",
            metadata={"hnsw:space": "cosine"}
        )
        print(f"✅ Created fresh ChromaDB collection")
        return True
    except Exception as e:
        print(f"❌ Error creating new ChromaDB collection: {e}")
        return False

def reset_embedding_cache(cache_file="embeddings_cache.db"):
    """Clear the embedding cache database"""
    print(f"🔄 Resetting embedding cache at {cache_file}")
    
    if os.path.exists(cache_file):
        try:
            os.remove(cache_file)
            print(f"✅ Removed embedding cache file: {cache_file}")
        except Exception as e:
            print(f"❌ Error removing cache file: {e}")
            return False
    else:
        print(f"ℹ️  Embedding cache doesn't exist: {cache_file}")
    
    return True

def reset_session_database(session_file="sessions.db"):
    """Reset the session database (optional)"""
    print(f"🔄 Resetting session database at {session_file}")
    
    if os.path.exists(session_file):
        try:
            # Backup the session file first
            backup_file = f"{session_file}.backup"
            shutil.copy2(session_file, backup_file)
            print(f"📁 Created backup: {backup_file}")
            
            # Clear the sessions table but keep the schema
            conn = sqlite3.connect(session_file)
            cursor = conn.cursor()
            
            # Get all table names
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
            tables = cursor.fetchall()
            
            for table in tables:
                table_name = table[0]
                cursor.execute(f"DELETE FROM {table_name};")
                print(f"✅ Cleared table: {table_name}")
            
            conn.commit()
            conn.close()
            print(f"✅ Reset session database (backup created)")
            return True
            
        except Exception as e:
            print(f"❌ Error resetting session database: {e}")
            return False
    else:
        print(f"ℹ️  Session database doesn't exist: {session_file}")
        return True

def verify_embedding_model():
    """Verify the embedding model configuration"""
    print("🔍 Verifying embedding model configuration...")
    
    try:
        from backend.core.config import get_settings
        from sentence_transformers import SentenceTransformer
        
        settings = get_settings()
        model_name = settings.EMBEDDING_MODEL
        print(f"📋 Configured model: {model_name}")
        
        # Test loading the model
        model = SentenceTransformer(model_name)
        dimension = model.get_sentence_embedding_dimension()
        print(f"📐 Model dimension: {dimension}")
        
        # Test a simple embedding
        test_text = "This is a test sentence."
        embedding = model.encode(test_text)
        print(f"✅ Model test successful - embedding shape: {embedding.shape}")
        
        return True, dimension
        
    except Exception as e:
        print(f"❌ Error verifying embedding model: {e}")
        return False, None

def main():
    """Main reset function"""
    print("=" * 60)
    print("🚀 Enhanced RAG System - Database Reset")
    print("=" * 60)
    print()
    
    # Verify embedding model first
    model_ok, dimension = verify_embedding_model()
    if not model_ok:
        print("❌ Embedding model verification failed. Please check your configuration.")
        return False
    
    print(f"✅ Using embedding model with {dimension} dimensions")
    print()
    
    # Ask for confirmation
    response = input("⚠️  This will reset all uploaded documents and embeddings. Continue? (y/N): ")
    if response.lower() not in ['y', 'yes']:
        print("❌ Reset cancelled by user")
        return False
    
    print()
    success = True
    
    # Reset ChromaDB
    if not reset_chroma_database():
        success = False
    
    print()
    
    # Reset embedding cache
    if not reset_embedding_cache():
        success = False
    
    print()
    
    # Ask about session reset
    response = input("🗂️  Reset session data too? This will clear user sessions (y/N): ")
    if response.lower() in ['y', 'yes']:
        if not reset_session_database():
            success = False
    
    print()
    print("=" * 60)
    
    if success:
        print("✅ Database reset completed successfully!")
        print()
        print("Next steps:")
        print("1. Restart your RAG server")
        print("2. Upload your documents again")
        print("3. All documents will use consistent embeddings")
    else:
        print("❌ Some operations failed. Please check the errors above.")
    
    print("=" * 60)
    return success

if __name__ == "__main__":
    main()