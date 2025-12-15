#!/bin/bash

echo "================================"
echo "LLM Audit Engine - Backend Setup"
echo "================================"
echo ""

# Check Python version
if ! command -v python3 &> /dev/null; then
    echo "Error: Python 3 is not installed"
    exit 1
fi

echo "✓ Python 3 found"

# Create virtual environment
echo ""
echo "Creating virtual environment..."
python3 -m venv venv

# Activate virtual environment
echo "Activating virtual environment..."
source venv/bin/activate

# Upgrade pip
echo ""
echo "Upgrading pip..."
pip install --upgrade pip

# Install dependencies
echo ""
echo "Installing dependencies..."
pip install -r requirements.txt

echo ""
echo "================================"
echo "Setup complete!"
echo "================================"
echo ""
echo "Next steps:"
echo "1. Create .env file with your configuration (see ../.env.example)"
echo "2. Make sure PostgreSQL is running"
echo "3. Run: alembic upgrade head"
echo "4. Start API server: uvicorn app.main:app --reload --port 8000"
echo "5. Start worker: python -m app.worker"
echo ""


