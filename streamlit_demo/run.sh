#!/bin/bash
# Quick start script for Streamlit demo

# Set default model mode if not set
export MODEL_MODE=${MODEL_MODE:-mock}

echo "🚀 Starting PaddleOCR-VL Financial Document Analyzer Demo"
echo "📝 Model Mode: $MODEL_MODE"
echo ""

# Check if streamlit is installed
if ! command -v streamlit &> /dev/null; then
    echo "❌ Streamlit is not installed. Please install dependencies:"
    echo "   pip install -r streamlit_demo/requirements.txt"
    exit 1
fi

# Run the application
cd "$(dirname "$0")/.."
streamlit run streamlit_demo/app.py
