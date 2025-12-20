"""Structured JSON logging configuration."""
import logging
import json
from datetime import datetime
from typing import Dict, Any, Optional


class JSONFormatter(logging.Formatter):
    """Custom formatter for structured JSON logs."""
    
    def format(self, record: logging.LogRecord) -> str:
        """Format log record as JSON."""
        log_data: Dict[str, Any] = {
            "timestamp": datetime.utcnow().isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        
        # Add job_id if present
        if hasattr(record, "job_id"):
            log_data["job_id"] = record.job_id
        
        # Add stage if present
        if hasattr(record, "stage"):
            log_data["stage"] = record.stage
        
        # Add exception info if present
        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)
        
        # Add extra fields
        for key, value in record.__dict__.items():
            if key not in ['name', 'msg', 'args', 'created', 'filename', 'funcName', 
                          'levelname', 'levelno', 'lineno', 'module', 'msecs', 'message', 
                          'pathname', 'process', 'processName', 'relativeCreated', 'thread', 
                          'threadName', 'exc_info', 'exc_text', 'stack_info', 'job_id', 'stage']:
                if not key.startswith('_'):
                    log_data[key] = value
        
        return json.dumps(log_data)


def setup_logging(
    log_level: str = "INFO",
    json_format: bool = True,
    job_id: Optional[str] = None,
    stage: Optional[str] = None
):
    """
    Setup logging configuration.
    
    Args:
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        json_format: Whether to use JSON formatting
        job_id: Optional job ID to include in all logs
        stage: Optional stage to include in all logs
    """
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, log_level.upper()))
    
    # Remove existing handlers
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)
    
    # Create console handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(getattr(logging, log_level.upper()))
    
    # Set formatter
    if json_format:
        formatter = JSONFormatter()
    else:
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
    console_handler.setFormatter(formatter)
    
    root_logger.addHandler(console_handler)
    
    # Add job_id and stage to all log records if provided
    if job_id or stage:
        old_factory = logging.getLogRecordFactory()
        
        def record_factory(*args, **kwargs):
            record = old_factory(*args, **kwargs)
            if job_id:
                record.job_id = job_id
            if stage:
                record.stage = stage
            return record
        
        logging.setLogRecordFactory(record_factory)
    
    return root_logger


def get_logger(name: str, job_id: Optional[str] = None, stage: Optional[str] = None) -> logging.Logger:
    """
    Get logger with optional job_id and stage context.
    
    Args:
        name: Logger name
        job_id: Optional job ID for context
        stage: Optional stage for context
    
    Returns:
        Logger instance
    """
    logger = logging.getLogger(name)
    
    # Add job_id and stage to log adapter
    if job_id or stage:
        class ContextAdapter(logging.LoggerAdapter):
            def process(self, msg, kwargs):
                if self.extra.get('job_id'):
                    kwargs.setdefault('extra', {})['job_id'] = self.extra['job_id']
                if self.extra.get('stage'):
                    kwargs.setdefault('extra', {})['stage'] = self.extra['stage']
                return msg, kwargs
        
        extra = {}
        if job_id:
            extra['job_id'] = job_id
        if stage:
            extra['stage'] = stage
        
        logger = ContextAdapter(logger, extra)
    
    return logger

