"""
Launch Gradio UI for Document Insight Service
Make sure the API server is running first (python run.py)
"""
from app.gradio_ui import create_interface

if __name__ == "__main__":
    print("🚀 Starting Gradio UI for Document Insight Service")
    print("=" * 50)
    print("⚠️  Make sure the API server is running on http://localhost:8000")
    print("   Run 'python run.py' in another terminal if not already running")
    print("=" * 50)
    
    demo = create_interface()
    
    print("\n🌐 Launching Gradio interface...")
    demo.launch(
        server_name="0.0.0.0",
        server_port=7860,
        share=False,
        show_error=True
    )