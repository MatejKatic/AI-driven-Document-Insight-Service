#!/bin/bash
set -e

echo "🚀 Starting AI Document Insight Service..."
echo "========================================="

if [[ "$DEEPSEEK_API_URL" == *"localai"* ]]; then
    echo "🤖 Using LocalAI"
    echo "🔗 API URL: $DEEPSEEK_API_URL"
    echo "📌 Model: gpt-4"
    echo "⏱️  Note: LocalAI may take 30-120 seconds to respond"
    
elif [ "$DEEPSEEK_API_KEY" = "demo-key-for-testing" ] || [ -z "$DEEPSEEK_API_KEY" ]; then
    echo "⚠️  No valid DEEPSEEK_API_KEY detected!"
    echo "📌 Running in DEMO MODE with mock API"
    echo ""
    echo "To use real DeepSeek API:"
    echo "  1. Get API key from https://platform.deepseek.com/"
    echo "  2. Set DEEPSEEK_API_KEY in docker-compose.yml or .env"
    echo ""
    export DEEPSEEK_API_URL="http://mock-deepseek:8080/v1/chat/completions"
    echo "🔗 API URL: $DEEPSEEK_API_URL"
    echo "📌 Model: deepseek-chat (mock responses)"
    
else
    echo "✅ DeepSeek API key configured"
    echo "🔗 Using real DeepSeek API"
    if [ -z "$DEEPSEEK_API_URL" ] || [[ "$DEEPSEEK_API_URL" == "https://api.deepseek.com/v1/chat/completions" ]]; then
        export DEEPSEEK_API_URL="https://api.deepseek.com/v1/chat/completions"
    fi
    echo "📌 Model: deepseek-chat"
    echo "💰 Note: Real API usage will incur costs"
fi

echo "========================================="


mkdir -p /app/uploads /app/cache /app/test_docs /app/logs

touch /app/app/__init__.py

export PYTHONPATH=/app:$PYTHONPATH

if [ -f "/app/create_test_docs.py" ] && [ -z "$(ls -A /app/test_docs 2>/dev/null)" ]; then
    echo ""
    echo "📄 Creating test documents..."
    cd /app
    python create_test_docs.py || {
        echo "⚠️  Could not create test docs with script, creating fallback document..."
        cat > /app/test_docs/sample_document.txt << 'EOF'
AI-Driven Document Insight Service - Test Document

This is a sample document for testing the document insight service.

Key Features:
1. Document Upload - Supports PDF and image files
2. Text Extraction - Uses PyMuPDF and EasyOCR
3. AI-powered Q&A - Answers questions about uploaded documents
4. Performance Monitoring - Tracks all operations
5. Smart Caching - Improves response times

Technical Details:
The service uses advanced machine learning models to extract and analyze text from documents.
It supports multiple file formats and can handle both text-based and scanned documents.
The caching system ensures fast responses for repeated queries.

Test Questions:
- What are the key features of this service?
- What file formats are supported?
- How does the caching system work?
- What technologies are used for text extraction?

This document can be used to test the upload and query functionality.
EOF
        echo "✅ Created fallback test document"
    }
fi

echo ""
echo "📋 Configuration:"
echo "  - Cache Type: ${CACHE_TYPE:-file}"
echo "  - Max File Size: ${MAX_FILE_SIZE_MB:-10}MB"
echo "  - Performance Monitoring: ${ENABLE_PERFORMANCE_MONITORING:-true}"
echo "  - API Mode: $([ "$DEEPSEEK_API_KEY" = "demo-key-for-testing" ] && echo "MOCK" || echo "PRODUCTION")"
echo ""

echo "🌐 Services will be available at:"
echo "  - API: http://localhost:8000"
echo "  - API Docs: http://localhost:8000/docs"
echo "  - Gradio UI: http://localhost:7860"
if [ "$DEEPSEEK_API_KEY" = "demo-key-for-testing" ]; then
    echo "  - Mock API: http://localhost:8080 (internal)"
fi
echo ""
echo "========================================="
echo ""

exec "$@"