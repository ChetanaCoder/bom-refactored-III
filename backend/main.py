"""
Enhanced Autonomous BOM Comparison Platform - Main FastAPI Application with QA Classification and Knowledge Base
"""

import asyncio
import json
import logging
import os
import uuid
from dotenv import load_dotenv
from datetime import datetime
from pathlib import Path
from typing import Dict, Optional

import aiofiles
import uvicorn
from fastapi import FastAPI, File, HTTPException, UploadFile, WebSocket, WebSocketDisconnect, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse

from .agents.agent_orchestrator import AgentOrchestrator
from .routers import autonomous, knowledge_base
from .utils.gemini_client import GeminiClient

load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(
    title="Enhanced Autonomous BOM Comparison Platform",
    description="AI-powered BOM comparison with QA classification and Knowledge Base integration",
    version="2.0.0"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:5173", "http://127.0.0.1:3000", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(autonomous.router)
app.include_router(knowledge_base.router)

# Health check endpoint
@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "version": "2.0.0",
        "features": {
            "qa_classification": True,
            "knowledge_base": True,
            "japanese_translation": True
        }
    }

# Simple route for testing
@app.get("/")
async def root():
    return {"message": "Enhanced Autonomous BOM Platform API", "version": "2.0.0"}

if __name__ == "__main__":
    # Ensure required directories exist
    Path("uploads").mkdir(exist_ok=True)
    Path("results").mkdir(exist_ok=True)

    # Start the server
    uvicorn.run(
        "main:app", 
        host="0.0.0.0", 
        port=int(os.getenv("PORT", 8000)),
        reload=True,
        log_level="info"
    )
