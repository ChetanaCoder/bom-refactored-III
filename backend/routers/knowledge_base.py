from fastapi import APIRouter, HTTPException
from typing import Dict, Optional
import logging

from ..database.knowledge_base import KnowledgeBase

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/knowledge-base", tags=["knowledge-base"])

# Initialize knowledge base
try:
    knowledge_base = KnowledgeBase()
    logger.info("Knowledge base router initialized successfully")
except Exception as e:
    logger.warning(f"Failed to initialize knowledge base: {e}")
    knowledge_base = None

@router.get("/stats")
async def get_knowledge_base_stats():
    """Get knowledge base statistics"""
    try:
        if knowledge_base:
            return knowledge_base.get_processing_stats()
        else:
            return {
                "total_items": 0,
                "total_workflows": 0,
                "total_matches": 0,
                "unique_matched_items": 0,
                "match_rate": 0
            }
    except Exception as e:
        logger.error(f"Failed to get knowledge base stats: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))