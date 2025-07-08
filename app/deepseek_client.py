import httpx
from typing import Dict, List, Optional
from app.config import config
import json

class DeepSeekClient:
    """Client for interacting with DeepSeek API"""
    
    def __init__(self):
        self.api_key = config.DEEPSEEK_API_KEY
        self.api_url = config.DEEPSEEK_API_URL
        self.model = config.DEFAULT_MODEL
        if not self.api_key:
            raise ValueError("DEEPSEEK_API_KEY not found in environment variables")
    
    async def ask_question(self, context: str, question: str) -> Dict[str, any]:
        """
        Ask a question about the provided context using DeepSeek API
        
        Args:
            context: The extracted text from documents
            question: User's question
            
        Returns:
            Dict containing answer and metadata
        """

        system_prompt = """You are a helpful AI assistant that answers questions based on the provided documents. 
        Always base your answers on the information given in the context. 
        If the answer cannot be found in the provided context, say so clearly.
        Be concise but thorough in your responses."""
        
        user_prompt = f"""Context from uploaded documents:
        
{context[:8000]}  # Limit context to avoid token limits

Question: {question}

Please answer the question based only on the information provided in the context above."""
        

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            "max_tokens": config.MAX_TOKENS,
            "temperature": config.TEMPERATURE
        }
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    self.api_url,
                    headers=headers,
                    json=payload,
                    timeout=30.0
                )
                if response.status_code == 200:
                    data = response.json()
                    answer = data['choices'][0]['message']['content']
                    
                    return {
                        "success": True,
                        "answer": answer,
                        "model": self.model,
                        "usage": data.get('usage', {})
                    }
                else:
                    return {
                        "success": False,
                        "answer": None,
                        "error": f"API error: {response.status_code} - {response.text}"
                    }
                    
        except Exception as e:
            return {
                "success": False,
                "answer": None,
                "error": f"Request failed: {str(e)}"
            }
    
    async def ask_with_multiple_contexts(self, contexts: Dict[str, str], question: str) -> Dict[str, any]:
        """
        Ask a question when multiple documents are involved
        
        Args:
            contexts: Dict mapping filename to extracted text
            question: User's question
        """
        

        combined_context = ""
        for filename, text in contexts.items():
            combined_context += f"\n\n--- Document: {filename} ---\n{text[:3000]}"  # Limit per document
        
        return await self.ask_question(combined_context, question)