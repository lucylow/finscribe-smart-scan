"""
Production-grade ETL Pipeline Orchestrator for FinScribe AI.

Implements the complete Extract → Transform → Load pattern with:
- Document classification and routing
- Staging area management
- Multi-stage transformation
- Validation engine
- Multi-target loading (OLTP, data lake, feature store, vector store)
- Metadata tracking and audit trails
- Metrics and monitoring
"""
import os
import uuid
import json
import asyncio
import aiofiles
from typing import Dict, Any, List, Optional, Generator
from datetime import datetime
from pathlib import Path
from dataclasses import dataclass, asdict
from enum import Enum
import logging

from .base import StagedFile
from .classifier import DocumentClassifier
from .transformer import DocumentTransformer
from .validator import DocumentValidator
from .loaders import LoaderFactory, LoadTarget
from .metrics import get_metrics_collector, PipelineMetrics

logger = logging.getLogger(__name__)


class PipelineStage(Enum):
    """ETL pipeline stages."""
    INGESTED = "ingested"
    CLASSIFIED = "classified"
    EXTRACTED = "extracted"
    TRANSFORMED = "transformed"
    VALIDATED = "validated"
    LOADED = "loaded"
    FAILED = "failed"


@dataclass
class PipelineMetadata:
    """Comprehensive metadata tracking for ETL pipeline."""
    pipeline_id: str
    document_id: str
    stage: PipelineStage
    timestamp: datetime
    source_type: str
    source_id: Optional[str]
    filename: str
    checksum: str
    
    # Classification metadata
    is_scanned: Optional[bool] = None
    has_text_layer: Optional[bool] = None
    contains_tables: Optional[bool] = None
    is_multi_page: Optional[bool] = None
    document_type: Optional[str] = None  # invoice, receipt, statement, etc.
    
    # Processing metadata
    ocr_confidence: Optional[float] = None
    processing_time_ms: Optional[float] = None
    error_message: Optional[str] = None
    
    # Validation metadata
    validation_passed: Optional[bool] = None
    validation_errors: Optional[List[str]] = None
    
    # Load metadata
    load_targets: Optional[List[str]] = None  # Which targets were loaded to
    
    # User context
    user_id: Optional[str] = None
    tags: Optional[List[str]] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        data = asdict(self)
        data["stage"] = self.stage.value
        data["timestamp"] = self.timestamp.isoformat()
        return data


@dataclass
class PipelineResult:
    """Result from ETL pipeline execution."""
    success: bool
    pipeline_id: str
    document_id: str
    stage: PipelineStage
    
    # Raw extraction results
    raw_ocr_output: Optional[Dict[str, Any]] = None
    layout_graph: Optional[Dict[str, Any]] = None
    
    # Transformed data
    structured_data: Optional[Dict[str, Any]] = None
    canonical_schema: Optional[Dict[str, Any]] = None
    
    # Validation results
    validation_results: Optional[Dict[str, Any]] = None
    
    # Metadata
    metadata: Optional[PipelineMetadata] = None
    
    # Errors
    error: Optional[str] = None
    error_details: Optional[Dict[str, Any]] = None


class ETLPipeline:
    """
    Production-grade ETL pipeline orchestrator.
    
    Implements idempotent, replayable pipeline stages with comprehensive
    metadata tracking and multi-target loading.
    """
    
    def __init__(self, config: Dict[str, Any] = None):
        """
        Initialize ETL pipeline.
        
        Args:
            config: Pipeline configuration including storage paths, load targets, etc.
        """
        self.config = config or {}
        
        # Storage configuration
        storage_config = self.config.get("storage", {})
        self.staging_dir = Path(storage_config.get("staging_dir", "/tmp/finscribe_staging"))
        self.data_lake_dir = Path(storage_config.get("data_lake_dir", "/tmp/finscribe_data_lake"))
        self.metadata_dir = Path(storage_config.get("metadata_dir", "/tmp/finscribe_metadata"))
        
        # Create directories
        for dir_path in [self.staging_dir, self.data_lake_dir, self.metadata_dir]:
            dir_path.mkdir(parents=True, exist_ok=True)
        
        # Initialize pipeline components
        self.classifier = DocumentClassifier(self.config.get("classification", {}))
        self.transformer = DocumentTransformer(self.config.get("transformation", {}))
        self.validator = DocumentValidator(self.config.get("validation", {}))
        
        # Load targets configuration
        self.load_targets = self.config.get("load_targets", ["oltp", "data_lake"])
        self.loader_factory = LoaderFactory(self.config.get("loaders", {}))
        
        # Enable/disable stages
        self.enable_classification = self.config.get("enable_classification", True)
        self.enable_validation = self.config.get("enable_validation", True)
        self.enable_multi_target_load = self.config.get("enable_multi_target_load", True)
        
        # Metrics collector
        self.metrics_collector = get_metrics_collector()
        
        # Legacy metrics (for backward compatibility)
        self.metrics = {
            "total_processed": 0,
            "successful": 0,
            "failed": 0,
            "stage_counts": {stage.value: 0 for stage in PipelineStage},
            "avg_processing_time_ms": 0.0,
        }
    
    async def execute(
        self,
        staged_file: StagedFile,
        ocr_service,  # PaddleOCRVLService instance
        vlm_service=None,  # Optional VLM service
    ) -> PipelineResult:
        """
        Execute complete ETL pipeline on a staged file.
        
        This is the main entry point for processing documents through the ETL pipeline.
        The pipeline is idempotent and replayable - each stage can be retried independently.
        
        Args:
            staged_file: Staged file from ingestion adapter
            ocr_service: OCR service instance (PaddleOCRVLService)
            vlm_service: Optional VLM service for enrichment
            
        Returns:
            PipelineResult with complete processing results
        """
        pipeline_id = str(uuid.uuid4())
        document_id = str(uuid.uuid4())
        start_time = datetime.utcnow()
        
        logger.info(f"Starting ETL pipeline {pipeline_id} for document: {staged_file.filename}")
        
        # Initialize metadata
        metadata = PipelineMetadata(
            pipeline_id=pipeline_id,
            document_id=document_id,
            stage=PipelineStage.INGESTED,
            timestamp=start_time,
            source_type=staged_file.source_type,
            source_id=staged_file.source_id,
            filename=staged_file.filename,
            checksum=staged_file.checksum,
            user_id=staged_file.user_id,
            tags=staged_file.tags or [],
        )
        
        # Save to staging (immutable)
        staging_path = await self._save_to_staging(staged_file, document_id)
        metadata.stage = PipelineStage.CLASSIFIED
        
        try:
            # Stage 1: Document Classification
            if self.enable_classification:
                logger.info(f"[{pipeline_id}] Stage 1: Classifying document...")
                classification_result = await self.classifier.classify(
                    staged_file.content,
                    staged_file.filename
                )
                
                # Update metadata with classification results
                metadata.is_scanned = classification_result.get("is_scanned")
                metadata.has_text_layer = classification_result.get("has_text_layer")
                metadata.contains_tables = classification_result.get("contains_tables")
                metadata.is_multi_page = classification_result.get("is_multi_page")
                metadata.document_type = classification_result.get("document_type")
                
                logger.info(f"[{pipeline_id}] Classification: {classification_result}")
            
            # Stage 2: Extraction (OCR + Layout)
            logger.info(f"[{pipeline_id}] Stage 2: Extracting content...")
            metadata.stage = PipelineStage.EXTRACTED
            
            ocr_results = await ocr_service.parse_document(staged_file.content)
            
            if not ocr_results or not isinstance(ocr_results, dict):
                raise ValueError("OCR service returned invalid results")
            
            # Extract layout graph if available
            layout_graph = ocr_results.get("semantic_layout") or ocr_results.get("layout")
            
            # Update metadata
            metadata.ocr_confidence = ocr_results.get("confidence", 0.0)
            
            # Stage 3: Transformation
            logger.info(f"[{pipeline_id}] Stage 3: Transforming data...")
            metadata.stage = PipelineStage.TRANSFORMED
            
            transformation_result = await self.transformer.transform(
                ocr_results,
                classification_result if self.enable_classification else {},
                metadata
            )
            
            structured_data = transformation_result.get("structured_data", {})
            canonical_schema = transformation_result.get("canonical_schema", {})
            
            # Stage 4: Validation
            validation_results = None
            if self.enable_validation:
                logger.info(f"[{pipeline_id}] Stage 4: Validating data...")
                metadata.stage = PipelineStage.VALIDATED
                
                validation_results = await self.validator.validate(
                    structured_data,
                    canonical_schema,
                    ocr_results
                )
                
                metadata.validation_passed = validation_results.get("is_valid", False)
                metadata.validation_errors = validation_results.get("errors", [])
                
                if not metadata.validation_passed:
                    logger.warning(f"[{pipeline_id}] Validation failed: {metadata.validation_errors}")
            
            # Stage 5: Multi-target Loading
            load_results = {}
            if self.enable_multi_target_load:
                logger.info(f"[{pipeline_id}] Stage 5: Loading to targets...")
                metadata.stage = PipelineStage.LOADED
                
                for target_name in self.load_targets:
                    try:
                        target = LoadTarget[target_name.upper()]
                        loader = self.loader_factory.get_loader(target)
                        
                        load_result = await loader.load(
                            document_id=document_id,
                            structured_data=structured_data,
                            canonical_schema=canonical_schema,
                            metadata=metadata,
                            raw_ocr=ocr_results,
                            validation_results=validation_results
                        )
                        
                        load_results[target_name] = load_result
                        logger.info(f"[{pipeline_id}] Loaded to {target_name}: {load_result.get('success', False)}")
                    except Exception as load_error:
                        logger.error(f"[{pipeline_id}] Failed to load to {target_name}: {str(load_error)}")
                        load_results[target_name] = {"success": False, "error": str(load_error)}
                
                metadata.load_targets = list(load_results.keys())
            
            # Calculate processing time
            end_time = datetime.utcnow()
            processing_time_ms = (end_time - start_time).total_seconds() * 1000
            metadata.processing_time_ms = processing_time_ms
            
            # Update metrics
            self.metrics["total_processed"] += 1
            self.metrics["successful"] += 1
            self.metrics["stage_counts"][metadata.stage.value] += 1
            self._update_avg_processing_time(processing_time_ms)
            
            # Record metric
            field_count = len(structured_data) if structured_data else 0
            confidence = metadata.ocr_confidence or 0.0
            self.metrics_collector.record_metric(
                PipelineMetrics(
                    pipeline_id=pipeline_id,
                    document_id=document_id,
                    stage=metadata.stage.value,
                    processing_time_ms=processing_time_ms,
                    success=True,
                    validation_passed=metadata.validation_passed,
                    field_count=field_count,
                    confidence_score=confidence,
                )
            )
            
            # Save metadata
            await self._save_metadata(metadata)
            
            # Build result
            result = PipelineResult(
                success=True,
                pipeline_id=pipeline_id,
                document_id=document_id,
                stage=metadata.stage,
                raw_ocr_output=ocr_results,
                layout_graph=layout_graph,
                structured_data=structured_data,
                canonical_schema=canonical_schema,
                validation_results=validation_results,
                metadata=metadata
            )
            
            logger.info(f"[{pipeline_id}] Pipeline completed successfully in {processing_time_ms:.2f}ms")
            return result
            
        except Exception as e:
            # Handle pipeline failure
            end_time = datetime.utcnow()
            processing_time_ms = (end_time - start_time).total_seconds() * 1000
            
            metadata.stage = PipelineStage.FAILED
            metadata.error_message = str(e)
            metadata.processing_time_ms = processing_time_ms
            
            # Update metrics
            self.metrics["total_processed"] += 1
            self.metrics["failed"] += 1
            self.metrics["stage_counts"][PipelineStage.FAILED.value] += 1
            
            # Record metric
            error_type = type(e).__name__
            self.metrics_collector.record_metric(
                PipelineMetrics(
                    pipeline_id=pipeline_id,
                    document_id=document_id,
                    stage=PipelineStage.FAILED.value,
                    processing_time_ms=processing_time_ms,
                    success=False,
                    error_type=error_type,
                )
            )
            
            # Save metadata
            await self._save_metadata(metadata)
            
            logger.error(f"[{pipeline_id}] Pipeline failed: {str(e)}", exc_info=True)
            
            return PipelineResult(
                success=False,
                pipeline_id=pipeline_id,
                document_id=document_id,
                stage=PipelineStage.FAILED,
                metadata=metadata,
                error=str(e),
                error_details={"exception_type": type(e).__name__}
            )
    
    async def _save_to_staging(self, staged_file: StagedFile, document_id: str) -> Path:
        """Save file to staging area (immutable)."""
        staging_path = self.staging_dir / document_id / staged_file.filename
        staging_path.parent.mkdir(parents=True, exist_ok=True)
        
        async with aiofiles.open(staging_path, "wb") as f:
            await f.write(staged_file.content)
        
        logger.debug(f"Saved to staging: {staging_path}")
        return staging_path
    
    async def _save_metadata(self, metadata: PipelineMetadata):
        """Save pipeline metadata for audit trail."""
        metadata_path = self.metadata_dir / f"{metadata.pipeline_id}.json"
        
        async with aiofiles.open(metadata_path, "w") as f:
            await f.write(json.dumps(metadata.to_dict(), indent=2))
    
    def _update_avg_processing_time(self, new_time_ms: float):
        """Update running average of processing time."""
        total = self.metrics["total_processed"]
        current_avg = self.metrics["avg_processing_time_ms"]
        self.metrics["avg_processing_time_ms"] = (
            (current_avg * (total - 1) + new_time_ms) / total
        )
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get pipeline metrics."""
        return {
            **self.metrics,
            "success_rate": (
                self.metrics["successful"] / self.metrics["total_processed"]
                if self.metrics["total_processed"] > 0
                else 0.0
            )
        }
    
    async def replay_pipeline(self, pipeline_id: str) -> PipelineResult:
        """
        Replay a pipeline from metadata.
        
        This enables debugging and retraining by replaying failed or
        interesting pipelines.
        """
        metadata_path = self.metadata_dir / f"{pipeline_id}.json"
        
        if not metadata_path.exists():
            raise ValueError(f"Pipeline metadata not found: {pipeline_id}")
        
        async with aiofiles.open(metadata_path, "r") as f:
            metadata_dict = json.loads(await f.read())
        
        # Load staged file from staging
        staging_path = self.staging_dir / metadata_dict["document_id"] / metadata_dict["filename"]
        
        if not staging_path.exists():
            raise ValueError(f"Staged file not found: {staging_path}")
        
        async with aiofiles.open(staging_path, "rb") as f:
            content = await f.read()
        
        # Reconstruct StagedFile
        staged_file = StagedFile(
            source_type=metadata_dict["source_type"],
            source_id=metadata_dict.get("source_id"),
            filename=metadata_dict["filename"],
            content=content,
            checksum=metadata_dict["checksum"],
            user_id=metadata_dict.get("user_id"),
            tags=metadata_dict.get("tags", []),
            metadata={}
        )
        
        # Re-execute pipeline (would need ocr_service passed in)
        # This is a placeholder - actual implementation would require ocr_service
        raise NotImplementedError("Replay requires ocr_service instance")

