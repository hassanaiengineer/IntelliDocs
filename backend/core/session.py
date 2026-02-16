# backend/core/session.py - Enhanced Session Management
import uuid
import sqlite3
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from backend.core.config import get_settings

settings = get_settings()

# SQLite database for session management
DB_PATH = "sessions.db"

def init_session_db():
    """Initialize the session database"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS sessions (
            session_id TEXT PRIMARY KEY,
            username TEXT NOT NULL,
            api_key TEXT,
            provider TEXT DEFAULT 'openai',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            last_activity TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            question_count INTEGER DEFAULT 0,
            file_count INTEGER DEFAULT 0,
            is_active BOOLEAN DEFAULT TRUE
        )
    """)
    
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS session_files (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id TEXT NOT NULL,
            filename TEXT NOT NULL,
            file_hash TEXT NOT NULL,
            upload_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            chunk_count INTEGER DEFAULT 0,
            file_size INTEGER DEFAULT 0,
            FOREIGN KEY (session_id) REFERENCES sessions (session_id)
        )
    """)
    
    conn.commit()
    conn.close()

def create_session(username: str) -> str:
    """Create a new session"""
    session_id = str(uuid.uuid4())
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute("""
        INSERT INTO sessions (session_id, username)
        VALUES (?, ?)
    """, (session_id, username))
    
    conn.commit()
    conn.close()
    
    return session_id

def get_session(session_id: str) -> Optional[Dict[str, Any]]:
    """Get session details"""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT * FROM sessions WHERE session_id = ? AND is_active = TRUE
    """, (session_id,))
    
    row = cursor.fetchone()
    conn.close()
    
    return dict(row) if row else None

def update_session_credentials(session_id: str, api_key: str, provider: str):
    """Update session with API credentials"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute("""
        UPDATE sessions 
        SET api_key = ?, provider = ?, last_activity = CURRENT_TIMESTAMP
        WHERE session_id = ?
    """, (api_key, provider, session_id))
    
    conn.commit()
    conn.close()

def increment_question_count(session_id: str) -> int:
    """Increment question count and return new count"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute("""
        UPDATE sessions 
        SET question_count = question_count + 1, last_activity = CURRENT_TIMESTAMP
        WHERE session_id = ?
    """, (session_id,))
    
    cursor.execute("""
        SELECT question_count FROM sessions WHERE session_id = ?
    """, (session_id,))
    
    result = cursor.fetchone()
    count = result[0] if result else 0
    
    conn.commit()
    conn.close()
    
    return count

def add_session_file(session_id: str, filename: str, file_hash: str, 
                    chunk_count: int, file_size: int):
    """Add a file to the session"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Check if file already exists in session
    cursor.execute("""
        SELECT id FROM session_files 
        WHERE session_id = ? AND file_hash = ?
    """, (session_id, file_hash))
    
    if cursor.fetchone():
        conn.close()
        return False  # File already exists
    
    cursor.execute("""
        INSERT INTO session_files 
        (session_id, filename, file_hash, chunk_count, file_size)
        VALUES (?, ?, ?, ?, ?)
    """, (session_id, filename, file_hash, chunk_count, file_size))
    
    # Update session file count
    cursor.execute("""
        UPDATE sessions 
        SET file_count = (
            SELECT COUNT(*) FROM session_files WHERE session_id = ?
        ), last_activity = CURRENT_TIMESTAMP
        WHERE session_id = ?
    """, (session_id, session_id))
    
    conn.commit()
    conn.close()
    return True

def get_session_files(session_id: str) -> list:
    """Get all files for a session"""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT filename, upload_time, chunk_count, file_size
        FROM session_files 
        WHERE session_id = ?
        ORDER BY upload_time DESC
    """, (session_id,))
    
    rows = cursor.fetchall()
    conn.close()
    
    return [dict(row) for row in rows]

def validate_session_limits(session_id: str) -> Dict[str, Any]:
    """Check if session can accept more files/questions"""
    session = get_session(session_id)
    if not session:
        return {"valid": False, "error": "Session not found"}
    
    if session["question_count"] >= settings.MAX_QUESTIONS_PER_SESSION:
        return {"valid": False, "error": "Question limit reached"}
    
    if session["file_count"] >= settings.MAX_FILES_PER_SESSION:
        return {"valid": False, "error": "File limit reached"}
    
    return {"valid": True}

# Initialize database on import
init_session_db()
