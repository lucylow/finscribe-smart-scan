# Makefile for FinScribe Smart Scan
# Provides convenient commands for building, running, and testing the stack

DOCKER_COMPOSE = docker-compose
DOCKER_COMPOSE_DEMO = docker-compose -f docker-compose.demo.yml
SAMPLE_SCRIPT = examples/generate_sample_invoice.py
SAMPLE_PATH = examples/sample_invoice.jpg
ACTIVE_QUEUE = data/active_learning_queue.jsonl

.PHONY: all generate-sample build up logs down clean help test-camel demo demo-up demo-down demo-logs dev test lint

all: generate-sample build up
	@echo "✓ Stack started. Use 'make logs' to tail logs, 'make down' to stop."
	@echo "✓ CAMEL endpoint available at: http://localhost:8000/api/v1/process_invoice"
	@echo "✓ Mock validator at: http://localhost:8100/health"

generate-sample:
	@echo "Generating sample invoice..."
	@python $(SAMPLE_SCRIPT) || python3 $(SAMPLE_SCRIPT)
	@echo "✓ Generated $(SAMPLE_PATH)"

build:
	@echo "Building docker-compose images..."
	$(DOCKER_COMPOSE) build --no-cache

up:
	@echo "Bringing up docker-compose stack..."
	$(DOCKER_COMPOSE) up -d
	@echo "Waiting for services to be healthy..."
	@sleep 5

logs:
	@echo "Tailing logs (press Ctrl-C to quit)..."
	$(DOCKER_COMPOSE) logs -f

down:
	@echo "Stopping stack..."
	$(DOCKER_COMPOSE) down

clean:
	@echo "Cleaning generated artifacts..."
	-rm -f $(SAMPLE_PATH)
	-rm -f $(ACTIVE_QUEUE)
	@echo "✓ Clean complete."

test-camel: generate-sample
	@echo "Testing CAMEL agent endpoint..."
	@curl -X POST "http://localhost:8000/api/v1/process_invoice" \
		-F "file=@$(SAMPLE_PATH)" \
		-H "accept: application/json" | python -m json.tool || \
		echo "✗ Service may not be running. Run 'make up' first."

test-validator:
	@echo "Testing mock validator..."
	@curl -X POST "http://localhost:8100/v1/validate" \
		-H "Content-Type: application/json" \
		-d '{"ocr_text": "Invoice Total: 1000.00\nSubtotal: 909.09\nTax: 90.91"}' | \
		python -m json.tool || echo "✗ Validator service may not be running."

health:
	@echo "Checking service health..."
	@echo "Backend:"
	@curl -s http://localhost:8000/api/v1/health | python -m json.tool || echo "✗ Backend not responding"
	@echo "\nCAMEL:"
	@curl -s http://localhost:8000/api/v1/camel/health | python -m json.tool || echo "✗ CAMEL not responding"
	@echo "\nMock Validator:"
	@curl -s http://localhost:8100/health | python -m json.tool || echo "✗ Validator not responding"

dev:
	@echo "Starting FinScribe demo environment..."
	@echo "This will start: Backend API (8000), Frontend Streamlit (8501), OCR Service (8001)"
	$(DOCKER_COMPOSE_DEMO) up --build
	@echo ""
	@echo "✓ Demo environment started!"
	@echo "  Frontend: http://localhost:8501"
	@echo "  Backend API: http://localhost:8000"
	@echo "  API Docs: http://localhost:8000/docs"
	@echo "  Health: http://localhost:8000/health"
	@echo ""
	@echo "Use 'make demo-down' to stop"

frontend:
	@echo "Starting Streamlit frontend..."
	docker-compose up --build streamlit-frontend
	@echo ""
	@echo "✓ Streamlit frontend started at http://localhost:8501"

demo: dev

demo-up:
	@echo "Starting demo services..."
	$(DOCKER_COMPOSE_DEMO) up -d --build

demo-down:
	@echo "Stopping demo services..."
	$(DOCKER_COMPOSE_DEMO) down

demo-logs:
	@echo "Tailing demo logs (press Ctrl-C to quit)..."
	$(DOCKER_COMPOSE_DEMO) logs -f backend frontend

test:
	@echo "Running tests..."
	pytest tests/ -v

lint:
	@echo "Running linter..."
	flake8 backend/ tests/ --max-line-length=120 --ignore=E501,W503

help:
	@echo "FinScribe CAMEL-AI Integration - Makefile targets:"
	@echo ""
	@echo "Demo Commands:"
	@echo "  make demo             -> build and start full demo stack (API + Frontend + DB)"
	@echo "  make demo-up          -> start demo services"
	@echo "  make demo-down        -> stop demo services"
	@echo "  make demo-logs        -> view demo service logs"
	@echo ""
	@echo "Development Commands:"
	@echo "  make all              -> generate sample, build images, start stack"
	@echo "  make generate-sample  -> create examples/sample_invoice.jpg"
	@echo "  make build            -> docker-compose build"
	@echo "  make up               -> docker-compose up -d"
	@echo "  make logs             -> docker-compose logs -f"
	@echo "  make down             -> docker-compose down"
	@echo "  make clean            -> remove sample and active queue"
	@echo "  make test-camel       -> test CAMEL agent with sample invoice"
	@echo "  make test-validator   -> test mock validator service"
	@echo "  make health           -> check all service health endpoints"
	@echo "  make help             -> show this help message"


