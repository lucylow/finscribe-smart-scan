"""Prometheus metrics collection."""
from prometheus_client import Counter, Histogram, Gauge
import time
from typing import Optional

# Job metrics
jobs_submitted = Counter(
    'finscribe_jobs_submitted_total',
    'Total number of jobs submitted',
    ['job_type']
)

jobs_completed = Counter(
    'finscribe_jobs_completed_total',
    'Total number of jobs completed',
    ['job_type', 'status']
)

jobs_failed = Counter(
    'finscribe_jobs_failed_total',
    'Total number of jobs failed',
    ['job_type', 'error_type']
)

# Latency metrics
ocr_latency = Histogram(
    'finscribe_ocr_latency_seconds',
    'OCR processing latency in seconds',
    ['model_type']
)

vlm_latency = Histogram(
    'finscribe_vlm_latency_seconds',
    'VLM parsing latency in seconds',
    ['model_type']
)

task_latency = Histogram(
    'finscribe_task_latency_seconds',
    'Task processing latency in seconds',
    ['task_name', 'status']
)

# Accuracy metrics
field_accuracy = Histogram(
    'finscribe_field_accuracy',
    'Field extraction accuracy (0.0-1.0)',
    ['field_name']
)

# Active learning metrics
active_learning_volume = Counter(
    'finscribe_active_learning_records_total',
    'Total number of active learning records created',
    ['needs_review']
)

active_learning_exported = Counter(
    'finscribe_active_learning_exported_total',
    'Total number of active learning records exported'
)

# Queue metrics
queue_size = Gauge(
    'finscribe_queue_size',
    'Current queue size',
    ['queue_name']
)

# Storage metrics
storage_objects_uploaded = Counter(
    'finscribe_storage_objects_uploaded_total',
    'Total number of objects uploaded to storage',
    ['object_type']
)

storage_objects_deleted = Counter(
    'finscribe_storage_objects_deleted_total',
    'Total number of objects deleted from storage',
    ['object_type']
)


class MetricsCollector:
    """Helper class for collecting metrics with context managers."""
    
    @staticmethod
    def record_ocr_latency(model_type: str, latency_seconds: float):
        """Record OCR latency."""
        ocr_latency.labels(model_type=model_type).observe(latency_seconds)
    
    @staticmethod
    def record_vlm_latency(model_type: str, latency_seconds: float):
        """Record VLM latency."""
        vlm_latency.labels(model_type=model_type).observe(latency_seconds)
    
    @staticmethod
    def record_task_latency(task_name: str, latency_seconds: float, status: str = "success"):
        """Record task latency."""
        task_latency.labels(task_name=task_name, status=status).observe(latency_seconds)
    
    @staticmethod
    def record_field_accuracy(field_name: str, accuracy: float):
        """Record field extraction accuracy."""
        field_accuracy.labels(field_name=field_name).observe(accuracy)
    
    @staticmethod
    def record_job_submitted(job_type: str):
        """Record job submission."""
        jobs_submitted.labels(job_type=job_type).inc()
    
    @staticmethod
    def record_job_completed(job_type: str, status: str = "completed"):
        """Record job completion."""
        jobs_completed.labels(job_type=job_type, status=status).inc()
    
    @staticmethod
    def record_job_failed(job_type: str, error_type: str = "unknown"):
        """Record job failure."""
        jobs_failed.labels(job_type=job_type, error_type=error_type).inc()
    
    @staticmethod
    def record_active_learning(needs_review: bool = False):
        """Record active learning record creation."""
        active_learning_volume.labels(needs_review=str(needs_review).lower()).inc()
    
    @staticmethod
    def record_active_learning_export():
        """Record active learning export."""
        active_learning_exported.inc()
    
    @staticmethod
    def record_storage_upload(object_type: str):
        """Record storage upload."""
        storage_objects_uploaded.labels(object_type=object_type).inc()
    
    @staticmethod
    def record_storage_delete(object_type: str):
        """Record storage deletion."""
        storage_objects_deleted.labels(object_type=object_type).inc()
    
    @staticmethod
    def update_queue_size(queue_name: str, size: int):
        """Update queue size gauge."""
        queue_size.labels(queue_name=queue_name).set(size)
    
    class Timer:
        """Context manager for timing operations."""
        def __init__(self, collector, metric_func, *labels):
            self.collector = collector
            self.metric_func = metric_func
            self.labels = labels
            self.start_time = None
        
        def __enter__(self):
            self.start_time = time.time()
            return self
        
        def __exit__(self, exc_type, exc_val, exc_tb):
            elapsed = time.time() - self.start_time
            status = "error" if exc_type else "success"
            if len(self.labels) == 1:
                self.metric_func(self.labels[0], elapsed)
            elif len(self.labels) == 2:
                # For task_latency with status
                task_latency.labels(task_name=self.labels[0], status=status).observe(elapsed)
            return False


# Singleton instance
_metrics_collector: Optional[MetricsCollector] = None


def get_metrics_collector() -> MetricsCollector:
    """Get or create metrics collector singleton."""
    global _metrics_collector
    if _metrics_collector is None:
        _metrics_collector = MetricsCollector()
    return _metrics_collector


