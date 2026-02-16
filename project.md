# 🧠 Enhanced RAG System - Project Overview

This document provides a comprehensive analysis of the **IntelliDocs** Enhanced RAG (Retrieval-Augmented Generation) system, detailing its architecture, technology stack, and operational workflow.

---

## 🛠 Technology Stack

### 🔹 Backend (Python-based)
- **Framework**: [FastAPI](https://fastapi.tiangolo.com/) - High-performance web framework for building APIs.
- **Vector Database**: [ChromaDB](https://www.trychroma.com/) - Persistent vector storage for document embeddings.
- **Embeddings**: [Sentence-Transformers](https://www.sbert.net/) (`all-MiniLM-L6-v2`) - Local embedding generation using HuggingFace models.
- **Document Processing**:
  - `PyMuPDF` (fitz): For high-quality PDF text and metadata extraction.
  - `python-docx`: For parsing Microsoft Word documents.
- **LLM Integration**: Direct REST API integration with:
  - **OpenAI** (GPT-3.5/4)
  - **Google Gemini** (Pro/Flash)
  - **Anthropic Claude** (Claude 3 family)
- **Data Validation**: `Pydantic` & `Pydantic-settings` for robust configuration and schema management.
- **Session Management**: Custom session handling via SQLite (`sessions.db`) to manage user context and file limits.

### 🔹 Frontend (Native Web Tech)
- **Structure**: Semantic HTML5.
- **Styling**: Vanilla CSS with modern components, glassmorphism effects, and responsive design.
- **Logic**: Modular Vanilla JavaScript (ES6+) - no heavy frameworks, ensuring fast load times.
- **Interactions**: Drag-and-drop file uploads, real-time typing indicators, and progressive UI updates.

---

## 🏗 System Architecture

The project follows a modular architecture designed for scalability and maintainability:

1.  **API Layer (`backend/api/`)**:
    - `routes_upload.py`: Handles file reception, validation, and triggering the ingestion pipeline.
    - `routes_rag.py`: Manages the Q&A logic, retrieval, and LLM communication.
    - `routes_files.py`: Provides endpoints for listing and deleting session files.
2.  **Ingestion Engine (`backend/ingestion/`)**:
    - `document_processor.py`: Extracts raw text and metadata (author, pages, etc.).
    - `chunker.py`: Implements semantic chunking to ensure context is preserved across text splits.
3.  **Embedding Service (`backend/embedding/`)**:
    - Manages local model loading and provides a caching layer (`embeddings_cache.db`) to avoid re-embedding identical text across sessions.
4.  **Vector Store interface (`backend/vector/`)**:
    - `vectorstore.py`: Abstracts ChromaDB operations (add, query, delete).
    - `retriever.py`: Implements **Hybrid Search** (combining vector similarity with keyword matching) for better accuracy.
5.  **LLM Provider Manager (`backend/llm/`)**:
    - A unified interface to swap between OpenAI, Gemini, and Anthropic seamlessly.

---

## 🔄 How It Works (The Workflow)

### 1. Session Initialization
- The user enters their name on the `welcome.html` page.
- A unique `session_id` is generated and stored.
- The user configures their preferred AI provider and API key on the `auth.html` page (stored securely in the browser session).

### 2. Document Ingestion
- When a file is uploaded:
  - **Extraction**: The `DocumentProcessor` parses the PDF/DOCX.
  - **Chunking**: The text is split into overlapping "chunks" (default ~1000 characters).
  - **Embedding**: Each chunk is converted into a high-dimensional vector using the local `Sentence-Transformers` model.
  - **Storage**: Chunks and vectors are stored in ChromaDB, tagged with the `session_id` and `filename`.

### 3. Retrieval-Augmented Generation (RAG)
- When a user asks a question:
  - **Embedding Query**: The question is converted into a vector.
  - **Retrieval**: The system searches ChromaDB for the Top-K (default 5) most relevant chunks related to the session.
  - **Context Construction**: Relevant chunks and metadata (source files) are assembled into a structured context.
  - **Augmentation**: An optimized prompt is sent to the chosen LLM containing the user's question + the retrieved document context.
  - **Response**: The LLM generates an answer based *only* on the provided context, ensuring factual accuracy and citing the source document.

---

## 🔥 Key Features

- **Progressive Upload**: Add new documents anytime without losing context from previous ones.
- **Source Attribution**: Every answer includes references to specific pages or files used.
- **Hybrid Search**: Uses both semantic meanings and exact keyword matches to find the best information.
- **Zero Persistence (Privacy)**: Documents are tied to temporary sessions and can be cleared instantly.
- **Local Embeddings**: Sensitive document content is embedded locally on your machine before searching.

---

## 📁 Directory Structure

- `main.py`: The application entry point (FastAPI).
- `backend/`: Core logic (API, LLM, Vector, Ingestion).
- `frontend/`: UI files (HTML, CSS, JS).
- `chroma_store/`: Persistent storage for document vectors.
- `requirements.txt`: List of all Python dependencies.
- `.env`: Configuration settings (Server, Chunk size, etc.).
