"""
Job lifecycle management with deterministic state machine.
Implements stages, progress tracking, retries, and logging.
"""
import uuid
import logging
import time
from typing import Dict, Any, List, Optional
from datetime import datetime
from enum import Enum
from dataclasses import dataclass, field
import json

from ..api.v1.schemas import JobStage, JobStatus, StageInfo, JobProgress

logger = logging.getLogger(__name__)


@dataclass
class JobState:
    """Complete job state with all lifecycle information."""
    job_id: str
    status: JobStatus
    current_stage: Optional[JobStage] = None
    progress: int = 0
    stages: Dict[JobStage, StageInfo] = field(default_factory=dict)
    logs: List[str] = field(default_factory=list)
    result_id: Optional[str] = None
    error: Optional[Dict[str, Any]] = None
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
    metadata: Dict[str, Any] = field(default_factory=dict)
    artifacts: Dict[str, str] = field(default_factory=dict)  # stage -> artifact_path
    
    def to_progress(self) -> JobProgress:
        """Convert to JobProgress schema."""
        return JobProgress(
            job_id=self.job_id,
            status=self.status,
            current_step=self.current_stage,
            progress=self.progress,
            stages=[stage_info for stage_info in self.stages.values()],
            logs=self.logs.copy(),
            result_id=self.result_id,
            error=self.error
        )


class JobManager:
    """
    Manages job lifecycle with deterministic state machine.
    Handles retries, logging, and progress tracking.
    """
    
    # State machine transitions
    VALID_TRANSITIONS: Dict[JobStage, List[JobStage]] = {
        JobStage.RECEIVED: [JobStage.STAGING],
        JobStage.STAGING: [JobStage.PREPROCESS],
        JobStage.PREPROCESS: [JobStage.OCR_LAYOUT],
        JobStage.OCR_LAYOUT: [JobStage.OCR_RECOGNIZE],
        JobStage.OCR_RECOGNIZE: [JobStage.SEMANTIC_PARSE],
        JobStage.SEMANTIC_PARSE: [JobStage.POSTPROCESS],
        JobStage.POSTPROCESS: [JobStage.VALIDATE],
        JobStage.VALIDATE: [JobStage.STORE],
        JobStage.STORE: [JobStage.COMPLETED],
        # Failure transitions
        JobStage.FAILED: [],  # Terminal state
        JobStage.COMPLETED: [],  # Terminal state
    }
    
    # Progress percentages for each stage
    STAGE_PROGRESS: Dict[JobStage, int] = {
        JobStage.RECEIVED: 0,
        JobStage.STAGING: 5,
        JobStage.PREPROCESS: 10,
        JobStage.OCR_LAYOUT: 20,
        JobStage.OCR_RECOGNIZE: 30,
        JobStage.SEMANTIC_PARSE: 50,
        JobStage.POSTPROCESS: 70,
        JobStage.VALIDATE: 85,
        JobStage.STORE: 95,
        JobStage.COMPLETED: 100,
        JobStage.FAILED: 0,
    }
    
    def __init__(self):
        """Initialize job manager with in-memory store (use Redis/DB in production)."""
        self.jobs: Dict[str, JobState] = {}
        self.max_retries = 3
        self.retry_delays = [1, 2, 5]  # Exponential backoff in seconds
    
    def create_job(
        self,
        metadata: Optional[Dict[str, Any]] = None,
        tags: Optional[List[str]] = None
    ) -> str:
        """Create a new job and return job_id."""
        job_id = str(uuid.uuid4())
        
        job_state = JobState(
            job_id=job_id,
            status=JobStatus.QUEUED,
            current_stage=JobStage.RECEIVED,
            progress=0,
            metadata=metadata or {},
            logs=[f"Job {job_id} created at {datetime.utcnow().isoformat()}"]
        )
        
        # Initialize first stage
        job_state.stages[JobStage.RECEIVED] = StageInfo(
            stage=JobStage.RECEIVED,
            start_timestamp=datetime.utcnow(),
            progress=0
        )
        
        self.jobs[job_id] = job_state
        logger.info(f"Created job {job_id}")
        return job_id
    
    def transition_stage(
        self,
        job_id: str,
        new_stage: JobStage,
        message: Optional[str] = None,
        artifact_path: Optional[str] = None
    ) -> bool:
        """
        Transition job to a new stage.
        Returns True if transition is valid, False otherwise.
        """
        if job_id not in self.jobs:
            logger.error(f"Job {job_id} not found")
            return False
        
        job = self.jobs[job_id]
        current_stage = job.current_stage
        
        # Validate transition
        if current_stage and current_stage not in self.VALID_TRANSITIONS:
            logger.error(f"Invalid current stage: {current_stage}")
            return False
        
        if current_stage:
            valid_next = self.VALID_TRANSITIONS.get(current_stage, [])
            if new_stage not in valid_next and new_stage != JobStage.FAILED:
                logger.warning(
                    f"Invalid transition from {current_stage} to {new_stage}. "
                    f"Valid: {valid_next}"
                )
                return False
        
        # End current stage
        if current_stage and current_stage in job.stages:
            job.stages[current_stage].end_timestamp = datetime.utcnow()
            job.stages[current_stage].progress = 100
        
        # Start new stage
        job.current_stage = new_stage
        job.progress = self.STAGE_PROGRESS.get(new_stage, 0)
        job.status = JobStatus.PROCESSING if new_stage != JobStage.COMPLETED and new_stage != JobStage.FAILED else (
            JobStatus.COMPLETED if new_stage == JobStage.COMPLETED else JobStatus.FAILED
        )
        job.updated_at = datetime.utcnow()
        
        # Create stage info
        stage_info = StageInfo(
            stage=new_stage,
            start_timestamp=datetime.utcnow(),
            progress=0
        )
        job.stages[new_stage] = stage_info
        
        # Store artifact if provided
        if artifact_path:
            job.artifacts[new_stage.value] = artifact_path
        
        # Log transition
        log_msg = f"Transitioned to {new_stage.value}"
        if message:
            log_msg += f": {message}"
        job.logs.append(f"[{datetime.utcnow().isoformat()}] {log_msg}")
        logger.info(f"Job {job_id}: {log_msg}")
        
        return True
    
    def update_stage_progress(
        self,
        job_id: str,
        progress: int,
        message: Optional[str] = None
    ):
        """Update progress within current stage."""
        if job_id not in self.jobs:
            return
        
        job = self.jobs[job_id]
        if job.current_stage and job.current_stage in job.stages:
            job.stages[job.current_stage].progress = max(0, min(100, progress))
            job.progress = max(
                self.STAGE_PROGRESS.get(job.current_stage, 0),
                min(100, self.STAGE_PROGRESS.get(job.current_stage, 0) + progress // 10)
            )
            job.updated_at = datetime.utcnow()
            
            if message:
                job.logs.append(f"[{datetime.utcnow().isoformat()}] {message}")
    
    def add_log(self, job_id: str, message: str, level: str = "info"):
        """Add log entry to job."""
        if job_id not in self.jobs:
            return
        
        job = self.jobs[job_id]
        timestamp = datetime.utcnow().isoformat()
        log_entry = f"[{timestamp}] [{level.upper()}] {message}"
        job.logs.append(log_entry)
        job.updated_at = datetime.utcnow()
        
        # Also log to logger
        if level == "error":
            logger.error(f"Job {job_id}: {message}")
        elif level == "warning":
            logger.warning(f"Job {job_id}: {message}")
        else:
            logger.info(f"Job {job_id}: {message}")
    
    def mark_failed(
        self,
        job_id: str,
        error_code: str,
        error_message: str,
        retriable: bool = False
    ):
        """Mark job as failed with error information."""
        if job_id not in self.jobs:
            return
        
        job = self.jobs[job_id]
        job.status = JobStatus.FAILED
        job.current_stage = JobStage.FAILED
        job.error = {
            "code": error_code,
            "message": error_message,
            "retriable": retriable
        }
        job.updated_at = datetime.utcnow()
        
        # End current stage if exists
        if job.current_stage and job.current_stage in job.stages:
            job.stages[job.current_stage].end_timestamp = datetime.utcnow()
            job.stages[job.current_stage].error = error_message
        
        self.add_log(job_id, f"Job failed: {error_message}", "error")
    
    def mark_completed(self, job_id: str, result_id: str):
        """Mark job as completed with result_id."""
        if job_id not in self.jobs:
            return
        
        job = self.jobs[job_id]
        job.status = JobStatus.COMPLETED
        job.result_id = result_id
        job.updated_at = datetime.utcnow()
        
        self.transition_stage(job_id, JobStage.COMPLETED, "Job completed successfully")
    
    def get_job(self, job_id: str) -> Optional[JobState]:
        """Get job state."""
        return self.jobs.get(job_id)
    
    def get_job_progress(self, job_id: str) -> Optional[JobProgress]:
        """Get job progress in schema format."""
        job = self.get_job(job_id)
        if not job:
            return None
        return job.to_progress()
    
    def should_retry(self, job_id: str) -> bool:
        """Check if job should be retried."""
        job = self.get_job(job_id)
        if not job or not job.current_stage:
            return False
        
        stage_info = job.stages.get(job.current_stage)
        if not stage_info:
            return False
        
        if job.error and not job.error.get("retriable", False):
            return False
        
        return stage_info.retry_count < self.max_retries
    
    def increment_retry(self, job_id: str):
        """Increment retry count for current stage."""
        job = self.get_job(job_id)
        if not job or not job.current_stage:
            return
        
        stage_info = job.stages.get(job.current_stage)
        if stage_info:
            stage_info.retry_count += 1
            self.add_log(job_id, f"Retry attempt {stage_info.retry_count}/{self.max_retries}")
    
    def get_retry_delay(self, job_id: str) -> int:
        """Get retry delay in seconds (exponential backoff)."""
        job = self.get_job(job_id)
        if not job or not job.current_stage:
            return self.retry_delays[0]
        
        stage_info = job.stages.get(job.current_stage)
        if not stage_info:
            return self.retry_delays[0]
        
        retry_idx = min(stage_info.retry_count - 1, len(self.retry_delays) - 1)
        return self.retry_delays[max(0, retry_idx)]


# Global job manager instance
job_manager = JobManager()


