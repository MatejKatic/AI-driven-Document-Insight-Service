import httpx
import asyncio
from pathlib import Path
import json

async def test_complete_workflow():
    """Test the complete workflow: upload files and ask questions"""
    
    test_files = list(Path("test_docs").glob("*.pdf"))
    
    if not test_files:
        print("❌ No PDF files found in test_docs folder!")
        print("Please add some PDF files to test_docs/ folder")
        return
    
    async with httpx.AsyncClient() as client:
        print("🚀 Starting Document Insight Service test...\n")
        
        print("📤 Step 1: Uploading documents...")
        files = []
        for file_path in test_files[:2]:  # Upload first 2 files
            files.append(
                ("files", (file_path.name, open(file_path, "rb"), "application/pdf"))
            )
        
        try:
            upload_response = await client.post(
                "http://localhost:8000/upload",
                files=files,
                timeout=30.0
            )
            
            if upload_response.status_code != 200:
                print(f"❌ Upload failed: {upload_response.text}")
                return
            
            upload_data = upload_response.json()
            session_id = upload_data["session_id"]
            
            print(f"✅ Uploaded {upload_data['uploaded_files']} files")
            print(f"📋 Session ID: {session_id}")
            print(f"📁 Files: {[f['filename'] for f in upload_data['files']]}\n")
            
        finally:
            for _, file_tuple in files:
                file_tuple[1].close()
        
        print("❓ Step 2: Asking questions about the documents...\n")
        
        test_questions = [
            "What is the main topic of these documents?",
            "Can you summarize the key points?",
            "What are the most important findings or conclusions?",
        ]
        
        for i, question in enumerate(test_questions, 1):
            print(f"Question {i}: {question}")
            
            request_data = {
                "session_id": session_id,
                "question": question
            }
            
            try:
                ask_response = await client.post(
                    "http://localhost:8000/ask",
                    json=request_data,
                    timeout=60.0  # Longer timeout for API calls
                )
                
                if ask_response.status_code == 200:
                    answer_data = ask_response.json()
                    print(f"✅ Answer: {answer_data['answer'][:200]}...")
                    print(f"⏱️  Processing time: {answer_data['processing_time']:.2f}s")
                    print(f"📚 Sources: {', '.join(answer_data['sources'])}\n")
                else:
                    print(f"❌ Failed to get answer: {ask_response.text}\n")
                    
            except httpx.TimeoutException:
                print("❌ Request timed out. Make sure your DeepSeek API key is valid.\n")
            except Exception as e:
                print(f"❌ Error: {str(e)}\n")
        
        print("📊 Step 3: Retrieving session information...")
        session_response = await client.get(
            f"http://localhost:8000/session/{session_id}"
        )
        
        if session_response.status_code == 200:
            session_info = session_response.json()
            print(f"✅ Session created at: {session_info['created_at']}")
            print(f"📁 Files in session:")
            for file in session_info['files']:
                print(f"   - {file['filename']} ({file['size']} bytes)")

def main():
    print("=" * 60)
    print("AI-Driven Document Insight Service - Complete Workflow Test")
    print("=" * 60)
    print("\nMake sure:")
    print("1. The server is running (python run.py)")
    print("2. You have PDF files in test_docs/ folder")
    print("3. Your .env file contains a valid DEEPSEEK_API_KEY")
    print("=" * 60)
    
    input("\nPress Enter to start the test...")
    
    asyncio.run(test_complete_workflow())

if __name__ == "__main__":
    main()