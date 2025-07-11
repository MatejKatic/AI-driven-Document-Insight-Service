# AI-Driven Document Insight Service

A Python-based REST API that ingests PDF and image documents (including scanned contracts and invoices), extracts text, and answers user questions using AI.


<img width="1517" height="888" alt="image" src="https://github.com/user-attachments/assets/0cf4e7f7-fdf8-4e9c-b6ad-80f5ff11d0a3" />
<img width="1564" height="841" alt="image" src="https://github.com/user-attachments/assets/cd4273e5-1548-4090-90dc-51d101b817fa" />
<img width="2031" height="1280" alt="image" src="https://github.com/user-attachments/assets/f3f3d4c3-6d57-4ce1-b9cd-878d4a162e9b" />
<img width="1940" height="1202" alt="image" src="https://github.com/user-attachments/assets/13784340-1bfb-455a-b56e-2f5ff91d2f6d" />


## ✨ Features

### Core Requirements:
- 🚀 REST API with FastAPI providing `/upload` and `/ask` endpoints
- 📄 Multi-format document ingestion: PDF and images (PNG, JPG, JPEG, TIFF, BMP)
- 🧠 Intelligent text extraction: PyMuPDF for PDFs, EasyOCR for images and scanned documents
- 🤖 AI-powered Q&A using DeepSeek API
- 🐳 Dockerized application with docker-compose

### Optional Enhancement Implemented:
- ⚡ High-performance caching layer with file-based and Redis support

### Additional Features:
- 🎭 Mock DeepSeek API for testing without API key
- 🎨 Beautiful Gradio UI with multiple tabs
- 📊 Document Intelligence: analysis, smart questions, similarity search
- 📈 Real-time performance monitoring dashboard
- 📁 Test documents included (contracts, invoices, reports, receipts)

## 🚀 Quick Start - Demo Mode

**No API key required! Uses mock API for testing:**

```bash
# Clone and run
git clone <repository-url>
cd ai-document-insight-service

# Start demo mode
make demo
```

**Access points:**
- 🌐 Gradio UI: http://localhost:7860
- 📖 API Docs: http://localhost:8000/docs
- 🔌 API Endpoint: http://localhost:8000

## 📋 Setup Instructions

### Docker Installation (Recommended)

```bash
# 1. Clone repository
git clone <repository-url>
cd ai-document-insight-service

# 2. Copy environment configuration
cp .env.example .env

# 3. For production: Add DeepSeek API key to .env
# For demo: Leave as-is

# 4. Build and start
docker-compose up -d

# 5. Verify health
make health
```

### Manual Installation

```bash
# 1. Clone repository
git clone <repository-url>
cd ai-document-insight-service

# 2. Create virtual environment
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Configure environment
cp .env.example .env

# 5. Run application
python run_all.py
```

## 🔄 Redis Installation & Cache Configuration

### Installing Redis

**Ubuntu/Debian:**
```bash
sudo apt update
sudo apt install redis-server
sudo systemctl start redis
sudo systemctl enable redis

# Verify installation
redis-cli ping  # Should return PONG
```

**macOS:**
```bash
brew install redis
brew services start redis

# Verify installation
redis-cli ping  # Should return PONG
```

**Windows:**
```bash
# Option 1: Use WSL2 (Recommended)
wsl --install
# Inside WSL, follow Ubuntu instructions

# Option 2: Use Docker (Easiest)
docker-compose --profile with-redis up
```

### Switching Between Cache Types

**Method 1: Environment Variable**
```bash
# Edit .env file
CACHE_TYPE=file    # Default file-based cache
# OR
CACHE_TYPE=redis   # Redis cache (auto-fallback if unavailable)
```

**Method 2: Docker Profiles**
```bash
# File cache only (default)
docker-compose up

# With Redis cache
docker-compose --profile with-redis up

# Or use makefile
make demo-redis
```

**Method 3: Runtime Check**
```bash
# Check current cache type
curl http://localhost:8000/cache/stats

# Verify Redis connection
python check_redis.py
```

> **Note:** The cache system automatically falls back to file-based caching if Redis is unavailable, ensuring the service always works.

## 🔑 Getting DeepSeek API Key

For production use (demo mode works without key):

1. Visit https://platform.deepseek.com/
2. Sign up and verify email
3. Navigate to "API Keys" section
4. Create new API key (starts with `sk-`)
5. Add to `.env` file:

```env
DEEPSEEK_API_KEY=sk-your-actual-key-here
```

## 📡 Example API Requests and Responses

### Basic Operations

**Single PDF Upload:**
```bash
curl -X POST "http://localhost:8000/upload" \
  -F "files=@test_docs/company_report_2024.pdf"
```

**Response:**
```json
{
  "session_id": "550e8400-e29b-41d4-a716-446655440000",
  "uploaded_files": 1,
  "files": [
    {"filename": "company_report_2024.pdf", "file_type": ".pdf"}
  ],
  "upload_time_ms": 234.5,
  "total_size_mb": 0.45
}
```

**Simple Question:**
```bash
curl -X POST "http://localhost:8000/ask" \
  -H "Content-Type: application/json" \
  -d '{
    "session_id": "550e8400-e29b-41d4-a716-446655440000",
    "question": "What is the main topic?"
  }'
```

### Complex API Operations

#### 1. Document Analysis with Intelligence Features:

```bash
# First upload multiple documents
curl -X POST "http://localhost:8000/upload" \
  -F "files=@test_docs/company_report_2024.pdf" \
  -F "files=@test_docs/contract_sample.pdf" \
  -F "files=@test_docs/technical_specification.pdf"

# Get comprehensive analysis
curl "http://localhost:8000/session/YOUR_SESSION_ID/analysis"
```

**Response:**
```json
{
  "session_id": "YOUR_SESSION_ID",
  "document_analyses": {
    "company_report_2024.pdf": {
      "basic_stats": {
        "word_count": 523,
        "sentence_count": 28,
        "reading_time_minutes": 2.6
      },
      "complexity_score": 45.3,
      "document_type": "report",
      "key_topics": ["revenue", "growth", "strategy", "Q4", "financial"],
      "summary": "Annual report showing 25% revenue growth with $10.5M total..."
    }
  },
  "cross_document_insights": {
    "total_documents": 3,
    "common_topics": ["performance", "2024", "services"],
    "total_reading_time_minutes": 8.5
  }
}
```

#### 2. Smart Questions Generation:

```bash
curl -X POST "http://localhost:8000/session/YOUR_SESSION_ID/smart-questions?num_questions=5"
```

**Response:**
```json
{
  "session_id": "YOUR_SESSION_ID",
  "questions": [
    {
      "question": "What specific financial metrics showed the most improvement?",
      "category": "analytical"
    },
    {
      "question": "What are the payment terms in the service agreement?",
      "category": "factual"
    }
  ],
  "generated_from": ["company_report_2024.pdf", "contract_sample.pdf", "technical_specification.pdf"]
}
```

#### 3. Cross-Document Similarity Search:

```bash
curl -X POST "http://localhost:8000/session/YOUR_SESSION_ID/similarity-search" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "query=payment terms financial obligations&threshold=0.3&top_k=5"
```

#### 4. Performance Metrics with Details:

```bash
curl "http://localhost:8000/metrics"
```

## 🏗️ Architecture & Design Approach

### System Architecture

```
                    ┌─────────────────────────┐
                    │      User Interface      │
                    │   Gradio UI (7860)      │
                    │   REST Clients          │
                    └───────────┬─────────────┘
                                │
                    ┌───────────▼─────────────┐
                    │    FastAPI Server       │
                    │      Port 8000          │
                    │  ┌─────────────────┐   │
                    │  │ Session Manager │   │
                    │  └─────────────────┘   │
                    └───────────┬─────────────┘
                                │
          ┌─────────────────────┴─────────────────────┐
          │                                           │
┌─────────▼────────────┐             ┌───────────────▼──────────┐
│   Document Processor  │             │    Question Answering    │
│ ┌─────────┬─────────┐ │             │ ┌──────────────────────┐ │
│ │ PyMuPDF │ EasyOCR │ │             │ │   DeepSeek Client    │ │
│ │  (PDF)  │ (Images)│ │             │ │  (Real or Mock API)  │ │
│ └─────────┴─────────┘ │             │ └──────────────────────┘ │
└───────────┬────────────┘             └──────────────────────────┘
            │
┌───────────▼────────────┐
│     Cache Layer        │
│ ┌─────────┬─────────┐ │
│ │  File   │  Redis  │ │
│ │ Cache   │  Cache  │ │
│ └─────────┴─────────┘ │
│   Content-based Keys   │
└────────────────────────┘
```

### Tools and Models Chosen

#### 1. FastAPI Framework
- **Why:** Native async support for better performance, automatic API documentation, modern Python features
- **Alternative considered:** Flask - rejected due to lack of native async and manual API doc requirements

#### 2. PyMuPDF for PDF Processing
- **Why:** Fastest PDF text extraction in Python, handles most PDFs without OCR
- **Performance:** Processes typical PDFs in < 1 second

#### 3. EasyOCR for Image/Scanned Documents
- **Why:** Best accuracy among open-source OCR, no cloud dependencies, supports multiple languages
- **Trade-off:** Slower than cloud OCR but maintains data privacy

#### 4. DeepSeek API for Q&A
- **Why:** Cost-effective ($0.14/1M tokens vs $3/1M for competitors), good performance, simple integration
- **Context window:** 8K tokens sufficient for document Q&A

#### 5. Content-Based Caching
- **Why:** Same document always gets same cache key regardless of filename
- **Implementation:** SHA-256 hash of file content + size
- **Result:** 10-50x performance improvement on repeated documents

#### 6. Gradio for UI
- **Why:** Built for ML demos, beautiful components, easy file handling
- **Features used:** Multiple tabs, real-time updates, performance charts

### Key Design Decisions

- **Session-based Storage:** Allows multiple users without authentication complexity
- **Lazy Extraction:** Text extracted only when first question asked
- **Dual Cache System:** Memory (L1) + Persistent (L2) for optimal performance
- **Mock API:** Enables full testing without API keys
- **Modular Architecture:** Easy to swap components (e.g., different LLM)

## 🧪 Testing

### Complete Test Suite

```bash
# Run all tests
make test

# Individual test files:

# Check all dependencies are installed
python check_dependencies.py

# Test DeepSeek API connection
python test_deepseek.py

# Test complete workflow (upload, extract, ask, cache)
python test_complete_workflow.py

# Test extraction methods (PDF and OCR)
python test_extraction_methods.py

# Test cache performance directly
python test_cache_direct.py

# Test image OCR functionality
python test_image_ocr.py

# Check Redis availability and connection
python check_redis.py

# Test upload endpoint
python test_upload.py

# Test Docker deployment
python test_docker.py

# Create test documents
python create_test_docs.py
```

### Performance Benchmarking

Run benchmarks through Gradio UI or:

```bash
# Quick benchmark
curl -X POST http://localhost:8000/benchmark/quick

# Run stress test with 10 concurrent users
curl -X POST http://localhost:8000/benchmark/stress?users=10
```

### Test Documents Included

The `test_docs` folder contains sample documents for testing:

- `company_report_2024.pdf` - Business report with financial data
- `contract_sample.pdf` - Service agreement with terms
- `technical_specification.pdf` - Technical documentation
- `scanned_invoice.png` - OCR test document
- `receipt_sample.jpg` - Image with text
- `business_card.png` - Contact information
- `meeting_notes.png` - Handwritten-style notes

## ⚙️ Configuration

All settings in `.env` file:

```env
# API Configuration
# Demo mode: use "demo-key-for-testing"
# Production: use your DeepSeek API key
DEEPSEEK_API_KEY=demo-key-for-testing

# Cache Configuration
# Options: "file" (default) or "redis"
CACHE_TYPE=file
CACHE_TTL_HOURS=24

# Redis Settings (if CACHE_TYPE=redis)
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_DB=0

# Performance Settings
ENABLE_PERFORMANCE_MONITORING=true
MAX_FILE_SIZE_MB=10
MAX_FILES_PER_UPLOAD=5

# Document Intelligence
ENABLE_DOCUMENT_INTELLIGENCE=true
MAX_TOPICS_EXTRACTION=5
MAX_SMART_QUESTIONS=10
SIMILARITY_CHUNK_SIZE=500
```

## 📊 Performance Metrics

Measured on standard hardware (4GB RAM, 2 CPU cores):

| Document Type | Extraction Method | Time (First) | Time (Cached) |
|---------------|-------------------|--------------|---------------|
| Text PDF      | PyMuPDF          | 0.5-1s       | 0.05s         |
| Scanned PDF   | EasyOCR          | 3-5s         | 0.08s         |
| PNG Image     | EasyOCR          | 2-3s         | 0.06s         |
| JPG Receipt   | EasyOCR          | 2-3s         | 0.07s         |

- **Q&A Response:** 2-4 seconds (including context building)
- **Concurrent users supported:** 20+
- **Cache hit rate:** Typically > 70% in production

## 🐳 Docker Commands

```bash
make demo         # Start demo mode (no API key needed)
make demo-redis   # Demo mode with Redis cache
make up          # Start services
make down        # Stop services
make logs        # View logs
make health      # Check health
make clean       # Clean all data
make shell       # Open container shell
make restart     # Restart all services
```

## 🔧 Troubleshooting

### Common Issues

**Docker won't start:**
```bash
# Ensure Docker Desktop is running
docker ps

# Check ports availability
netstat -an | grep 8000
netstat -an | grep 7860
```

**Redis connection issues:**
```bash
# Check Redis is running
redis-cli ping

# Verify configuration
python check_redis.py

# Fall back to file cache
CACHE_TYPE=file
```

**OCR slow on first run:**
- Normal behavior - downloading models (~64MB)
- Check progress in logs: `make logs`
- Subsequent runs will be fast

**API not responding:**
```bash
# Check health
curl http://localhost:8000/

# View detailed logs
docker-compose logs app

# Restart services
make restart
```

## 🎯 Creative Additions

- **Mock API Mode:** Full functionality without API keys
- **Performance Dashboard:** Real-time metrics visualization
- **Document Intelligence:** AI-powered analysis and insights
- **Smart Questions:** AI generates relevant questions about documents
- **Similarity Search:** Find related content across documents
- **Benchmark Tools:** Built-in performance testing
- **Auto-recovery:** Services restart automatically if they crash
