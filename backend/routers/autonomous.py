from fastapi import APIRouter, HTTPException, UploadFile, File, BackgroundTasks
from fastapi.responses import JSONResponse
from typing import Dict, Optional
import logging
import asyncio
from datetime import datetime
import uuid
import aiofiles
import os
from pathlib import Path

from ..agents.agent_orchestrator import AgentOrchestrator
from ..database.knowledge_base import KnowledgeBase
from ..utils.gemini_client import GeminiClient

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/autonomous", tags=["autonomous"])

# Initialize services
try:
    gemini_client = GeminiClient()
    orchestrator = AgentOrchestrator(gemini_client)
    knowledge_base = KnowledgeBase()
    logger.info("Autonomous router initialized successfully")
except Exception as e:
    logger.warning(f"Failed to initialize services: {e}")
    orchestrator = None
    knowledge_base = None

# In-memory storage for workflows (in production, use database)
workflows = {}
results_storage = {}

@router.post("/upload")
async def upload_documents(
    background_tasks: BackgroundTasks,
    wi_document: UploadFile = File(...),
    item_master: UploadFile = File(...)
):
    """Upload and start processing WI/QC document and Item Master"""
    try:
        # Validate file formats
        if not wi_document.filename.lower().endswith(('.pdf', '.docx', '.doc', '.txt')):
            raise HTTPException(status_code=400, detail="WI document must be PDF, DOCX, DOC, or TXT format")

        if not item_master.filename.lower().endswith(('.xlsx', '.xls', '.csv')):
            raise HTTPException(status_code=400, detail="Item Master must be XLSX, XLS, or CSV format")

        # Create workflow
        workflow_id = str(uuid.uuid4())
        workflows[workflow_id] = {
            "workflow_id": workflow_id,
            "status": "initialized",
            "current_stage": "upload",
            "progress": 0,
            "created_at": datetime.utcnow().isoformat(),
            "updated_at": datetime.utcnow().isoformat(),
            "message": "Documents uploaded successfully"
        }

        # Save uploaded files temporarily
        upload_dir = Path("uploads")
        upload_dir.mkdir(exist_ok=True)

        wi_path = upload_dir / wi_document.filename
        item_path = upload_dir / item_master.filename

        async with aiofiles.open(wi_path, 'wb') as f:
            content = await wi_document.read()
            await f.write(content)

        async with aiofiles.open(item_path, 'wb') as f:
            content = await item_master.read()
            await f.write(content)

        # Start processing in background
        background_tasks.add_task(
            process_documents_background,
            workflow_id,
            str(wi_path),
            str(item_path)
        )

        return JSONResponse({
            "success": True,
            "workflow_id": workflow_id,
            "message": "Documents uploaded successfully. Processing started."
        })

    except Exception as e:
        logger.error(f"Upload failed: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Upload failed: {str(e)}")

async def process_documents_background(workflow_id: str, wi_path: str, item_path: str):
    """Background task to process documents"""
    try:
        # Update workflow status
        workflows[workflow_id].update({
            "status": "processing",
            "current_stage": "translation",
            "message": "Starting document processing with knowledge base integration",
            "progress": 10,
            "updated_at": datetime.utcnow().isoformat()
        })

        if orchestrator:
            # Process using orchestrator with corrected async callback
            results = await orchestrator.process_documents_enhanced(
                wi_path,
                item_path,
                workflow_id,
                progress_callback=lambda stage, progress, message: asyncio.create_task(
                    update_workflow_progress(workflow_id, stage, progress, message)
                )
            )
        else:
            # Mock results for demo
            await asyncio.sleep(5)  # Simulate processing time
            results = {
                "workflow_id": workflow_id,
                "matches": [
                    {
                        "qa_material_name": "Sample Material",
                        "qa_excerpt": "Sample excerpt from document",
                        "qa_classification_label": 1,
                        "qa_confidence_level": "high",
                        "confidence_score": 0.85,
                        "supplier_description": "Matched supplier item",
                        "reasoning": "Demonstration match"
                    }
                ],
                "summary": {
                    "total_materials": 1,
                    "successful_matches": 1,
                    "knowledge_base_matches": 0
                },
                "knowledge_base_stats": knowledge_base.get_processing_stats() if knowledge_base else {}
            }

        # Store results
        results_storage[workflow_id] = results

        workflows[workflow_id].update({
            "status": "completed",
            "current_stage": "completed",
            "message": "Processing completed successfully",
            "progress": 100,
            "updated_at": datetime.utcnow().isoformat()
        })

        # Cleanup temporary files
        try:
            if os.path.exists(wi_path):
                os.remove(wi_path)
            if os.path.exists(item_path):
                os.remove(item_path)
        except Exception as e:
            logger.warning(f"Failed to cleanup files: {e}")

        logger.info(f"Workflow {workflow_id} completed successfully")

    except Exception as e:
        logger.error(f"Processing failed for workflow {workflow_id}: {str(e)}")
        workflows[workflow_id].update({
            "status": "error",
            "current_stage": "error",
            "message": f"Processing failed: {str(e)}",
            "progress": 0,
            "updated_at": datetime.utcnow().isoformat()
        })

async def update_workflow_progress(workflow_id: str, stage: str, progress: float, message: str):
    """Update workflow progress - NOW ASYNC"""
    if workflow_id in workflows:
        workflows[workflow_id].update({
            "current_stage": stage,
            "progress": progress,
            "message": message,
            "updated_at": datetime.utcnow().isoformat()
        })

@router.get("/workflow/{workflow_id}/status")
async def get_workflow_status(workflow_id: str):
    """Get workflow status"""
    try:
        if workflow_id not in workflows:
            raise HTTPException(status_code=404, detail="Workflow not found")
        return workflows[workflow_id]
    except Exception as e:
        logger.error(f"Failed to get workflow status: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/workflow/{workflow_id}/results")
async def get_results(workflow_id: str):
    """Get workflow results"""
    try:
        if workflow_id not in results_storage:
            raise HTTPException(status_code=404, detail="Results not found")

        return results_storage[workflow_id]
    except Exception as e:
        logger.error(f"Failed to get results: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/workflows")
async def list_workflows():
    """List all workflows"""
    try:
        return {"workflows": list(workflows.values())}
    except Exception as e:
        logger.error(f"Failed to list workflows: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
