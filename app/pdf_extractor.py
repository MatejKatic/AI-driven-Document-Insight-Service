import fitz  # PyMuPDF
import easyocr
from PIL import Image
from pathlib import Path
from typing import Dict, List, Optional
import io
import numpy as np
from app.cache_manager import cache_manager

class PDFExtractor:
    """Handles text extraction from various types of PDFs and images"""
    
    def __init__(self):
        self._ocr_reader = None
    
    @property
    def ocr_reader(self):
        """Lazy initialization of OCR reader"""
        if self._ocr_reader is None:
            print("Initializing EasyOCR... (this may take a moment)")
            self._ocr_reader = easyocr.Reader(['en'])
        return self._ocr_reader
    
    def extract_text(self, file_path: str) -> Dict[str, any]:
        """
        Extract text from a document using the most appropriate method
        
        Returns:
            Dict containing:
            - text: extracted text
            - method: extraction method used
            - page_count: number of pages (for PDFs)
            - success: boolean indicating success
            - error: error message if any
            - from_cache: boolean indicating if result was from cache
        """
        file_path = Path(file_path)
        file_ext = file_path.suffix.lower()
        
        cached_result = cache_manager.get(str(file_path))
        if cached_result:
            cached_result["from_cache"] = True
            return cached_result
        
        result = {"from_cache": False}
        
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
        
        if result.get("success") and result.get("text"):
            cache_manager.set(
                str(file_path), 
                result,
                ttl_hours=24
            )
        
        return result
    
    def _extract_from_pdf(self, file_path: Path) -> Dict[str, any]:
        """Extract text from PDF using multiple methods"""
        result = {
            "text": "",
            "method": "",
            "page_count": 0,
            "success": False,
            "error": None
        }
        
        try:
            text, page_count = self._extract_with_pymupdf(file_path)
            if text and len(text.strip()) > 50:  # Reasonable amount of text
                result.update({
                    "text": text,
                    "method": "PyMuPDF",
                    "page_count": page_count,
                    "success": True
                })
                return result
        except Exception as e:
            print(f"PyMuPDF text extraction failed: {e}")
        
        try:
            print(f"Attempting OCR on {file_path.name}...")
            text = self._extract_with_ocr_from_pdf(file_path)
            if text:
                result.update({
                    "text": text,
                    "method": "EasyOCR",
                    "success": True
                })
                return result
        except Exception as e:
            result["error"] = f"All extraction methods failed: {e}"
        
        return result
    
    def _extract_with_pymupdf(self, file_path: Path) -> tuple[str, int]:
        """Extract text using PyMuPDF"""
        text = ""
        doc = fitz.open(str(file_path))
        page_count = len(doc)
        
        for page_num in range(page_count):
            page = doc[page_num]
            text += page.get_text() + "\n"
        
        doc.close()
        return text, page_count
    
    def _extract_with_ocr_from_pdf(self, file_path: Path) -> str:
        """Extract text from PDF using OCR (for scanned PDFs)"""
        text = ""
        doc = fitz.open(str(file_path))
        
        for page_num in range(len(doc)):
            page = doc[page_num]
            mat = fitz.Matrix(2, 2)  # 2x zoom for better OCR
            pix = page.get_pixmap(matrix=mat)
            img_data = pix.tobytes("png")
            
            image = Image.open(io.BytesIO(img_data))
            
            ocr_result = self.ocr_reader.readtext(np.array(image))
            
            page_text = " ".join([item[1] for item in ocr_result])
            text += page_text + "\n\n"
        
        doc.close()
        return text
    
    def _extract_from_image(self, file_path: Path) -> Dict[str, any]:
        """Extract text from image files"""
        try:
            image = Image.open(file_path)
            
            ocr_result = self.ocr_reader.readtext(np.array(image))
            
            text = " ".join([item[1] for item in ocr_result])
            
            return {
                "text": text,
                "method": "EasyOCR",
                "success": True,
                "error": None
            }
        except Exception as e:
            return {
                "text": "",
                "method": "EasyOCR",
                "success": False,
                "error": str(e)
            }
    
    def extract_from_multiple_files(self, file_paths: List[str]) -> Dict[str, Dict]:
        """Extract text from multiple files"""
        results = {}
        
        for file_path in file_paths:
            file_name = Path(file_path).name
            results[file_name] = self.extract_text(file_path)
        
        return results