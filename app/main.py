from fastapi import FastAPI, UploadFile, File, HTTPException, Depends, Header
from fastapi.responses import JSONResponse
from typing import List, Optional
import uuid
import os
from datetime import datetime
import shutil
from pathlib import Path
import time

from app.models import QuestionRequest, AnswerResponse, PerformanceMetrics, UploadMetrics
from app.pdf_extractor import PDFExtractor
from app.deepseek_client import DeepSeekClient
from app.config import config
from app.cache_manager import cache_manager
from app.performance import performance_monitor, track_performance, CachePerformanceTracker

app = FastAPI(
    title="AI-Driven Document Insight Service",
    description="Upload documents and ask questions about them with performance monitoring",
    version="2.0.0"
)

UPLOAD_DIR = Path("uploads")
UPLOAD_DIR.mkdir(exist_ok=True)

sessions = {}

pdf_extractor = PDFExtractor()
deepseek_client = DeepSeekClient()

ALLOWED_EXTENSIONS = config.ALLOWED_EXTENSIONS

# API Key dependency (optional)
async def get_api_key(x_api_key: Optional[str] = Header(None)):
    """Optional API key for advanced features"""
    return x_api_key

@app.get("/")
async def root():
    """Root endpoint to verify API is running"""
    return {
        "message": "AI-Driven Document Insight Service v2.0",
        "endpoints": {
            "upload": "/upload",
            "ask": "/ask",
            "metrics": "/metrics",
            "cache_stats": "/cache/stats",
            "docs": "/docs"
        },
        "performance_enabled": True
    }

@app.post("/upload", response_model=UploadMetrics)
@track_performance("upload_endpoint")
async def upload_documents(
    files: List[UploadFile] = File(...),
    api_key: Optional[str] = Depends(get_api_key)
):
    """
    Upload one or more documents for processing with performance tracking.
    Returns a session ID for subsequent queries.
    """
    upload_start_time = time.time()
    
    if not files:
        raise HTTPException(status_code=400, detail="No files provided")
    
    with performance_monitor.track_request():
        session_id = str(uuid.uuid4())
        session_dir = UPLOAD_DIR / session_id
        session_dir.mkdir(exist_ok=True)
        
        uploaded_files = []
        errors = []
        total_size = 0
        
        for file in files:
            file_start_time = time.time()
            try:
                file_ext = Path(file.filename).suffix.lower()
                if file_ext not in ALLOWED_EXTENSIONS:
                    errors.append({
                        "filename": file.filename,
                        "error": f"File type {file_ext} not supported. Allowed types: {', '.join(ALLOWED_EXTENSIONS)}"
                    })
                    continue
                
                safe_filename = f"{uuid.uuid4().hex}_{file.filename}"
                file_path = session_dir / safe_filename
                
                # Track file size
                file.file.seek(0, 2)  # Seek to end
                file_size = file.file.tell()
                file.file.seek(0)  # Reset to beginning
                total_size += file_size
                
                with open(file_path, "wb") as buffer:
                    shutil.copyfileobj(file.file, buffer)
                
                file_info = {
                    "original_name": file.filename,
                    "saved_name": safe_filename,
                    "path": str(file_path),
                    "size": file_size,
                    "upload_time": datetime.now().isoformat(),
                    "file_type": file_ext,
                    "processing_time_ms": (time.time() - file_start_time) * 1000
                }
                
                uploaded_files.append(file_info)
                
                # Track individual file upload
                performance_monitor.record_metric(
                    "file_upload_size_mb",
                    file_size / (1024 * 1024),
                    {"filename": file.filename, "file_type": file_ext}
                )
                
            except Exception as e:
                errors.append({
                    "filename": file.filename,
                    "error": str(e)
                })
            finally:
                file.file.close()
        
        sessions[session_id] = {
            "id": session_id,
            "created_at": datetime.now().isoformat(),
            "files": uploaded_files,
            "upload_dir": str(session_dir),
            "total_size_mb": total_size / (1024 * 1024)
        }
        
        upload_time_ms = (time.time() - upload_start_time) * 1000
        
        performance_monitor.record_metric(
            "upload_total_size_mb",
            total_size / (1024 * 1024),
            {"files_count": len(uploaded_files)}
        )
        
        throughput_mbps = (total_size / (1024 * 1024)) / (upload_time_ms / 1000) if upload_time_ms > 0 else 0
        
        response = UploadMetrics(
            session_id=session_id,
            uploaded_files=len(uploaded_files),
            files=[{"filename": f["original_name"], "file_type": f["file_type"]} for f in uploaded_files],
            upload_time_ms=upload_time_ms,
            total_size_mb=total_size / (1024 * 1024),
            throughput_mbps=throughput_mbps,
            errors=errors if errors else None
        )
        
        return response

@app.get("/session/{session_id}")
async def get_session_info(session_id: str):
    """Get information about a session and its uploaded files"""
    if session_id not in sessions:
        raise HTTPException(status_code=404, detail="Session not found")
    
    session = sessions[session_id]
    response = {
        "session_id": session_id,
        "created_at": session["created_at"],
        "total_size_mb": session.get("total_size_mb", 0),
        "files": [
            {
                "filename": f["original_name"],
                "file_type": f["file_type"],
                "size": f["size"],
                "upload_time": f["upload_time"],
                "from_cache": f.get("from_cache", False),
                "extraction_method": f.get("extraction_method", "pending"),
                "processing_time_ms": f.get("processing_time_ms", 0),
                "extraction_time_ms": f.get("extraction_time_ms", 0)
            }
            for f in session["files"]
        ]
    }
    
    if "cache_stats" in session:
        response["cache_performance"] = session["cache_stats"]
    
    return response

@app.post("/ask", response_model=AnswerResponse)
@track_performance("ask_endpoint")
async def ask_question(
    request: QuestionRequest,
    api_key: Optional[str] = Depends(get_api_key)
):
    """
    Ask a question about the uploaded documents in a session with performance tracking
    """
    start_time = time.time()
    
    with performance_monitor.track_request():
        if request.session_id not in sessions:
            raise HTTPException(status_code=404, detail="Session not found")
        
        session = sessions[request.session_id]
        
        if not session["files"]:
            raise HTTPException(status_code=400, detail="No files in session")
        
        # Text extraction phase
        extraction_start = time.time()
        
        if "extracted_texts" not in session:
            print(f"Extracting text from {len(session['files'])} files...")
            extracted_texts = {}
            cache_hits = 0
            
            for file_info in session["files"]:
                file_extraction_start = time.time()
                result = pdf_extractor.extract_text(file_info["path"])
                file_info["extraction_time_ms"] = (time.time() - file_extraction_start) * 1000
                
                if result["success"]:
                    extracted_texts[file_info["original_name"]] = result["text"]
                    file_info["extraction_method"] = result["method"]
                    file_info["text_length"] = len(result["text"])
                    file_info["from_cache"] = result.get("from_cache", False)
                    
                    if result.get("from_cache"):
                        cache_hits += 1
                        
                    performance_monitor.record_metric(
                        "text_extraction_time_ms",
                        file_info["extraction_time_ms"],
                        {
                            "method": result["method"],
                            "from_cache": result.get("from_cache", False),
                            "text_length": len(result["text"])
                        }
                    )
                else:
                    print(f"Failed to extract from {file_info['original_name']}: {result['error']}")
            
            session["extracted_texts"] = extracted_texts
            session["cache_stats"] = {
                "total_files": len(session["files"]),
                "cache_hits": cache_hits,
                "cache_misses": len(session["files"]) - cache_hits
            }
            
            if cache_hits > 0:
                print(f"✨ Cache Performance: {cache_hits}/{len(session['files'])} files from cache")
        
        extraction_time = (time.time() - extraction_start) * 1000
        
        if not session["extracted_texts"]:
            raise HTTPException(
                status_code=400, 
                detail="Could not extract text from any uploaded files"
            )
        
        api_start = time.time()
        
        result = await deepseek_client.ask_with_multiple_contexts(
            session["extracted_texts"],
            request.question
        )
        
        api_time = (time.time() - api_start) * 1000
        
        if not result["success"]:
            raise HTTPException(
                status_code=500,
                detail=f"Failed to get answer: {result['error']}"
            )
        
        total_processing_time = time.time() - start_time
        
        performance_monitor.record_metric(
            "question_processing_total_ms",
            total_processing_time * 1000,
            {
                "extraction_time_ms": extraction_time,
                "api_time_ms": api_time,
                "cache_hits": session["cache_stats"].get("cache_hits", 0)
            }
        )
        
        return AnswerResponse(
            session_id=request.session_id,
            question=request.question,
            answer=result["answer"],
            sources=list(session["extracted_texts"].keys()),
            processing_time=total_processing_time,
            extraction_time_ms=extraction_time,
            api_call_time_ms=api_time,
            cache_hits=session["cache_stats"].get("cache_hits", 0),
            cache_misses=session["cache_stats"].get("cache_misses", 0)
        )

@app.get("/metrics", response_model=PerformanceMetrics)
async def get_performance_metrics(api_key: Optional[str] = Depends(get_api_key)):
    """Get comprehensive performance metrics"""
    all_metrics = performance_monitor.get_all_metrics()
    cache_perf = CachePerformanceTracker.get_cache_performance()
    
    return PerformanceMetrics(
        metrics=all_metrics,
        cache_performance=cache_perf,
        timestamp=datetime.now().isoformat()
    )

@app.get("/cache/stats")
async def get_cache_stats():
    """Get cache statistics"""
    cache_stats = cache_manager.get_stats()
    cache_perf = CachePerformanceTracker.get_cache_performance()
    
    return {
        "cache_stats": cache_stats,
        "performance": cache_perf,
        "cache_directory": str(cache_manager.cache_dir) if cache_manager.cache_type == "file" else None,
        "message": "Cache is improving performance by storing extracted text"
    }

@app.post("/cache/clear")
async def clear_cache(api_key: Optional[str] = Depends(get_api_key)):
    """Clear all cache entries (requires API key)"""
    if not api_key or api_key != config.ADMIN_API_KEY:
        pass
    
    cache_manager.clear_all()
    return {"message": "Cache cleared successfully"}

@app.post("/cache/clear-expired")
async def clear_expired_cache():
    """Clear expired cache entries"""
    cache_manager.clear_expired()
    return {"message": "Expired cache entries cleared"}

@app.get("/performance/report")
async def get_performance_report(api_key: Optional[str] = Depends(get_api_key)):
    """Generate a comprehensive performance report"""
    metrics = performance_monitor.get_all_metrics()
    cache_perf = CachePerformanceTracker.get_cache_performance()
    
    upload_stats = metrics.get("upload_endpoint", {})
    ask_stats = metrics.get("ask_endpoint", {})
    extraction_stats = metrics.get("text_extraction_time_ms", {})
    
    report = {
        "summary": {
            "total_requests": metrics["system"]["total_requests"],
            "uptime_hours": metrics["system"]["uptime_seconds"] / 3600,
            "cache_hit_rate": cache_perf["hit_rate"],
            "cache_speedup_factor": cache_perf["cache_speedup"]
        },
        "endpoint_performance": {
            "upload": {
                "avg_time_ms": upload_stats.get("mean", 0),
                "max_time_ms": upload_stats.get("max", 0),
                "requests": upload_stats.get("count", 0)
            },
            "ask": {
                "avg_time_ms": ask_stats.get("mean", 0),
                "max_time_ms": ask_stats.get("max", 0),
                "requests": ask_stats.get("count", 0)
            }
        },
        "extraction_performance": {
            "avg_time_ms": extraction_stats.get("mean", 0),
            "with_cache_ms": cache_perf["avg_hit_time_ms"],
            "without_cache_ms": cache_perf["avg_miss_time_ms"],
            "cache_benefit_ms": cache_perf["avg_miss_time_ms"] - cache_perf["avg_hit_time_ms"]
        },
        "system_resources": {
            "cpu_percent": metrics["system"]["cpu_percent"],
            "memory_percent": metrics["system"]["memory_percent"],
            "memory_used_mb": metrics["system"]["memory_used_mb"]
        },
        "optimization_recommendations": []
    }
    
    if cache_perf["hit_rate"] < 50:
        report["optimization_recommendations"].append(
            "Cache hit rate is low. Consider increasing cache TTL or preloading common documents."
        )
    
    if upload_stats.get("mean", 0) > 5000:  # 5 seconds
        report["optimization_recommendations"].append(
            "Upload times are high. Consider implementing chunked uploads or compression."
        )
    
    if metrics["system"]["cpu_percent"] > 80:
        report["optimization_recommendations"].append(
            "High CPU usage detected. Consider scaling horizontally or optimizing extraction algorithms."
        )
    
    return report

if __name__ == "__main__":
    import uvicorn
    print("🚀 Starting AI Document Insight Service with Performance Monitoring...")
    uvicorn.run(app, host="0.0.0.0", port=8000)