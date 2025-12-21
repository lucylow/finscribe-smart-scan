"""
ETL Pipeline Metrics and Monitoring.

Tracks pipeline performance, quality metrics, and operational statistics.
"""
import logging
from typing import Dict, Any, List
from datetime import datetime, timedelta
from collections import defaultdict
from dataclasses import dataclass, asdict

logger = logging.getLogger(__name__)


@dataclass
class PipelineMetrics:
    """Metrics for a single pipeline execution."""
    pipeline_id: str
    document_id: str
    stage: str
    processing_time_ms: float
    success: bool
    error_type: str = None
    validation_passed: bool = None
    field_count: int = 0
    confidence_score: float = 0.0
    timestamp: datetime = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.utcnow()
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        data = asdict(self)
        data["timestamp"] = self.timestamp.isoformat()
        return data


class MetricsCollector:
    """
    Collects and aggregates ETL pipeline metrics.
    
    Provides:
    - Real-time metrics
    - Historical trends
    - Quality metrics
    - Performance metrics
    """
    
    def __init__(self):
        """Initialize metrics collector."""
        self.metrics: List[PipelineMetrics] = []
        self.max_metrics = 10000  # Keep last 10k metrics in memory
        
        # Aggregated counters
        self.counters = defaultdict(int)
        self.timers = defaultdict(list)
        
    def record_metric(self, metric: PipelineMetrics):
        """Record a pipeline metric."""
        self.metrics.append(metric)
        
        # Update counters
        self.counters[f"total_{metric.stage}"] += 1
        if metric.success:
            self.counters["successful"] += 1
        else:
            self.counters["failed"] += 1
            if metric.error_type:
                self.counters[f"error_{metric.error_type}"] += 1
        
        # Update timers
        self.timers[metric.stage].append(metric.processing_time_ms)
        
        # Trim old metrics
        if len(self.metrics) > self.max_metrics:
            self.metrics = self.metrics[-self.max_metrics:]
    
    def get_summary(self, time_window_minutes: int = 60) -> Dict[str, Any]:
        """
        Get metrics summary for time window.
        
        Args:
            time_window_minutes: Time window in minutes (default: last hour)
            
        Returns:
            Summary dictionary with aggregated metrics
        """
        cutoff_time = datetime.utcnow() - timedelta(minutes=time_window_minutes)
        recent_metrics = [
            m for m in self.metrics
            if m.timestamp >= cutoff_time
        ]
        
        if not recent_metrics:
            return {
                "time_window_minutes": time_window_minutes,
                "total": 0,
                "successful": 0,
                "failed": 0,
                "success_rate": 0.0,
            }
        
        successful = sum(1 for m in recent_metrics if m.success)
        failed = len(recent_metrics) - successful
        
        # Calculate averages
        avg_processing_time = (
            sum(m.processing_time_ms for m in recent_metrics) / len(recent_metrics)
        )
        
        # Stage breakdown
        stage_counts = defaultdict(int)
        stage_times = defaultdict(list)
        for m in recent_metrics:
            stage_counts[m.stage] += 1
            stage_times[m.stage].append(m.processing_time_ms)
        
        stage_avg_times = {
            stage: sum(times) / len(times) if times else 0
            for stage, times in stage_times.items()
        }
        
        # Validation metrics
        validation_metrics = [m for m in recent_metrics if m.validation_passed is not None]
        validation_passed = sum(1 for m in validation_metrics if m.validation_passed)
        validation_rate = (
            validation_passed / len(validation_metrics)
            if validation_metrics else None
        )
        
        # Quality metrics
        avg_confidence = (
            sum(m.confidence_score for m in recent_metrics if m.confidence_score > 0) /
            max(1, sum(1 for m in recent_metrics if m.confidence_score > 0))
        )
        
        avg_field_count = (
            sum(m.field_count for m in recent_metrics) / len(recent_metrics)
        )
        
        return {
            "time_window_minutes": time_window_minutes,
            "total": len(recent_metrics),
            "successful": successful,
            "failed": failed,
            "success_rate": successful / len(recent_metrics) if recent_metrics else 0.0,
            "avg_processing_time_ms": avg_processing_time,
            "stage_counts": dict(stage_counts),
            "stage_avg_times_ms": stage_avg_times,
            "validation_rate": validation_rate,
            "avg_confidence_score": avg_confidence,
            "avg_field_count": avg_field_count,
        }
    
    def get_quality_metrics(self) -> Dict[str, Any]:
        """Get data quality metrics."""
        recent_metrics = self.metrics[-1000:] if len(self.metrics) > 1000 else self.metrics
        
        if not recent_metrics:
            return {"total": 0}
        
        # Field extraction success
        metrics_with_fields = [m for m in recent_metrics if m.field_count > 0]
        avg_fields = (
            sum(m.field_count for m in metrics_with_fields) / len(metrics_with_fields)
            if metrics_with_fields else 0
        )
        
        # Confidence distribution
        confidence_scores = [m.confidence_score for m in recent_metrics if m.confidence_score > 0]
        avg_confidence = sum(confidence_scores) / len(confidence_scores) if confidence_scores else 0.0
        
        # Validation pass rate
        validation_metrics = [m for m in recent_metrics if m.validation_passed is not None]
        validation_pass_rate = (
            sum(1 for m in validation_metrics if m.validation_passed) / len(validation_metrics)
            if validation_metrics else None
        )
        
        return {
            "total_samples": len(recent_metrics),
            "avg_fields_extracted": avg_fields,
            "avg_confidence_score": avg_confidence,
            "validation_pass_rate": validation_pass_rate,
            "high_confidence_rate": (
                sum(1 for c in confidence_scores if c >= 0.8) / len(confidence_scores)
                if confidence_scores else 0.0
            ),
        }
    
    def get_performance_metrics(self) -> Dict[str, Any]:
        """Get performance metrics."""
        recent_metrics = self.metrics[-1000:] if len(self.metrics) > 1000 else self.metrics
        
        if not recent_metrics:
            return {"total": 0}
        
        processing_times = [m.processing_time_ms for m in recent_metrics]
        
        return {
            "total_samples": len(recent_metrics),
            "avg_processing_time_ms": sum(processing_times) / len(processing_times),
            "min_processing_time_ms": min(processing_times),
            "max_processing_time_ms": max(processing_times),
            "p50_processing_time_ms": self._percentile(processing_times, 50),
            "p95_processing_time_ms": self._percentile(processing_times, 95),
            "p99_processing_time_ms": self._percentile(processing_times, 99),
        }
    
    def _percentile(self, data: List[float], percentile: int) -> float:
        """Calculate percentile."""
        if not data:
            return 0.0
        sorted_data = sorted(data)
        index = int(len(sorted_data) * percentile / 100)
        return sorted_data[min(index, len(sorted_data) - 1)]
    
    def get_error_breakdown(self) -> Dict[str, int]:
        """Get error type breakdown."""
        error_counts = defaultdict(int)
        for metric in self.metrics:
            if not metric.success and metric.error_type:
                error_counts[metric.error_type] += 1
        return dict(error_counts)
    
    def reset(self):
        """Reset all metrics."""
        self.metrics = []
        self.counters = defaultdict(int)
        self.timers = defaultdict(list)


# Global metrics collector instance
_metrics_collector = MetricsCollector()


def get_metrics_collector() -> MetricsCollector:
    """Get global metrics collector instance."""
    return _metrics_collector


