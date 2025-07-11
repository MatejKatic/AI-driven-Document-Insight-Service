# Makefile for AI Document Insight Service
.PHONY: help build up down logs clean test demo health

help:
	@echo "AI Document Insight Service - Docker Commands"
	@echo "============================================="
	@echo ""
	@echo "Quick Start:"
	@echo "  make demo      - Run in demo mode (no API key needed)"
	@echo "  make up        - Start all services"
	@echo "  make down      - Stop all services"
	@echo "  make fix       - Apply Gradio connection fixes"
	@echo ""
	@echo "Other Commands:"
	@echo "  make build     - Build Docker images"
	@echo "  make logs      - View logs"
	@echo "  make clean     - Clean up containers and volumes"
	@echo "  make test      - Run tests in container"
	@echo "  make health    - Check service health"
	@echo "  make shell     - Open shell in app container"

fix:
	@echo "🔧 Applying Gradio connection fixes..."
	@python fix_gradio_connection.py || echo "Fix script not found, skipping..."
	@chmod +x run_services.sh || echo "run_services.sh not found"

build: fix
	docker-compose build

demo: fix
	@echo "🚀 Starting in DEMO MODE (using mock DeepSeek API)..."
	@cp .env.docker .env 2>/dev/null || echo "DEEPSEEK_API_KEY=demo-key-for-testing" > .env
	docker-compose build
	docker-compose up -d
	@echo ""
	@echo "✅ Services started!"
	@echo "📌 Access points:"
	@echo "   - Gradio UI: http://localhost:7860"
	@echo "   - API Docs: http://localhost:8000/docs"
	@echo "   - Mock DeepSeek API: http://localhost:8080"
	@echo ""
	@echo "📄 Test documents available in the UI"
	@echo "🔍 Try asking: 'What is the main topic of these documents?'"

up: fix
	docker-compose up -d
	@echo "✅ Services started!"
	@echo "   - Gradio UI: http://localhost:7860"
	@echo "   - API: http://localhost:8000"

down:
	docker-compose down


logs:
	docker-compose logs -f

clean:
	docker-compose down -v
	rm -rf uploads/* cache/* logs/*
	@echo "✅ Cleaned up containers, volumes, and data"

test:
	@echo "Running tests in Docker container..."
	docker-compose run --rm app python test_complete_workflow.py

health:
	@echo "Checking service health..."
	@docker-compose ps
	@echo ""
	@echo "API Health:"
	@curl -s http://localhost:8000/ | python -m json.tool || echo "API not responding"
	@echo ""
	@echo "Mock DeepSeek Health:"
	@curl -s http://localhost:8080/health | python -m json.tool || echo "Mock API not responding"

shell:
	docker-compose exec app /bin/bash

api-only:
	docker-compose --profile api-only up -d
 
ui-only:
	docker-compose --profile ui-only up -d

fix-permissions:
	chmod +x docker-entrypoint.sh