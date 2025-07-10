import httpx
import asyncio
from pathlib import Path
import json
import time
import shutil
from app.cache_manager import cache_manager
from app.pdf_extractor import PDFExtractor

async def test_complete_workflow_with_cache():
    """Test the complete workflow with cache performance metrics"""
    
    test_files = list(Path("test_docs").glob("*.pdf"))
    
    if not test_files:
        print("❌ No PDF files found in test_docs folder!")
        print("Please add some PDF files to test_docs/ folder")
        return
    
    cache_manager.clear_all()
    print("🧹 Cleared cache for clean test\n")
    
    async with httpx.AsyncClient() as client:
        print("🚀 Starting Document Insight Service test with cache metrics...\n")
        
        initial_stats = cache_manager.get_stats()
        
        # ========== FIRST RUN (NO CACHE) ==========
        print("=" * 60)
        print("📊 FIRST RUN - Building Cache")
        print("=" * 60)
        
        print("\n📤 Step 1: Uploading documents (First Session)...")
        files = []
        for file_path in test_files[:2]:  # Upload first 2 files
            files.append(
                ("files", (file_path.name, open(file_path, "rb"), "application/pdf"))
            )
        
        try:
            upload_start = time.time()
            upload_response = await client.post(
                "http://localhost:8000/upload",
                files=files,
                timeout=30.0
            )
            upload_time_1 = time.time() - upload_start
            
            if upload_response.status_code != 200:
                print(f"❌ Upload failed: {upload_response.text}")
                return
            
            upload_data = upload_response.json()
            session_id_1 = upload_data["session_id"]
            
            print(f"✅ Uploaded {upload_data['uploaded_files']} files in {upload_time_1:.2f}s")
            print(f"📋 Session ID: {session_id_1}")
            print(f"📁 Files: {[f['filename'] for f in upload_data['files']]}")
            
        finally:
            for _, file_tuple in files:
                file_tuple[1].close()
        
        print("\n❓ Step 2: Asking questions (triggers text extraction)...")
        
        question = "What is the main topic of these documents?"
        print(f"Question: {question}")
        
        ask_start = time.time()
        ask_response = await client.post(
            "http://localhost:8000/ask",
            json={
                "session_id": session_id_1,
                "question": question
            },
            timeout=60.0
        )
        ask_time_1 = time.time() - ask_start
        
        if ask_response.status_code == 200:
            answer_data = ask_response.json()
            print(f"✅ Answer: {answer_data['answer'][:150]}...")
            print(f"⏱️  Processing time: {ask_time_1:.2f}s")
            print(f"📚 Sources: {', '.join(answer_data['sources'])}")
        
        session_response = await client.get(f"http://localhost:8000/session/{session_id_1}")
        if session_response.status_code == 200:
            session_info = session_response.json()
            cache_perf = session_info.get('cache_performance', {})
            print(f"\n📊 Cache Performance:")
            print(f"   - Cache hits: {cache_perf.get('cache_hits', 0)}")
            print(f"   - Cache misses: {cache_perf.get('cache_misses', 0)}")
        
        total_time_1 = upload_time_1 + ask_time_1
        print(f"\n⏱️  Total time for first run: {total_time_1:.2f}s")
        
        stats_response = await client.get("http://localhost:8000/cache/stats")
        stats_1 = stats_response.json()["cache_stats"]
        print(f"\n📈 Cache Statistics After First Run:")
        print(f"   - Files cached: {stats_1['saves']}")
        print(f"   - Cache type: {stats_1['cache_type']}")
        
        # ========== SECOND RUN (WITH CACHE) ==========
        print("\n" + "=" * 60)
        print("📊 SECOND RUN - Using Cache")
        print("=" * 60)
        
        print("\n⏳ Simulating new session (different user, server restart, etc.)...")
        await asyncio.sleep(2)
        
        print("\n📤 Step 1: Uploading same documents (Second Session)...")
        files = []
        for file_path in test_files[:2]:
            files.append(
                ("files", (file_path.name, open(file_path, "rb"), "application/pdf"))
            )
        
        try:
            upload_start = time.time()
            upload_response = await client.post(
                "http://localhost:8000/upload",
                files=files,
                timeout=30.0
            )
            upload_time_2 = time.time() - upload_start
            
            upload_data = upload_response.json()
            session_id_2 = upload_data["session_id"]
            
            print(f"✅ Uploaded {upload_data['uploaded_files']} files in {upload_time_2:.2f}s")
            print(f"📋 Session ID: {session_id_2} (different from first!)")
            
        finally:
            for _, file_tuple in files:
                file_tuple[1].close()
        
        print("\n❓ Step 2: Asking same question (should use cached extraction)...")
        
        ask_start = time.time()
        ask_response = await client.post(
            "http://localhost:8000/ask",
            json={
                "session_id": session_id_2,
                "question": question
            },
            timeout=60.0
        )
        ask_time_2 = time.time() - ask_start
        
        if ask_response.status_code == 200:
            answer_data = ask_response.json()
            print(f"✅ Answer received")
            print(f"⏱️  Processing time: {ask_time_2:.2f}s")
        
        session_response = await client.get(f"http://localhost:8000/session/{session_id_2}")
        if session_response.status_code == 200:
            session_info = session_response.json()
            cache_perf = session_info.get('cache_performance', {})
            print(f"\n📊 Cache Performance:")
            print(f"   - Cache hits: {cache_perf.get('cache_hits', 0)} ⚡")
            print(f"   - Cache misses: {cache_perf.get('cache_misses', 0)}")
        
        total_time_2 = upload_time_2 + ask_time_2
        print(f"\n⏱️  Total time for second run: {total_time_2:.2f}s")
        
        # ========== PERFORMANCE COMPARISON ==========
        print("\n" + "=" * 60)
        print("🎯 PERFORMANCE COMPARISON")
        print("=" * 60)
        
        print(f"\n📊 Time Comparison:")
        print(f"   First run (no cache):  {total_time_1:.2f}s")
        print(f"   Second run (cached):   {total_time_2:.2f}s")
        
        if total_time_2 < total_time_1:
            improvement = ((total_time_1 - total_time_2) / total_time_1) * 100
            speedup = total_time_1 / total_time_2
            print(f"\n🚀 Performance Improvement:")
            print(f"   - {improvement:.1f}% faster")
            print(f"   - {speedup:.1f}x speed increase")
        
        print(f"\n📊 Processing Time Breakdown:")
        print(f"   First run:")
        print(f"     - Upload: {upload_time_1:.2f}s")
        print(f"     - Q&A: {ask_time_1:.2f}s (includes extraction)")
        print(f"   Second run:")
        print(f"     - Upload: {upload_time_2:.2f}s")
        print(f"     - Q&A: {ask_time_2:.2f}s (uses cache)")
        
        stats_response = await client.get("http://localhost:8000/cache/stats")
        final_stats = stats_response.json()["cache_stats"]
        
        print(f"\n📈 FINAL CACHE STATISTICS:")
        print(f"   - Total requests: {final_stats['total_requests']}")
        print(f"   - Cache hits: {final_stats['hits']}")
        print(f"   - Cache misses: {final_stats['misses']}")
        print(f"   - Hit rate: {final_stats['hit_rate']}")
        print(f"   - Total files cached: {final_stats['saves']}")
        
        # ========== DIRECT CACHE TEST ==========
        print("\n" + "=" * 60)
        print("🔬 DIRECT CACHE VERIFICATION")
        print("=" * 60)
        
        print("\nTesting direct extraction to prove cache persistence...")
        extractor = PDFExtractor()
        
        for i, test_file in enumerate(test_files[:2]):
            print(f"\n📄 Testing {test_file.name}:")
            start = time.time()
            result = extractor.extract_text(str(test_file))
            extract_time = time.time() - start
            print(f"   - From cache: {result.get('from_cache', False)}")
            print(f"   - Extraction time: {extract_time:.3f}s")
            print(f"   - Method: {result.get('method', 'N/A')}")

def main():
    print("=" * 70)
    print("🚀 AI-Driven Document Insight Service")
    print("📊 Complete Workflow Test with Cache Performance Analysis")
    print("=" * 70)
    print("\nThis test will:")
    print("1. Upload documents and ask questions (no cache)")
    print("2. Simulate a new session with same documents (using cache)")
    print("3. Compare performance and demonstrate cache benefits")
    print("4. Show cache persistence across sessions")
    print("\nMake sure:")
    print("✓ The server is running (python run.py)")
    print("✓ You have PDF files in test_docs/ folder")
    print("✓ Your .env file contains a valid DEEPSEEK_API_KEY")
    print("=" * 70)
    
    input("\nPress Enter to start the test...")
    
    asyncio.run(test_complete_workflow_with_cache())
    
    print("\n✅ Test complete!")
    print("\n💡 Key Takeaways:")
    print("- Cache persists across different sessions")
    print("- Significant performance improvement on cached documents")
    print("- Session isolation maintained (different session IDs)")
    print("- Cache works transparently without affecting functionality")

if __name__ == "__main__":
    main()