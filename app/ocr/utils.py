"""
Utility functions for OCR backends: retries, caching, and error handling.
"""
import time
import logging
from typing import Callable, Any, Optional
from functools import wraps

logger = logging.getLogger(__name__)


def with_retries(
    fn: Callable,
    retries: int = 3,
    backoff: int = 2,
    exceptions: tuple = (Exception,)
) -> Any:
    """
    Retry a function call with exponential backoff.
    
    Args:
        fn: Function to call (should be a callable that takes no args)
        retries: Number of retry attempts
        backoff: Base for exponential backoff (wait time = backoff^attempt)
        exceptions: Tuple of exception types to catch and retry on
        
    Returns:
        Result of function call
        
    Raises:
        Last exception if all retries fail
    """
    last_exception = None
    
    for attempt in range(retries):
        try:
            return fn()
        except exceptions as e:
            last_exception = e
            if attempt < retries - 1:
                wait_time = backoff ** attempt
                logger.warning(
                    f"Function call failed (attempt {attempt + 1}/{retries}): {e}. "
                    f"Retrying in {wait_time}s..."
                )
                time.sleep(wait_time)
            else:
                logger.error(f"Function call failed after {retries} attempts: {e}")
                raise
    
    if last_exception:
        raise last_exception
    else:
        raise Exception(f"Function call failed after {retries} attempts")


def retry_on_failure(
    retries: int = 3,
    backoff: int = 2,
    exceptions: tuple = (Exception,)
):
    """
    Decorator to retry a function on failure.
    
    Args:
        retries: Number of retry attempts
        backoff: Base for exponential backoff
        exceptions: Tuple of exception types to catch and retry on
        
    Example:
        @retry_on_failure(retries=3, backoff=2)
        def my_function():
            ...
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            last_exception = None
            
            for attempt in range(retries):
                try:
                    return func(*args, **kwargs)
                except exceptions as e:
                    last_exception = e
                    if attempt < retries - 1:
                        wait_time = backoff ** attempt
                        logger.warning(
                            f"{func.__name__} failed (attempt {attempt + 1}/{retries}): {e}. "
                            f"Retrying in {wait_time}s..."
                        )
                        time.sleep(wait_time)
                    else:
                        logger.error(f"{func.__name__} failed after {retries} attempts: {e}")
                        raise
            
            if last_exception:
                raise last_exception
            else:
                raise Exception(f"{func.__name__} failed after {retries} attempts")
        
        return wrapper
    return decorator

