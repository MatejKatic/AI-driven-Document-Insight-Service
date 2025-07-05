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

class UploadResponse(BaseModel):
    """Response model for file upload"""
    session_id: str
    uploaded_files: int
    files: List[Dict[str, str]]
    errors: Optional[List[Dict[str, str]]] = None

class SessionInfo(BaseModel):
    """Session information model"""
    session_id: str
    created_at: str
    files: List[Dict[str, Any]]

class QuestionRequest(BaseModel):
    """Request model for asking questions"""
    session_id: str
    question: str

class AnswerResponse(BaseModel):
    """Response model for answers"""
    session_id: str
    question: str
    answer: str
    sources: Optional[List[str]] = None
    processing_time: Optional[float] = None