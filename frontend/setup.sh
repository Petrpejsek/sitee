#!/bin/bash

echo "================================="
echo "LLM Audit Engine - Frontend Setup"
echo "================================="
echo ""

# Check Node.js version
if ! command -v node &> /dev/null; then
    echo "Error: Node.js is not installed"
    exit 1
fi

echo "✓ Node.js found: $(node --version)"

# Check npm
if ! command -v npm &> /dev/null; then
    echo "Error: npm is not installed"
    exit 1
fi

echo "✓ npm found: $(npm --version)"

# Install dependencies
echo ""
echo "Installing dependencies..."
npm install

echo ""
echo "================================="
echo "Setup complete!"
echo "================================="
echo ""
echo "Next steps:"
echo "1. Make sure backend is running on http://localhost:8000"
echo "2. Start dev server: npm run dev"
echo "3. Open browser: http://localhost:3000"
echo ""


