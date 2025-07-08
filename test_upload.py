import httpx
import asyncio
from pathlib import Path

async def test_upload():
    """Test the upload endpoint with sample files"""
    
    test_files = list(Path("test_docs").glob("*.pdf"))
    
    if not test_files:
        print("No PDF files found in test_docs folder!")
        return
    
    async with httpx.AsyncClient() as client:
        files = []
        for file_path in test_files[:2]:  # Upload first 2 files
            files.append(
                ("files", (file_path.name, open(file_path, "rb"), "application/pdf"))
            )
        
        try:
            response = await client.post(
                "http://localhost:8000/upload",
                files=files
            )
            
            print(f"Status: {response.status_code}")
            print(f"Response: {response.json()}")
            
            if response.status_code == 200:
                session_id = response.json()["session_id"]
                session_response = await client.get(
                    f"http://localhost:8000/session/{session_id}"
                )
                print(f"\nSession Info: {session_response.json()}")
                
        finally:
            for _, file_tuple in files:
                file_tuple[1].close()

if __name__ == "__main__":
    asyncio.run(test_upload())