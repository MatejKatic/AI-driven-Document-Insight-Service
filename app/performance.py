"""
Performance Monitoring Module
Provides comprehensive performance tracking and analysis capabilities
"""
import time
import psutil
import functools
from datetime import datetime
from typing import Dict, List, Optional
from collections import defaultdict, deque
import statistics
import asyncio
from contextlib import contextmanager
from app.config import config

class PerformanceMonitor:
    """Track and analyze performance metrics"""
    
    def __init__(self, max_history: int = None):
        self.max_history = max_history or config.PERFORMANCE_METRICS_MAX_HISTORY
        self.metrics = defaultdict(lambda: deque(maxlen=self.max_history))
        self.active_requests = 0
        self.total_requests = 0
        self.start_time = time.time()
        self.enabled = config.ENABLE_PERFORMANCE_MONITORING
        
    def record_metric(self, metric_name: str, value: float, metadata: Optional[dict] = None):
        """Record a performance metric"""
        if not self.enabled:
            return
            
        self.metrics[metric_name].append({
            "value": value,
            "timestamp": datetime.now().isoformat(),
            "metadata": metadata or {}
        })
        
        if config.PERFORMANCE_LOG_SLOW_REQUESTS and value > config.SLOW_REQUEST_THRESHOLD_MS:
            print(f"⚠️ Slow operation detected: {metric_name} took {value:.2f}ms")
            if metadata:
                print(f"   Metadata: {metadata}")
    
    def get_stats(self, metric_name: str) -> Dict:
        """Get statistics for a specific metric"""
        values = [m["value"] for m in self.metrics[metric_name]]
        
        if not values:
            return {
                "count": 0,
                "mean": 0,
                "min": 0,
                "max": 0,
                "median": 0,
                "std_dev": 0,
                "percentile_95": 0,
                "percentile_99": 0
            }
        
        sorted_values = sorted(values)
        count = len(values)
        
        return {
            "count": count,
            "mean": statistics.mean(values),
            "min": min(values),
            "max": max(values),
            "median": statistics.median(values),
            "std_dev": statistics.stdev(values) if count > 1 else 0,
            "percentile_95": sorted_values[int(count * 0.95)] if count > 0 else 0,
            "percentile_99": sorted_values[int(count * 0.99)] if count > 0 else 0,
            "recent_values": list(values[-10:])  # Last 10 values
        }
    
    def get_system_metrics(self) -> Dict:
        """Get current system metrics"""
        memory = psutil.virtual_memory()
        cpu_percent = psutil.cpu_percent(interval=0.1)
        
        warnings = []
        if cpu_percent > config.MAX_CPU_PERCENT:
            warnings.append(f"High CPU usage: {cpu_percent:.1f}%")
        
        if memory.percent > (config.MAX_MEMORY_MB / (memory.total / (1024 * 1024)) * 100):
            warnings.append(f"High memory usage: {memory.percent:.1f}%")
        
        return {
            "cpu_percent": cpu_percent,
            "memory_percent": memory.percent,
            "memory_available_mb": memory.available / (1024 * 1024),
            "memory_used_mb": memory.used / (1024 * 1024),
            "active_requests": self.active_requests,
            "total_requests": self.total_requests,
            "uptime_seconds": time.time() - self.start_time,
            "warnings": warnings
        }
    
    def get_all_metrics(self) -> Dict:
        """Get all performance metrics"""
        metrics = {}
        
        for metric_name in self.metrics:
            metrics[metric_name] = self.get_stats(metric_name)
        
        metrics["system"] = self.get_system_metrics()
        
        return metrics
    
    @contextmanager
    def track_request(self):
        """Context manager to track request metrics"""
        if not self.enabled:
            yield
            return
            
        self.active_requests += 1
        self.total_requests += 1
        start_time = time.time()
        
        try:
            yield
        finally:
            self.active_requests -= 1
            duration = time.time() - start_time
            self.record_metric("request_duration", duration * 1000)  # in ms

performance_monitor = PerformanceMonitor()

def track_performance(metric_name: str):
    """Decorator to track function performance"""
    def decorator(func):
        @functools.wraps(func)
        async def async_wrapper(*args, **kwargs):
            if not performance_monitor.enabled:
                return await func(*args, **kwargs)
                
            start_time = time.time()
            success = True
            error_type = None
            
            try:
                result = await func(*args, **kwargs)
                return result
            except Exception as e:
                success = False
                error_type = type(e).__name__
                raise
            finally:
                duration = (time.time() - start_time) * 1000  # Convert to ms
                performance_monitor.record_metric(
                    metric_name,
                    duration,
                    {
                        "success": success,
                        "error_type": error_type,
                        "function": func.__name__
                    }
                )
        
        @functools.wraps(func)
        def sync_wrapper(*args, **kwargs):
            if not performance_monitor.enabled:
                return func(*args, **kwargs)
                
            start_time = time.time()
            success = True
            error_type = None
            
            try:
                result = func(*args, **kwargs)
                return result
            except Exception as e:
                success = False
                error_type = type(e).__name__
                raise
            finally:
                duration = (time.time() - start_time) * 1000  # Convert to ms
                performance_monitor.record_metric(
                    metric_name,
                    duration,
                    {
                        "success": success,
                        "error_type": error_type,
                        "function": func.__name__
                    }
                )
        
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper
    
    return decorator

class CachePerformanceTracker:
    """Track cache-specific performance metrics"""
    
    @staticmethod
    def track_cache_operation(operation: str, hit: bool, duration: float):
        """Track cache operation performance"""
        if not performance_monitor.enabled:
            return
            
        metric_name = f"cache_{operation}_{'hit' if hit else 'miss'}"
        performance_monitor.record_metric(metric_name, duration * 1000)
    
    @staticmethod
    def get_cache_performance() -> Dict:
        """Get cache performance statistics"""
        hit_stats = performance_monitor.get_stats("cache_get_hit")
        miss_stats = performance_monitor.get_stats("cache_get_miss")
        
        total_gets = hit_stats["count"] + miss_stats["count"]
        hit_rate = (hit_stats["count"] / total_gets * 100) if total_gets > 0 else 0
        
        avg_speedup = 0
        if hit_stats["mean"] > 0 and miss_stats["mean"] > 0:
            avg_speedup = miss_stats["mean"] / hit_stats["mean"]
        
        return {
            "hit_rate": hit_rate,
            "total_gets": total_gets,
            "hits": hit_stats["count"],
            "misses": miss_stats["count"],
            "avg_hit_time_ms": hit_stats["mean"],
            "avg_miss_time_ms": miss_stats["mean"],
            "cache_speedup": avg_speedup,
            "time_saved_ms": (miss_stats["mean"] - hit_stats["mean"]) * hit_stats["count"] if hit_stats["count"] > 0 else 0
        }

def track_memory_usage(func):
    """Decorator to track memory usage of a function"""
    @functools.wraps(func)
    async def async_wrapper(*args, **kwargs):
        if not performance_monitor.enabled:
            return await func(*args, **kwargs)
            
        process = psutil.Process()
        mem_before = process.memory_info().rss / (1024 * 1024)  # MB
        
        result = await func(*args, **kwargs)
        
        mem_after = process.memory_info().rss / (1024 * 1024)  # MB
        mem_used = mem_after - mem_before
        
        performance_monitor.record_metric(
            f"memory_usage_{func.__name__}",
            mem_used,
            {
                "function": func.__name__,
                "mem_before_mb": mem_before,
                "mem_after_mb": mem_after
            }
        )
        
        return result
    
    @functools.wraps(func)
    def sync_wrapper(*args, **kwargs):
        if not performance_monitor.enabled:
            return func(*args, **kwargs)
            
        process = psutil.Process()
        mem_before = process.memory_info().rss / (1024 * 1024)  # MB
        
        result = func(*args, **kwargs)
        
        mem_after = process.memory_info().rss / (1024 * 1024)  # MB
        mem_used = mem_after - mem_before
        
        performance_monitor.record_metric(
            f"memory_usage_{func.__name__}",
            mem_used,
            {
                "function": func.__name__,
                "mem_before_mb": mem_before,
                "mem_after_mb": mem_after
            }
        )
        
        return result
    
    if asyncio.iscoroutinefunction(func):
        return async_wrapper
    else:
        return sync_wrapper

class BatchOperationTracker:
    """Track performance of batch operations"""
    
    def __init__(self, operation_name: str):
        self.operation_name = operation_name
        self.start_time = None
        self.items_processed = 0
        
    def __enter__(self):
        self.start_time = time.time()
        return self
        
    def __exit__(self, exc_type, exc_val, exc_tb):
        if not performance_monitor.enabled:
            return
            
        duration = (time.time() - self.start_time) * 1000
        
        performance_monitor.record_metric(
            f"batch_{self.operation_name}_duration_ms",
            duration,
            {
                "items_processed": self.items_processed,
                "items_per_second": (self.items_processed / (duration / 1000)) if duration > 0 else 0,
                "success": exc_type is None
            }
        )
    
    def increment(self, count: int = 1):
        """Increment the processed items counter"""
        self.items_processed += count

def get_optimization_suggestions() -> List[str]:
    """Get performance optimization suggestions based on metrics"""
    suggestions = []
    metrics = performance_monitor.get_all_metrics()
    
    cache_perf = CachePerformanceTracker.get_cache_performance()
    if cache_perf["hit_rate"] < 50:
        suggestions.append(
            f"Low cache hit rate ({cache_perf['hit_rate']:.1f}%). "
            "Consider increasing cache TTL or preloading common documents."
        )
    
    api_stats = metrics.get("deepseek_api_latency_ms", {})
    if api_stats.get("mean", 0) > 3000:
        suggestions.append(
            f"High API latency ({api_stats['mean']:.0f}ms average). "
            "Consider implementing request batching or using a faster model."
        )
    
    extraction_stats = metrics.get("text_extraction_time_ms", {})
    if extraction_stats.get("mean", 0) > 5000:
        suggestions.append(
            f"Slow text extraction ({extraction_stats['mean']:.0f}ms average). "
            "Consider using PyMuPDF for text PDFs and OCR only for scanned documents."
        )
    
    system = metrics.get("system", {})
    if system.get("cpu_percent", 0) > config.MAX_CPU_PERCENT:
        suggestions.append(
            f"High CPU usage ({system['cpu_percent']:.1f}%). "
            "Consider horizontal scaling or optimizing CPU-intensive operations."
        )
    
    if system.get("memory_percent", 0) > 80:
        suggestions.append(
            f"High memory usage ({system['memory_percent']:.1f}%). "
            "Consider implementing memory limits or optimizing memory-intensive operations."
        )
    
    return suggestions