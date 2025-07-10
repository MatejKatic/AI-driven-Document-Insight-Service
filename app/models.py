from pydantic import BaseModel
from typing import List, Optional, Dict, Any
from datetime import datetime

class FileInfo(BaseModel):
    """Information about an uploaded file"""
    original_name: str
    saved_name: str
    path: str
    size: int
    upload_time: str
    file_type: str
    from_cache: Optional[bool] = False
    extraction_method: Optional[str] = None
    processing_time_ms: Optional[float] = None
    extraction_time_ms: Optional[float] = None

class UploadResponse(BaseModel):
    """Response model for file upload"""
    session_id: str
    uploaded_files: int
    files: List[Dict[str, str]]
    errors: Optional[List[Dict[str, str]]] = None

class UploadMetrics(BaseModel):
    """Response model for file upload with performance metrics"""
    session_id: str
    uploaded_files: int
    files: List[Dict[str, str]]
    upload_time_ms: float
    total_size_mb: float
    throughput_mbps: float
    errors: Optional[List[Dict[str, str]]] = None

class SessionInfo(BaseModel):
    """Session information model"""
    session_id: str
    created_at: str
    files: List[Dict[str, Any]]
    cache_performance: Optional[Dict[str, int]] = None
    total_size_mb: Optional[float] = None

class QuestionRequest(BaseModel):
    """Request model for asking questions"""
    session_id: str
    question: str

class AnswerResponse(BaseModel):
    """Response model for answers with performance metrics"""
    session_id: str
    question: str
    answer: str
    sources: Optional[List[str]] = None
    processing_time: Optional[float] = None
    extraction_time_ms: Optional[float] = None
    api_call_time_ms: Optional[float] = None
    cache_hits: Optional[int] = None
    cache_misses: Optional[int] = None

class CacheStats(BaseModel):
    """Cache statistics model"""
    cache_type: str
    hits: int
    misses: int
    saves: int
    hit_rate: str
    total_requests: int
    performance: Optional[Dict[str, float]] = None

class SystemMetrics(BaseModel):
    """System performance metrics"""
    cpu_percent: float
    memory_percent: float
    memory_available_mb: float
    memory_used_mb: float
    active_requests: int
    total_requests: int
    uptime_seconds: float

class MetricStats(BaseModel):
    """Statistics for a specific metric"""
    count: int
    mean: float
    min: float
    max: float
    median: float
    std_dev: float
    recent_values: List[float]

class PerformanceMetrics(BaseModel):
    """Comprehensive performance metrics response"""
    metrics: Dict[str, Any]
    cache_performance: Dict[str, Any]
    timestamp: str

class PerformanceReport(BaseModel):
    """Performance optimization report"""
    summary: Dict[str, float]
    endpoint_performance: Dict[str, Dict[str, float]]
    extraction_performance: Dict[str, float]
    system_resources: Dict[str, float]
    optimization_recommendations: List[str]

class BenchmarkResult(BaseModel):
    """Benchmark test results"""
    test_type: str
    duration_ms: float
    operations_per_second: float
    success_rate: float
    resource_usage: Dict[str, float]
    timestamp: str

class APIHealthCheck(BaseModel):
    """API health check response"""
    status: str
    response_time_ms: float
    api_reachable: bool
    model: Optional[str] = None
    error: Optional[str] = None

class ExtractionStats(BaseModel):
    """Text extraction statistics"""
    total_extractions: int
    ocr_used: int
    pymupdf_used: int
    failures: int
    ocr_initialized: bool
    performance_metrics: Dict[str, Any]

class APIStats(BaseModel):
    """DeepSeek API usage statistics"""
    total_requests: int
    successful_requests: int
    failed_requests: int
    total_tokens_used: int
    total_cost_estimate: float
    success_rate: str
    avg_cost_per_request: str
    avg_tokens_per_request: float
    performance_metrics: Dict[str, Any]

class DocumentAnalysis(BaseModel):
    """Document analysis results"""
    filename: str
    timestamp: str
    basic_stats: Dict[str, Any]
    complexity_score: float
    key_topics: List[str]
    document_type: str
    language_features: Dict[str, Any]
    summary: str

class SmartQuestion(BaseModel):
    """Smart question model"""
    question: str
    category: str

class SimilarityResult(BaseModel):
    """Similarity search result"""
    score: float
    filename: str
    chunk_index: int
    text: str
    full_text: str

class DocumentIntelligenceResponse(BaseModel):
    """Response for document intelligence features"""
    session_id: str
    document_analyses: Optional[Dict[str, DocumentAnalysis]] = None
    cross_document_insights: Optional[Dict[str, Any]] = None
    questions: Optional[List[SmartQuestion]] = None
    similarity_results: Optional[List[SimilarityResult]] = None