"""
Document Intelligence Module
Provides advanced document analysis and similarity search capabilities
"""
import numpy as np
from typing import List, Dict, Tuple, Optional
from collections import Counter
import re
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import hashlib
import json
from datetime import datetime
from app.cache_manager import cache_manager
from app.performance import performance_monitor, track_performance
from app.deepseek_client import DeepSeekClient

class DocumentIntelligence:
    """Advanced document analysis and intelligence features"""
    
    def __init__(self):
        self.deepseek_client = DeepSeekClient()
        self.vectorizer = TfidfVectorizer(
            max_features=1000,
            stop_words='english',
            ngram_range=(1, 2)
        )
        self.document_vectors = {}
        self.document_metadata = {}
    
    @track_performance("document_analysis")
    async def analyze_document(self, text: str, filename: str) -> Dict:
        """
        Perform comprehensive document analysis
        
        Returns:
            Dict containing document insights
        """
        cache_key = f"doc_analysis_{hashlib.md5(text.encode()).hexdigest()[:16]}"
        cached_result = cache_manager.get(cache_key)
        if cached_result:
            return cached_result
        
        analysis = {
            "filename": filename,
            "timestamp": datetime.now().isoformat(),
            "basic_stats": self._get_basic_stats(text),
            "complexity_score": self._calculate_complexity(text),
            "key_topics": await self._extract_key_topics(text),
            "document_type": self._detect_document_type(text),
            "language_features": self._analyze_language(text),
            "summary": await self._generate_summary(text)
        }
        
        cache_manager.set(cache_key, analysis, ttl_hours=48)
        
        return analysis
    
    def _get_basic_stats(self, text: str) -> Dict:
        """Calculate basic document statistics"""
        words = text.split()
        sentences = re.split(r'[.!?]+', text)
        paragraphs = text.split('\n\n')
        
        return {
            "character_count": len(text),
            "word_count": len(words),
            "sentence_count": len([s for s in sentences if s.strip()]),
            "paragraph_count": len([p for p in paragraphs if p.strip()]),
            "avg_word_length": np.mean([len(w) for w in words]) if words else 0,
            "avg_sentence_length": np.mean([len(s.split()) for s in sentences if s.strip()]) if sentences else 0,
            "reading_time_minutes": len(words) / 200  # Assuming 200 words per minute
        }
    
    def _calculate_complexity(self, text: str) -> float:
        """
        Calculate document complexity score (0-100)
        Based on vocabulary diversity, sentence length, and word complexity
        """
        words = text.lower().split()
        if not words:
            return 0
        
        unique_words = len(set(words))
        diversity_score = (unique_words / len(words)) * 100 if words else 0
        
        avg_word_length = np.mean([len(w) for w in words])
        length_score = min(avg_word_length * 10, 100)
        
        sentences = re.split(r'[.!?]+', text)
        avg_sentence_length = np.mean([len(s.split()) for s in sentences if s.strip()])
        sentence_score = min(avg_sentence_length * 2, 100)
        
        complexity = (diversity_score * 0.4 + length_score * 0.3 + sentence_score * 0.3)
        
        return round(complexity, 2)
    
    def _detect_document_type(self, text: str) -> str:
        """Detect the type of document based on content patterns"""
        text_lower = text.lower()
        
        patterns = {
            "contract": ["agreement", "party", "shall", "terms", "conditions", "hereby"],
            "invoice": ["invoice", "total", "amount", "payment", "due date", "bill"],
            "report": ["executive summary", "findings", "conclusion", "analysis", "results"],
            "email": ["from:", "to:", "subject:", "dear", "regards", "sincerely"],
            "academic": ["abstract", "introduction", "methodology", "references", "figure"],
            "technical": ["implementation", "algorithm", "system", "performance", "architecture"],
            "financial": ["revenue", "profit", "loss", "balance", "fiscal", "quarter"]
        }
        
        scores = {}
        for doc_type, keywords in patterns.items():
            score = sum(1 for keyword in keywords if keyword in text_lower)
            scores[doc_type] = score
        
        if max(scores.values()) > 2:
            return max(scores, key=scores.get)
        return "general"
    
    def _analyze_language(self, text: str) -> Dict:
        """Analyze language features of the document"""
        words = text.split()
        
        word_freq = Counter(word.lower() for word in words if len(word) > 3)
        most_common = word_freq.most_common(10)
        
        numbers = re.findall(r'\b\d+\.?\d*\b', text)
        dates = re.findall(r'\b\d{1,2}[/-]\d{1,2}[/-]\d{2,4}\b', text)
        
        technical_terms = re.findall(r'\b[A-Z]{2,}\b', text)  # Acronyms
        
        return {
            "most_frequent_words": [word for word, _ in most_common],
            "number_count": len(numbers),
            "date_count": len(dates),
            "acronym_count": len(technical_terms),
            "question_count": text.count('?'),
            "exclamation_count": text.count('!')
        }
    
    @track_performance("extract_key_topics")
    async def _extract_key_topics(self, text: str, num_topics: int = 5) -> List[str]:
        """Extract key topics using DeepSeek API"""
        prompt = f"""Extract the {num_topics} most important topics or themes from this document. 
        Return only the topics as a JSON array of strings.
        
        Document excerpt: {text[:2000]}...
        
        Response format: ["topic1", "topic2", "topic3", "topic4", "topic5"]"""
        
        result = await self.deepseek_client.ask_question("", prompt)
        
        if result["success"]:
            try:
                topics = json.loads(result["answer"])
                return topics[:num_topics] if isinstance(topics, list) else []
            except:
                return self._extract_topics_fallback(text, num_topics)
        
        return self._extract_topics_fallback(text, num_topics)
    
    def _extract_topics_fallback(self, text: str, num_topics: int) -> List[str]:
        """Fallback topic extraction using TF-IDF"""
        words = text.split()
        word_freq = Counter(word.lower() for word in words if len(word) > 4)
        return [word for word, _ in word_freq.most_common(num_topics)]
    
    @track_performance("generate_summary")
    async def _generate_summary(self, text: str, max_length: int = 150) -> str:
        """Generate a concise summary of the document"""
        prompt = f"""Provide a concise summary of this document in {max_length} words or less.
        Focus on the main points and key information.
        
        Document: {text[:3000]}...
        
        Summary:"""
        
        result = await self.deepseek_client.ask_question("", prompt)
        
        if result["success"]:
            return result["answer"]
        
        sentences = re.split(r'[.!?]+', text)
        return ". ".join(sentences[:3]) + "." if sentences else "Summary unavailable"
    
  
    @track_performance("generate_smart_questions")
    async def generate_smart_questions(self, text: str, num_questions: int = 5) -> List[Dict[str, str]]:
        """
        Generate intelligent questions based on document content
        
        Returns:
            List of dictionaries with 'question' and 'category' keys
        """
        cache_key = f"smart_questions_{hashlib.md5(text.encode()).hexdigest()[:16]}_{num_questions}"
        cached_result = cache_manager.get(cache_key)
        if cached_result:
            return cached_result
        
        example_questions = []
        categories = ['factual', 'analytical', 'comparative', 'clarification']
        for i in range(min(num_questions, 3)):  # Show 3 examples
            cat = categories[i % len(categories)]
            example_questions.append(f'{{"question": "Example question {i+1}...", "category": "{cat}"}}')
        
        example_questions_str = ',\n            '.join(example_questions)
        prompt = f"""Based on this document, generate exactly {num_questions} insightful questions that someone might ask.
Include different types of questions: factual, analytical, comparative, and clarification.

Return as a JSON array with exactly {num_questions} objects containing 'question' and 'category' fields.
Categories should be one of: 'factual', 'analytical', 'comparative', 'clarification'

Document excerpt: {text[:2000]}...

Response format (generate exactly {num_questions} questions):
[
    {example_questions_str},
    ... (continue until {num_questions} questions)
]"""
        
        result = await self.deepseek_client.ask_question("", prompt)
        
        questions = []
        if result["success"]:
            try:
                questions = json.loads(result["answer"])
                if isinstance(questions, list) and len(questions) < num_questions:
                    basic_questions = self._generate_basic_questions(text)
                    questions.extend(basic_questions[len(questions):num_questions])
                questions = questions[:num_questions]  # Limit to requested number
            except:
                questions = self._generate_basic_questions(text)[:num_questions]
        else:
            questions = self._generate_basic_questions(text)[:num_questions]
        
        cache_manager.set(cache_key, questions, ttl_hours=48)
        
        return questions
    
    def _generate_basic_questions(self, text: str) -> List[Dict[str, str]]:
        """Generate basic questions as fallback"""
        questions = [
            {"question": "What is the main topic of this document?", "category": "factual"},
            {"question": "What are the key points mentioned?", "category": "analytical"},
            {"question": "Are there any important dates or numbers?", "category": "factual"},
            {"question": "What conclusions can be drawn?", "category": "analytical"},
            {"question": "How does this relate to other documents?", "category": "comparative"},
            {"question": "What specific details are provided?", "category": "factual"},
            {"question": "What are the implications of this information?", "category": "analytical"},
            {"question": "Are there any unclear or ambiguous points?", "category": "clarification"},
            {"question": "What actions or recommendations are suggested?", "category": "analytical"},
            {"question": "How current is this information?", "category": "clarification"}
        ]
        return questions

    @track_performance("similarity_search")
    def similarity_search(self, query: str, documents: Dict[str, str], 
                         threshold: float = 0.3, top_k: int = 5) -> List[Dict]:
        """
        Find similar content across multiple documents
        
        Args:
            query: Search query
            documents: Dict mapping filenames to extracted text
            threshold: Minimum similarity score (0-1)
            top_k: Maximum number of results to return
            
        Returns:
            List of similar sections with metadata
        """
        if not documents:
            return []
        
        all_chunks = []
        chunk_metadata = []
        
        for filename, text in documents.items():
            chunks = self._split_into_chunks(text, chunk_size=500)
            
            for i, chunk in enumerate(chunks):
                all_chunks.append(chunk)
                chunk_metadata.append({
                    "filename": filename,
                    "chunk_index": i,
                    "chunk_text": chunk[:200] + "..." if len(chunk) > 200 else chunk
                })
        
        if not all_chunks:
            return []
        
        all_texts = all_chunks + [query]
        
        try:
            vectors = self.vectorizer.fit_transform(all_texts)
        except:
            return self._fallback_similarity_search(query, all_chunks, chunk_metadata, threshold, top_k)
        
        query_vector = vectors[-1]
        chunk_vectors = vectors[:-1]
        
        similarities = cosine_similarity(query_vector, chunk_vectors).flatten()
        
        results = []
        for i, score in enumerate(similarities):
            if score >= threshold:
                results.append({
                    "score": float(score),
                    "filename": chunk_metadata[i]["filename"],
                    "chunk_index": chunk_metadata[i]["chunk_index"],
                    "text": chunk_metadata[i]["chunk_text"],
                    "full_text": all_chunks[i]
                })
        
        results.sort(key=lambda x: x["score"], reverse=True)
        
        performance_monitor.record_metric(
            "similarity_search_results",
            len(results),
            {"query_length": len(query), "total_chunks": len(all_chunks)}
        )
        
        return results[:top_k]
    
    def _split_into_chunks(self, text: str, chunk_size: int = 500) -> List[str]:
        """Split text into chunks of approximately chunk_size characters"""
        paragraphs = text.split('\n\n')
        
        chunks = []
        current_chunk = ""
        
        for para in paragraphs:
            if len(current_chunk) + len(para) < chunk_size:
                current_chunk += para + "\n\n"
            else:
                if current_chunk:
                    chunks.append(current_chunk.strip())
                current_chunk = para + "\n\n"
        
        if current_chunk:
            chunks.append(current_chunk.strip())
        
        final_chunks = []
        for chunk in chunks:
            if len(chunk) > chunk_size * 1.5:
                sentences = re.split(r'[.!?]+', chunk)
                sub_chunk = ""
                for sent in sentences:
                    if len(sub_chunk) + len(sent) < chunk_size:
                        sub_chunk += sent + ". "
                    else:
                        if sub_chunk:
                            final_chunks.append(sub_chunk.strip())
                        sub_chunk = sent + ". "
                if sub_chunk:
                    final_chunks.append(sub_chunk.strip())
            else:
                final_chunks.append(chunk)
        
        return final_chunks
    
    def _fallback_similarity_search(self, query: str, chunks: List[str], 
                                   metadata: List[Dict], threshold: float, 
                                   top_k: int) -> List[Dict]:
        """Simple word-based similarity search as fallback"""
        query_words = set(query.lower().split())
        results = []
        
        for i, chunk in enumerate(chunks):
            chunk_words = set(chunk.lower().split())
            common_words = query_words.intersection(chunk_words)
            
            if len(query_words) > 0:
                score = len(common_words) / len(query_words)
                if score >= threshold:
                    results.append({
                        "score": score,
                        "filename": metadata[i]["filename"],
                        "chunk_index": metadata[i]["chunk_index"],
                        "text": metadata[i]["chunk_text"],
                        "full_text": chunk
                    })
        
        results.sort(key=lambda x: x["score"], reverse=True)
        return results[:top_k]
    
    def get_cross_document_insights(self, documents: Dict[str, Dict]) -> Dict:
        """
        Generate insights across multiple documents
        
        Args:
            documents: Dict mapping filenames to their analysis results
            
        Returns:
            Cross-document insights
        """
        if not documents:
            return {}
        
        total_words = sum(doc["basic_stats"]["word_count"] for doc in documents.values())
        avg_complexity = np.mean([doc["complexity_score"] for doc in documents.values()])
        
        all_topics = []
        for doc in documents.values():
            all_topics.extend(doc.get("key_topics", []))
        
        topic_counts = Counter(all_topics)
        common_topics = [topic for topic, count in topic_counts.most_common(5) if count > 1]
        
        doc_types = Counter(doc["document_type"] for doc in documents.values())
        
        return {
            "total_documents": len(documents),
            "total_words": total_words,
            "average_complexity": round(avg_complexity, 2),
            "common_topics": common_topics,
            "document_types": dict(doc_types),
            "total_reading_time_minutes": sum(
                doc["basic_stats"]["reading_time_minutes"] for doc in documents.values()
            )
        }

document_intelligence = DocumentIntelligence()