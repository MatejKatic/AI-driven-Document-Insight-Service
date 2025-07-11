"""
Quick test script for Docker deployment
Tests basic functionality without requiring external dependencies
"""
import httpx
import asyncio
import sys
from pathlib import Path

async def test_docker_deployment():
    """Test the Docker deployment"""
    print("🧪 Testing AI Document Insight Service Docker Deployment")
    print("=" * 60)
    
    # Check if API is accessible
    print("\n1️⃣ Checking API availability...")
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get("http://localhost:8000/", timeout=5.0)
            if response.status_code == 200:
                print("✅ API is running at http://localhost:8000")
                data = response.json()
                print(f"   Version: {data.get('message', 'Unknown')}")
            else:
                print("❌ API returned unexpected status:", response.status_code)
                return False
    except Exception as e:
        print("❌ Cannot connect to API:", str(e))
        print("\n💡 Make sure Docker services are running:")
        print("   docker-compose up -d")
        return False
    
    # Test file upload
    print("\n2️⃣ Testing file upload...")
    test_file = Path("test_docs/company_report_2024.pdf")
    
    if not test_file.exists():
        print("⚠️  Test file not found, creating test documents...")
        import subprocess
        subprocess.run([sys.executable, "create_test_docs.py"])
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        with open(test_file, "rb") as f:
            files = {"files": (test_file.name, f, "application/pdf")}
            response = await client.post("http://localhost:8000/upload", files=files)
        
        if response.status_code == 200:
            data = response.json()
            session_id = data["session_id"]
            print(f"✅ File uploaded successfully")
            print(f"   Session ID: {session_id}")
            print(f"   Files: {data['uploaded_files']}")
        else:
            print("❌ Upload failed:", response.text)
            return False
    
    # Test question answering
    print("\n3️⃣ Testing question answering...")
    question = "What is the main topic of this document?"
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.post(
            "http://localhost:8000/ask",
            json={"session_id": session_id, "question": question}
        )
        
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Question answered successfully")
            print(f"   Question: {question}")
            print(f"   Answer: {data['answer'][:150]}...")
            print(f"   Processing time: {data.get('processing_time', 0):.2f}s")
        else:
            print("❌ Question answering failed:", response.text)
            return False
    
    # Check cache stats
    print("\n4️⃣ Checking cache performance...")
    async with httpx.AsyncClient() as client:
        response = await client.get("http://localhost:8000/cache/stats")
        if response.status_code == 200:
            data = response.json()
            cache_stats = data["cache_stats"]
            print(f"✅ Cache is working")
            print(f"   Type: {cache_stats['cache_type']}")
            print(f"   Hit rate: {cache_stats['hit_rate']}")
    
    # Check if UI is accessible
    print("\n5️⃣ Checking Gradio UI...")
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get("http://localhost:7860/", timeout=5.0)
            if response.status_code == 200:
                print("✅ Gradio UI is running at http://localhost:7860")
            else:
                print("⚠️  Gradio UI returned status:", response.status_code)
    except:
        print("⚠️  Gradio UI might still be starting...")
    
    print("\n" + "=" * 60)
    print("✅ Docker deployment test completed successfully!")
    print("\n📌 You can now:")
    print("   1. Access the Gradio UI at http://localhost:7860")
    print("   2. View API docs at http://localhost:8000/docs")
    print("   3. Check logs with: docker-compose logs")
    
    return True

if __name__ == "__main__":
    print("Waiting 5 seconds for services to be ready...")
    import time
    time.sleep(5)
    
    success = asyncio.run(test_docker_deployment())
    sys.exit(0 if success else 1)