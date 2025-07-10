"""
Run both API server and Gradio UI
Windows-friendly version with real-time output
"""
import subprocess
import time
import sys
import os
from pathlib import Path
import threading
import signal

if sys.platform == "win32":
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

def stream_output(process, name):
    """Stream output from subprocess in real-time"""
    try:
        while True:
            line = process.stdout.readline()
            if not line and process.poll() is not None:
                break
            if line:
                print(f"[{name}] {line.strip()}", flush=True)
    except:
        pass

def stream_error(process, name):
    """Stream error output from subprocess in real-time"""
    try:
        while True:
            line = process.stderr.readline()
            if not line and process.poll() is not None:
                break
            if line:
                print(f"[{name} ERROR] {line.strip()}", flush=True)
    except:
        pass

def run_services():
    print("Starting AI Document Insight Service (API + UI)", flush=True)
    print("=" * 60, flush=True)
    
    if not Path(".env").exists():
        print("Warning: .env file not found!", flush=True)
        print("Copy .env.example to .env and add your DEEPSEEK_API_KEY", flush=True)
        print(flush=True)
    
    env = os.environ.copy()
    current_dir = os.path.dirname(os.path.abspath(__file__))
    env['PYTHONUNBUFFERED'] = '1'
    if sys.platform == "win32":
        env['PYTHONIOENCODING'] = 'utf-8'
    
    if 'PYTHONPATH' in env:
        env['PYTHONPATH'] = f"{current_dir}{os.pathsep}{env['PYTHONPATH']}"
    else:
        env['PYTHONPATH'] = current_dir
    
    sys.path.insert(0, current_dir)
    
    api_process = None
    ui_process = None
    
    try:
        print("\n1. Starting API server on http://localhost:8000...", flush=True)
        
        api_process = subprocess.Popen(
            [sys.executable, "-u", "run.py"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            env=env,
            cwd=current_dir,
            bufsize=0,
            universal_newlines=True,
            encoding='utf-8',
            errors='replace'
        )
        
        api_stdout_thread = threading.Thread(target=stream_output, args=(api_process, "API"))
        api_stderr_thread = threading.Thread(target=stream_error, args=(api_process, "API"))
        api_stdout_thread.daemon = True
        api_stderr_thread.daemon = True
        api_stdout_thread.start()
        api_stderr_thread.start()
        
        print("   Waiting for API to start...", flush=True)
        time.sleep(5)
        
        import httpx
        api_ready = False
        for i in range(10):
            try:
                response = httpx.get("http://localhost:8000/", timeout=2)
                if response.status_code == 200:
                    print("   [OK] API server is ready!", flush=True)
                    api_ready = True
                    break
            except:
                time.sleep(1)
        
        if not api_ready:
            print("   [WARNING] API might still be starting...", flush=True)
        
        print("\n2. Starting Gradio UI on http://localhost:7860...", flush=True)
        
        ui_process = subprocess.Popen(
            [sys.executable, "-u", "run_gradio.py"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            env=env,
            cwd=current_dir,
            bufsize=0,
            universal_newlines=True,
            encoding='utf-8',
            errors='replace'
        )
        
        ui_stdout_thread = threading.Thread(target=stream_output, args=(ui_process, "Gradio"))
        ui_stderr_thread = threading.Thread(target=stream_error, args=(ui_process, "Gradio"))
        ui_stdout_thread.daemon = True
        ui_stderr_thread.daemon = True
        ui_stdout_thread.start()
        ui_stderr_thread.start()
        
        time.sleep(5)
        
        print("\n" + "=" * 60, flush=True)
        print("Both services should be running!", flush=True)
        print("\nAccess points:", flush=True)
        print("   - Gradio UI: http://localhost:7860", flush=True)
        print("   - API Docs:  http://localhost:8000/docs", flush=True)
        print("   - API Root:  http://localhost:8000", flush=True)
        print("\nPress Ctrl+C to stop both services", flush=True)
        print("=" * 60 + "\n", flush=True)
        
        while True:
            if api_process.poll() is not None:
                print("\n[ERROR] API server stopped unexpectedly!", flush=True)
                break
            if ui_process.poll() is not None:
                print("\n[ERROR] Gradio UI stopped unexpectedly!", flush=True)
                break
            
            time.sleep(0.5)
            
    except KeyboardInterrupt:
        print("\n\nShutting down services...", flush=True)
        
    finally:
        if api_process and api_process.poll() is None:
            api_process.terminate()
            try:
                api_process.wait(timeout=5)
                print("   - API server stopped", flush=True)
            except subprocess.TimeoutExpired:
                api_process.kill()
                print("   - API server force stopped", flush=True)
        
        if ui_process and ui_process.poll() is None:
            ui_process.terminate()
            try:
                ui_process.wait(timeout=5)
                print("   - Gradio UI stopped", flush=True)
            except subprocess.TimeoutExpired:
                ui_process.kill()
                print("   - Gradio UI force stopped", flush=True)
        
        print("\nAll services stopped!", flush=True)

if __name__ == "__main__":
    signal.signal(signal.SIGINT, lambda sig, frame: sys.exit(0))
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    
    run_services()