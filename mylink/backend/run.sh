#!/bin/bash

# SmartBot Backend Startup Script

echo "🚀 Starting SmartBot Backend..."

# Check if .env exists
if [ ! -f .env ]; then
    echo "⚠️  .env file not found. Copying from .env.example..."
    cp .env.example .env
    echo "✅ Created .env file. Please update it with your settings."
fi

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo "📦 Creating virtual environment..."
    python -m venv venv
fi

# Activate virtual environment
echo "🔧 Activating virtual environment..."
source venv/bin/activate

# Install dependencies
echo "📥 Installing dependencies..."
pip install -r requirements.txt

# Run migrations
echo "⬆️  Running database migrations..."
alembic upgrade head

# Start server
echo "✅ Starting FastAPI server..."
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

