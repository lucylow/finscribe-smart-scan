"""Service layer for job and result database operations."""
import logging
import uuid
from typing import Optional, Dict, Any
from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy import and_

from ..db.models import Job, Result, JobStatus
from ..storage import get_storage

logger = logging.getLogger(__name__)


class JobService:
    """Service for managing jobs and results in the database."""
    
    def __init__(self, db: Session):
        self.db = db
        self.storage = get_storage()
    
    def create_job(
        self,
        filename: str,
        file_content: bytes,
        file_size: int,
        checksum: str,
        source_type: str = "upload",
        metadata: Optional[Dict[str, Any]] = None
    ) -> Job:
        """Create a new job record and store file in storage."""
        job_id = str(uuid.uuid4())
        
        # Store file in storage
        storage_key = f"staging/{job_id}/{filename}"
        try:
            self.storage.put_bytes(storage_key, file_content, metadata={
                'job_id': job_id,
                'filename': filename,
                'uploaded_at': datetime.utcnow().isoformat()
            })
        except Exception as e:
            logger.error(f"Failed to store file for job {job_id}: {e}")
            raise
        
        # Create job record
        job = Job(
            id=job_id,
            status=JobStatus.QUEUED.value,
            progress="0",
            stage="received",
            source_type=source_type,
            filename=filename,
            file_size=str(file_size),
            checksum=checksum,
            job_metadata=metadata or {},
            attempts="0"
        )
        
        self.db.add(job)
        self.db.commit()
        self.db.refresh(job)
        
        logger.info(f"Created job {job_id} for file {filename}")
        return job
    
    def get_job(self, job_id: str) -> Optional[Job]:
        """Get job by ID."""
        return self.db.query(Job).filter(Job.id == job_id).first()
    
    def update_job_status(
        self,
        job_id: str,
        status: Optional[str] = None,
        progress: Optional[int] = None,
        stage: Optional[str] = None,
        error: Optional[str] = None
    ) -> Optional[Job]:
        """Update job status and progress."""
        job = self.get_job(job_id)
        if not job:
            return None
        
        if status is not None:
            job.status = status
        if progress is not None:
            job.progress = str(progress)
        if stage is not None:
            job.stage = stage
        if error is not None:
            job.error = error
        
        job.updated_at = datetime.utcnow()
        self.db.commit()
        self.db.refresh(job)
        
        return job
    
    def increment_attempts(self, job_id: str) -> Optional[Job]:
        """Increment retry attempts."""
        job = self.get_job(job_id)
        if not job:
            return None
        
        current_attempts = int(job.attempts or "0")
        job.attempts = str(current_attempts + 1)
        job.updated_at = datetime.utcnow()
        self.db.commit()
        self.db.refresh(job)
        
        return job
    
    def create_result(
        self,
        job_id: str,
        data: Dict[str, Any],
        validation: Optional[Dict[str, Any]] = None,
        models_used: Optional[list] = None,
        raw_ocr_output: Optional[Dict[str, Any]] = None,
        schema_version: str = "1.0"
    ) -> Result:
        """Create result record and optionally store in object storage."""
        result_id = str(uuid.uuid4())
        
        # Store full result in object storage
        storage_key = f"results/{result_id}/result.json"
        try:
            result_data = {
                'id': result_id,
                'job_id': job_id,
                'data': data,
                'validation': validation,
                'models_used': models_used,
                'raw_ocr_output': raw_ocr_output,
                'created_at': datetime.utcnow().isoformat()
            }
            self.storage.put_json(storage_key, result_data)
        except Exception as e:
            logger.warning(f"Failed to store result in object storage: {e}")
            storage_key = None
        
        # Create result record
        result = Result(
            id=result_id,
            job_id=job_id,
            schema_version=schema_version,
            data=data,
            validation=validation,
            models_used=models_used,
            raw_ocr_output=raw_ocr_output,
            object_storage_key=storage_key
        )
        
        self.db.add(result)
        self.db.commit()
        self.db.refresh(result)
        
        # Update job to completed
        self.update_job_status(job_id, status=JobStatus.COMPLETED.value, progress=100, stage="completed")
        
        logger.info(f"Created result {result_id} for job {job_id}")
        return result
    
    def get_result_by_job_id(self, job_id: str) -> Optional[Result]:
        """Get result by job ID."""
        return self.db.query(Result).filter(Result.job_id == job_id).first()
    
    def get_result(self, result_id: str) -> Optional[Result]:
        """Get result by ID."""
        return self.db.query(Result).filter(Result.id == result_id).first()
    
    def list_jobs(
        self,
        status: Optional[str] = None,
        limit: int = 100,
        offset: int = 0
    ) -> list[Job]:
        """List jobs with optional filtering."""
        query = self.db.query(Job)
        if status:
            query = query.filter(Job.status == status)
        return query.order_by(Job.created_at.desc()).limit(limit).offset(offset).all()

