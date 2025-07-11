# Makefile for AI Document Insight Service
.PHONY: help build up down logs clean test demo demo-redis health shell fix-permissions

help:
	@echo "AI Document Insight Service - Make Commands"
	@echo "==========================================="
	@echo ""
	@echo "🚀 Quick Start:"
	@echo "  make demo        - Run in demo mode (no API key needed)"
	@echo "  make demo-redis  - Run demo mode with Redis cache"
	@echo "  make up          - Start all services"
	@echo "  make down        - Stop all services"
	@echo ""
	@echo "🔧 Build & Setup:"
	@echo "  make build       - Build Docker images"
	@echo "  make setup       - Initial setup (copy .env, fix permissions)"
	@echo ""
	@echo "📊 Monitoring:"
	@echo "  make logs        - View logs (follow mode)"
	@echo "  make health      - Check service health"
	@echo "  make shell       - Open shell in app container"
	@echo ""
	@echo "🧹 Maintenance:"
	@echo "  make clean       - Clean up containers and volumes"
	@echo "  make clean-cache - Clean cache files only"
	@echo "  make test        - Run tests in container"
	@echo ""
	@echo "📝 Configuration:"
	@echo "  Edit .env to add your DeepSeek API key"
	@echo "  Set CACHE_TYPE=redis in .env to use Redis cache"

setup:
	@echo "🔧 Initial setup..."
	@if [ ! -f .env ]; then \
		echo "📋 Creating .env from .env.example..."; \
		cp .env.example .env; \
		echo "✅ Created .env file"; \
	else \
		echo "ℹ️  .env already exists, skipping..."; \
	fi
	@chmod +x docker-entrypoint.sh run_services.sh make_executable.sh 2>/dev/null || true
	@echo "✅ Setup complete!"

build: setup
	@echo "🏗️  Building Docker images..."
	docker-compose build
	@echo "✅ Build complete!"

demo: setup
	@echo "🚀 Starting in DEMO MODE (using mock DeepSeek API)..."
	@echo "=================================================="
	@if [ ! -f .env ]; then \
		cp .env.example .env; \
		echo "📋 Created .env from template"; \
	fi
	docker-compose up -d
	@sleep 3
	@echo ""
	@echo "✅ Services started in DEMO MODE!"
	@echo ""
	@echo "📌 Access points:"
	@echo "   - 🎨 Gradio UI: http://localhost:7860"
	@echo "   - 📚 API Docs:  http://localhost:8000/docs"
	@echo "   - 🔌 API Root:  http://localhost:8000"
	@echo "   - 🤖 Mock API:  http://localhost:8080 (internal)"
	@echo ""
	@echo "💡 Quick Start Guide:"
	@echo "   1. Open http://localhost:7860 in your browser"
	@echo "   2. Upload test documents (or use 'Create Test Docs')"
	@echo "   3. Try asking: 'What is the main topic of these documents?'"
	@echo ""
	@echo "📝 To use your own DeepSeek API key:"
	@echo "   1. Edit .env and replace DEEPSEEK_API_KEY"
	@echo "   2. Run: make restart"

demo-redis: setup
	@echo "🚀 Starting DEMO MODE with Redis cache..."
	@if [ ! -f .env ]; then \
		cp .env.example .env; \
	fi
	@echo "📝 Enabling Redis cache..."
	@sed -i.bak 's/CACHE_TYPE=file/CACHE_TYPE=redis/' .env 2>/dev/null || \
		sed -i '' 's/CACHE_TYPE=file/CACHE_TYPE=redis/' .env
	docker-compose --profile with-redis up -d
	@echo ""
	@echo "✅ Services started with Redis cache!"
	@echo "   - Redis UI: redis://localhost:6379"
	@echo "   - See cache stats in Gradio UI"

up: setup
	docker-compose up -d
	@echo ""
	@echo "✅ Services started!"
	@echo "   - 🎨 Gradio UI: http://localhost:7860"
	@echo "   - 📚 API: http://localhost:8000"

down:
	@echo "🛑 Stopping services..."
	docker-compose down
	@echo "✅ Services stopped"

restart: down up

logs:
	@echo "📜 Showing logs (Ctrl+C to exit)..."
	docker-compose logs -f

logs-api:
	docker-compose logs -f app | grep -E "(API|FastAPI|INFO)"

logs-ui:
	docker-compose logs -f app | grep -E "(Gradio|UI)"

clean:
	@echo "🧹 Cleaning up everything..."
	docker-compose down -v
	rm -rf uploads/* cache/* logs/* 2>/dev/null || true
	@echo "✅ Cleaned up containers, volumes, and data"

clean-cache:
	@echo "🧹 Cleaning cache only..."
	rm -rf cache/* 2>/dev/null || true
	@echo "✅ Cache cleaned"

test:
	@echo "🧪 Running tests..."
	@if [ -f test_complete_workflow.py ]; then \
		docker-compose run --rm app python test_complete_workflow.py; \
	else \
		echo "⚠️  No test file found, running health check instead..."; \
		make health; \
	fi

health:
	@echo "🏥 Checking service health..."
	@echo "=============================="
	@echo ""
	@echo "📊 Container Status:"
	@docker-compose ps
	@echo ""
	@echo "🔌 API Health:"
	@curl -sf http://localhost:8000/ | python -m json.tool || echo "❌ API not responding"
	@echo ""
	@echo "🤖 Mock DeepSeek Health:"
	@curl -sf http://localhost:8080/health | python -m json.tool || echo "❌ Mock API not responding"
	@echo ""
	@echo "💾 Cache Stats:"
	@curl -sf http://localhost:8000/cache/stats | python -m json.tool 2>/dev/null || echo "ℹ️  Cache stats not available"

shell:
	@echo "🐚 Opening shell in app container..."
	docker-compose exec app /bin/bash

shell-root:
	@echo "🐚 Opening root shell in app container..."
	docker-compose exec -u root app /bin/bash

fix-permissions:
	@echo "🔧 Fixing file permissions..."
	chmod +x docker-entrypoint.sh run_services.sh make_executable.sh
	@echo "✅ Permissions fixed"

dev-setup:
	@echo "🛠️  Setting up development environment..."
	python -m venv venv
	./venv/bin/pip install -r requirements.txt
	cp .env.example .env
	@echo "✅ Dev environment ready!"
	@echo "   Activate with: source venv/bin/activate"

docker-clean:
	@echo "🐋 Cleaning Docker system..."
	docker system prune -f
	@echo "✅ Docker cleaned"

ui:
	@echo "Opening Gradio UI in browser..."
	@python -m webbrowser http://localhost:7860 2>/dev/null || \
		echo "Please open http://localhost:7860 in your browser"

api:
	@echo "Opening API docs in browser..."
	@python -m webbrowser http://localhost:8000/docs 2>/dev/null || \
		echo "Please open http://localhost:8000/docs in your browser"