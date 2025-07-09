"""Direct cache test that bypasses session memory to show cache working"""
import asyncio
import time
from pathlib import Path
import shutil
import httpx
from app.pdf_extractor import PDFExtractor
from app.cache_manager import cache_manager

async def test_cache_directly():
    """Test cache by simulating real-world scenario"""
    
    print("🧪 Direct Cache Test - Simulating Real Usage")
    print("=" * 60)
    
    test_files = list(Path("test_docs").glob("*.pdf"))[:2]
    if not test_files:
        print("❌ No PDF files found in test_docs folder!")
        return
    
    cache_manager.clear_all()
    print("🧹 Cleared cache for clean test\n")
    
    extractor = PDFExtractor()
    
    print("📋 TEST 1: Direct Extraction (bypassing API)")
    print("-" * 40)
    
    test_file = test_files[0]
    print(f"Testing with: {test_file.name}")
    
    print("\n1️⃣ First extraction (no cache):")
    start = time.time()
    result1 = extractor.extract_text(str(test_file))
    time1 = time.time() - start
    print(f"   ⏱️  Time: {time1:.2f}s")
    print(f"   📊 From cache: {result1.get('from_cache', False)}")
    
    print("\n2️⃣ Second extraction (should use cache):")
    start = time.time()
    result2 = extractor.extract_text(str(test_file))
    time2 = time.time() - start
    print(f"   ⏱️  Time: {time2:.2f}s")
    print(f"   📊 From cache: {result2.get('from_cache', False)}")
    
    if result2.get('from_cache'):
        speedup = time1 / time2 if time2 > 0 else float('inf')
        print(f"\n   🚀 Cache made it {speedup:.0f}x faster!")
    
    print("\n\n📋 TEST 2: API Test with Session Simulation")
    print("-" * 40)
    
    async with httpx.AsyncClient(timeout=60.0) as client:
        print("\n1️⃣ First session - upload and extract:")
        
        upload_dir = Path("uploads/test_cache_session")
        upload_dir.mkdir(exist_ok=True, parents=True)
        
        fixed_files = []
        for i, test_file in enumerate(test_files):
            fixed_path = upload_dir / f"test_file_{i}_{test_file.name}"
            shutil.copy(test_file, fixed_path)
            fixed_files.append(fixed_path)
        
        files = []
        for file_path in fixed_files:
            files.append(
                ("files", (file_path.name, open(file_path, "rb"), "application/pdf"))
            )
        
        start = time.time()
        upload_response = await client.post(
            "http://localhost:8000/upload",
            files=files
        )
        session_id = upload_response.json()["session_id"]
        
        for _, file_tuple in files:
            file_tuple[1].close()
        
        await client.post(
            "http://localhost:8000/ask",
            json={
                "session_id": session_id,
                "question": "What is this about?"
            }
        )
        
        time_first = time.time() - start
        print(f"   ⏱️  Total time: {time_first:.2f}s")
        
        stats = await client.get("http://localhost:8000/cache/stats")
        cache_data = stats.json()["cache_stats"]
        print(f"   📊 Cache saves: {cache_data['saves']}")
        
        print("\n2️⃣ Simulating new session with same files:")
        print("   (In real world: server restart, different user, etc.)")
        
        start = time.time()
        for fixed_file in fixed_files:
            result = extractor.extract_text(str(fixed_file))
            print(f"   📄 {fixed_file.name}: Cache hit = {result.get('from_cache', False)}")
        
        time_cache = time.time() - start
        print(f"   ⏱️  Extraction time: {time_cache:.2f}s")
        
        print("\n📊 FINAL CACHE STATISTICS:")
        print("-" * 40)
        
        final_stats = cache_manager.get_stats()
        print(f"Cache type: {final_stats['cache_type']}")
        print(f"Total requests: {final_stats['total_requests']}")
        print(f"Cache hits: {final_stats['hits']}")
        print(f"Cache misses: {final_stats['misses']}")
        print(f"Hit rate: {final_stats['hit_rate']}")
        
        shutil.rmtree(upload_dir, ignore_errors=True)

def main():
    print("Direct Cache Test")
    print("This test shows cache working by:")
    print("1. Testing extraction directly (bypassing session memory)")
    print("2. Simulating real-world usage patterns")
    print("=" * 60)
    
    asyncio.run(test_cache_directly())
    
    print("\n✅ Test complete!")
    print("\n💡 Key Insights:")
    print("- Session memory acts as L1 cache (fastest)")
    print("- File/Redis cache acts as L2 cache (persistent)")
    print("- Cache helps most when sessions are cleared/restarted")

if __name__ == "__main__":
    main()