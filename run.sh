#!/bin/bash
# HighTrack NSE Quick Start Script
cd "$(dirname "$0")"

# Activate virtualenv if present
if [ -d ".venv" ]; then
    source .venv/bin/activate
fi

echo "🚀 Starting HighTrack NSE Dashboard..."
echo "📊 Opening in your default browser at http://localhost:8501"
streamlit run app.py
