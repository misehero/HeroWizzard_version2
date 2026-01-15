#!/bin/bash
# Mise HERo Finance - Quick Setup Script
# =======================================

set -e

echo "🚀 Mise HERo Finance - Setup Script"
echo "===================================="

# Check Python version
python_version=$(python3 --version 2>&1 | cut -d' ' -f2 | cut -d'.' -f1,2)
echo "✓ Python version: $python_version"

# Create virtual environment if not exists
if [ ! -d "venv" ]; then
    echo "📦 Creating virtual environment..."
    python3 -m venv venv
fi

# Activate virtual environment
echo "🔧 Activating virtual environment..."
source venv/bin/activate

# Install dependencies
echo "📥 Installing dependencies..."
pip install --upgrade pip
pip install -r requirements.txt

# Copy environment file if not exists
if [ ! -f ".env" ]; then
    echo "📝 Creating .env file from template..."
    cp .env.example .env
    echo "⚠️  Please edit .env with your database credentials"
fi

# Check if PostgreSQL is available
if command -v psql &> /dev/null; then
    echo "✓ PostgreSQL client found"
    
    # Try to create database
    echo "🗄️  Creating database (if not exists)..."
    createdb mise_hero_finance 2>/dev/null || echo "   Database already exists or cannot be created"
else
    echo "⚠️  PostgreSQL client not found - please create database manually"
fi

# Run migrations
echo "🔄 Running migrations..."
python manage.py migrate

# Seed initial data
echo "🌱 Seeding initial lookup data..."
python manage.py seed_lookups

# Collect static files
echo "📁 Collecting static files..."
python manage.py collectstatic --no-input

echo ""
echo "✅ Setup complete!"
echo ""
echo "Next steps:"
echo "  1. Edit .env with your database credentials (if needed)"
echo "  2. Create superuser: python manage.py createsuperuser"
echo "  3. Start server: python manage.py runserver"
echo ""
echo "Or use Docker:"
echo "  docker-compose up -d"
echo ""
