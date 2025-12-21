"""
Example integration of ETL Pipeline with FinScribe AI.

This demonstrates how to use the ETL pipeline system with
the existing document processor.
"""
import asyncio
import logging
from typing import Dict, Any

from app.core.etl import (
    ETLPipeline,
    ETLAdapterFactory,
    StagedFile,
    get_metrics_collector,
)
from app.core.models.paddleocr_vl_service import PaddleOCRVLService
from app.config.settings import load_config

logger = logging.getLogger(__name__)


async def example_etl_workflow():
    """
    Example ETL workflow demonstrating:
    1. Ingesting documents via adapter
    2. Processing through ETL pipeline
    3. Accessing results and metrics
    """
    # Load configuration
    config = load_config()
    
    # Initialize ETL pipeline
    etl_config = {
        "storage": {
            "staging_dir": "/tmp/finscribe_staging",
            "data_lake_dir": "/tmp/finscribe_data_lake",
            "metadata_dir": "/tmp/finscribe_metadata",
        },
        "load_targets": ["oltp", "data_lake", "feature_store"],
        "loaders": {
            "oltp": {
                "storage_dir": "/tmp/finscribe_oltp",
            },
            "data_lake": {
                "bucket_name": "finscribe-data-lake",
                # "endpoint_url": "http://localhost:9000",  # For MinIO
                # "access_key": "minioadmin",
                # "secret_key": "minioadmin",
            },
            "feature_store": {
                "storage_dir": "/tmp/finscribe_feature_store",
            },
        },
        "enable_classification": True,
        "enable_validation": True,
        "enable_multi_target_load": True,
    }
    
    pipeline = ETLPipeline(etl_config)
    
    # Initialize OCR service
    ocr_service = PaddleOCRVLService(config)
    
    # Example 1: Process a file from multipart upload
    print("Example 1: Processing file from multipart upload")
    
    # Create a staged file (simulating multipart upload)
    with open("example_invoice.pdf", "rb") as f:
        file_content = f.read()
    
    staged_file = StagedFile(
        source_type="multipart",
        filename="example_invoice.pdf",
        content=file_content,
        user_id="user_123",
        tags=["invoice", "q1-2024"],
    )
    
    # Execute pipeline
    result = await pipeline.execute(staged_file, ocr_service)
    
    if result.success:
        print(f"✓ Pipeline completed successfully")
        print(f"  Document ID: {result.document_id}")
        print(f"  Stage: {result.stage.value}")
        print(f"  Fields extracted: {len(result.canonical_schema)}")
        print(f"  Validation passed: {result.validation_results.get('is_valid', False)}")
    else:
        print(f"✗ Pipeline failed: {result.error}")
    
    # Example 2: Process multiple files from S3 adapter
    print("\nExample 2: Processing files from S3")
    
    s3_adapter = ETLAdapterFactory.create("s3")
    if s3_adapter:
        s3_config = {
            "bucket_name": "invoices",
            "prefix": "2024/",
            # "endpoint_url": "http://localhost:9000",
            # "access_key": "minioadmin",
            # "secret_key": "minioadmin",
        }
        
        if s3_adapter.validate_config(s3_config):
            for staged_file in s3_adapter.ingest(s3_config):
                result = await pipeline.execute(staged_file, ocr_service)
                print(f"Processed: {staged_file.filename} - {'✓' if result.success else '✗'}")
    
    # Example 3: Get metrics
    print("\nExample 3: Pipeline Metrics")
    metrics_collector = get_metrics_collector()
    
    summary = metrics_collector.get_summary(time_window_minutes=60)
    print(f"Last hour summary:")
    print(f"  Total processed: {summary['total']}")
    print(f"  Success rate: {summary['success_rate']*100:.1f}%")
    print(f"  Avg processing time: {summary['avg_processing_time_ms']:.2f}ms")
    
    quality_metrics = metrics_collector.get_quality_metrics()
    print(f"\nQuality metrics:")
    print(f"  Avg fields extracted: {quality_metrics['avg_fields_extracted']:.1f}")
    print(f"  Avg confidence: {quality_metrics['avg_confidence_score']:.2f}")
    print(f"  Validation pass rate: {quality_metrics['validation_pass_rate']*100:.1f}%")
    
    performance_metrics = metrics_collector.get_performance_metrics()
    print(f"\nPerformance metrics:")
    print(f"  P50: {performance_metrics['p50_processing_time_ms']:.2f}ms")
    print(f"  P95: {performance_metrics['p95_processing_time_ms']:.2f}ms")
    print(f"  P99: {performance_metrics['p99_processing_time_ms']:.2f}ms")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(example_etl_workflow())


