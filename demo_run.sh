#!/usr/bin/env bash
# Quick demo runner for FinScribe
# This script starts the full demo stack with one command

set -euo pipefail

echo "🚀 Starting FinScribe Demo..."
echo ""

# Check if Docker is running
if ! docker info > /dev/null 2>&1; then
    echo "❌ Error: Docker is not running. Please start Docker and try again."
    exit 1
fi

# Check if docker-compose is available
if ! command -v docker-compose > /dev/null 2>&1 && ! docker compose version > /dev/null 2>&1; then
    echo "❌ Error: docker-compose is not installed. Please install it and try again."
    exit 1
fi

# Use docker compose (newer) or docker-compose (older)
if docker compose version > /dev/null 2>&1; then
    DOCKER_COMPOSE="docker compose"
else
    DOCKER_COMPOSE="docker-compose"
fi

echo "📦 Building images (this may take a few minutes on first run)..."
$DOCKER_COMPOSE build api frontend

echo ""
echo "🚀 Starting services..."
$DOCKER_COMPOSE up -d api frontend postgres redis minio

echo ""
echo "⏳ Waiting for services to be ready..."
sleep 10

echo ""
echo "✅ Demo stack is running!"
echo ""
echo "📍 Access points:"
echo "   Frontend:    http://localhost:5173"
echo "   Backend API: http://localhost:8000"
echo "   API Docs:    http://localhost:8000/docs"
echo "   MinIO:       http://localhost:9001 (minioadmin/minioadmin)"
echo ""
echo "📊 View logs:   docker-compose logs -f"
echo "🛑 Stop demo:   docker-compose down"
echo ""
echo "💡 Tip: Open http://localhost:5173 in your browser to see the demo!"

