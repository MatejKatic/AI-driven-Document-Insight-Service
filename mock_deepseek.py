"""
Mock DeepSeek API for testing without a real API key
"""
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, ConfigDict
from typing import List, Dict, Any, Optional
import random
import time

app = FastAPI(title="Mock DeepSeek API")

class BaseModelConfig(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)

class Message(BaseModelConfig):
    role: str
    content: str

class ChatRequest(BaseModelConfig):
    model: str
    messages: List[Message]
    max_tokens: Optional[int] = 2000
    temperature: Optional[float] = 0.7

class ChatResponse(BaseModelConfig):
    id: str = "mock-response-id"
    object: str = "chat.completion"
    created: int
    model: str
    choices: List[Dict[str, Any]]
    usage: Dict[str, int]

@app.get("/")
async def root():
    return {"message": "Mock DeepSeek API is running", "status": "ready"}

@app.get("/health")
async def health():
    return {"status": "healthy", "timestamp": time.time()}

@app.post("/v1/chat/completions")
async def chat_completions(request: ChatRequest):
    """Mock chat completion endpoint"""
    
    user_messages = [msg for msg in request.messages if msg.role == "user"]
    if not user_messages:
        raise HTTPException(status_code=400, detail="No user message found")
    
    last_message = user_messages[-1].content.lower()
    
    if "what is" in last_message or "explain" in last_message:
        response = "Based on the provided documents, this appears to be a comprehensive analysis of the subject matter. The document contains detailed information about the topic, including key concepts, methodologies, and findings. The main points discussed include various aspects that are relevant to understanding the complete picture."
    
    elif "summarize" in last_message or "summary" in last_message:
        response = "Summary of the documents: The uploaded materials present a thorough examination of the subject. Key findings include: 1) Important discoveries related to the main topic, 2) Significant patterns identified in the data, 3) Relevant conclusions drawn from the analysis. The documents provide valuable insights that contribute to a better understanding of the subject matter."
    
    elif "main topic" in last_message or "about" in last_message:
        response = "The main topic of these documents appears to be a detailed exploration of important concepts and their practical applications. The documents cover various aspects including theoretical foundations, practical implementations, and real-world examples. This comprehensive coverage makes the material suitable for both academic study and practical application."
    
    elif "key points" in last_message or "important" in last_message:
        response = "The key points from the documents include:\n\n1. **Fundamental Concepts**: The documents establish core principles that form the foundation of the subject.\n\n2. **Practical Applications**: Several real-world examples demonstrate how these concepts apply in practice.\n\n3. **Recent Developments**: The material includes updates on the latest advancements in the field.\n\n4. **Best Practices**: Guidelines and recommendations for optimal implementation are provided.\n\n5. **Future Directions**: The documents discuss potential future developments and areas for further research."
    
    elif "conclusion" in last_message or "findings" in last_message:
        response = "The conclusions drawn from these documents indicate significant progress in understanding the subject matter. The findings suggest that the approaches discussed are both effective and practical. The evidence presented supports the main hypotheses, and the results have important implications for future work in this area."
    
    else:
        response = f"Based on the analysis of the uploaded documents, I can provide the following insight regarding your question: '{last_message}'. The documents contain relevant information that addresses this query. The content suggests multiple perspectives on this topic, with evidence supporting various viewpoints. The material provides a comprehensive foundation for understanding the subject matter in depth."
    
    prompt_tokens = sum(len(msg.content.split()) * 1.3 for msg in request.messages)
    completion_tokens = len(response.split()) * 1.3
    
    return ChatResponse(
        created=int(time.time()),
        model=request.model,
        choices=[{
            "index": 0,
            "message": {
                "role": "assistant",
                "content": response
            },
            "finish_reason": "stop"
        }],
        usage={
            "prompt_tokens": int(prompt_tokens),
            "completion_tokens": int(completion_tokens),
            "total_tokens": int(prompt_tokens + completion_tokens)
        }
    )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8080)