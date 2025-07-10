import fitz  # PyMuPDF
import easyocr
from PIL import Image
from pathlib import Path
from typing import Dict, List, Optional
import io
import numpy as np
import time
import psutil
from app.cache_manager import cache_manager
from app.performance import performance_monitor, track_performance, track_memory_usage, CachePerformanceTracker

class PDFExtractor:
    """Handles text extraction from various types of PDFs and images with performance monitoring"""
    
    def __init__(self):
        self._ocr_reader = None
        self.extraction_stats = {
            "total_extractions": 0,
            "ocr_used": 0,
            "pymupdf_used": 0,
            "failures": 0
        }
    
    @property
    def ocr_reader(self):
        """Lazy initialization of OCR reader with performance tracking"""
        if self._ocr_reader is None:
            start_time = time.time()
            print("Initializing EasyOCR... (this may take a moment)")
            
            process = psutil.Process()
            mem_before = process.memory_info().rss / (1024 * 1024)
            
            self._ocr_reader = easyocr.Reader(['en'])
            
            mem_after = process.memory_info().rss / (1024 * 1024)
            init_time = (time.time() - start_time) * 1000
            
            performance_monitor.record_metric(
                "ocr_init_time_ms",
                init_time
            )
            performance_monitor.record_metric(
                "ocr_init_memory_mb",
                mem_after - mem_before
            )
            
            print(f"✅ EasyOCR initialized in {init_time:.2f}ms, using {mem_after - mem_before:.2f}MB")
            
        return self._ocr_reader
    
    @track_memory_usage
    def extract_text(self, file_path: str) -> Dict[str, any]:
        """
        Extract text from a document using the most appropriate method with performance tracking
        
        Returns:
            Dict containing:
            - text: extracted text
            - method: extraction method used
            - page_count: number of pages (for PDFs)
            - success: boolean indicating success
            - error: error message if any
            - from_cache: boolean indicating if result was from cache
            - extraction_time_ms: extraction time in milliseconds
        """
        extraction_start = time.time()
        file_path = Path(file_path)
        file_ext = file_path.suffix.lower()
        file_size_mb = file_path.stat().st_size / (1024 * 1024)
        
        cache_start = time.time()
        cached_result = cache_manager.get(str(file_path))
        cache_duration = time.time() - cache_start
        
        if cached_result:
            cached_result["from_cache"] = True
            cached_result["extraction_time_ms"] = cache_duration * 1000
            
            CachePerformanceTracker.track_cache_operation("get", True, cache_duration)
            
            # Track cache hit metrics
            performance_monitor.record_metric(
                "extraction_cache_hit",
                cache_duration * 1000,
                {"file_size_mb": file_size_mb, "file_type": file_ext}
            )
            
            return cached_result
        
        CachePerformanceTracker.track_cache_operation("get", False, cache_duration)
        
        result = {"from_cache": False}
        self.extraction_stats["total_extractions"] += 1
        
        if file_ext == '.pdf':
            result.update(self._extract_from_pdf(file_path))
        elif file_ext in ['.png', '.jpg', '.jpeg', '.tiff', '.bmp']:
            result.update(self._extract_from_image(file_path))
        else:
            result.update({
                "text": "",
                "method": "none",
                "success": False,
                "error": f"Unsupported file type: {file_ext}"
            })
            self.extraction_stats["failures"] += 1
        
        extraction_time = (time.time() - extraction_start) * 1000
        result["extraction_time_ms"] = extraction_time
        
        if result.get("success"):
            performance_monitor.record_metric(
                "extraction_success_time_ms",
                extraction_time,
                {
                    "method": result.get("method"),
                    "file_type": file_ext,
                    "file_size_mb": file_size_mb,
                    "text_length": len(result.get("text", "")),
                    "pages": result.get("page_count", 1)
                }
            )
            
            if result.get("text"):
                cache_start = time.time()
                cache_manager.set(
                    str(file_path), 
                    result,
                    ttl_hours=24
                )
                cache_duration = time.time() - cache_start
                
                performance_monitor.record_metric(
                    "cache_save_time_ms",
                    cache_duration * 1000
                )
        else:
            performance_monitor.record_metric(
                "extraction_failure_time_ms",
                extraction_time,
                {
                    "error": result.get("error"),
                    "file_type": file_ext,
                    "file_size_mb": file_size_mb
                }
            )
        
        return result
    
    @track_performance("pdf_extraction")
    def _extract_from_pdf(self, file_path: Path) -> Dict[str, any]:
        """Extract text from PDF using multiple methods with performance tracking"""
        result = {
            "text": "",
            "method": "",
            "page_count": 0,
            "success": False,
            "error": None
        }
        
        pymupdf_start = time.time()
        try:
            text, page_count = self._extract_with_pymupdf(file_path)
            pymupdf_time = (time.time() - pymupdf_start) * 1000
            
            if text and len(text.strip()) > 50:
                result.update({
                    "text": text,
                    "method": "PyMuPDF",
                    "page_count": page_count,
                    "success": True,
                    "pymupdf_time_ms": pymupdf_time
                })
                self.extraction_stats["pymupdf_used"] += 1
                
                performance_monitor.record_metric(
                    "pymupdf_extraction_time_ms",
                    pymupdf_time,
                    {"page_count": page_count}
                )
                
                return result
        except Exception as e:
            print(f"PyMuPDF text extraction failed: {e}")
            performance_monitor.record_metric(
                "pymupdf_extraction_failure",
                (time.time() - pymupdf_start) * 1000
            )
        
        ocr_start = time.time()
        try:
            print(f"Attempting OCR on {file_path.name}...")
            text = self._extract_with_ocr_from_pdf(file_path)
            ocr_time = (time.time() - ocr_start) * 1000
            
            if text:
                result.update({
                    "text": text,
                    "method": "EasyOCR",
                    "success": True,
                    "ocr_time_ms": ocr_time
                })
                self.extraction_stats["ocr_used"] += 1
                
                performance_monitor.record_metric(
                    "ocr_extraction_time_ms",
                    ocr_time,
                    {"file_type": "pdf"}
                )
                
                return result
        except Exception as e:
            result["error"] = f"All extraction methods failed: {e}"
            performance_monitor.record_metric(
                "ocr_extraction_failure",
                (time.time() - ocr_start) * 1000
            )
        
        self.extraction_stats["failures"] += 1
        return result
    
    def _extract_with_pymupdf(self, file_path: Path) -> tuple[str, int]:
        """Extract text using PyMuPDF with page-level performance tracking"""
        text = ""
        doc = fitz.open(str(file_path))
        page_count = len(doc)
        
        page_times = []
        
        for page_num in range(page_count):
            page_start = time.time()
            page = doc[page_num]
            page_text = page.get_text()
            text += page_text + "\n"
            
            page_time = (time.time() - page_start) * 1000
            page_times.append(page_time)
        
        doc.close()
        
        if page_times:
            performance_monitor.record_metric(
                "pymupdf_avg_page_time_ms",
                sum(page_times) / len(page_times),
                {"total_pages": page_count}
            )
        
        return text, page_count
    
    @track_memory_usage
    def _extract_with_ocr_from_pdf(self, file_path: Path) -> str:
        """Extract text from PDF using OCR with performance tracking"""
        text = ""
        doc = fitz.open(str(file_path))
        total_pages = len(doc)
        
        for page_num in range(total_pages):
            page_start = time.time()
            page = doc[page_num]
            
            mat = fitz.Matrix(2, 2)  # 2x zoom for better OCR
            pix = page.get_pixmap(matrix=mat)
            img_data = pix.tobytes("png")
            
            image = Image.open(io.BytesIO(img_data))
            
            ocr_result = self.ocr_reader.readtext(np.array(image))
            
            page_text = " ".join([item[1] for item in ocr_result])
            text += page_text + "\n\n"
            
            page_time = (time.time() - page_start) * 1000
            performance_monitor.record_metric(
                "ocr_page_time_ms",
                page_time,
                {
                    "page_num": page_num + 1,
                    "total_pages": total_pages,
                    "text_length": len(page_text)
                }
            )
        
        doc.close()
        return text
    
    @track_performance("image_extraction")
    def _extract_from_image(self, file_path: Path) -> Dict[str, any]:
        """Extract text from image files with performance tracking"""
        try:
            img_start = time.time()
            
            image = Image.open(file_path)
            img_size = image.size
            
            ocr_start = time.time()
            ocr_result = self.ocr_reader.readtext(np.array(image))
            ocr_time = (time.time() - ocr_start) * 1000
            
            text = " ".join([item[1] for item in ocr_result])
            total_time = (time.time() - img_start) * 1000
            
            performance_monitor.record_metric(
                "image_ocr_time_ms",
                ocr_time,
                {
                    "image_width": img_size[0],
                    "image_height": img_size[1],
                    "text_length": len(text),
                    "detected_regions": len(ocr_result)
                }
            )
            
            self.extraction_stats["ocr_used"] += 1
            
            return {
                "text": text,
                "method": "EasyOCR",
                "success": True,
                "error": None,
                "ocr_time_ms": ocr_time,
                "total_time_ms": total_time
            }
        except Exception as e:
            self.extraction_stats["failures"] += 1
            return {
                "text": "",
                "method": "EasyOCR",
                "success": False,
                "error": str(e)
            }
    
    def extract_from_multiple_files(self, file_paths: List[str]) -> Dict[str, Dict]:
        """Extract text from multiple files with batch performance tracking"""
        results = {}
        batch_start = time.time()
        total_size = 0
        
        for file_path in file_paths:
            file_name = Path(file_path).name
            file_size = Path(file_path).stat().st_size
            total_size += file_size
            
            results[file_name] = self.extract_text(file_path)
        
        batch_time = (time.time() - batch_start) * 1000
        
        performance_monitor.record_metric(
            "batch_extraction_time_ms",
            batch_time,
            {
                "file_count": len(file_paths),
                "total_size_mb": total_size / (1024 * 1024),
                "avg_time_per_file_ms": batch_time / len(file_paths) if file_paths else 0
            }
        )
        
        return results
    
    def get_extraction_stats(self) -> Dict[str, any]:
        """Get extraction performance statistics"""
        return {
            **self.extraction_stats,
            "ocr_initialized": self._ocr_reader is not None,
            "performance_metrics": {
                "pymupdf": performance_monitor.get_stats("pymupdf_extraction_time_ms"),
                "ocr": performance_monitor.get_stats("ocr_extraction_time_ms"),
                "cache_hits": performance_monitor.get_stats("extraction_cache_hit")
            }
        }