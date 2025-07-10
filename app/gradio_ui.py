"""
Gradio UI for AI-Driven Document Insight Service
Provides a visual interface for document upload and Q&A
"""
import gradio as gr
import httpx
from typing import List, Tuple, Dict
import asyncio
from pathlib import Path
import json
import time


API_BASE_URL = "http://localhost:8000"

current_session_id = None
uploaded_files_info = []

async def upload_documents(files) -> Tuple[str, List, str, str]:
    """Upload documents and create a session"""
    global current_session_id, uploaded_files_info
    
    if not files:
        return "❌ Please select files to upload", [], "", ""
    
    async with httpx.AsyncClient(timeout=60.0) as client:
        upload_files = []
        for file_path in files:
            file_name = Path(file_path).name
            file_ext = Path(file_path).suffix.lower()
            mime_types = {
                '.pdf': 'application/pdf',
                '.png': 'image/png',
                '.jpg': 'image/jpeg',
                '.jpeg': 'image/jpeg',
                '.tiff': 'image/tiff',
                '.bmp': 'image/bmp'
            }
            mime_type = mime_types.get(file_ext, 'application/octet-stream')
            
            with open(file_path, "rb") as f:
                file_content = f.read()
            
            upload_files.append(
                ("files", (file_name, file_content, mime_type))
            )
        
        try:
            response = await client.post(
                f"{API_BASE_URL}/upload",
                files=upload_files
            )
            
            if response.status_code == 200:
                data = response.json()
                current_session_id = data["session_id"]
                uploaded_files_info = data["files"]
                
                session_response = await client.get(
                    f"{API_BASE_URL}/session/{current_session_id}"
                )
                
                session_info = session_response.json() if session_response.status_code == 200 else {}
                
                file_list = "\n".join([f"✅ {f['filename']} ({f['file_type']})" 
                                      for f in uploaded_files_info])
                
                message = f"""📁 **Upload Successful!**

**Session ID:** `{current_session_id[:8]}...`
**Files uploaded:** {len(uploaded_files_info)}

{file_list}

Ready to ask questions about these documents!"""
                
                return message, uploaded_files_info, current_session_id, ""
            else:
                return f"❌ Upload failed: {response.text}", [], "", ""
                
        except Exception as e:
            return f"❌ Error during upload: {str(e)}", [], "", ""

async def ask_question(question: str, session_id: str) -> Tuple[str, str]:
    """Ask a question about the uploaded documents"""
    
    if not session_id:
        return "❌ Please upload documents first!", ""
    
    if not question:
        return "❌ Please enter a question!", ""
    
    async with httpx.AsyncClient(timeout=60.0) as client:
        try:
            start_time = time.time()
            
            response = await client.post(
                f"{API_BASE_URL}/ask",
                json={
                    "session_id": session_id,
                    "question": question
                }
            )
            
            if response.status_code == 200:
                data = response.json()
                processing_time = time.time() - start_time
                
                session_response = await client.get(
                    f"{API_BASE_URL}/session/{session_id}"
                )
                
                cache_info = ""
                if session_response.status_code == 200:
                    session_data = session_response.json()
                    if "cache_performance" in session_data:
                        cache_perf = session_data["cache_performance"]
                        cache_info = f"""
📊 **Cache Performance:**
- Cache hits: {cache_perf.get('cache_hits', 0)}
- Cache misses: {cache_perf.get('cache_misses', 0)}
"""
                
                answer = f"""💡 **Answer:**

{data['answer']}

---
📚 **Sources:** {', '.join(data['sources'])}
⏱️ **Processing time:** {processing_time:.2f} seconds
{cache_info}"""
                
                return answer, ""
            else:
                error_msg = response.json().get('detail', 'Unknown error')
                return f"❌ Error: {error_msg}", ""
                
        except httpx.TimeoutException:
            return "❌ Request timed out. Please try again.", ""
        except Exception as e:
            return f"❌ Error: {str(e)}", ""

async def get_cache_stats() -> str:
    """Get cache statistics"""
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(f"{API_BASE_URL}/cache/stats")
            if response.status_code == 200:
                stats = response.json()["cache_stats"]
                
                return f"""📈 **Cache Statistics:**

**Type:** {stats['cache_type']}
**Total Requests:** {stats['total_requests']}
**Hits:** {stats['hits']}
**Misses:** {stats['misses']}
**Hit Rate:** {stats['hit_rate']}
**Files Cached:** {stats['saves']}

💡 Cache improves performance by storing extracted text from documents."""
            else:
                return "❌ Could not fetch cache statistics"
        except Exception as e:
            return f"❌ Error: {str(e)}"

async def clear_cache() -> str:
    """Clear the cache"""
    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(f"{API_BASE_URL}/cache/clear")
            if response.status_code == 200:
                return "✅ Cache cleared successfully!"
            else:
                return "❌ Failed to clear cache"
        except Exception as e:
            return f"❌ Error: {str(e)}"

def create_interface():
    """Create the Gradio interface"""
    
    with gr.Blocks(title="AI Document Insight Service", theme=gr.themes.Soft()) as demo:
        gr.Markdown("""
        # 🤖 AI-Driven Document Insight Service
        
        Upload PDF documents and ask questions about their content using AI!
        """)
        
        with gr.Tab("📤 Upload & Ask"):
            with gr.Row():
                with gr.Column(scale=1):
                    gr.Markdown("### 1️⃣ Upload Documents")
                    file_input = gr.File(
                        label="Select PDF or Image files",
                        file_count="multiple",
                        file_types=[".pdf", ".png", ".jpg", ".jpeg", ".tiff", ".bmp"],
                        type="filepath"
                    )
                    upload_btn = gr.Button("Upload Documents", variant="primary")
                    upload_output = gr.Markdown()
                    
                    session_state = gr.State()
                    files_state = gr.State()
                
                with gr.Column(scale=1):
                    gr.Markdown("### 2️⃣ Ask Questions")
                    question_input = gr.Textbox(
                        label="Your Question",
                        placeholder="What is the main topic of these documents?",
                        lines=3
                    )
                    ask_btn = gr.Button("Ask Question", variant="primary")
                    answer_output = gr.Markdown()
        
        with gr.Tab("📊 Cache Stats"):
            gr.Markdown("""
            ### Cache Performance Monitoring
            
            Monitor how the caching system improves performance by storing extracted text.
            """)
            
            stats_output = gr.Markdown()
            with gr.Row():
                refresh_btn = gr.Button("🔄 Refresh Stats")
                clear_btn = gr.Button("🗑️ Clear Cache", variant="stop")
            clear_output = gr.Markdown()
        
        with gr.Tab("ℹ️ About"):
            gr.Markdown("""
            ### About This Application
            
            This is a visual interface for the AI-Driven Document Insight Service.
            
            **Features:**
            - 📄 Multi-format support (PDFs and images)
            - 🧠 AI-powered question answering using DeepSeek
            - ⚡ Smart caching for improved performance
            - 🔍 Text extraction using PyMuPDF and EasyOCR
            
            **How it works:**
            1. Upload one or more PDF documents
            2. Ask questions about the content
            3. Get AI-powered answers based on the document text
            4. Benefit from cached extractions for repeated queries
            
            **Tips:**
            - Upload multiple related documents for comprehensive answers
            - Ask specific questions for better results
            - Check cache stats to see performance improvements
            """)
        
        with gr.Row():
            gr.Examples(
                examples=[
                    "What is the main topic of these documents?",
                    "Summarize the key points from the uploaded files",
                    "What are the financial figures mentioned?",
                    "What are the important dates or deadlines?",
                    "List the main stakeholders or parties involved"
                ],
                inputs=question_input,
                label="Example Questions"
            )
        
        upload_btn.click(
            fn=lambda x: asyncio.run(upload_documents(x)),
            inputs=[file_input],
            outputs=[upload_output, files_state, session_state, question_input]
        )
        
        ask_btn.click(
            fn=lambda q, s: asyncio.run(ask_question(q, s)),
            inputs=[question_input, session_state],
            outputs=[answer_output, question_input]
        )
        
        refresh_btn.click(
            fn=lambda: asyncio.run(get_cache_stats()),
            outputs=[stats_output]
        )
        
        clear_btn.click(
            fn=lambda: asyncio.run(clear_cache()),
            outputs=[clear_output]
        )
        
        demo.load(
            fn=lambda: asyncio.run(get_cache_stats()),
            outputs=[stats_output]
        )
    
    return demo

if __name__ == "__main__":
    demo = create_interface()
    demo.launch(
        server_name="0.0.0.0",
        server_port=7860,
        share=False,
        show_error=True
    )