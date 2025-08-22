#!/bin/bash

# BlackSwan Credit Intelligence Platform - Local Demo Runner
# This script sets up and runs the complete platform locally

set -e

echo "🚀 Starting BlackSwan Credit Intelligence Platform Demo"
echo "=================================================="

# Check if Docker is running
if ! docker info > /dev/null 2>&1; then
    echo "❌ Docker is not running. Please start Docker and try again."
    exit 1
fi

# Check if docker-compose is available
if ! command -v docker-compose &> /dev/null; then
    echo "❌ docker-compose is not installed. Please install it and try again."
    exit 1
fi

# Create .env file if it doesn't exist
if [ ! -f .env ]; then
    echo "📝 Creating .env file from template..."
    cp env.example .env
    echo "✅ .env file created. You can modify it if needed."
fi

# Create data directory
mkdir -p data

echo "🐳 Starting services with Docker Compose..."
docker-compose up -d

echo "⏳ Waiting for services to be ready..."
sleep 30

# Check if services are healthy
echo "🔍 Checking service health..."

# Check PostgreSQL
if docker-compose exec -T postgres pg_isready -U credtech > /dev/null 2>&1; then
    echo "✅ PostgreSQL is ready"
else
    echo "❌ PostgreSQL is not ready. Waiting..."
    sleep 10
fi

# Check Redis
if docker-compose exec -T redis redis-cli ping > /dev/null 2>&1; then
    echo "✅ Redis is ready"
else
    echo "❌ Redis is not ready. Waiting..."
    sleep 10
fi

# Check API
if curl -f http://localhost:8000/health > /dev/null 2>&1; then
    echo "✅ API is ready"
else
    echo "❌ API is not ready. Waiting..."
    sleep 10
fi

echo "🌱 Seeding demo data..."
docker-compose exec -T api python scripts/seed_demo_data.py

echo "🎯 Starting background workers..."
docker-compose exec -d worker celery -A celery_app worker --loglevel=info --concurrency=2

echo "📊 Starting scheduled tasks..."
docker-compose exec -d worker celery -A celery_app beat --loglevel=info

echo ""
echo "🎉 BlackSwan Credit Intelligence Platform is now running!"
echo ""
echo "📱 Access the application:"
echo "   • Frontend Dashboard: http://localhost:3000"
echo "   • API Documentation:  http://localhost:8000/docs"
echo "   • API Health Check:   http://localhost:8000/health"
echo "   • MLflow Tracking:    http://localhost:5000"
echo "   • Grafana:           http://localhost:3001 (admin/admin)"
echo ""
echo "🧪 Demo Commands:"
echo "   • View all issuers: curl http://localhost:8000/api/v1/issuers"
echo "   • Get issuer detail: curl http://localhost:8000/api/v1/issuer/1"
echo "   • Inject demo event: python scripts/inject_demo_headline.py --issuer AAPL --headline 'Apple announces debt restructuring' --type restructuring"
echo ""
echo "📋 Useful Commands:"
echo "   • View logs: docker-compose logs -f [service_name]"
echo "   • Stop services: docker-compose down"
echo "   • Restart services: docker-compose restart"
echo "   • View running containers: docker-compose ps"
echo ""
echo "🔧 Troubleshooting:"
echo "   • If services fail to start, check logs: docker-compose logs"
echo "   • If database connection fails, wait a bit longer and try again"
echo "   • If demo data seeding fails, run: docker-compose exec api python scripts/seed_demo_data.py"
echo ""
echo "Press Ctrl+C to stop all services"
echo ""

# Keep the script running and show logs
docker-compose logs -f





