import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

class Config:
    """Application configuration with performance settings"""
    
    # DeepSeek API
    DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY")
    DEEPSEEK_API_URL = "https://api.deepseek.com/v1/chat/completions"
    
    # File upload settings
    MAX_FILE_SIZE_MB = int(os.getenv("MAX_FILE_SIZE_MB", "10"))
    MAX_FILES_PER_UPLOAD = int(os.getenv("MAX_FILES_PER_UPLOAD", "5"))
    ALLOWED_EXTENSIONS = {'.pdf', '.png', '.jpg', '.jpeg', '.tiff', '.bmp'}
    
    # Session settings
    SESSION_EXPIRE_HOURS = int(os.getenv("SESSION_EXPIRE_HOURS", "24"))
    
    # Storage
    UPLOAD_DIR = Path("uploads")
    UPLOAD_DIR.mkdir(exist_ok=True)
    
    # Cache settings
    CACHE_TYPE = os.getenv("CACHE_TYPE", "file")  # "file" or "redis"
    CACHE_TTL_HOURS = int(os.getenv("CACHE_TTL_HOURS", "24"))
    REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
    REDIS_PORT = int(os.getenv("REDIS_PORT", "6379"))
    REDIS_DB = int(os.getenv("REDIS_DB", "0"))
    
    # Model settings
    DEFAULT_MODEL = "deepseek-chat"
    MAX_TOKENS = 2000
    TEMPERATURE = 0.7
    
    # Performance monitoring settings
    ENABLE_PERFORMANCE_MONITORING = os.getenv("ENABLE_PERFORMANCE_MONITORING", "true").lower() == "true"
    PERFORMANCE_METRICS_MAX_HISTORY = int(os.getenv("PERFORMANCE_METRICS_MAX_HISTORY", "1000"))
    PERFORMANCE_LOG_SLOW_REQUESTS = os.getenv("PERFORMANCE_LOG_SLOW_REQUESTS", "true").lower() == "true"
    SLOW_REQUEST_THRESHOLD_MS = int(os.getenv("SLOW_REQUEST_THRESHOLD_MS", "5000"))
    
    # API settings
    ADMIN_API_KEY = os.getenv("ADMIN_API_KEY", "demo-api-key-2024")
    ENABLE_API_KEY_AUTH = os.getenv("ENABLE_API_KEY_AUTH", "false").lower() == "true"
    
    # Performance optimization settings
    ENABLE_REQUEST_CACHING = os.getenv("ENABLE_REQUEST_CACHING", "true").lower() == "true"
    ENABLE_RESPONSE_COMPRESSION = os.getenv("ENABLE_RESPONSE_COMPRESSION", "true").lower() == "true"
    MAX_CONTEXT_LENGTH = int(os.getenv("MAX_CONTEXT_LENGTH", "8000"))
    
    # Resource limits
    MAX_MEMORY_MB = int(os.getenv("MAX_MEMORY_MB", "1024"))  # Max memory usage before warning
    MAX_CPU_PERCENT = int(os.getenv("MAX_CPU_PERCENT", "80"))  # Max CPU usage before warning
    
    # Benchmark settings
    BENCHMARK_SAMPLE_FILES_DIR = Path("test_docs")
    BENCHMARK_SAMPLE_FILES_DIR.mkdir(exist_ok=True)
    
    # Logging settings
    LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
    LOG_PERFORMANCE_METRICS = os.getenv("LOG_PERFORMANCE_METRICS", "true").lower() == "true"
    
    # OCR settings
    OCR_LANGUAGES = os.getenv("OCR_LANGUAGES", "en").split(",")
    OCR_GPU_ENABLED = os.getenv("OCR_GPU_ENABLED", "false").lower() == "true"
    
    # Document Intelligence settings
    ENABLE_DOCUMENT_INTELLIGENCE = os.getenv("ENABLE_DOCUMENT_INTELLIGENCE", "true").lower() == "true"
    MAX_TOPICS_EXTRACTION = int(os.getenv("MAX_TOPICS_EXTRACTION", "5"))
    MAX_SMART_QUESTIONS = int(os.getenv("MAX_SMART_QUESTIONS", "10"))
    SIMILARITY_CHUNK_SIZE = int(os.getenv("SIMILARITY_CHUNK_SIZE", "500"))
    SIMILARITY_MAX_RESULTS = int(os.getenv("SIMILARITY_MAX_RESULTS", "10"))
    DOCUMENT_SUMMARY_LENGTH = int(os.getenv("DOCUMENT_SUMMARY_LENGTH", "150"))
    
    @classmethod
    def get_performance_config(cls) -> dict:
        """Get performance-related configuration as dict"""
        return {
            "monitoring_enabled": cls.ENABLE_PERFORMANCE_MONITORING,
            "metrics_history": cls.PERFORMANCE_METRICS_MAX_HISTORY,
            "slow_request_threshold_ms": cls.SLOW_REQUEST_THRESHOLD_MS,
            "resource_limits": {
                "max_memory_mb": cls.MAX_MEMORY_MB,
                "max_cpu_percent": cls.MAX_CPU_PERCENT
            },
            "optimizations": {
                "request_caching": cls.ENABLE_REQUEST_CACHING,
                "response_compression": cls.ENABLE_RESPONSE_COMPRESSION,
                "max_context_length": cls.MAX_CONTEXT_LENGTH
            }
        }

config = Config()