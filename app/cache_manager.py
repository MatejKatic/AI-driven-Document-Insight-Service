"""
Cache Manager for Document Text Extraction
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
from app.config import config

# Try to import Redis, but don't fail if not available
try:
    import redis
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False


class CacheManager:
    """Manages caching of extracted text from documents"""
    
    def __init__(self, cache_type: str = "file"):
        """
        Initialize cache manager
        
        Args:
            cache_type: 'file' for file-based cache, 'redis' for Redis cache
        """
        self.cache_type = cache_type
        self.cache_dir = Path("cache")
        self.cache_dir.mkdir(exist_ok=True)
        
        # Redis configuration
        self.redis_client = None
        if cache_type == "redis" and REDIS_AVAILABLE:
            try:
                self.redis_client = redis.Redis(
                    host=os.getenv("REDIS_HOST", "localhost"),
                    port=int(os.getenv("REDIS_PORT", 6379)),
                    db=int(os.getenv("REDIS_DB", 0)),
                    decode_responses=False  # We'll handle encoding
                )
                # Test connection
                self.redis_client.ping()
                self.cache_type = "redis"
                print("✅ Redis cache initialized")
            except Exception as e:
                print(f"⚠️ Redis not available, falling back to file cache: {e}")
                self.cache_type = "file"
        
        # Cache statistics
        self.stats = {
            "hits": 0,
            "misses": 0,
            "saves": 0
        }
    
    def _get_content_hash(self, file_path: str) -> str:
        """
        Generate hash based on file content only (not path)
        This enables cross-session cache hits for identical files
        """
        hash_md5 = hashlib.md5()
        
        try:
            with open(file_path, "rb") as f:
                # Read file in chunks to handle large files
                for chunk in iter(lambda: f.read(4096), b""):
                    hash_md5.update(chunk)
            
            # Get file size for additional uniqueness
            file_size = os.path.getsize(file_path)
            
            # Create hash from content + size only (no path!)
            content_string = f"{hash_md5.hexdigest()}_{file_size}"
            return hashlib.sha256(content_string.encode()).hexdigest()[:32]
            
        except Exception as e:
            print(f"Error hashing file {file_path}: {e}")
            # Fallback to path-based hash if content reading fails
            return hashlib.sha256(str(file_path).encode()).hexdigest()[:32]
    
    def _get_cache_key(self, file_path: str, method: str = "") -> str:
        """
        Generate cache key based on content hash
        This ensures identical files get the same cache key regardless of path
        """
        content_hash = self._get_content_hash(file_path)
        
        # Debug logging to show cache key generation
        filename = Path(file_path).name
        print(f"🔑 Cache key for {filename}: content_{content_hash[:8]}...")
        
        return f"doc_text_content_{content_hash}"
    
    def get(self, file_path: str, method: str = "") -> Optional[Dict[str, Any]]:
        """
        Get cached extraction result based on content
        
        Args:
            file_path: Path to the document
            method: Extraction method used (optional, ignored for content-based cache)
            
        Returns:
            Cached result or None if not found/expired
        """
        cache_key = self._get_cache_key(file_path, method)
        
        if self.cache_type == "redis" and self.redis_client:
            return self._get_from_redis(cache_key)
        else:
            return self._get_from_file(cache_key)
    
    def set(self, file_path: str, result: Dict[str, Any], method: str = "", 
            ttl_hours: int = 24) -> bool:
        """
        Cache extraction result based on content
        
        Args:
            file_path: Path to the document
            result: Extraction result to cache
            method: Extraction method used (stored but not used in key)
            ttl_hours: Time to live in hours
            
        Returns:
            Success status
        """
        cache_key = self._get_cache_key(file_path, method)
        
        # Add metadata
        cache_data = {
            "result": result,
            "cached_at": datetime.now().isoformat(),
            "original_path": file_path,  # Store for reference
            "method": method or result.get("method", ""),
            "expires_at": (datetime.now() + timedelta(hours=ttl_hours)).isoformat(),
            "content_hash": self._get_content_hash(file_path)
        }
        
        if self.cache_type == "redis" and self.redis_client:
            return self._set_to_redis(cache_key, cache_data, ttl_hours)
        else:
            return self._set_to_file(cache_key, cache_data)
    
    def _get_from_file(self, cache_key: str) -> Optional[Dict[str, Any]]:
        """Get from file-based cache"""
        cache_file = self.cache_dir / f"{cache_key}.json"
        
        if not cache_file.exists():
            self.stats["misses"] += 1
            return None
        
        try:
            with open(cache_file, 'r', encoding='utf-8') as f:
                cache_data = json.load(f)
            
            # Check expiration
            expires_at = datetime.fromisoformat(cache_data["expires_at"])
            if datetime.now() > expires_at:
                # Expired, remove file
                cache_file.unlink()
                self.stats["misses"] += 1
                return None
            
            self.stats["hits"] += 1
            original_path = cache_data.get('original_path', 'unknown')
            print(f"📋 Cache hit! Using cached extraction (originally from: {Path(original_path).name})")
            return cache_data["result"]
            
        except Exception as e:
            print(f"Cache read error: {e}")
            self.stats["misses"] += 1
            return None
    
    def _set_to_file(self, cache_key: str, cache_data: Dict[str, Any]) -> bool:
        """Save to file-based cache"""
        cache_file = self.cache_dir / f"{cache_key}.json"
        
        try:
            with open(cache_file, 'w', encoding='utf-8') as f:
                json.dump(cache_data, f, ensure_ascii=False, indent=2)
            
            self.stats["saves"] += 1
            print(f"💾 Cached extraction (content-based key: {cache_key[:20]}...)")
            return True
            
        except Exception as e:
            print(f"Cache write error: {e}")
            return False
    
    def _get_from_redis(self, cache_key: str) -> Optional[Dict[str, Any]]:
        """Get from Redis cache"""
        try:
            cached = self.redis_client.get(cache_key)
            if cached:
                cache_data = pickle.loads(cached)
                self.stats["hits"] += 1
                original_path = cache_data.get('original_path', 'unknown')
                print(f"📋 Redis cache hit! (originally from: {Path(original_path).name})")
                return cache_data["result"]
            else:
                self.stats["misses"] += 1
                return None
        except Exception as e:
            print(f"Redis get error: {e}")
            self.stats["misses"] += 1
            return None
    
    def _set_to_redis(self, cache_key: str, cache_data: Dict[str, Any], 
                      ttl_hours: int) -> bool:
        """Save to Redis cache"""
        try:
            serialized = pickle.dumps(cache_data)
            self.redis_client.setex(
                cache_key,
                timedelta(hours=ttl_hours),
                serialized
            )
            self.stats["saves"] += 1
            print(f"💾 Redis cached (content-based key: {cache_key[:20]}...)")
            return True
        except Exception as e:
            print(f"Redis set error: {e}")
            return False
    
    def clear_expired(self):
        """Clear expired entries from file cache"""
        if self.cache_type == "file":
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
            
            if cleared > 0:
                print(f"🧹 Cleared {cleared} expired cache entries")
    
    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        total_requests = self.stats["hits"] + self.stats["misses"]
        hit_rate = (self.stats["hits"] / total_requests * 100) if total_requests > 0 else 0
        
        return {
            "cache_type": self.cache_type,
            "hits": self.stats["hits"],
            "misses": self.stats["misses"],
            "saves": self.stats["saves"],
            "hit_rate": f"{hit_rate:.1f}%",
            "total_requests": total_requests
        }
    
    def clear_all(self):
        """Clear all cache entries"""
        if self.cache_type == "file":
            for cache_file in self.cache_dir.glob("*.json"):
                cache_file.unlink()
            print("🧹 Cleared all file cache")
        elif self.cache_type == "redis" and self.redis_client:
            # Clear only our keys (with prefix)
            for key in self.redis_client.scan_iter("doc_text_content_*"):
                self.redis_client.delete(key)
            print("🧹 Cleared all Redis cache entries")
        
        # Reset statistics
        self.stats = {
            "hits": 0,
            "misses": 0,
            "saves": 0
        }


# Global cache manager instance
cache_manager = CacheManager(cache_type=os.getenv("CACHE_TYPE", "file"))