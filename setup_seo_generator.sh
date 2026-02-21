#!/bin/bash
# Quick setup script for SEO generator

set -e

echo "🚀 SEO Generator Quick Setup"
echo "=============================="
echo ""

# Check if .env exists
if [ ! -f ".env" ]; then
    echo "📝 Creating .env file from template..."
    cp .env.example .env
    echo "✅ .env created"
else
    echo "✅ .env already exists"
fi

# Check if GOOGLE_API_KEY is set
if grep -q "GOOGLE_API_KEY=your-gemini-api-key-here" .env; then
    echo ""
    echo "⚠️  GOOGLE_API_KEY is not set in .env"
    echo "Please get a free API key from: https://aistudio.google.com/apikey"
    echo "Then edit .env and replace 'your-gemini-api-key-here' with your actual key"
    echo ""
    read -p "Press Enter after adding your key to .env..."
fi

# Check if python package python-dotenv is installed
echo ""
echo "📦 Checking dependencies..."
python -c "import dotenv" 2>/dev/null || {
    echo "Installing python-dotenv..."
    pip install python-dotenv
}

echo "✅ All setup complete!"
echo ""
echo "Next step:"
echo "  python generate_seo_complete.py --dry-run"
echo ""
