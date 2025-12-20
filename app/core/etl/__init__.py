"""
ETL Pipeline System for FinScribe AI.

Complete ETL infrastructure including:
- Data source adapters (multipart, S3, IMAP, local)
- Document classification
- Transformation and schema mapping
- Validation engine
- Multi-target loading (OLTP, data lake, feature store, vector store)
- Metrics and monitoring
"""
from .base import ETLAdapter, StagedFile
from .adapters import (
    ETLAdapterFactory,
    MultipartAdapter,
    S3Adapter,
    IMAPAdapter,
    LocalFolderAdapter,
)
from .pipeline import ETLPipeline, PipelineStage, PipelineMetadata, PipelineResult
from .classifier import DocumentClassifier
from .transformer import DocumentTransformer
from .validator import DocumentValidator
from .loaders import (
    LoadTarget,
    BaseLoader,
    OLTPLoader,
    DataLakeLoader,
    FeatureStoreLoader,
    VectorStoreLoader,
    LoaderFactory,
)
from .metrics import MetricsCollector, PipelineMetrics, get_metrics_collector

__all__ = [
    # Base
    "ETLAdapter",
    "StagedFile",
    # Adapters
    "ETLAdapterFactory",
    "MultipartAdapter",
    "S3Adapter",
    "IMAPAdapter",
    "LocalFolderAdapter",
    # Pipeline
    "ETLPipeline",
    "PipelineStage",
    "PipelineMetadata",
    "PipelineResult",
    # Components
    "DocumentClassifier",
    "DocumentTransformer",
    "DocumentValidator",
    # Loaders
    "LoadTarget",
    "BaseLoader",
    "OLTPLoader",
    "DataLakeLoader",
    "FeatureStoreLoader",
    "VectorStoreLoader",
    "LoaderFactory",
    # Metrics
    "MetricsCollector",
    "PipelineMetrics",
    "get_metrics_collector",
]

