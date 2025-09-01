"""
Enhanced Autonomous Agent Orchestrator - Coordinates document-handling agents with QA classification
"""
import asyncio
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Callable, Dict, List, Optional
from ..models.schemas import BOMComparisonResult,  QAClassificationSummary
from ..database.knowledge_base import KnowledgeBase
from ..database.item_matcher import ItemMatcher
from .translation_agent import TranslationAgent
from .extraction_agent import ExtractionAgent  
from .supplier_bom_agent import SupplierBOMAgent
from .comparison_agent import ComparisonAgent

logger = logging.getLogger(__name__)

class AgentOrchestrator:
    def __init__(self, gemini_client):
        self.gemini_client = gemini_client
        # Initialize autonomous agents
        self.translation_agent = TranslationAgent(gemini_client)
        self.extraction_agent = ExtractionAgent(gemini_client)
        self.supplier_bom_agent = SupplierBOMAgent(gemini_client)
        self.comparison_agent = ComparisonAgent(gemini_client)

        # Initialize knowledge base and matcher
        try:
            self.knowledge_base = KnowledgeBase()
            self.item_matcher = ItemMatcher(self.knowledge_base)
        except Exception as e:
            logger.warning(f"Failed to initialize knowledge base: {e}")
            self.knowledge_base = None
            self.item_matcher = None

        logger.info("Enhanced Autonomous Agent Orchestrator initialized with QA classification and Knowledge Base")

    async def process_documents_enhanced(
        self,
        qa_document_path: str,
        supplier_bom_path: str,
        workflow_id: str,
        progress_callback: Optional[Callable] = None
    ) -> Dict:
        logger.info(f"Starting enhanced autonomous workflow for {workflow_id}")
        try:
            # Stage 1: Translation Agent
            if progress_callback:
                if asyncio.iscoroutinefunction(progress_callback):
                    await progress_callback("translation", 5.0, "Translation agent processing QA document...")
                else:
                    progress_callback("translation", 5.0, "Translation agent processing QA document...")
            translation_result = await self.translation_agent.process_document(
                qa_document_path,
                source_language="ja",
                target_language="en"
            )
            await self._save_stage_result(workflow_id, "translation", translation_result)
            if not translation_result or not translation_result.get('translated_content'):
                raise Exception("Translation failed - no translated content received")
            if progress_callback:
                if asyncio.iscoroutinefunction(progress_callback):
                    await progress_callback("translation", 30.0, "Translation completed successfully")
                else:
                    progress_callback("translation", 30.0, "Translation completed successfully")

            # Stage 2: Extraction Agent
            if progress_callback:
                if asyncio.iscoroutinefunction(progress_callback):
                    await progress_callback("extraction", 35.0, "Extraction agent processing materials with QA classification...")
                else:
                    progress_callback("extraction", 35.0, "Extraction agent processing materials with QA classification...")
            extraction_result = await self.extraction_agent.process_translated_content(
                translation_result['translated_content']
            )
            await self._save_stage_result(workflow_id, "extraction", extraction_result)
            if not extraction_result or not extraction_result.get('materials'):
                raise Exception("Material extraction failed - no materials extracted")
            extracted_materials_raw = extraction_result['materials']
            logger.info(f"Extracted {len(extracted_materials_raw)} materials with QA classification")

            # Convert ExtractedMaterial models to dicts for compatibility
            if extracted_materials_raw and hasattr(extracted_materials_raw[0], 'dict'):
                extracted_materials = [m.dict() for m in extracted_materials_raw]
            else:
                extracted_materials = extracted_materials_raw

            if progress_callback:
                if asyncio.iscoroutinefunction(progress_callback):
                    await progress_callback("extraction", 60.0, f"Extracted {len(extracted_materials)} materials with QA classification")
                else:
                    progress_callback("extraction", 60.0, f"Extracted {len(extracted_materials)} materials with QA classification")

            # Stage 3: Supplier BOM Agent
            if progress_callback:
                if asyncio.iscoroutinefunction(progress_callback):
                    await progress_callback("supplier_bom", 65.0, "Supplier BOM agent processing Excel data...")
                else:
                    progress_callback("supplier_bom", 65.0, "Supplier BOM agent processing Excel data...")
            supplier_result = await self.supplier_bom_agent.process_supplier_bom(
                supplier_bom_path
            )
            await self._save_stage_result(workflow_id, "supplier_bom", supplier_result)
            if not supplier_result or not supplier_result.get('items'):
                raise Exception("Supplier BOM processing failed - no items extracted")
            supplier_items = supplier_result['items']
            logger.info(f"Processed {len(supplier_items)} supplier BOM items")
            if progress_callback:
                if asyncio.iscoroutinefunction(progress_callback):
                    await progress_callback("supplier_bom", 80.0, f"Processed {len(supplier_items)} supplier BOM items")
                else:
                    progress_callback("supplier_bom", 80.0, f"Processed {len(supplier_items)} supplier BOM items")

            # Stage 4: Comparison and Knowledge Base
            if progress_callback:
                if asyncio.iscoroutinefunction(progress_callback):
                    await progress_callback("comparison", 85.0, "Enhanced comparison using knowledge base...")
                else:
                    progress_callback("comparison", 85.0, "Enhanced comparison using knowledge base...")

            if self.item_matcher:
                matched_models = self.item_matcher.match_items_with_knowledge_base(
                    extracted_materials_raw,  # pass raw models if required
                    supplier_items,
                    workflow_id
                )
                # Convert matched models to dicts
                enhanced_matches = [m.dict() for m in matched_models]
            else:
                enhanced_matches = await self.comparison_agent.compare_materials(
                    extracted_materials,
                    supplier_items
                )

            if progress_callback:
                if asyncio.iscoroutinefunction(progress_callback):
                    await progress_callback("comparison", 95.0, "Knowledge base matching completed")
                else:
                    progress_callback("comparison", 95.0, "Knowledge base matching completed")

            final_result = {
                "workflow_id": workflow_id,
                "matches": enhanced_matches,
                "summary": {
                    "total_materials": len(extracted_materials),
                    "total_supplier_items": len(supplier_items),
                    "successful_matches": sum(1 for m in enhanced_matches if m.get('confidence_score', 0) > 0.5),
                    "knowledge_base_matches": sum(1 for m in enhanced_matches if m.get('has_previous_match', False)),
                    "processing_date": datetime.utcnow().isoformat(),
                    "enhanced_matching": True
                },
                "knowledge_stats": self.knowledge_base.get_processing_stats() if self.knowledge_base else {},
                "qa_classification_summary": self._generate_qa_classification_summary(enhanced_matches)
            }
            await self._save_stage_result(workflow_id, "final", final_result)

            if progress_callback:
                if asyncio.iscoroutinefunction(progress_callback):
                    await progress_callback("completed", 100.0, "Processing completed successfully")
                else:
                    progress_callback("completed", 100.0, "Processing completed successfully")

            logger.info(f"Enhanced workflow {workflow_id} completed successfully")
            return final_result

        except Exception as e:
            logger.error(f"Enhanced workflow failed for {workflow_id}: {str(e)}")
            if progress_callback:
                if asyncio.iscoroutinefunction(progress_callback):
                    await progress_callback("error", 0.0, f"Processing failed: {str(e)}")
                else:
                    progress_callback("error", 0.0, f"Processing failed: {str(e)}")
            raise

    async def process_documents(self, qa_document_path, supplier_bom_path, workflow_id, progress_callback=None):
        result = await self.process_documents_enhanced(
            qa_document_path, supplier_bom_path, workflow_id, progress_callback
        )
        return BOMComparisonResult(
            workflow_id=result['workflow_id'],
            matches=result['matches'],
            summary=result['summary']
        )

    def _generate_qa_classification_summary(self, matches: List[Dict]) -> Dict:
        classification_counts = {}
        confidence_distribution = {"high": 0, "medium": 0, "low": 0}
        for m in matches:
            label = m.get('qa_classification_label', 5)
            classification_counts[label] = classification_counts.get(label, 0) + 1
            conf_level = m.get('qa_confidence_level', 'medium').lower()
            if conf_level in confidence_distribution:
                confidence_distribution[conf_level] += 1
        return {
            "classification_counts": classification_counts,
            "confidence_distribution": confidence_distribution,
            "total_items": len(matches)
        }

    async def _save_stage_result(self, workflow_id: str, stage: str, result: Dict):
        try:
            stage_dir = Path(f"results/{workflow_id}")
            stage_dir.mkdir(parents=True, exist_ok=True)
            stage_file = stage_dir / f"{stage}_result.json"
            with open(stage_file, "w", encoding="utf-8") as f:
                json.dump(result, f, ensure_ascii=False, indent=2, default=str)
            logger.info(f"Saved {stage} results for workflow {workflow_id}")
        except Exception as e:
            logger.warning(f"Failed to save {stage} results for workflow {workflow_id}: {e}")
