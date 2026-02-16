# Enhanced RAG System - Main Application
import uvicorn
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware

# Import enhanced routes
from backend.api.routes_upload import router as upload_router
from backend.api.routes_rag import router as rag_router
from backend.api.routes_validate import router as validate_router
from backend.api.routes_files import router as files_router

app = FastAPI(
    title="Enhanced RAG System", 
    version="2.0.0",
    description="Production-ready RAG system with progressive file upload"
)

# CORS Configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Static file serving
app.mount("/static", StaticFiles(directory="frontend/static"), name="static")

# API Routes
app.include_router(upload_router, prefix="/api")
app.include_router(rag_router, prefix="/api")
app.include_router(validate_router, prefix="/api")
app.include_router(files_router, prefix="/api")

# Frontend Routes
@app.get("/")
async def serve_landing():
    return FileResponse("frontend/welcome.html")

@app.get("/auth")
async def serve_auth():
    return FileResponse("frontend/auth.html")

@app.get("/chat")
async def serve_chat():
    return FileResponse("frontend/chat.html")

@app.get("/health")
async def health():
    return {"status": "healthy", "version": "2.0.0"}

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
