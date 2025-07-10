"""
Gradio UI for AI-Driven Document Insight Service with Performance Monitoring and Document Intelligence
Provides a visual interface for document upload, Q&A, performance analytics, and intelligent features
"""
import gradio as gr
import httpx
from typing import List, Tuple, Dict, Optional
import asyncio
from pathlib import Path
import json
import time
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from datetime import datetime, timedelta
from collections import deque, defaultdict
import numpy as np

API_BASE_URL = "http://localhost:8000"
API_KEY = "demo-api-key-2024"  # Default demo API key

class PerformanceTracker:
    def __init__(self, max_history=100):
        self.max_history = max_history
        self.upload_times = deque(maxlen=max_history)
        self.ask_times = deque(maxlen=max_history)
        self.cache_hits = deque(maxlen=max_history)
        self.cache_misses = deque(maxlen=max_history)
        self.timestamps = deque(maxlen=max_history)
        self.file_sizes = deque(maxlen=max_history)
        self.response_times = defaultdict(lambda: deque(maxlen=max_history))
        
    def add_upload_metric(self, time_taken: float, file_count: int, total_size: float):
        """Track upload performance"""
        self.upload_times.append(time_taken)
        self.file_sizes.append(total_size)
        self.timestamps.append(datetime.now())
        
    def add_ask_metric(self, time_taken: float, cache_hit: int, cache_miss: int):
        """Track question/answer performance"""
        self.ask_times.append(time_taken)
        self.cache_hits.append(cache_hit)
        self.cache_misses.append(cache_miss)
        self.timestamps.append(datetime.now())
        
    def get_metrics_summary(self):
        """Get summary of performance metrics"""
        if not self.upload_times and not self.ask_times:
            return {
                "avg_upload_time": 0,
                "avg_ask_time": 0,
                "cache_hit_rate": 0,
                "total_operations": 0
            }
        
        total_hits = sum(self.cache_hits) if self.cache_hits else 0
        total_misses = sum(self.cache_misses) if self.cache_misses else 0
        total_cache_ops = total_hits + total_misses
        
        return {
            "avg_upload_time": np.mean(self.upload_times) if self.upload_times else 0,
            "avg_ask_time": np.mean(self.ask_times) if self.ask_times else 0,
            "cache_hit_rate": (total_hits / total_cache_ops * 100) if total_cache_ops > 0 else 0,
            "total_operations": len(self.upload_times) + len(self.ask_times),
            "total_cache_hits": total_hits,
            "total_cache_misses": total_misses
        }

performance_tracker = PerformanceTracker()
current_session_id = None
uploaded_files_info = []

async def upload_documents_with_metrics(files) -> Tuple[str, List, str, str, object]:
    """Upload documents with performance tracking"""
    global current_session_id, uploaded_files_info
    
    if not files:
        return "❌ Please select files to upload", [], "", "", get_performance_charts()
    
    start_time = time.time()
    total_size = 0
    
    async with httpx.AsyncClient(timeout=60.0) as client:
        upload_files = []
        for file_path in files:
            file_name = Path(file_path).name
            file_ext = Path(file_path).suffix.lower()
            file_size = Path(file_path).stat().st_size
            total_size += file_size
            
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
            headers = {"X-API-Key": API_KEY}
            response = await client.post(
                f"{API_BASE_URL}/upload",
                files=upload_files,
                headers=headers
            )
            
            upload_time = time.time() - start_time
            
            if response.status_code == 200:
                data = response.json()
                current_session_id = data["session_id"]
                uploaded_files_info = data["files"]
                
                performance_tracker.add_upload_metric(
                    upload_time, 
                    len(uploaded_files_info),
                    total_size / (1024 * 1024)  # Convert to MB
                )
                
                actual_upload_time = data.get("upload_time_ms", upload_time * 1000) / 1000
                
                file_list = "\n".join([f"✅ {f['filename']} ({f['file_type']})" 
                                      for f in uploaded_files_info])
                
                perf_info = f"""⚡ **Performance Metrics:**
- Upload time: {actual_upload_time:.2f}s
- Total size: {total_size / (1024 * 1024):.2f}MB
- Files/second: {len(uploaded_files_info) / actual_upload_time:.2f}
- Throughput: {(total_size / (1024 * 1024)) / actual_upload_time:.2f}MB/s"""
                
                message = f"""📁 **Upload Successful!**

**Session ID:** `{current_session_id[:8]}...`
**Files uploaded:** {len(uploaded_files_info)}

{file_list}

{perf_info}

Ready to ask questions about these documents!"""
                
                return message, uploaded_files_info, current_session_id, "", get_performance_charts()
            else:
                return f"❌ Upload failed: {response.text}", [], "", "", get_performance_charts()
                
        except Exception as e:
            return f"❌ Error during upload: {str(e)}", [], "", "", get_performance_charts()

async def ask_question_with_metrics(question: str, session_id: str) -> Tuple[str, str, object]:
    """Ask a question with performance tracking"""
    
    if not session_id:
        return "❌ Please upload documents first!", "", get_performance_charts()
    
    if not question:
        return "❌ Please enter a question!", "", get_performance_charts()
    
    start_time = time.time()
    
    async with httpx.AsyncClient(timeout=60.0) as client:
        try:
            headers = {"X-API-Key": API_KEY}
            response = await client.post(
                f"{API_BASE_URL}/ask",
                json={
                    "session_id": session_id,
                    "question": question
                },
                headers=headers
            )
            
            ask_time = time.time() - start_time
            
            if response.status_code == 200:
                data = response.json()
                
                session_response = await client.get(
                    f"{API_BASE_URL}/session/{session_id}",
                    headers=headers
                )
                
                cache_info = ""
                cache_hits = 0
                cache_misses = 0
                
                if session_response.status_code == 200:
                    session_data = session_response.json()
                    if "cache_performance" in session_data:
                        cache_perf = session_data["cache_performance"]
                        cache_hits = cache_perf.get('cache_hits', 0)
                        cache_misses = cache_perf.get('cache_misses', 0)
                        cache_info = f"""
📊 **Cache Performance:**
- Cache hits: {cache_hits} ✅
- Cache misses: {cache_misses} ❌
- Hit rate: {(cache_hits / (cache_hits + cache_misses) * 100) if (cache_hits + cache_misses) > 0 else 0:.1f}%
"""
                
                performance_tracker.add_ask_metric(ask_time, cache_hits, cache_misses)
                
                actual_processing_time = data.get('processing_time', ask_time)
                
                perf_metrics = f"""⚡ **Performance Metrics:**
- Total response time: {ask_time:.2f}s
- Server processing: {actual_processing_time:.2f}s
- Network overhead: {(ask_time - actual_processing_time):.2f}s
"""
                
                answer = f"""💡 **Answer:**

{data['answer']}

---
📚 **Sources:** {', '.join(data['sources'])}
{perf_metrics}
{cache_info}"""
                
                return answer, "", get_performance_charts()
            else:
                error_msg = response.json().get('detail', 'Unknown error')
                return f"❌ Error: {error_msg}", "", get_performance_charts()
                
        except httpx.TimeoutException:
            return "❌ Request timed out. Please try again.", "", get_performance_charts()
        except Exception as e:
            return f"❌ Error: {str(e)}", "", get_performance_charts()

async def get_system_metrics() -> Dict:
    """Get system performance metrics"""
    async with httpx.AsyncClient() as client:
        try:
            headers = {"X-API-Key": API_KEY}
            response = await client.get(f"{API_BASE_URL}/metrics", headers=headers)
            
            if response.status_code == 200:
                return response.json()["metrics"]
            else:
                cache_response = await client.get(f"{API_BASE_URL}/cache/stats")
                if cache_response.status_code == 200:
                    return {"cache_stats": cache_response.json()["cache_stats"]}
                return {}
        except:
            return {}

def get_performance_charts():
    """Generate performance visualization charts"""
    try:
        metrics = performance_tracker.get_metrics_summary()
        
        from plotly.subplots import make_subplots
        
        fig = make_subplots(
            rows=2, cols=2,
            subplot_titles=('Response Times', 'Cache Performance', 
                          'Operation Timeline', 'Throughput Metrics'),
            specs=[[{"type": "bar"}, {"type": "pie"}],
                   [{"type": "scatter"}, {"type": "indicator"}]]
        )
        
        if performance_tracker.upload_times or performance_tracker.ask_times:
            categories = []
            times = []
            colors = []
            
            if performance_tracker.upload_times:
                recent_uploads = list(performance_tracker.upload_times)[-10:]
                for i, t in enumerate(recent_uploads):
                    categories.append(f"Upload {i+1}")
                    times.append(t)
                    colors.append('lightblue')
            
            if performance_tracker.ask_times:
                recent_asks = list(performance_tracker.ask_times)[-10:]
                for i, t in enumerate(recent_asks):
                    categories.append(f"Query {i+1}")
                    times.append(t)
                    colors.append('lightgreen')
            
            fig.add_trace(
                go.Bar(x=categories, y=times, marker_color=colors, name="Response Time"),
                row=1, col=1
            )
        
        total_hits = metrics.get("total_cache_hits", 0)
        total_misses = metrics.get("total_cache_misses", 0)
        
        if total_hits > 0 or total_misses > 0:
            fig.add_trace(
                go.Pie(
                    labels=['Cache Hits', 'Cache Misses'],
                    values=[total_hits, total_misses],
                    marker_colors=['#4CAF50', '#FF5252'],
                    name="Cache"
                ),
                row=1, col=2
            )
        
        if performance_tracker.timestamps:
            timeline_data = []
            for i, ts in enumerate(performance_tracker.timestamps):
                if i < len(performance_tracker.upload_times):
                    timeline_data.append((ts, performance_tracker.upload_times[i], 'Upload'))
                elif i - len(performance_tracker.upload_times) < len(performance_tracker.ask_times):
                    idx = i - len(performance_tracker.upload_times)
                    timeline_data.append((ts, performance_tracker.ask_times[idx], 'Query'))
            
            if timeline_data:
                df = pd.DataFrame(timeline_data, columns=['Timestamp', 'Time', 'Type'])
                for op_type in df['Type'].unique():
                    df_type = df[df['Type'] == op_type]
                    fig.add_trace(
                        go.Scatter(
                            x=df_type['Timestamp'], 
                            y=df_type['Time'],
                            mode='lines+markers',
                            name=op_type
                        ),
                        row=2, col=1
                    )
        
        avg_total = (metrics["avg_upload_time"] + metrics["avg_ask_time"]) / 2 if metrics["total_operations"] > 0 else 0
        fig.add_trace(
            go.Indicator(
                mode="gauge+number+delta",
                value=avg_total,
                title={'text': "Avg Response Time (s)"},
                delta={'reference': 2.0, 'decreasing': {'color': "green"}},
                gauge={
                    'axis': {'range': [None, 5]},
                    'bar': {'color': "darkblue"},
                    'steps': [
                        {'range': [0, 1], 'color': "lightgreen"},
                        {'range': [1, 3], 'color': "yellow"},
                        {'range': [3, 5], 'color': "lightcoral"}
                    ],
                    'threshold': {
                        'line': {'color': "red", 'width': 4},
                        'thickness': 0.75,
                        'value': 4
                    }
                }
            ),
            row=2, col=2
        )
        
        fig.update_layout(
            height=600,
            showlegend=False,
            title_text="📊 Performance Analytics Dashboard",
            title_font_size=20
        )
        
        fig.update_xaxes(title_text="Operations", row=1, col=1)
        fig.update_yaxes(title_text="Time (seconds)", row=1, col=1)
        fig.update_xaxes(title_text="Time", row=2, col=1)
        fig.update_yaxes(title_text="Response Time (s)", row=2, col=1)
        
        return fig
        
    except Exception as e:
        print(f"Error creating performance charts: {e}")
        fig = go.Figure()
        fig.add_annotation(
            text="Performance data will appear here after operations",
            xref="paper", yref="paper",
            x=0.5, y=0.5, showarrow=False,
            font=dict(size=16, color="gray")
        )
        fig.update_layout(
            height=600,
            title_text="📊 Performance Analytics Dashboard",
            title_font_size=20
        )
        return fig

async def get_live_metrics() -> str:
    """Get live performance metrics"""
    metrics = performance_tracker.get_metrics_summary()
    system_metrics = await get_system_metrics()
    
    perf_summary = f"""📊 **Performance Summary**

**Operation Metrics:**
- Total operations: {metrics['total_operations']}
- Avg upload time: {metrics['avg_upload_time']:.2f}s
- Avg query time: {metrics['avg_ask_time']:.2f}s

**Cache Performance:**
- Hit rate: {metrics['cache_hit_rate']:.1f}%
- Total hits: {metrics.get('total_cache_hits', 0)}
- Total misses: {metrics.get('total_cache_misses', 0)}
"""
    
    if "system" in system_metrics:
        sys = system_metrics["system"]
        perf_summary += f"""
**System Resources:**
- CPU usage: {sys.get('cpu_percent', 0):.1f}%
- Memory usage: {sys.get('memory_percent', 0):.1f}%
- Active requests: {sys.get('active_requests', 0)}
- Uptime: {sys.get('uptime_seconds', 0) / 3600:.1f} hours
"""
    
    return perf_summary

async def clear_cache() -> str:
    """Clear the cache"""
    async with httpx.AsyncClient() as client:
        try:
            headers = {"X-API-Key": API_KEY}
            response = await client.post(
                f"{API_BASE_URL}/cache/clear",
                headers=headers
            )
            if response.status_code == 200:
                return "✅ Cache cleared successfully!"
            else:
                return "✅ Cache cleared (no auth required)"
        except Exception as e:
            return f"❌ Error: {str(e)}"

def create_interface():
    """Create the enhanced Gradio interface with performance monitoring and document intelligence"""
    
    with gr.Blocks(
        title="AI Document Insight Service - Enhanced Edition",
        theme=gr.themes.Soft(),
        css="""
        .performance-metric {
            background-color: #f0f0f0;
            padding: 10px;
            border-radius: 5px;
            margin: 5px 0;
        }
        """
    ) as demo:
        gr.Markdown("""
        # 🚀 AI-Driven Document Insight Service
        ### Enhanced with Performance Monitoring & Document Intelligence
        
        Upload documents, ask questions, get insights, and monitor performance!
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
                    upload_btn = gr.Button("📤 Upload Documents", variant="primary")
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
                    ask_btn = gr.Button("🤔 Ask Question", variant="primary")
                    answer_output = gr.Markdown()
        
        with gr.Tab("🧠 Document Intelligence"):
            gr.Markdown("""
            ### AI-Powered Document Analysis
            
            Get smart insights, suggested questions, and find similar content across documents.
            """)
            
            with gr.Row():
                with gr.Column(scale=1):
                    gr.Markdown("#### 📊 Document Analysis")
                    analysis_btn = gr.Button("🔍 Analyze Documents", variant="primary")
                    analysis_output = gr.Markdown()
                
                with gr.Column(scale=1):
                    gr.Markdown("#### 💡 Smart Questions")
                    num_questions = gr.Slider(minimum=3, maximum=10, value=5, step=1, label="Number of questions")
                    generate_questions_btn = gr.Button("💡 Generate Questions", variant="primary")
                    questions_output = gr.Markdown()
            
            gr.Markdown("#### 🔎 Similarity Search")
            with gr.Row():
                search_query = gr.Textbox(
                    label="Search Query",
                    placeholder="Find content about...",
                    lines=2
                )
                search_threshold = gr.Slider(
                    minimum=0.1, maximum=0.9, value=0.3, step=0.1,
                    label="Similarity Threshold"
                )
                search_top_k = gr.Slider(
                    minimum=1, maximum=10, value=5, step=1,
                    label="Number of Results"
                )
            
            search_btn = gr.Button("🔍 Search Similar Content", variant="primary")
            search_results = gr.Markdown()
        
        with gr.Tab("📈 Performance Dashboard"):
            gr.Markdown("""
            ### Real-Time Performance Analytics
            
            Monitor system performance and optimization metrics.
            """)
            
            with gr.Row():
                refresh_btn = gr.Button("🔄 Refresh Metrics", variant="primary")
            
            performance_plot = gr.Plot(label="Performance Charts")
            metrics_output = gr.Markdown()
            
        with gr.Tab("📊 Cache Stats"):
            gr.Markdown("""
            ### Cache Performance Monitoring
            
            Track how caching improves document processing speed.
            """)
            
            cache_stats_output = gr.Markdown()
            with gr.Row():
                cache_refresh_btn = gr.Button("🔄 Refresh Cache Stats")
                cache_clear_btn = gr.Button("🗑️ Clear Cache", variant="stop")
            cache_clear_output = gr.Markdown()
        
        with gr.Tab("⚡ Benchmark"):
            gr.Markdown("""
            ### Performance Benchmarking
            
            Run standardized tests to measure system performance.
            """)
            
            with gr.Row():
                with gr.Column():
                    benchmark_type = gr.Radio(
                        ["Quick Test", "Full Benchmark", "Stress Test"],
                        label="Benchmark Type",
                        value="Quick Test"
                    )
                    concurrent_users = gr.Slider(
                        minimum=1, maximum=20, value=5, step=1,
                        label="Concurrent Users (for Stress Test)"
                    )
                    run_benchmark_btn = gr.Button("🏃 Run Benchmark", variant="primary")
                
                with gr.Column():
                    benchmark_output = gr.Markdown()
                    benchmark_plot = gr.Plot()
        
        with gr.Tab("ℹ️ About"):
            gr.Markdown("""
            ### About This Enhanced Version
            
            This enhanced interface includes:
            
            **🚀 Core Features:**
            - Document upload and text extraction (PyMuPDF, EasyOCR)
            - AI-powered Q&A using DeepSeek
            - Smart caching for improved performance
            
            **🧠 Document Intelligence:**
            - Automatic document analysis and insights
            - AI-generated smart questions
            - Similarity search across documents
            - Cross-document insights
            
            **📊 Performance Monitoring:**
            - Real-time response time tracking
            - Cache hit/miss visualization
            - System resource monitoring
            - Throughput analysis
            - Performance benchmarking
            
            **💡 Tips:**
            - Files are cached after first extraction
            - Use smart questions to explore documents
            - Search for similar content across all uploaded files
            - Monitor performance to optimize usage
            """)
        
        # Event handlers
        upload_btn.click(
            fn=lambda x: asyncio.run(upload_documents_with_metrics(x)),
            inputs=[file_input],
            outputs=[upload_output, files_state, session_state, question_input, performance_plot]
        )
        
        ask_btn.click(
            fn=lambda q, s: asyncio.run(ask_question_with_metrics(q, s)),
            inputs=[question_input, session_state],
            outputs=[answer_output, question_input, performance_plot]
        )
        
        # Document Intelligence handlers - Define as sync wrappers
        def analyze_documents_sync(session_id):
            """Sync wrapper for analyze documents"""
            return asyncio.run(analyze_documents_async(session_id))
        
        def generate_questions_sync(session_id, num_q):
            """Sync wrapper for generate questions"""
            return asyncio.run(generate_smart_questions_async(session_id, num_q))
        
        def search_content_sync(session_id, query, threshold, top_k):
            """Sync wrapper for similarity search"""
            return asyncio.run(search_similar_content_async(session_id, query, threshold, top_k))
        
        # Loading message functions
        def show_analysis_progress():
            return """🔄 **Document Analysis in Progress...**

📊 Currently processing:
• Extracting text content
• Analyzing document structure  
• Computing statistics
• Identifying key topics
• Generating AI summaries

⏱️ Estimated time: 15-30 seconds

<div style='text-align: center; margin: 20px;'>
    <span style='font-size: 30px;'>📄</span>
    <span style='font-size: 30px;'>➡️</span>
    <span style='font-size: 30px;'>🧠</span>
    <span style='font-size: 30px;'>➡️</span>
    <span style='font-size: 30px;'>📊</span>
</div>

*Please wait while our AI analyzes your documents...*"""

        def show_questions_progress():
            return """💡 **Generating Smart Questions...**

🤔 AI is working on:
• Understanding document context
• Identifying key concepts
• Creating relevant questions
• Categorizing by type

⏱️ Estimated time: 10-20 seconds

<div style='text-align: center; margin: 20px;'>
    <span style='font-size: 30px;'>📖</span>
    <span style='font-size: 30px;'>➡️</span>
    <span style='font-size: 30px;'>💭</span>
    <span style='font-size: 30px;'>➡️</span>
    <span style='font-size: 30px;'>❓</span>
</div>

*Creating thoughtful questions based on your content...*"""

        def show_search_progress():
            return """🔍 **Searching for Similar Content...**

🔎 Processing:
• Analyzing search query
• Scanning all documents
• Computing similarity scores
• Ranking results by relevance

⏱️ Estimated time: 5-15 seconds

<div style='text-align: center; margin: 20px;'>
    <span style='font-size: 30px;'>🔍</span>
    <span style='font-size: 30px;'>➡️</span>
    <span style='font-size: 30px;'>📑</span>
    <span style='font-size: 30px;'>➡️</span>
    <span style='font-size: 30px;'>✅</span>
</div>

*Finding the most relevant content across your documents...*"""
        
        async def analyze_documents_async(session_id):
            if not session_id:
                return "❌ Please upload documents first!"
            
            async with httpx.AsyncClient(timeout=60.0) as client:
                try:
                    headers = {"X-API-Key": API_KEY} if API_KEY else {}
                    response = await client.get(
                        f"{API_BASE_URL}/session/{session_id}/analysis",
                        headers=headers
                    )
                    
                    if response.status_code == 200:
                        data = response.json()
                        
                        output = "📊 **Document Analysis Results**\n\n"
                        
                        if not data.get("document_analyses"):
                            return "⏳ Analyzing documents... This may take a moment for the first time.\n\nPlease click again in a few seconds."
                        
                        for filename, analysis in data["document_analyses"].items():
                            output += f"### 📄 {filename}\n\n"
                            
                            stats = analysis.get("basic_stats", {})
                            if stats:
                                output += f"**📈 Statistics:**\n"
                                output += f"- Words: {stats.get('word_count', 0):,}\n"
                                output += f"- Sentences: {stats.get('sentence_count', 0)}\n"
                                output += f"- Reading time: {stats.get('reading_time_minutes', 0):.1f} minutes\n"
                                output += f"- Complexity score: {analysis.get('complexity_score', 0)}/100\n\n"
                            
                            output += f"**📑 Type:** {analysis.get('document_type', 'Unknown').title()}\n"
                            
                            topics = analysis.get('key_topics', [])
                            if topics:
                                output += f"**🏷️ Key Topics:** {', '.join(topics)}\n\n"
                            
                            summary = analysis.get('summary', '')
                            if summary:
                                output += f"**📝 Summary:**\n{summary}\n\n"
                            
                            output += "---\n\n"
                        
                        if "cross_document_insights" in data and data["cross_document_insights"]:
                            insights = data["cross_document_insights"]
                            output += "### 🔗 Cross-Document Insights\n\n"
                            output += f"- Total documents: {insights.get('total_documents', 0)}\n"
                            output += f"- Total words: {insights.get('total_words', 0):,}\n"
                            output += f"- Average complexity: {insights.get('average_complexity', 0)}/100\n"
                            output += f"- Total reading time: {insights.get('total_reading_time_minutes', 0):.1f} minutes\n"
                            
                            common_topics = insights.get('common_topics', [])
                            if common_topics:
                                output += f"- Common topics: {', '.join(common_topics)}\n"
                        
                        return output
                    else:
                        try:
                            error_detail = response.json().get('detail', response.text)
                        except:
                            error_detail = response.text
                        return f"❌ Error: {error_detail}"
                except httpx.TimeoutException:
                    return "⏱️ Analysis is taking longer than expected. The documents are being processed. Please try again in a moment."
                except Exception as e:
                    return f"❌ Error: {str(e)}\n\nPlease check if the API server is running on {API_BASE_URL}"
        
        async def generate_smart_questions_async(session_id, num_q):
            if not session_id:
                return "❌ Please upload documents first!"
            
            async with httpx.AsyncClient(timeout=60.0) as client:
                try:
                    headers = {"X-API-Key": API_KEY} if API_KEY else {}
                    response = await client.post(
                        f"{API_BASE_URL}/session/{session_id}/smart-questions",
                        params={"num_questions": int(num_q)},
                        headers=headers
                    )
                    
                    if response.status_code == 200:
                        data = response.json()
                        
                        output = "💡 **Suggested Questions**\n\n"
                        
                        if data.get("generated_from"):
                            output += f"*Based on {', '.join(data['generated_from'])}*\n\n"
                        
                        questions = data.get("questions", [])
                        if not questions:
                            return "❌ No questions could be generated. Please ensure documents have been processed."
                        
                        for i, q in enumerate(questions, 1):
                            emoji = {
                                "factual": "📌",
                                "analytical": "🔍",
                                "comparative": "⚖️",
                                "clarification": "❓"
                            }.get(q.get("category", ""), "❔")
                            
                            output += f"{i}. {emoji} **{q.get('question', 'Question unavailable')}**\n"
                            output += f"   *Category: {q.get('category', 'general')}*\n\n"
                        
                        output += "\n💡 *Copy any question to use in the Q&A tab!*"
                        
                        return output
                    else:
                        try:
                            error_detail = response.json().get('detail', response.text)
                        except:
                            error_detail = response.text
                        return f"❌ Error: {error_detail}"
                except httpx.TimeoutException:
                    return "⏱️ Question generation is taking longer than expected. Please try again."
                except Exception as e:
                    return f"❌ Error: {str(e)}"
        
        async def search_similar_content_async(session_id, query, threshold, top_k):
            if not session_id:
                return "❌ Please upload documents first!"
            
            if not query or not query.strip():
                return "❌ Please enter a search query!"
            
            async with httpx.AsyncClient(timeout=60.0) as client:
                try:
                    headers = {"X-API-Key": API_KEY} if API_KEY else {}
                    response = await client.post(
                        f"{API_BASE_URL}/session/{session_id}/similarity-search",
                        params={
                            "query": query.strip(),
                            "threshold": float(threshold),
                            "top_k": int(top_k)
                        },
                        headers=headers
                    )
                    
                    if response.status_code == 200:
                        data = response.json()
                        
                        output = f"🔍 **Search Results for:** *{query}*\n\n"
                        output += f"Searched across {data.get('total_documents_searched', 0)} documents\n\n"
                        
                        results = data.get("results", [])
                        if results:
                            for i, result in enumerate(results, 1):
                                score = result.get("score", 0)
                                score_bar = "█" * int(score * 10) + "░" * (10 - int(score * 10))
                                
                                output += f"### Result {i}\n"
                                output += f"📄 **File:** {result.get('filename', 'Unknown')}\n"
                                output += f"📊 **Similarity:** [{score_bar}] {score:.1%}\n"
                                output += f"📝 **Content:**\n> {result.get('text', 'No content')}\n\n"
                                output += "---\n\n"
                        else:
                            output += "No matching content found. Try:\n"
                            output += "- Lowering the similarity threshold\n"
                            output += "- Using different keywords\n"
                            output += "- Checking if documents have been processed"
                        
                        return output
                    else:
                        try:
                            error_detail = response.json().get('detail', response.text)
                        except:
                            error_detail = response.text
                        return f"❌ Error: {error_detail}"
                except httpx.TimeoutException:
                    return "⏱️ Search is taking longer than expected. Please try again."
                except Exception as e:
                    return f"❌ Error: {str(e)}"
        
        analysis_btn.click(
            fn=show_analysis_progress,
            outputs=[analysis_output],
            queue=False
        ).then(
            fn=analyze_documents_sync,
            inputs=[session_state],
            outputs=[analysis_output],
            show_progress="full"
        )
        
        generate_questions_btn.click(
            fn=show_questions_progress,
            outputs=[questions_output],
            queue=False
        ).then(
            fn=generate_questions_sync,
            inputs=[session_state, num_questions],
            outputs=[questions_output],
            show_progress="full"
        )
        
        search_btn.click(
            fn=show_search_progress,
            outputs=[search_results],
            queue=False
        ).then(
            fn=search_content_sync,
            inputs=[session_state, search_query, search_threshold, search_top_k],
            outputs=[search_results],
            show_progress="full"
        )
        
        async def refresh_performance():
            metrics = await get_live_metrics()
            plot = get_performance_charts()
            return metrics, plot
        
        refresh_btn.click(
            fn=lambda: asyncio.run(refresh_performance()),
            outputs=[metrics_output, performance_plot]
        )

        async def get_cache_stats_with_chart():
            async with httpx.AsyncClient() as client:
                try:
                    response = await client.get(f"{API_BASE_URL}/cache/stats")
                    if response.status_code == 200:
                        data = response.json()
                        stats = data["cache_stats"]
                        
                        fig = go.Figure()
                        
                        fig.add_trace(go.Bar(
                            x=['Hits', 'Misses', 'Saves'],
                            y=[stats['hits'], stats['misses'], stats['saves']],
                            marker_color=['green', 'red', 'blue']
                        ))
                        
                        fig.update_layout(
                            title="Cache Operations",
                            yaxis_title="Count",
                            showlegend=False
                        )
                        
                        stats_text = f"""📈 **Cache Statistics:**

**Type:** {stats['cache_type']}
**Total Requests:** {stats['total_requests']}
**Hits:** {stats['hits']} ✅
**Misses:** {stats['misses']} ❌
**Hit Rate:** {stats['hit_rate']}
**Files Cached:** {stats['saves']}

💡 Cache improves performance by {float(stats['hit_rate'].rstrip('%')):.0f}% on repeated operations."""
                        
                        return stats_text, fig
                except:
                    return "❌ Error fetching cache stats", None
        
        cache_refresh_btn.click(
            fn=lambda: asyncio.run(get_cache_stats_with_chart()),
            outputs=[cache_stats_output, performance_plot]
        )
        
        cache_clear_btn.click(
            fn=lambda: asyncio.run(clear_cache()),
            outputs=[cache_clear_output]
        )
        
        async def run_performance_benchmark(benchmark_type, concurrent_users):
            """Run performance benchmark"""
            import os
            from pathlib import Path
            
            start_time = time.time()
            
            test_docs_path = Path("test_docs")
            print(f"Looking for test_docs at: {test_docs_path.absolute()}")
            
            if not test_docs_path.exists():
                return f"❌ test_docs folder not found at {test_docs_path.absolute()}\n\nPlease create the folder and add PDF files.", None
            
            pdf_files = list(test_docs_path.glob("*.pdf"))
            print(f"Found {len(pdf_files)} PDF files: {[f.name for f in pdf_files]}")
            
            if not pdf_files:
                return f"❌ No PDF files found in test_docs folder.\n\nPlease add at least one PDF file to: {test_docs_path.absolute()}", None
            
            if benchmark_type == "Quick Test":
                test_file = [str(pdf_files[0])]  # Convert Path to string
                print(f"Using test file: {test_file[0]}")
                
                try:
                    upload_start = time.time()
                    upload_result = await upload_documents_with_metrics(test_file)
                    upload_time = time.time() - upload_start
                    
                    if not current_session_id:
                        return f"❌ Upload failed. Result: {upload_result[0]}", None
                    
                    ask_start = time.time()
                    ask_result = await ask_question_with_metrics("What is this document about?", current_session_id)
                    ask_time = time.time() - ask_start
                    
                    total_time = time.time() - start_time
                    
                    file_size_mb = os.path.getsize(test_file[0]) / (1024 * 1024)
                    
                    return f"""✅ **Quick Test Complete**
                        
**Test File:** {Path(test_file[0]).name}
**File Size:** {file_size_mb:.2f} MB

**Results:**
- Upload time: {upload_time:.2f}s
- Query time: {ask_time:.2f}s  
- Total time: {total_time:.2f}s

**Performance Metrics:**
- Upload speed: {file_size_mb / upload_time:.2f} MB/s
- Processing speed: {1 / total_time:.2f} docs/sec

**Performance Grade:** {'🟢 Excellent' if total_time < 5 else '🟡 Good' if total_time < 10 else '🔴 Needs Optimization'}""", get_performance_charts()
                
                except Exception as e:
                    return f"❌ Benchmark error: {str(e)}\n\nCheck console for details.", None
            
            elif benchmark_type == "Full Benchmark":
                test_files = [str(f) for f in pdf_files[:3]]  # Use up to 3 files
                results = []
                
                all_files = [str(f) for f in pdf_files[:3]]
                
                try:
                    upload_start = time.time()
                    upload_result = await upload_documents_with_metrics(all_files)
                    upload_time = time.time() - upload_start
                    
                    test_session_id = current_session_id  # Save it before it gets overwritten
                    
                    if not test_session_id:
                        return "❌ Upload failed in Full Benchmark", None
                    
                    questions = [
                        "What is the main topic of these documents?",
                        "Are there any dates mentioned?",
                        "What are the key findings or conclusions?",
                        "Summarize the documents in one paragraph."
                    ]
                    
                    query_times = []
                    for i, question in enumerate(questions):
                        ask_start = time.time()
                        await ask_question_with_metrics(question, test_session_id)
                        query_time = time.time() - ask_start
                        query_times.append(query_time)
                        results.append({
                            "question": question[:50] + "...",
                            "query_time": query_time
                        })
                    
                    total_time = time.time() - start_time
                    
                    total_size_mb = sum(os.path.getsize(f) / (1024 * 1024) for f in all_files)
                    
                    report = f"""📊 **Full Benchmark Complete**

**Files Tested:** {len(all_files)} files ({total_size_mb:.2f} MB total)
**Questions Asked:** {len(questions)}
**Total Time:** {total_time:.2f}s

**Upload Performance:**
- Time: {upload_time:.2f}s
- Speed: {total_size_mb / upload_time:.2f} MB/s

**Query Performance:**
"""
                    for i, r in enumerate(results):
                        report += f"\nQ{i+1}: {r['query_time']:.2f}s - {r['question']}"
                    
                    avg_query = sum(query_times) / len(query_times)
                    report += f"""

**Summary:**
- Avg Query Time: {avg_query:.2f}s
- Min Query Time: {min(query_times):.2f}s
- Max Query Time: {max(query_times):.2f}s
- Queries/second: {len(query_times) / sum(query_times):.2f}

**Overall Grade:** {'🟢 Excellent' if avg_query < 3 else '🟡 Good' if avg_query < 5 else '🔴 Needs Optimization'}"""
                    
                    return report, get_performance_charts()
                    
                except Exception as e:
                    return f"❌ Full Benchmark error: {str(e)}", None
            
            elif benchmark_type == "Stress Test":
                import asyncio
                
                test_file = [str(pdf_files[0])]
                file_size_mb = os.path.getsize(test_file[0]) / (1024 * 1024)
                
                async def simulate_user(user_id):
                    """Simulate a single user session"""
                    try:
                        user_start = time.time()
                        
                        upload_start = time.time()
                        
                        async with httpx.AsyncClient(timeout=60.0) as client:
                            with open(test_file[0], "rb") as f:
                                file_content = f.read()
                            
                            upload_files = [
                                ("files", (f"user{user_id}_{Path(test_file[0]).name}", file_content, "application/pdf"))
                            ]
                            
                            headers = {"X-API-Key": API_KEY}
                            response = await client.post(
                                f"{API_BASE_URL}/upload",
                                files=upload_files,
                                headers=headers
                            )
                            
                            if response.status_code != 200:
                                raise Exception(f"Upload failed: {response.status_code}")
                            
                            data = response.json()
                            user_session_id = data["session_id"]
                            upload_time = time.time() - upload_start
                        
                        ask_start = time.time()
                        async with httpx.AsyncClient(timeout=60.0) as client:
                            response = await client.post(
                                f"{API_BASE_URL}/ask",
                                json={
                                    "session_id": user_session_id,
                                    "question": f"What is this document about? (User {user_id})"
                                },
                                headers=headers
                            )
                            
                            if response.status_code != 200:
                                raise Exception(f"Ask failed: {response.status_code}")
                        
                        ask_time = time.time() - ask_start
                        total_user_time = time.time() - user_start
                        
                        return {
                            "user_id": user_id,
                            "session_id": user_session_id,
                            "upload_time": upload_time,
                            "query_time": ask_time,
                            "total_time": total_user_time,
                            "success": True
                        }
                    except Exception as e:
                        return {
                            "user_id": user_id,
                            "error": str(e),
                            "success": False
                        }
                
                print(f"Starting stress test with {concurrent_users} concurrent users...")
                tasks = [simulate_user(i+1) for i in range(concurrent_users)]
                results = await asyncio.gather(*tasks)
                
                total_time = time.time() - start_time
                successful = [r for r in results if r.get("success", False)]
                failed = [r for r in results if not r.get("success", False)]
                
                if successful:
                    avg_upload = sum(r['upload_time'] for r in successful) / len(successful)
                    avg_query = sum(r['query_time'] for r in successful) / len(successful)
                    avg_total = sum(r['total_time'] for r in successful) / len(successful)
                    min_time = min(r['total_time'] for r in successful)
                    max_time = max(r['total_time'] for r in successful)
                else:
                    avg_upload = avg_query = avg_total = min_time = max_time = 0
                
                report = f"""⚡ **Stress Test Complete**

**Test Configuration:**
- Concurrent Users: {concurrent_users}
- Test File: {Path(test_file[0]).name} ({file_size_mb:.2f} MB)
- Total Test Duration: {total_time:.2f}s

**Results:**
- Successful: {len(successful)}/{len(results)} ({len(successful)/len(results)*100:.1f}%)
- Failed: {len(failed)}

**Performance Metrics:**
- Avg Upload Time: {avg_upload:.2f}s
- Avg Query Time: {avg_query:.2f}s
- Avg Total Time/User: {avg_total:.2f}s
- Min Response Time: {min_time:.2f}s
- Max Response Time: {max_time:.2f}s
- Throughput: {len(successful)/total_time:.2f} successful requests/sec

**Load Test Grade:** """
                
                if len(successful) == len(results) and avg_total < 5:
                    report += "🟢 Excellent - System handles concurrent load well"
                elif len(successful) >= len(results) * 0.8 and avg_total < 10:
                    report += "🟡 Good - Some performance degradation under load"
                else:
                    report += "🔴 Needs Optimization - Significant issues under load"
                
                report += "\n\n**Sample Results:**"
                for r in results[:5]:
                    if r.get("success"):
                        report += f"\n✅ User {r['user_id']}: {r['total_time']:.2f}s (Upload: {r['upload_time']:.2f}s, Query: {r['query_time']:.2f}s)"
                    else:
                        report += f"\n❌ User {r['user_id']}: Failed - {r.get('error', 'Unknown error')[:50]}"
                
                if len(results) > 5:
                    report += f"\n... and {len(results)-5} more users"
                
                if failed:
                    report += "\n\n**Failure Analysis:**"
                    error_types = {}
                    for f in failed:
                        error = f.get('error', 'Unknown')[:30]
                        error_types[error] = error_types.get(error, 0) + 1
                    
                    for error, count in error_types.items():
                        report += f"\n- {error}: {count} occurrences"
                
                return report, get_performance_charts()
        
        run_benchmark_btn.click(
            fn=lambda t, c: asyncio.run(run_performance_benchmark(t, c)),
            inputs=[benchmark_type, concurrent_users],
            outputs=[benchmark_output, benchmark_plot]
        )
        
        demo.load(
            fn=lambda: asyncio.run(refresh_performance()),
            outputs=[metrics_output, performance_plot]
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