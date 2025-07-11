import httpx
from typing import Dict, List, Optional
from app.config import config
from app.performance import performance_monitor, track_performance
import json
import time

class DeepSeekClient:
    """Client for interacting with DeepSeek API with performance monitoring"""
    
    def __init__(self):
        self.api_key = config.DEEPSEEK_API_KEY
        self.api_url = config.DEEPSEEK_API_URL
        self.model = config.get_default_model()
        self.api_stats = {
            "total_requests": 0,
            "successful_requests": 0,
            "failed_requests": 0,
            "total_tokens_used": 0,
            "total_cost_estimate": 0.0
        }
        
        if not self.api_key:
            raise ValueError("DEEPSEEK_API_KEY not found in environment variables")
    
    @track_performance("deepseek_api_call")
    async def ask_question(self, context: str, question: str) -> Dict[str, any]:
        """
        Ask a question about the provided context using DeepSeek API with performance tracking
        
        Args:
            context: The extracted text from documents
            question: User's question
            
        Returns:
            Dict containing answer and metadata with performance metrics
        """
        self.api_stats["total_requests"] += 1
        request_start = time.time()
        
        system_prompt = """You are a helpful AI assistant that answers questions based on the provided documents. 
        Always base your answers on the information given in the context. 
        If the answer cannot be found in the provided context, say so clearly.
        Be concise but thorough in your responses."""
        
        context_limit = 8000
        truncated = False
        if len(context) > context_limit:
            context = context[:context_limit]
            truncated = True
        
        user_prompt = f"""Context from uploaded documents:
        
{context}

Question: {question}

Please answer the question based only on the information provided in the context above."""
        
        approx_tokens = len(system_prompt + user_prompt) // 4  # Rough estimation
        
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
        
        payload_size = len(json.dumps(payload))
        performance_monitor.record_metric(
            "api_payload_size_kb",
            payload_size / 1024,
            {"context_truncated": truncated}
        )
        
        try:
            api_start = time.time()
            
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    self.api_url,
                    headers=headers,
                    json=payload,
                    timeout=120.0
                )
                
            api_latency = (time.time() - api_start) * 1000
            
            performance_monitor.record_metric(
                "deepseek_api_latency_ms",
                api_latency,
                {"status_code": response.status_code}
            )
            
            if response.status_code == 200:
                data = response.json()
                answer = data['choices'][0]['message']['content']
                usage = data.get('usage', {})
                
                self.api_stats["successful_requests"] += 1
                if usage:
                    self.api_stats["total_tokens_used"] += usage.get('total_tokens', 0)
                    # Estimate cost (example: $0.001 per 1K tokens)
                    cost_estimate = (usage.get('total_tokens', 0) / 1000) * 0.001
                    self.api_stats["total_cost_estimate"] += cost_estimate
                
                performance_monitor.record_metric(
                    "deepseek_tokens_used",
                    usage.get('total_tokens', 0),
                    {
                        "prompt_tokens": usage.get('prompt_tokens', 0),
                        "completion_tokens": usage.get('completion_tokens', 0)
                    }
                )
                
                performance_monitor.record_metric(
                    "deepseek_response_length",
                    len(answer),
                    {"question_length": len(question)}
                )
                
                total_time = (time.time() - request_start) * 1000
                
                return {
                    "success": True,
                    "answer": answer,
                    "model": self.model,
                    "usage": usage,
                    "api_latency_ms": api_latency,
                    "total_time_ms": total_time,
                    "context_truncated": truncated,
                    "approx_input_tokens": approx_tokens
                }
            else:
                self.api_stats["failed_requests"] += 1
                error_msg = f"API error: {response.status_code} - {response.text}"
                
                performance_monitor.record_metric(
                    "deepseek_api_error",
                    1,
                    {
                        "status_code": response.status_code,
                        "error": response.text[:100]
                    }
                )
                
                return {
                    "success": False,
                    "answer": None,
                    "error": error_msg,
                    "api_latency_ms": api_latency
                }
                
        except httpx.TimeoutException:
            self.api_stats["failed_requests"] += 1
            
            performance_monitor.record_metric(
                "deepseek_api_timeout",
                1,
                {"timeout_seconds": 30}
            )
            
            return {
                "success": False,
                "answer": None,
                "error": "Request timed out after 30 seconds"
            }
        except Exception as e:
            self.api_stats["failed_requests"] += 1
            
            performance_monitor.record_metric(
                "deepseek_api_exception",
                1,
                {"exception_type": type(e).__name__}
            )
            
            return {
                "success": False,
                "answer": None,
                "error": f"Request failed: {str(e)}"
            }
    
    async def ask_with_multiple_contexts(self, contexts: Dict[str, str], question: str) -> Dict[str, any]:
        """
        Ask a question when multiple documents are involved with performance tracking
        
        Args:
            contexts: Dict mapping filename to extracted text
            question: User's question
        """
        combine_start = time.time()
        
        combined_context = ""
        total_chars = 0
        doc_count = 0
        
        for filename, text in contexts.items():
            doc_text = text[:3000] if len(text) > 3000 else text
            combined_context += f"\n\n--- Document: {filename} ---\n{doc_text}"
            total_chars += len(doc_text)
            doc_count += 1
        
        combine_time = (time.time() - combine_start) * 1000
        
        performance_monitor.record_metric(
            "context_combination_time_ms",
            combine_time,
            {
                "document_count": doc_count,
                "total_characters": total_chars,
                "avg_chars_per_doc": total_chars / doc_count if doc_count > 0 else 0
            }
        )
        
        result = await self.ask_question(combined_context, question)
        
        result["document_count"] = doc_count
        result["total_context_chars"] = total_chars
        
        return result
    
    def get_api_stats(self) -> Dict[str, any]:
        """Get API usage statistics"""
        success_rate = (
            self.api_stats["successful_requests"] / self.api_stats["total_requests"] * 100
            if self.api_stats["total_requests"] > 0 else 0
        )
        
        avg_cost_per_request = (
            self.api_stats["total_cost_estimate"] / self.api_stats["successful_requests"]
            if self.api_stats["successful_requests"] > 0 else 0
        )
        
        return {
            **self.api_stats,
            "success_rate": f"{success_rate:.1f}%",
            "avg_cost_per_request": f"${avg_cost_per_request:.4f}",
            "avg_tokens_per_request": (
                self.api_stats["total_tokens_used"] / self.api_stats["successful_requests"]
                if self.api_stats["successful_requests"] > 0 else 0
            ),
            "performance_metrics": {
                "api_latency": performance_monitor.get_stats("deepseek_api_latency_ms"),
                "token_usage": performance_monitor.get_stats("deepseek_tokens_used"),
                "response_length": performance_monitor.get_stats("deepseek_response_length")
            }
        }
    
    async def health_check(self) -> Dict[str, any]:
        """Perform a health check on the DeepSeek API"""
        health_start = time.time()
        
        try:
            result = await self.ask_question(
                "This is a test document.",
                "What is this document?"
            )
            
            health_time = (time.time() - health_start) * 1000
            
            return {
                "status": "healthy" if result["success"] else "unhealthy",
                "response_time_ms": health_time,
                "api_reachable": result["success"],
                "model": self.model,
                "error": result.get("error") if not result["success"] else None
            }
        except Exception as e:
            return {
                "status": "unhealthy",
                "response_time_ms": (time.time() - health_start) * 1000,
                "api_reachable": False,
                "error": str(e)
            }