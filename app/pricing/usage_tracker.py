"""
Usage Tracking & Analytics for SaaS billing and monitoring
"""
import time
import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from dataclasses import dataclass, asdict
from decimal import Decimal
import logging

logger = logging.getLogger(__name__)

try:
    import redis
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False
    logger.warning("Redis not available, usage tracking will use in-memory storage")


@dataclass
class UsageEvent:
    """Usage event for tracking"""
    tenant_id: str
    user_id: Optional[str]
    event_type: str  # document_processed, api_call, storage_used
    resource: str  # documents, api_requests, storage_gb
    quantity: float
    metadata: Dict
    timestamp: datetime = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.utcnow()


class UsageTracker:
    """Track usage for billing and analytics"""
    
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
                # Test connection
                self.redis_client.ping()
                logger.info("Redis connection established for usage tracking")
            except Exception as e:
                logger.warning(f"Redis connection failed: {e}, using in-memory storage")
                self.use_redis = False
        
        # Fallback in-memory storage
        if not self.use_redis:
            self._in_memory_store = {}
            logger.info("Using in-memory storage for usage tracking")
        
        self.rate_limit_window = 3600  # 1 hour in seconds
    
    def track_usage(self, event: UsageEvent):
        """Track a usage event"""
        try:
            if self.use_redis and self.redis_client:
                self._track_redis(event)
            else:
                self._track_memory(event)
        except Exception as e:
            logger.error(f"Error tracking usage: {e}", exc_info=True)
    
    def _track_redis(self, event: UsageEvent):
        """Track usage in Redis"""
        month_key = datetime.now().strftime("%Y-%m")
        
        # Increment monthly counters
        usage_key = f"usage_monthly:{event.tenant_id}:{month_key}"
        self.redis_client.hincrbyfloat(usage_key, event.resource, event.quantity)
        self.redis_client.expire(usage_key, 90 * 24 * 3600)  # Expire after 90 days
        
        # Store event for analytics (Redis Stream)
        event_data = {
            "tenant_id": event.tenant_id,
            "user_id": event.user_id or "",
            "event_type": event.event_type,
            "resource": event.resource,
            "quantity": str(event.quantity),
            "metadata": json.dumps(event.metadata),
            "timestamp": event.timestamp.isoformat()
        }
        
        try:
            self.redis_client.xadd("usage_events", event_data, maxlen=10000)
        except Exception as e:
            logger.debug(f"Could not add to Redis stream: {e}")
        
        # Update real-time dashboard
        self._update_realtime_dashboard(event)
    
    def _track_memory(self, event: UsageEvent):
        """Track usage in memory (fallback)"""
        month_key = datetime.now().strftime("%Y-%m")
        tenant_month_key = f"{event.tenant_id}:{month_key}"
        
        if tenant_month_key not in self._in_memory_store:
            self._in_memory_store[tenant_month_key] = {}
        
        if event.resource not in self._in_memory_store[tenant_month_key]:
            self._in_memory_store[tenant_month_key][event.resource] = 0.0
        
        self._in_memory_store[tenant_month_key][event.resource] += event.quantity
        
        # Keep only last 3 months
        self._cleanup_old_memory_records()
    
    def get_tenant_usage(self, tenant_id: str, month: Optional[str] = None) -> Dict[str, float]:
        """Get usage statistics for a tenant"""
        if not month:
            month = datetime.now().strftime("%Y-%m")
        
        if self.use_redis and self.redis_client:
            key = f"usage_monthly:{tenant_id}:{month}"
            usage_data = self.redis_client.hgetall(key)
            return {resource: float(value) for resource, value in usage_data.items()}
        else:
            tenant_month_key = f"{tenant_id}:{month}"
            return self._in_memory_store.get(tenant_month_key, {})
    
    def check_quota(self, tenant_id: str, resource: str, requested_amount: float = 1, limits: Dict[str, int] = None) -> Dict:
        """Check if tenant has quota available"""
        limits = limits or {}
        
        if resource not in limits or limits[resource] is None:
            return {"has_quota": True, "remaining": None, "limit": None}
        
        current_usage = self.get_tenant_usage(tenant_id).get(resource, 0)
        limit = limits[resource]
        remaining = max(0, limit - current_usage)
        
        return {
            "has_quota": current_usage + requested_amount <= limit,
            "remaining": remaining,
            "limit": limit,
            "current_usage": current_usage
        }
    
    def generate_usage_report(self, tenant_id: str, start_date: datetime, end_date: datetime) -> Dict:
        """Generate detailed usage report for a period"""
        # Get all months in range
        months = []
        current = start_date.replace(day=1)
        while current <= end_date:
            months.append(current.strftime("%Y-%m"))
            if current.month == 12:
                current = current.replace(year=current.year + 1, month=1)
            else:
                current = current.replace(month=current.month + 1)
        
        # Aggregate usage by resource
        usage_by_resource = {}
        usage_by_day = {}
        
        for month in months:
            month_usage = self.get_tenant_usage(tenant_id, month)
            for resource, quantity in month_usage.items():
                if resource not in usage_by_resource:
                    usage_by_resource[resource] = 0.0
                usage_by_resource[resource] += quantity
        
        # Calculate costs (would need subscription manager)
        costs = {}
        total_cost = 0.0
        
        return {
            "tenant_id": tenant_id,
            "period": {
                "start": start_date.isoformat(),
                "end": end_date.isoformat()
            },
            "usage_summary": usage_by_resource,
            "daily_breakdown": usage_by_day,
            "cost_breakdown": costs,
            "total_cost": total_cost,
            "currency": "USD"
        }
    
    def create_usage_alert(self, tenant_id: str, resource: str, threshold_percent: float = 80, limits: Dict[str, int] = None) -> Optional[Dict]:
        """Create alert for high usage"""
        limits = limits or {}
        
        if resource not in limits or limits[resource] is None:
            return None
        
        current_usage = self.get_tenant_usage(tenant_id).get(resource, 0)
        limit = limits[resource]
        usage_percent = (current_usage / limit) * 100 if limit > 0 else 0
        
        if usage_percent >= threshold_percent:
            alert_data = {
                "tenant_id": tenant_id,
                "resource": resource,
                "current_usage": current_usage,
                "limit": limit,
                "usage_percent": usage_percent,
                "threshold": threshold_percent,
                "timestamp": datetime.utcnow().isoformat()
            }
            
            # Store alert
            if self.use_redis and self.redis_client:
                alert_key = f"alert:{tenant_id}:{resource}"
                self.redis_client.setex(
                    alert_key,
                    86400,  # 24 hours
                    json.dumps(alert_data)
                )
            
            logger.info(f"Usage alert for tenant {tenant_id}: {resource} at {usage_percent:.1f}%")
            return alert_data
        
        return None
    
    def _update_realtime_dashboard(self, event: UsageEvent):
        """Update real-time dashboard counters"""
        if not (self.use_redis and self.redis_client):
            return
        
        dashboard_key = f"dashboard_realtime:{event.tenant_id}"
        
        # Increment counters
        pipeline = self.redis_client.pipeline()
        pipeline.hincrbyfloat(dashboard_key, f"{event.resource}_today", event.quantity)
        pipeline.hincrbyfloat(dashboard_key, f"{event.resource}_this_hour", event.quantity)
        pipeline.hincrby(dashboard_key, "total_events_today", 1)
        pipeline.execute()
        
        # Set expiry for hourly counter
        expire_at = datetime.now().replace(minute=0, second=0, microsecond=0) + timedelta(hours=1)
        pipeline.expireat(f"{dashboard_key}:this_hour", int(expire_at.timestamp()))
    
    def _cleanup_old_memory_records(self):
        """Clean up old in-memory records (keep only last 3 months)"""
        if not hasattr(self, '_in_memory_store'):
            return
        
        cutoff_month = (datetime.now() - timedelta(days=90)).strftime("%Y-%m")
        keys_to_delete = [
            key for key in self._in_memory_store.keys()
            if key.split(":")[1] < cutoff_month
        ]
        for key in keys_to_delete:
            del self._in_memory_store[key]
    
    def get_realtime_stats(self, tenant_id: str) -> Dict:
        """Get real-time usage statistics"""
        if self.use_redis and self.redis_client:
            dashboard_key = f"dashboard_realtime:{tenant_id}"
            stats = self.redis_client.hgetall(dashboard_key)
            return {k: float(v) if v.replace('.', '', 1).isdigit() else int(v) for k, v in stats.items()}
        else:
            return {}


