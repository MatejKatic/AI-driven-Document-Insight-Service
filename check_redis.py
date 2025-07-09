"""Check if Redis is available for caching"""
import os
import sys

def check_redis():
    print("🔍 Checking Redis availability...")
    print("=" * 50)
    
    try:
        import redis
        print("✅ Redis Python module installed")
    except ImportError:
        print("❌ Redis Python module NOT installed")
        print("   Install with: pip install redis")
        return False
    
    try:
        client = redis.Redis(
            host=os.getenv("REDIS_HOST", "localhost"),
            port=int(os.getenv("REDIS_PORT", 6379)),
            db=int(os.getenv("REDIS_DB", 0))
        )
        
        client.ping()
        print("✅ Redis server is running and accessible")
        
        info = client.info()
        print(f"   Version: {info.get('redis_version', 'Unknown')}")
        print(f"   Memory used: {info.get('used_memory_human', 'Unknown')}")
        
        client.set("test_key", "test_value", ex=60)
        value = client.get("test_key")
        client.delete("test_key")
        
        print("✅ Redis read/write test successful")
        
        print("\n📋 To use Redis caching, set in .env:")
        print("   CACHE_TYPE=redis")
        
        return True
        
    except Exception as e:
        print(f"❌ Redis server NOT available: {e}")
        print("\n📌 Redis is optional. The app uses file-based cache by default.")
        print("\nTo install Redis:")
        print("   Ubuntu/Debian: sudo apt-get install redis-server")
        print("   MacOS: brew install redis")
        print("   Windows: Download from https://redis.io/download")
        
        return False

if __name__ == "__main__":
    print("Redis Cache Checker")
    print("This tool checks if Redis is available for caching")
    print()
    
    if check_redis():
        print("\n✅ Redis is ready to use!")
    else:
        print("\n💡 File-based cache will be used instead (works great too!)")
    
    print("\nCurrent cache setting:")
    cache_type = os.getenv("CACHE_TYPE", "file")
    print(f"CACHE_TYPE={cache_type}")