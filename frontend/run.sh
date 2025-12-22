#!/bin/bash
# Quick start script for Streamlit frontend

echo "🚀 Starting FinScribe Smart Scan Frontend..."
echo ""

# Check if backend is running
if ! curl -s http://localhost:8000/api/v1/health > /dev/null 2>&1; then
    echo "⚠️  Warning: Backend API not detected at http://localhost:8000"
    echo "   Please start the backend first:"
    echo "   uvicorn app.main:app --host 0.0.0.0 --port 8000"
    echo ""
fi

# Install dependencies if needed
if [ ! -d "venv" ]; then
    echo "📦 Creating virtual environment..."
    python3 -m venv venv
    source venv/bin/activate
    pip install -r requirements.txt
else
    source venv/bin/activate
fi

# Run Streamlit
echo "🎨 Starting Streamlit..."
streamlit run app.py

