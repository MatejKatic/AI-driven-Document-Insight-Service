from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.responses import JSONResponse
from typing import List
import uuid
import os
from datetime import datetime
import shutil
from pathlib import Path
import time


from app.models import QuestionRequest, AnswerResponse
from app.pdf_extractor import PDFExtractor
from app.deepseek_client import DeepSeekClient
from app.config import config


app = FastAPI(
    title="AI-Driven Document Insight Service",
    description="Upload documents and ask questions about them",
    version="1.0.0"
)


UPLOAD_DIR = Path("uploads")
UPLOAD_DIR.mkdir(exist_ok=True)


sessions = {}


pdf_extractor = PDFExtractor()
deepseek_client = DeepSeekClient()

ALLOWED_EXTENSIONS = config.ALLOWED_EXTENSIONS

@app.get("/")
async def root():
    """Root endpoint to verify API is running"""
    return {
        "message": "AI-Driven Document Insight Service",
        "endpoints": {
            "upload": "/upload",
            "ask": "/ask",
            "docs": "/docs"
        }
    }

@app.post("/upload")
async def upload_documents(files: List[UploadFile] = File(...)):
    """
    Upload one or more documents for processing.
    Returns a session ID for subsequent queries.
    """

    if not files:
        raise HTTPException(status_code=400, detail="No files provided")
    

    session_id = str(uuid.uuid4())
    session_dir = UPLOAD_DIR / session_id
    session_dir.mkdir(exist_ok=True)
    uploaded_files = []
    errors = []
    
    for file in files:
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
            
            with open(file_path, "wb") as buffer:
                shutil.copyfileobj(file.file, buffer)

            file_info = {
                "original_name": file.filename,
                "saved_name": safe_filename,
                "path": str(file_path),
                "size": os.path.getsize(file_path),
                "upload_time": datetime.now().isoformat(),
                "file_type": file_ext
            }
            
            uploaded_files.append(file_info)
            
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
        "upload_dir": str(session_dir)
    }
    

    response = {
        "session_id": session_id,
        "uploaded_files": len(uploaded_files),
        "files": [{"filename": f["original_name"], "file_type": f["file_type"]} for f in uploaded_files]
    }
    
    if errors:
        response["errors"] = errors
    
    return JSONResponse(
        status_code=200 if uploaded_files else 400,
        content=response
    )

@app.get("/session/{session_id}")
async def get_session_info(session_id: str):
    """Get information about a session and its uploaded files"""
    if session_id not in sessions:
        raise HTTPException(status_code=404, detail="Session not found")
    
    session = sessions[session_id]
    return {
        "session_id": session_id,
        "created_at": session["created_at"],
        "files": [
            {
                "filename": f["original_name"],
                "file_type": f["file_type"],
                "size": f["size"],
                "upload_time": f["upload_time"]
            }
            for f in session["files"]
        ]
    }

@app.post("/ask", response_model=AnswerResponse)
async def ask_question(request: QuestionRequest):
    """
    Ask a question about the uploaded documents in a session
    """
    start_time = time.time()

    if request.session_id not in sessions:
        raise HTTPException(status_code=404, detail="Session not found")
    
    session = sessions[request.session_id]
    
    if not session["files"]:
        raise HTTPException(status_code=400, detail="No files in session")
    

    if "extracted_texts" not in session:
        print(f"Extracting text from {len(session['files'])} files...")
        extracted_texts = {}
        
        for file_info in session["files"]:
            result = pdf_extractor.extract_text(file_info["path"])
            
            if result["success"]:
                extracted_texts[file_info["original_name"]] = result["text"]
                file_info["extraction_method"] = result["method"]
                file_info["text_length"] = len(result["text"])
            else:
                print(f"Failed to extract from {file_info['original_name']}: {result['error']}")
        
        session["extracted_texts"] = extracted_texts
    

    if not session["extracted_texts"]:
        raise HTTPException(
            status_code=400, 
            detail="Could not extract text from any uploaded files"
        )
    

    result = await deepseek_client.ask_with_multiple_contexts(
        session["extracted_texts"],
        request.question
    )
    
    if not result["success"]:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get answer: {result['error']}"
        )
    
    processing_time = time.time() - start_time
    
    return AnswerResponse(
        session_id=request.session_id,
        question=request.question,
        answer=result["answer"],
        sources=list(session["extracted_texts"].keys()),
        processing_time=processing_time
    )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)