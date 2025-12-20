"""
Multi-target Loaders for ETL Pipeline.

Implements loaders for different destinations:
- OLTP Database (PostgreSQL) - for app queries
- Data Lake (S3/MinIO) - for retraining and audits
- Feature Store - for ML inference
- Vector Store - for semantic search/RAG
"""
import os
import json
import logging
from typing import Dict, Any, Optional, List
from enum import Enum
from pathlib import Path
from datetime import datetime
from abc import ABC, abstractmethod

try:
    import boto3
    from botocore.exceptions import ClientError
    BOTO3_AVAILABLE = True
except ImportError:
    BOTO3_AVAILABLE = False

logger = logging.getLogger(__name__)


class LoadTarget(Enum):
    """ETL load targets."""
    OLTP = "oltp"  # PostgreSQL for app queries
    DATA_LAKE = "data_lake"  # S3/MinIO for retraining
    FEATURE_STORE = "feature_store"  # For ML inference
    VECTOR_STORE = "vector_store"  # For semantic search/RAG


class BaseLoader(ABC):
    """Base class for loaders."""
    
    @abstractmethod
    async def load(
        self,
        document_id: str,
        structured_data: Dict[str, Any],
        canonical_schema: Dict[str, Any],
        metadata: Any,  # PipelineMetadata
        raw_ocr: Optional[Dict[str, Any]] = None,
        validation_results: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Load data to target destination.
        
        Returns:
            Dict with success status and any relevant information
        """
        pass


class OLTPLoader(BaseLoader):
    """
    Loader for OLTP database (PostgreSQL).
    
    Stores structured data for fast app queries and UI display.
    """
    
    def __init__(self, config: Dict[str, Any] = None):
        """Initialize OLTP loader."""
        self.config = config or {}
        # In production, this would initialize a database connection
        # For now, we'll use file-based storage as a placeholder
        self.storage_dir = Path(self.config.get("storage_dir", "/tmp/finscribe_oltp"))
        self.storage_dir.mkdir(parents=True, exist_ok=True)
    
    async def load(
        self,
        document_id: str,
        structured_data: Dict[str, Any],
        canonical_schema: Dict[str, Any],
        metadata: Any,
        raw_ocr: Optional[Dict[str, Any]] = None,
        validation_results: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Load to OLTP database.
        
        In production, this would:
        1. Insert into documents table
        2. Insert line items into line_items table
        3. Create indexes for fast queries
        """
        try:
            # For now, save as JSON file (placeholder)
            # In production, use SQLAlchemy or similar ORM
            
            record = {
                "document_id": document_id,
                "structured_data": structured_data,
                "canonical_schema": canonical_schema,
                "metadata": metadata.to_dict() if hasattr(metadata, 'to_dict') else {},
                "validation_results": validation_results,
                "created_at": datetime.utcnow().isoformat(),
            }
            
            # Save to file (placeholder for database insert)
            file_path = self.storage_dir / f"{document_id}.json"
            with open(file_path, "w") as f:
                json.dump(record, f, indent=2)
            
            logger.info(f"Loaded to OLTP: {document_id}")
            
            return {
                "success": True,
                "document_id": document_id,
                "target": "oltp"
            }
            
        except Exception as e:
            logger.error(f"OLTP load failed: {str(e)}", exc_info=True)
            return {
                "success": False,
                "error": str(e),
                "target": "oltp"
            }


class DataLakeLoader(BaseLoader):
    """
    Loader for Data Lake (S3/MinIO).
    
    Stores raw and processed data for:
    - Retraining models
    - Audit trails
    - Compliance
    - Analytics
    """
    
    def __init__(self, config: Dict[str, Any] = None):
        """Initialize data lake loader."""
        self.config = config or {}
        self.bucket_name = self.config.get("bucket_name", "finscribe-data-lake")
        self.endpoint_url = self.config.get("endpoint_url")  # For MinIO
        self.access_key = self.config.get("access_key")
        self.secret_key = self.config.get("secret_key")
        
        # Fallback to local storage if S3 not configured
        self.use_s3 = BOTO3_AVAILABLE and all([
            self.access_key,
            self.secret_key
        ])
        
        if not self.use_s3:
            self.storage_dir = Path(self.config.get("storage_dir", "/tmp/finscribe_data_lake"))
            self.storage_dir.mkdir(parents=True, exist_ok=True)
            logger.warning("S3 not configured, using local storage for data lake")
        
        if self.use_s3:
            self.s3_client = boto3.client(
                "s3",
                endpoint_url=self.endpoint_url,
                aws_access_key_id=self.access_key,
                aws_secret_access_key=self.secret_key
            )
    
    async def load(
        self,
        document_id: str,
        structured_data: Dict[str, Any],
        canonical_schema: Dict[str, Any],
        metadata: Any,
        raw_ocr: Optional[Dict[str, Any]] = None,
        validation_results: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Load to data lake.
        
        Stores:
        - Raw OCR output
        - Structured data
        - Metadata
        - Validation results
        """
        try:
            timestamp = datetime.utcnow()
            date_prefix = timestamp.strftime("%Y/%m/%d")
            
            # Prepare data lake record
            record = {
                "document_id": document_id,
                "timestamp": timestamp.isoformat(),
                "raw_ocr": raw_ocr,
                "structured_data": structured_data,
                "canonical_schema": canonical_schema,
                "metadata": metadata.to_dict() if hasattr(metadata, 'to_dict') else {},
                "validation_results": validation_results,
            }
            
            # Key structure: {date_prefix}/{document_id}/data.json
            key = f"{date_prefix}/{document_id}/data.json"
            
            if self.use_s3:
                # Upload to S3
                self.s3_client.put_object(
                    Bucket=self.bucket_name,
                    Key=key,
                    Body=json.dumps(record, indent=2),
                    ContentType="application/json"
                )
                logger.info(f"Loaded to data lake (S3): s3://{self.bucket_name}/{key}")
            else:
                # Save to local storage
                file_path = self.storage_dir / key
                file_path.parent.mkdir(parents=True, exist_ok=True)
                with open(file_path, "w") as f:
                    json.dump(record, f, indent=2)
                logger.info(f"Loaded to data lake (local): {file_path}")
            
            return {
                "success": True,
                "document_id": document_id,
                "target": "data_lake",
                "key": key
            }
            
        except Exception as e:
            logger.error(f"Data lake load failed: {str(e)}", exc_info=True)
            return {
                "success": False,
                "error": str(e),
                "target": "data_lake"
            }


class FeatureStoreLoader(BaseLoader):
    """
    Loader for Feature Store.
    
    Stores processed features for ML model inference.
    Features are normalized and ready for model consumption.
    """
    
    def __init__(self, config: Dict[str, Any] = None):
        """Initialize feature store loader."""
        self.config = config or {}
        # In production, this would connect to a feature store like Feast, Tecton, etc.
        # For now, we'll use file-based storage
        self.storage_dir = Path(self.config.get("storage_dir", "/tmp/finscribe_feature_store"))
        self.storage_dir.mkdir(parents=True, exist_ok=True)
    
    async def load(
        self,
        document_id: str,
        structured_data: Dict[str, Any],
        canonical_schema: Dict[str, Any],
        metadata: Any,
        raw_ocr: Optional[Dict[str, Any]] = None,
        validation_results: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Load to feature store.
        
        Extracts and stores features ready for ML inference.
        """
        try:
            # Extract features from canonical schema
            features = self._extract_features(canonical_schema, metadata)
            
            # Store features
            feature_record = {
                "document_id": document_id,
                "features": features,
                "timestamp": datetime.utcnow().isoformat(),
                "metadata": {
                    "source_type": metadata.source_type if hasattr(metadata, 'source_type') else None,
                    "document_type": metadata.document_type if hasattr(metadata, 'document_type') else None,
                }
            }
            
            # Save to file (placeholder for feature store)
            file_path = self.storage_dir / f"{document_id}_features.json"
            with open(file_path, "w") as f:
                json.dump(feature_record, f, indent=2)
            
            logger.info(f"Loaded to feature store: {document_id}")
            
            return {
                "success": True,
                "document_id": document_id,
                "target": "feature_store",
                "feature_count": len(features)
            }
            
        except Exception as e:
            logger.error(f"Feature store load failed: {str(e)}", exc_info=True)
            return {
                "success": False,
                "error": str(e),
                "target": "feature_store"
            }
    
    def _extract_features(
        self,
        canonical_schema: Dict[str, Any],
        metadata: Any
    ) -> Dict[str, Any]:
        """Extract ML-ready features from canonical schema."""
        features = {}
        
        # Numerical features
        features["total_amount"] = canonical_schema.get("total", 0.0)
        features["subtotal"] = canonical_schema.get("subtotal", 0.0)
        features["tax_amount"] = canonical_schema.get("tax", 0.0)
        features["line_item_count"] = len(canonical_schema.get("line_items", []))
        
        # Categorical features
        features["currency"] = canonical_schema.get("currency", "USD")
        features["document_type"] = (
            metadata.document_type if hasattr(metadata, 'document_type') else None
        )
        
        # Derived features
        if features["subtotal"] > 0:
            features["tax_rate"] = features["tax_amount"] / features["subtotal"]
        else:
            features["tax_rate"] = 0.0
        
        # Date features (if available)
        date_str = canonical_schema.get("date")
        if date_str:
            try:
                date_obj = datetime.fromisoformat(date_str.replace('Z', '+00:00'))
                features["invoice_year"] = date_obj.year
                features["invoice_month"] = date_obj.month
                features["invoice_day_of_week"] = date_obj.weekday()
            except Exception:
                pass
        
        return features


class VectorStoreLoader(BaseLoader):
    """
    Loader for Vector Store (for semantic search/RAG).
    
    Stores document embeddings for similarity search and retrieval.
    """
    
    def __init__(self, config: Dict[str, Any] = None):
        """Initialize vector store loader."""
        self.config = config or {}
        # In production, this would connect to a vector store like Pinecone, Weaviate, etc.
        # For now, we'll use file-based storage
        self.storage_dir = Path(self.config.get("storage_dir", "/tmp/finscribe_vector_store"))
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        self.enable_embeddings = self.config.get("enable_embeddings", False)
    
    async def load(
        self,
        document_id: str,
        structured_data: Dict[str, Any],
        canonical_schema: Dict[str, Any],
        metadata: Any,
        raw_ocr: Optional[Dict[str, Any]] = None,
        validation_results: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Load to vector store.
        
        Creates embeddings and stores for semantic search.
        """
        try:
            # Extract text for embedding
            text_content = self._extract_text_content(canonical_schema, raw_ocr)
            
            # Generate embedding (placeholder - would use actual embedding model)
            embedding = None
            if self.enable_embeddings:
                embedding = await self._generate_embedding(text_content)
            
            # Store vector record
            vector_record = {
                "document_id": document_id,
                "text_content": text_content,
                "embedding": embedding,
                "metadata": {
                    "vendor": canonical_schema.get("vendor"),
                    "date": canonical_schema.get("date"),
                    "total": canonical_schema.get("total"),
                    "document_type": (
                        metadata.document_type if hasattr(metadata, 'document_type') else None
                    ),
                },
                "timestamp": datetime.utcnow().isoformat(),
            }
            
            # Save to file (placeholder for vector store)
            file_path = self.storage_dir / f"{document_id}_vector.json"
            with open(file_path, "w") as f:
                json.dump(vector_record, f, indent=2)
            
            logger.info(f"Loaded to vector store: {document_id}")
            
            return {
                "success": True,
                "document_id": document_id,
                "target": "vector_store",
                "text_length": len(text_content)
            }
            
        except Exception as e:
            logger.error(f"Vector store load failed: {str(e)}", exc_info=True)
            return {
                "success": False,
                "error": str(e),
                "target": "vector_store"
            }
    
    def _extract_text_content(
        self,
        canonical_schema: Dict[str, Any],
        raw_ocr: Optional[Dict[str, Any]]
    ) -> str:
        """Extract text content for embedding."""
        parts = []
        
        # Add structured fields
        if canonical_schema.get("vendor"):
            parts.append(f"Vendor: {canonical_schema['vendor']}")
        if canonical_schema.get("invoice_id"):
            parts.append(f"Invoice ID: {canonical_schema['invoice_id']}")
        if canonical_schema.get("date"):
            parts.append(f"Date: {canonical_schema['date']}")
        if canonical_schema.get("line_items"):
            for item in canonical_schema["line_items"]:
                desc = item.get("description", "")
                if desc:
                    parts.append(desc)
        
        # Add raw OCR text if available
        if raw_ocr:
            text_blocks = raw_ocr.get("text_blocks", [])
            for block in text_blocks:
                if isinstance(block, dict):
                    text = block.get("text", "")
                else:
                    text = str(block)
                if text:
                    parts.append(text)
        
        return " ".join(parts)
    
    async def _generate_embedding(self, text: str) -> Optional[List[float]]:
        """
        Generate embedding for text.
        
        Placeholder - in production, would use:
        - OpenAI embeddings
        - Sentence transformers
        - Custom embedding model
        """
        # Placeholder: return None for now
        # In production, this would call an embedding service
        return None


class LoaderFactory:
    """Factory for creating loaders."""
    
    def __init__(self, config: Dict[str, Any] = None):
        """Initialize loader factory."""
        self.config = config or {}
        self._loaders = {}
    
    def get_loader(self, target: LoadTarget) -> BaseLoader:
        """Get loader for target."""
        if target not in self._loaders:
            loader_config = self.config.get(target.value, {})
            
            if target == LoadTarget.OLTP:
                self._loaders[target] = OLTPLoader(loader_config)
            elif target == LoadTarget.DATA_LAKE:
                self._loaders[target] = DataLakeLoader(loader_config)
            elif target == LoadTarget.FEATURE_STORE:
                self._loaders[target] = FeatureStoreLoader(loader_config)
            elif target == LoadTarget.VECTOR_STORE:
                self._loaders[target] = VectorStoreLoader(loader_config)
            else:
                raise ValueError(f"Unknown load target: {target}")
        
        return self._loaders[target]

