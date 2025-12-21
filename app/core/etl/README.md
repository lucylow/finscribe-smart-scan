# ETL Pipeline System for FinScribe AI

A production-grade ETL (Extract, Transform, Load) pipeline system designed specifically for financial document intelligence. This system implements the complete data processing workflow from raw document ingestion to structured data storage across multiple targets.

## 🏗 Architecture Overview

The ETL pipeline follows a modular, stage-based architecture:

```
Raw Documents
    ↓
[Ingestion Adapters] → StagedFile
    ↓
[Document Classifier] → Classification Metadata
    ↓
[OCR Extraction] → Raw OCR Output
    ↓
[Transformer] → Structured Data + Canonical Schema
    ↓
[Validator] → Validation Results
    ↓
[Multi-target Loaders] → OLTP / Data Lake / Feature Store / Vector Store
```

## 📦 Components

### 1. **Ingestion Adapters** (`adapters.py`)

Pluggable adapters for different data sources:

- **MultipartAdapter**: Web uploads via FastAPI
- **S3Adapter**: S3/MinIO bucket monitoring
- **IMAPAdapter**: Email attachment ingestion
- **LocalFolderAdapter**: Batch folder processing

### 2. **Document Classifier** (`classifier.py`)

Intelligent document classification for routing:

- **Scanned vs Native PDF**: Detects document type
- **Text Layer Detection**: Identifies searchable PDFs
- **Table Detection**: Detects tabular structures
- **Document Type**: Classifies as invoice, receipt, statement, etc.

### 3. **Transformer** (`transformer.py`)

Converts OCR output to structured data:

- **Lexical Cleaning**: Removes OCR noise, fixes common errors
- **Semantic Structuring**: Extracts fields (invoice ID, vendor, amounts, etc.)
- **Schema Mapping**: Maps to canonical schema format
- **Data Enrichment**: Optional entity resolution and normalization

### 4. **Validator** (`validator.py`)

Comprehensive data validation:

- **Arithmetic Validation**: Checks subtotal + tax = total
- **Logical Validation**: Date ranges, non-negative amounts, required fields
- **Statistical Validation**: Outlier detection (placeholder)
- **Business Rules**: Tax rate validation, format checks

### 5. **Multi-target Loaders** (`loaders.py`)

Loads processed data to different destinations:

- **OLTPLoader**: PostgreSQL for app queries (fast access)
- **DataLakeLoader**: S3/MinIO for retraining and audits
- **FeatureStoreLoader**: ML-ready features for inference
- **VectorStoreLoader**: Embeddings for semantic search/RAG

### 6. **Pipeline Orchestrator** (`pipeline.py`)

Main ETL pipeline that orchestrates all stages:

- **Idempotent**: Stages can be retried safely
- **Replayable**: Can replay pipelines from metadata
- **Metadata Tracking**: Comprehensive audit trail
- **Error Handling**: Graceful failure with detailed error info

### 7. **Metrics & Monitoring** (`metrics.py`)

Real-time metrics collection:

- **Performance Metrics**: Processing times, percentiles (P50, P95, P99)
- **Quality Metrics**: Field extraction rates, confidence scores, validation rates
- **Error Tracking**: Error type breakdown
- **Historical Trends**: Time-windowed summaries

## 🚀 Usage

### Basic Example

```python
from app.core.etl import ETLPipeline, StagedFile
from app.core.models.paddleocr_vl_service import PaddleOCRVLService
from app.config.settings import load_config

# Initialize
config = load_config()
pipeline = ETLPipeline({
    "load_targets": ["oltp", "data_lake"],
    "enable_classification": True,
    "enable_validation": True,
})
ocr_service = PaddleOCRVLService(config)

# Create staged file
staged_file = StagedFile(
    source_type="multipart",
    filename="invoice.pdf",
    content=file_bytes,
    user_id="user_123",
)

# Execute pipeline
result = await pipeline.execute(staged_file, ocr_service)

if result.success:
    print(f"Document ID: {result.document_id}")
    print(f"Structured data: {result.canonical_schema}")
    print(f"Validation: {result.validation_results}")
```

### Using Adapters

```python
from app.core.etl import ETLAdapterFactory

# S3 adapter
s3_adapter = ETLAdapterFactory.create("s3")
s3_config = {
    "bucket_name": "invoices",
    "prefix": "2024/",
    "access_key": "...",
    "secret_key": "...",
}

for staged_file in s3_adapter.ingest(s3_config):
    result = await pipeline.execute(staged_file, ocr_service)
    print(f"Processed: {staged_file.filename}")
```

### Accessing Metrics

```python
from app.core.etl import get_metrics_collector

metrics = get_metrics_collector()

# Last hour summary
summary = metrics.get_summary(time_window_minutes=60)
print(f"Success rate: {summary['success_rate']*100:.1f}%")
print(f"Avg processing time: {summary['avg_processing_time_ms']:.2f}ms")

# Quality metrics
quality = metrics.get_quality_metrics()
print(f"Avg fields: {quality['avg_fields_extracted']:.1f}")
print(f"Validation pass rate: {quality['validation_pass_rate']*100:.1f}%")

# Performance metrics
perf = metrics.get_performance_metrics()
print(f"P95: {perf['p95_processing_time_ms']:.2f}ms")
```

## ⚙️ Configuration

### Pipeline Configuration

```python
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
            "endpoint_url": "http://localhost:9000",  # MinIO
            "access_key": "minioadmin",
            "secret_key": "minioadmin",
        },
        "feature_store": {
            "storage_dir": "/tmp/finscribe_feature_store",
        },
    },
    "enable_classification": True,
    "enable_validation": True,
    "enable_multi_target_load": True,
    "classification": {
        "enable_table_detection": True,
        "enable_document_type_classification": True,
    },
    "transformation": {
        "enable_lexical_cleaning": True,
        "enable_enrichment": False,
    },
    "validation": {
        "arithmetic_tolerance": 0.01,
        "enable_statistical_validation": False,
        "enable_business_rules": True,
    },
}
```

## 📊 Canonical Schema

The transformer outputs data in a canonical schema format:

```python
{
    "invoice_id": str,
    "vendor": str,
    "date": str,  # ISO format
    "due_date": Optional[str],
    "line_items": [
        {
            "description": str,
            "quantity": float,
            "unit_price": float,
            "amount": float,
        }
    ],
    "subtotal": Optional[float],
    "tax": Optional[float],
    "total": float,
    "currency": str,
    "payment_terms": Optional[str],
    "vendor_address": Optional[Dict[str, str]],
    "customer_address": Optional[Dict[str, str]],
    "notes": Optional[str],
}
```

## 🔍 Pipeline Stages

The pipeline progresses through these stages:

1. **INGESTED**: File received and staged
2. **CLASSIFIED**: Document type and characteristics identified
3. **EXTRACTED**: OCR and layout analysis complete
4. **TRANSFORMED**: Structured data extracted
5. **VALIDATED**: Validation rules applied
6. **LOADED**: Data written to target destinations
7. **FAILED**: Error occurred (with error details)

## 🎯 Best Practices

### 1. **Idempotency**

The pipeline is designed to be idempotent. Each stage can be retried safely:

```python
# Pipeline can be replayed from metadata
result = await pipeline.replay_pipeline(pipeline_id)
```

### 2. **Metadata Tracking**

All pipeline executions are tracked with comprehensive metadata:

- Source information
- Processing timestamps
- Classification results
- Validation results
- Load targets
- Error details (if failed)

### 3. **Multi-target Loading**

Load to multiple destinations for different use cases:

- **OLTP**: Fast queries for UI
- **Data Lake**: Retraining and compliance
- **Feature Store**: ML inference
- **Vector Store**: Semantic search

### 4. **Error Handling**

Failures are captured with detailed error information:

```python
if not result.success:
    print(f"Error: {result.error}")
    print(f"Stage: {result.stage.value}")
    print(f"Details: {result.error_details}")
```

### 5. **Metrics Monitoring**

Monitor pipeline health in real-time:

```python
# Get error breakdown
errors = metrics.get_error_breakdown()
print(f"Error types: {errors}")

# Get stage performance
summary = metrics.get_summary()
print(f"Stage times: {summary['stage_avg_times_ms']}")
```

## 🔧 Integration with Existing System

The ETL pipeline integrates seamlessly with the existing `FinancialDocumentProcessor`:

```python
# Option 1: Use ETL pipeline directly
from app.core.etl import ETLPipeline
result = await pipeline.execute(staged_file, ocr_service)

# Option 2: Use existing processor (which can be enhanced with ETL)
from app.core.document_processor import FinancialDocumentProcessor
processor = FinancialDocumentProcessor(config)
result = await processor.process_document(file_content, filename)
```

## 📈 Metrics Dashboard (Future)

The metrics system provides data for building dashboards:

- **Success Rate**: Percentage of successful pipelines
- **Processing Time**: P50, P95, P99 latencies
- **Quality Metrics**: Field extraction rates, confidence scores
- **Error Rates**: Breakdown by error type
- **Validation Rates**: Percentage passing validation

## 🚧 Future Enhancements

- [ ] Real-time streaming pipeline
- [ ] Distributed processing with Celery
- [ ] Advanced table detection and extraction
- [ ] ML-based field extraction
- [ ] Active learning integration
- [ ] Real-time metrics dashboard
- [ ] Pipeline scheduling (Airflow integration)
- [ ] Data quality scoring

## 📚 References

This ETL system implements best practices from:

- **ETL Patterns**: Extract → Transform → Load
- **Data Quality**: Validation and monitoring
- **Multi-target Loading**: Different destinations for different use cases
- **Metadata Tracking**: Comprehensive audit trails
- **Idempotency**: Safe retries and replays

See the main research document for detailed background on AI data sources and ETL processing.


