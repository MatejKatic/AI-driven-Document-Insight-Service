import asyncio
import httpx
from dotenv import load_dotenv
import os

async def test_deepseek_api():
    """Test if DeepSeek API is working"""
    
    # Load environment variables
    load_dotenv()
    api_key = os.getenv("DEEPSEEK_API_KEY")
    
    if not api_key:
        print("❌ DEEPSEEK_API_KEY not found in .env file!")
        return
    
    print(f"✅ API Key found: {api_key[:10]}...")
    
    # Test API
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    
    payload = {
        "model": "deepseek-chat",
        "messages": [
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": "Say 'Hello, the API is working!' in exactly those words."}
        ],
        "max_tokens": 50
    }
    
    try:
        async with httpx.AsyncClient() as client:
            print("🔄 Testing DeepSeek API...")
            response = await client.post(
                "https://api.deepseek.com/v1/chat/completions",
                headers=headers,
                json=payload,
                timeout=15.0
            )
            
            if response.status_code == 200:
                data = response.json()
                answer = data['choices'][0]['message']['content']
                print(f"✅ API Response: {answer}")
                print("✅ DeepSeek API is working correctly!")
            else:
                print(f"❌ API Error: {response.status_code}")
                print(f"Response: {response.text}")
                
    except Exception as e:
        print(f"❌ Connection Error: {str(e)}")

if __name__ == "__main__":
    print("Testing DeepSeek API Connection...")
    print("-" * 40)
    asyncio.run(test_deepseek_api())