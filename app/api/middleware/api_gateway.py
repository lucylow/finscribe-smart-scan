"""
API Gateway with rate limiting, authentication, and usage tracking
"""
import time
import hashlib
import json
from datetime import datetime
from typing import Optional, Dict, Any
from fastapi import Request, HTTPException, status, Header
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import logging

logger = logging.getLogger(__name__)

try:
    import redis
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False
    logger.warning("Redis not available, API gateway will use in-memory rate limiting")


class APIKeyAuth(HTTPBearer):
    """API Key authentication"""
    
    def __init__(self, auto_error: bool = True):
        super(APIKeyAuth, self).__init__(auto_error=auto_error)
        self.redis_client = None
        if REDIS_AVAILABLE:
            try:
                import os
                self.redis_client = redis.Redis(
                    host=os.getenv("REDIS_HOST", "localhost"),
                    port=int(os.getenv("REDIS_PORT", "6379")),
                    db=int(os.getenv("REDIS_DB", "0")),
                    decode_responses=True
                )
                self.redis_client.ping()
            except Exception as e:
                logger.warning(f"Redis connection failed: {e}")
    
    async def __call__(self, request: Request) -> Optional[Dict[str, Any]]:
        # Try to get API key from header
        api_key = request.headers.get("X-API-Key") or request.headers.get("Authorization")
        
        if api_key:
            # Remove "Bearer " prefix if present
            if api_key.startswith("Bearer "):
                api_key = api_key[7:]
            
            # Validate API key
            tenant_info = self.validate_api_key(api_key)
            if tenant_info:
                request.state.tenant_id = tenant_info["tenant_id"]
                request.state.api_key = api_key
                request.state.tenant_info = tenant_info
                return tenant_info
        
        # If no API key, check for user session (web interface)
        # This would integrate with your auth system
        return None
    
    def validate_api_key(self, api_key: str) -> Optional[Dict[str, Any]]:
        """Validate API key and return tenant info"""
        # Check Redis cache first
        if self.redis_client:
            cached = self.redis_client.get(f"api_key:{api_key}")
            if cached:
                return json.loads(cached)
        
        # In production, query database
        # For now, use a simple lookup
        tenant_info = self._validate_api_key_in_db(api_key)
        
        if tenant_info and self.redis_client:
            # Cache for 5 minutes
            self.redis_client.setex(
                f"api_key:{api_key}",
                300,
                json.dumps(tenant_info)
            )
        
        return tenant_info
    
    def _validate_api_key_in_db(self, api_key: str) -> Optional[Dict[str, Any]]:
        """Validate API key in database (placeholder)"""
        # This should query the APIKey table
        # For now, return None (would need database session)
        return None


class APIGateway:
    """API Gateway with rate limiting and tracking"""
    
    def __init__(self, redis_host: str = "localhost", redis_port: int = 6379, redis_db: int = 0):
        self.redis_client = None
        self.use_redis = REDIS_AVAILABLE
        
        if self.use_redis:
            try:
                self.redis_client = redis.Redis(
                    host=redis_host,
                    port=redis_port,
                    db=redis_db,
                    decode_responses=True
                )
                self.redis_client.ping()
            except Exception as e:
                logger.warning(f"Redis connection failed: {e}")
                self.use_redis = False
        
        self.rate_limit_window = 3600  # 1 hour in seconds
        self.default_rate_limit = 1000  # Default requests per hour
    
    def rate_limit(self, tenant_id: str, endpoint: str) -> tuple[bool, Dict[str, Any]]:
        """Check and enforce rate limits"""
        if not self.use_redis or not self.redis_client:
            # No rate limiting without Redis
            return True, {"limit": self.default_rate_limit, "remaining": self.default_rate_limit}
        
        # Use sliding window for rate limiting
        current_hour = int(time.time() // 3600)
        key = f"ratelimit:{tenant_id}:{endpoint}:{current_hour}"
        
        # Get current count
        current = self.redis_client.get(key)
        if current is None:
            current = 0
        else:
            current = int(current)
        
        # Get tenant's rate limit (would query from database)
        limit = self._get_tenant_rate_limit(tenant_id)
        
        if current >= limit:
            return False, {
                "limit": limit,
                "remaining": 0,
                "reset_at": (current_hour + 1) * 3600
            }
        
        # Increment counter
        pipeline = self.redis_client.pipeline()
        pipeline.incr(key)
        pipeline.expire(key, self.rate_limit_window)
        pipeline.execute()
        
        return True, {
            "limit": limit,
            "remaining": limit - current - 1,
            "reset_at": (current_hour + 1) * 3600
        }
    
    def track_api_usage(self, tenant_id: str, endpoint: str, processing_time_ms: int, status_code: int = 200):
        """Track API usage for analytics and billing"""
        if not self.use_redis or not self.redis_client:
            return
        
        usage_event = {
            "tenant_id": tenant_id,
            "endpoint": endpoint,
            "processing_time_ms": processing_time_ms,
            "status_code": status_code,
            "timestamp": datetime.utcnow().isoformat(),
            "size": 1  # 1 API call
        }
        
        try:
            # Store in Redis stream
            self.redis_client.xadd("api_usage_events", usage_event, maxlen=10000)
            
            # Update monthly counters
            month_key = datetime.now().strftime("%Y-%m")
            usage_key = f"api_usage_monthly:{tenant_id}:{month_key}"
            self.redis_client.hincrby(usage_key, endpoint, 1)
            self.redis_client.hincrby(usage_key, "total", 1)
            self.redis_client.expire(usage_key, 90 * 24 * 3600)  # 90 days
            
            # Update performance metrics
            perf_key = f"performance:{tenant_id}:{endpoint}"
            self.redis_client.rpush(perf_key, processing_time_ms)
            self.redis_client.ltrim(perf_key, -1000, -1)  # Keep last 1000 samples
            self.redis_client.expire(perf_key, 7 * 24 * 3600)  # 7 days
            
        except Exception as e:
            logger.error(f"Error tracking API usage: {e}", exc_info=True)
    
    def _get_tenant_rate_limit(self, tenant_id: str) -> int:
        """Get tenant's rate limit (placeholder)"""
        # In production, query from database based on subscription tier
        # For now, return default
        return self.default_rate_limit
    
    def get_usage_stats(self, tenant_id: str, month: Optional[str] = None) -> Dict[str, Any]:
        """Get API usage statistics for a tenant"""
        if not month:
            month = datetime.now().strftime("%Y-%m")
        
        if not self.use_redis or not self.redis_client:
            return {}
        
        usage_key = f"api_usage_monthly:{tenant_id}:{month}"
        stats = self.redis_client.hgetall(usage_key)
        
        return {
            k: int(v) if v.isdigit() else v
            for k, v in stats.items()
        }


# Middleware function for FastAPI
async def api_gateway_middleware(request: Request, call_next):
    """FastAPI middleware for API gateway functionality"""
    gateway = APIGateway()
    
    # Skip rate limiting for certain paths
    skip_paths = ["/health", "/ready", "/docs", "/openapi.json", "/redoc"]
    if any(request.url.path.startswith(path) for path in skip_paths):
        return await call_next(request)
    
    # Get tenant ID from request state (set by auth middleware)
    tenant_id = getattr(request.state, "tenant_id", None)
    
    if tenant_id:
        endpoint = request.url.path
        method = request.method
        endpoint_key = f"{method}:{endpoint}"
        
        # Check rate limit
        allowed, rate_info = gateway.rate_limit(tenant_id, endpoint_key)
        
        if not allowed:
            return HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail={
                    "error": "Rate limit exceeded",
                    "message": f"Too many requests to {endpoint}",
                    "limit": rate_info["limit"],
                    "reset_at": rate_info["reset_at"]
                },
                headers={
                    "X-RateLimit-Limit": str(rate_info["limit"]),
                    "X-RateLimit-Remaining": "0",
                    "X-RateLimit-Reset": str(rate_info["reset_at"]),
                    "Retry-After": str(rate_info["reset_at"] - int(time.time()))
                }
            )
        
        # Process request
        start_time = time.time()
        response = await call_next(request)
        processing_time_ms = int((time.time() - start_time) * 1000)
        
        # Track usage
        gateway.track_api_usage(tenant_id, endpoint_key, processing_time_ms, response.status_code)
        
        # Add rate limit headers
        response.headers["X-RateLimit-Limit"] = str(rate_info["limit"])
        response.headers["X-RateLimit-Remaining"] = str(rate_info["remaining"])
        response.headers["X-RateLimit-Reset"] = str(rate_info["reset_at"])
        response.headers["X-Processing-Time"] = f"{processing_time_ms}ms"
        
        return response
    else:
        # No tenant ID, proceed without rate limiting
        # (web interface, public endpoints, etc.)
        return await call_next(request)


