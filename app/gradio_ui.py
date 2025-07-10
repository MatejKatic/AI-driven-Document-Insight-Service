"""
Gradio UI for AI-Driven Document Insight Service with Performance Monitoring
Provides a visual interface for document upload, Q&A, and performance analytics
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

async def upload_documents_with_metrics(files) -> Tuple[str, List, str, str, str]:
    """Upload documents with performance tracking"""
    global current_session_id, uploaded_files_info
    
    if not files:
        return "❌ Please select files to upload", [], "", "", ""
    
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
                return f"❌ Upload failed: {response.text}", [], "", "", ""
                
        except Exception as e:
            return f"❌ Error during upload: {str(e)}", [], "", "", ""

async def ask_question_with_metrics(question: str, session_id: str) -> Tuple[str, str, str]:
    """Ask a question with performance tracking"""
    
    if not session_id:
        return "❌ Please upload documents first!", "", ""
    
    if not question:
        return "❌ Please enter a question!", "", ""
    
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
                return f"❌ Error: {error_msg}", "", ""
                
        except httpx.TimeoutException:
            return "❌ Request timed out. Please try again.", "", ""
        except Exception as e:
            return f"❌ Error: {str(e)}", "", ""

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
            x=0.5, y=0.5, showarrow=False
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

def create_interface():
    """Create the enhanced Gradio interface with performance monitoring"""
    
    with gr.Blocks(
        title="AI Document Insight Service - Performance Edition",
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
        ### Performance-Enhanced Edition
        
        Upload documents and ask questions with real-time performance monitoring!
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
            ### About This Performance-Enhanced Version
            
            This enhanced interface includes comprehensive performance monitoring:
            
            **🚀 Performance Features:**
            - Real-time response time tracking
            - Cache hit/miss visualization
            - System resource monitoring
            - Throughput analysis
            - Performance benchmarking
            
            **📊 Metrics Tracked:**
            - Upload/download speeds
            - Query processing times
            - Cache effectiveness
            - System CPU/Memory usage
            - Concurrent request handling
            
            **💡 Performance Tips:**
            - Files are cached after first extraction
            - Subsequent queries on same documents are faster
            - Monitor cache hit rate for optimization
            - Use benchmarks to test system limits
            """)
        
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
            start_time = time.time()
            results = []
            
            if benchmark_type == "Quick Test":
                test_file = list(Path("test_docs").glob("*.pdf"))[:1]
                if test_file:
                    upload_start = time.time()
                    result = await upload_documents_with_metrics(test_file)
                    upload_time = time.time() - upload_start
                    
                    if current_session_id:
                        ask_start = time.time()
                        await ask_question_with_metrics("What is this document about?", current_session_id)
                        ask_time = time.time() - ask_start
                        
                        total_time = time.time() - start_time
                        
                        return f"""✅ **Quick Test Complete**
                        
**Results:**
- Upload time: {upload_time:.2f}s
- Query time: {ask_time:.2f}s
- Total time: {total_time:.2f}s

**Performance Grade:** {'🟢 Excellent' if total_time < 5 else '🟡 Good' if total_time < 10 else '🔴 Needs Optimization'}""", get_performance_charts()
            
            return "❌ Benchmark failed - ensure test documents exist", None
        
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

if __name__ == "__main__":
    demo = create_interface()
    demo.launch(
        server_name="0.0.0.0",
        server_port=7860,
        share=False,
        show_error=True
    )