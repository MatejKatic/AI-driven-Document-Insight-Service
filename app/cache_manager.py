"""
Cache Manager for Document Text Extraction with Performance Monitoring
Supports both file-based cache and Redis (configurable)
Uses content-based hashing for cross-session cache hits
"""
import json
import hashlib
import os
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, Optional, Any
import pickle
import time
from app.config import config
from app.performance import performance_monitor, CachePerformanceTracker, track_performance

try:
    import redis
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False


class CacheManager:
    """Manages caching of extracted text from documents with performance monitoring"""
    
    def __init__(self, cache_type: str = "file"):
        """
        Initialize cache manager with performance tracking
        
        Args:
            cache_type: 'file' for file-based cache, 'redis' for Redis cache
        """
        init_start = time.time()
        
        self.cache_type = cache_type
        self.cache_dir = Path("cache")
        self.cache_dir.mkdir(exist_ok=True)
        
        self.redis_client = None
        if cache_type == "redis" and REDIS_AVAILABLE:
            try:
                redis_start = time.time()
                self.redis_client = redis.Redis(
                    host=os.getenv("REDIS_HOST", "localhost"),
                    port=int(os.getenv("REDIS_PORT", 6379)),
                    db=int(os.getenv("REDIS_DB", 0)),
                    decode_responses=False
                )
                self.redis_client.ping()
                self.cache_type = "redis"
                
                redis_init_time = (time.time() - redis_start) * 1000
                performance_monitor.record_metric("redis_init_time_ms", redis_init_time)
                
                print(f"✅ Redis cache initialized in {redis_init_time:.2f}ms")
            except Exception as e:
                print(f"⚠️ Redis not available, falling back to file cache: {e}")
                self.cache_type = "file"
        
        self.stats = {
            "hits": 0,
            "misses": 0,
            "saves": 0
        }
        
        self._update_cache_size_metrics()
        
        init_time = (time.time() - init_start) * 1000
        performance_monitor.record_metric(
            "cache_manager_init_time_ms",
            init_time,
            {"cache_type": self.cache_type}
        )
    
    def _get_content_hash(self, file_path: str) -> str:
        """
        Generate hash based on file content only (not path) with performance tracking
        This enables cross-session cache hits for identical files
        """
        hash_start = time.time()
        hash_md5 = hashlib.md5()
        
        try:
            if os.path.exists(file_path):
                with open(file_path, "rb") as f:
                    bytes_read = 0
                    for chunk in iter(lambda: f.read(4096), b""):
                        hash_md5.update(chunk)
                        bytes_read += len(chunk)
                
                file_size = os.path.getsize(file_path)
                
                content_string = f"{hash_md5.hexdigest()}_{file_size}"
            else:
                content_string = file_path
            
            final_hash = hashlib.sha256(content_string.encode()).hexdigest()[:32]
            
            hash_time = (time.time() - hash_start) * 1000
            performance_monitor.record_metric(
                "cache_hash_generation_ms",
                hash_time
            )
            
            return final_hash
            
        except Exception as e:
            print(f"Error hashing file {file_path}: {e}")
            return hashlib.sha256(str(file_path).encode()).hexdigest()[:32]
    
    def _get_cache_key(self, file_path: str, method: str = "") -> str:
        """
        Generate cache key based on content hash
        This ensures identical files get the same cache key regardless of path
        """
        content_hash = self._get_content_hash(file_path)
        
        filename = Path(file_path).name if os.path.exists(file_path) else file_path
        print(f"🔑 Cache key for {filename}: content_{content_hash[:8]}...")
        
        return f"doc_text_content_{content_hash}"
    
    def get(self, file_path: str, method: str = "") -> Optional[Dict[str, Any]]:
        """
        Get cached extraction result based on content with performance tracking
        
        Args:
            file_path: Path to the document
            method: Extraction method used (optional, ignored for content-based cache)
            
        Returns:
            Cached result or None if not found/expired
        """
        get_start = time.time()
        cache_key = self._get_cache_key(file_path, method)
        
        if self.cache_type == "redis" and self.redis_client:
            result = self._get_from_redis(cache_key)
        else:
            result = self._get_from_file(cache_key)
        
        get_duration = time.time() - get_start
        
        CachePerformanceTracker.track_cache_operation(
            "get",
            result is not None,
            get_duration
        )
        
        return result
    
    def set(self, file_path: str, result: Any, method: str = "", 
            ttl_hours: int = 24) -> bool:
        """
        Cache extraction result based on content with performance tracking
        
        Args:
            file_path: Path to the document
            result: Extraction result to cache (can be dict, list, or any serializable type)
            method: Extraction method used (stored but not used in key)
            ttl_hours: Time to live in hours
            
        Returns:
            Success status
        """
        set_start = time.time()
        cache_key = self._get_cache_key(file_path, method)
        
        if isinstance(result, dict):
            result_data = result
            result_method = method or result.get("method", "")
            result_size = len(json.dumps(result))
        elif isinstance(result, list):
            result_data = {"data": result, "type": "list"}
            result_method = method
            result_size = len(json.dumps(result))
        else:
            result_data = {"data": result, "type": type(result).__name__}
            result_method = method
            result_size = len(str(result))
        
        cache_data = {
            "result": result_data,
            "cached_at": datetime.now().isoformat(),
            "original_path": file_path,  # Store for reference
            "method": result_method,
            "expires_at": (datetime.now() + timedelta(hours=ttl_hours)).isoformat(),
            "content_hash": self._get_content_hash(file_path),
            "result_size_kb": result_size / 1024  # Track cached data size
        }
        
        if self.cache_type == "redis" and self.redis_client:
            success = self._set_to_redis(cache_key, cache_data, ttl_hours)
        else:
            success = self._set_to_file(cache_key, cache_data)
        
        set_duration = time.time() - set_start
        
        performance_monitor.record_metric(
            "cache_set_duration_ms",
            set_duration * 1000,
            {
                "cache_type": self.cache_type,
                "data_size_kb": cache_data["result_size_kb"],
                "ttl_hours": ttl_hours
            }
        )
        
        if success:
            self._update_cache_size_metrics()
        
        return success
    
    @track_performance("file_cache_get")
    def _get_from_file(self, cache_key: str) -> Optional[Any]:
        """Get from file-based cache with performance tracking"""
        cache_file = self.cache_dir / f"{cache_key}.json"
        
        if not cache_file.exists():
            self.stats["misses"] += 1
            return None
        
        try:
            read_start = time.time()
            with open(cache_file, 'r', encoding='utf-8') as f:
                cache_data = json.load(f)
            
            read_time = (time.time() - read_start) * 1000
            
            expires_at = datetime.fromisoformat(cache_data["expires_at"])
            if datetime.now() > expires_at:
                cache_file.unlink()
                self.stats["misses"] += 1
                
                performance_monitor.record_metric(
                    "cache_expired_entries",
                    1,
                    {"cache_key": cache_key[:20]}
                )
                
                return None
            
            self.stats["hits"] += 1
            original_path = cache_data.get('original_path', 'unknown')
            
            performance_monitor.record_metric(
                "file_cache_read_time_ms",
                read_time,
                {"file_size_kb": cache_file.stat().st_size / 1024}
            )
            
            print(f"📋 Cache hit! Using cached extraction (originally from: {Path(original_path).name})")
            
            result = cache_data["result"]
            if isinstance(result, dict) and result.get("type") == "list":
                return result["data"]
            elif isinstance(result, dict) and "type" in result and "data" in result:
                return result["data"]
            return result
            
        except Exception as e:
            print(f"Cache read error: {e}")
            self.stats["misses"] += 1
            return None
    
    @track_performance("file_cache_set")
    def _set_to_file(self, cache_key: str, cache_data: Dict[str, Any]) -> bool:
        """Save to file-based cache with performance tracking"""
        cache_file = self.cache_dir / f"{cache_key}.json"
        
        try:
            write_start = time.time()
            with open(cache_file, 'w', encoding='utf-8') as f:
                json.dump(cache_data, f, ensure_ascii=False, indent=2)
            
            write_time = (time.time() - write_start) * 1000
            file_size_kb = cache_file.stat().st_size / 1024
            
            self.stats["saves"] += 1
            
            performance_monitor.record_metric(
                "file_cache_write_time_ms",
                write_time,
                {"file_size_kb": file_size_kb}
            )
            
            print(f"💾 Cached extraction (content-based key: {cache_key[:20]}..., size: {file_size_kb:.2f}KB)")
            return True
            
        except Exception as e:
            print(f"Cache write error: {e}")
            return False
    
    @track_performance("redis_cache_get")
    def _get_from_redis(self, cache_key: str) -> Optional[Any]:
        """Get from Redis cache with performance tracking"""
        try:
            cached = self.redis_client.get(cache_key)
            if cached:
                cache_data = pickle.loads(cached)
                self.stats["hits"] += 1
                original_path = cache_data.get('original_path', 'unknown')
                
                performance_monitor.record_metric(
                    "redis_cache_data_size_kb",
                    len(cached) / 1024
                )
                
                print(f"📋 Redis cache hit! (originally from: {Path(original_path).name})")
                
                result = cache_data["result"]
                if isinstance(result, dict) and result.get("type") == "list":
                    return result["data"]
                elif isinstance(result, dict) and "type" in result and "data" in result:
                    return result["data"]
                return result
            else:
                self.stats["misses"] += 1
                return None
        except Exception as e:
            print(f"Redis get error: {e}")
            self.stats["misses"] += 1
            return None
    
    @track_performance("redis_cache_set")
    def _set_to_redis(self, cache_key: str, cache_data: Dict[str, Any], 
                      ttl_hours: int) -> bool:
        """Save to Redis cache with performance tracking"""
        try:
            serialized = pickle.dumps(cache_data)
            data_size_kb = len(serialized) / 1024
            
            self.redis_client.setex(
                cache_key,
                timedelta(hours=ttl_hours),
                serialized
            )
            
            self.stats["saves"] += 1
            
            performance_monitor.record_metric(
                "redis_cache_data_size_kb",
                data_size_kb,
                {"ttl_hours": ttl_hours}
            )
            
            print(f"💾 Redis cached (content-based key: {cache_key[:20]}..., size: {data_size_kb:.2f}KB)")
            return True
        except Exception as e:
            print(f"Redis set error: {e}")
            return False
    
    def _update_cache_size_metrics(self):
        """Update cache size metrics"""
        try:
            if self.cache_type == "file":
                total_size = 0
                file_count = 0
                
                for cache_file in self.cache_dir.glob("*.json"):
                    total_size += cache_file.stat().st_size
                    file_count += 1
                
                performance_monitor.record_metric(
                    "cache_total_size_mb",
                    total_size / (1024 * 1024),
                    {"file_count": file_count}
                )
            
            elif self.cache_type == "redis" and self.redis_client:
                info = self.redis_client.info("memory")
                used_memory_mb = info.get("used_memory", 0) / (1024 * 1024)
                
                performance_monitor.record_metric(
                    "redis_memory_usage_mb",
                    used_memory_mb
                )
        except Exception as e:
            print(f"Error updating cache size metrics: {e}")
    
    @track_performance("cache_clear_expired")
    def clear_expired(self):
        """Clear expired entries from file cache with performance tracking"""
        if self.cache_type == "file":
            clear_start = time.time()
            cleared = 0
            
            for cache_file in self.cache_dir.glob("*.json"):
                try:
                    with open(cache_file, 'r') as f:
                        cache_data = json.load(f)
                    
                    expires_at = datetime.fromisoformat(cache_data["expires_at"])
                    if datetime.now() > expires_at:
                        cache_file.unlink()
                        cleared += 1
                except:
                    pass
            
            clear_time = (time.time() - clear_start) * 1000
            
            performance_monitor.record_metric(
                "cache_clear_expired_time_ms",
                clear_time,
                {"cleared_count": cleared}
            )
            
            if cleared > 0:
                print(f"🧹 Cleared {cleared} expired cache entries in {clear_time:.2f}ms")
                self._update_cache_size_metrics()
    
    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics with performance metrics"""
        total_requests = self.stats["hits"] + self.stats["misses"]
        hit_rate = (self.stats["hits"] / total_requests * 100) if total_requests > 0 else 0
        
        cache_perf = CachePerformanceTracker.get_cache_performance()
        
        return {
            "cache_type": self.cache_type,
            "hits": self.stats["hits"],
            "misses": self.stats["misses"],
            "saves": self.stats["saves"],
            "hit_rate": f"{hit_rate:.1f}%",
            "total_requests": total_requests,
            "performance": {
                "avg_hit_time_ms": cache_perf["avg_hit_time_ms"],
                "avg_miss_time_ms": cache_perf["avg_miss_time_ms"],
                "speedup_factor": cache_perf["cache_speedup"]
            }
        }
    
    @track_performance("cache_clear_all")
    def clear_all(self):
        """Clear all cache entries with performance tracking"""
        clear_start = time.time()
        
        if self.cache_type == "file":
            cleared = 0
            for cache_file in self.cache_dir.glob("*.json"):
                cache_file.unlink()
                cleared += 1
            print(f"🧹 Cleared {cleared} file cache entries")
            
        elif self.cache_type == "redis" and self.redis_client:
            cleared = 0
            for key in self.redis_client.scan_iter("doc_text_content_*"):
                self.redis_client.delete(key)
                cleared += 1
            print(f"🧹 Cleared {cleared} Redis cache entries")
        
        clear_time = (time.time() - clear_start) * 1000
        
        performance_monitor.record_metric(
            "cache_clear_all_time_ms",
            clear_time,
            {"cache_type": self.cache_type}
        )
        
        self.stats = {
            "hits": 0,
            "misses": 0,
            "saves": 0
        }
        
        self._update_cache_size_metrics()


cache_manager = CacheManager(cache_type=os.getenv("CACHE_TYPE", "file"))