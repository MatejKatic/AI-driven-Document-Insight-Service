#!/bin/bash

cleanup() {
    echo ""
    echo "🛑 Shutting down services..."
    
    if [ ! -z "$API_PID" ]; then
        kill $API_PID 2>/dev/null
    fi
    if [ ! -z "$UI_PID" ]; then
        kill $UI_PID 2>/dev/null
    fi
    
    sleep 2
    
    if [ ! -z "$API_PID" ]; then
        kill -9 $API_PID 2>/dev/null
    fi
    if [ ! -z "$UI_PID" ]; then
        kill -9 $UI_PID 2>/dev/null
    fi
    
    echo "✅ All services stopped"
    exit 0
}

trap cleanup SIGTERM SIGINT SIGQUIT

echo "🚀 Starting AI Document Insight Service..."
echo "========================================="

if [ "$DEEPSEEK_API_KEY" = "demo-key-for-testing" ] || [ -z "$DEEPSEEK_API_KEY" ]; then
    echo "📌 Using MOCK DeepSeek API (no real key provided)"
    export DEEPSEEK_API_URL="http://mock-deepseek:8080/v1/chat/completions"
else
    echo "✅ Using REAL DeepSeek API"
    export DEEPSEEK_API_URL="https://api.deepseek.com/v1/chat/completions"
fi

echo "  - API URL: $DEEPSEEK_API_URL"
echo "  - Cache Type: ${CACHE_TYPE:-file}"
echo "========================================="

check_api() {
    curl -sf http://localhost:8000/ >/dev/null 2>&1
}

echo "Starting API server..."
cd /app
python run.py &
API_PID=$!

echo "Waiting for API to be ready..."
MAX_WAIT=60
WAITED=0

while ! check_api; do
    if [ $WAITED -ge $MAX_WAIT ]; then
        echo "❌ API failed to start after ${MAX_WAIT} seconds!"
        kill $API_PID 2>/dev/null
        exit 1
    fi
    
    echo "  Waiting... ($WAITED/$MAX_WAIT seconds)"
    sleep 2
    WAITED=$((WAITED + 2))
done

echo "✅ API is ready!"

echo "Starting Gradio UI..."
cd /app
export API_BASE_URL="http://localhost:8000"
python run_gradio.py &
UI_PID=$!

sleep 5

echo ""
echo "✅ All services started!"
echo "📌 Access points:"
echo "   - API: http://localhost:8000"
echo "   - API Docs: http://localhost:8000/docs"
echo "   - Gradio UI: http://localhost:7860"
echo ""
echo "Press Ctrl+C to stop all services"
echo "========================================="

while true; do
    if ! kill -0 $API_PID 2>/dev/null; then
        echo "❌ API process died! Restarting..."
        cd /app
        python run.py &
        API_PID=$!
        sleep 5
    fi
    
    if ! kill -0 $UI_PID 2>/dev/null; then
        echo "❌ Gradio UI process died! Restarting..."
        cd /app
        python run_gradio.py &
        UI_PID=$!
        sleep 5
    fi
    
    sleep 10
done