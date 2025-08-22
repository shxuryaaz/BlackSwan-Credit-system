#!/bin/bash

echo "🚀 Starting BlackSwan Credit Intelligence Platform..."
echo ""

# Check if Docker is running
if ! docker info > /dev/null 2>&1; then
    echo "❌ Docker is not running. Please start Docker first."
    exit 1
fi

# Start all services
echo "📦 Starting all services..."
docker-compose up -d

# Wait for services to be ready
echo "⏳ Waiting for services to be ready..."
sleep 10

# Check if services are healthy
echo "🔍 Checking service health..."

# Check API
if curl -f http://localhost:8000/health > /dev/null 2>&1; then
    echo "✅ API is running at http://localhost:8000"
else
    echo "⚠️  API is starting up... (may take a minute)"
fi

# Check Frontend
if curl -f http://localhost:3000 > /dev/null 2>&1; then
    echo "✅ Frontend is running at http://localhost:3000"
else
    echo "⚠️  Frontend is starting up... (may take a minute)"
fi

echo ""
echo "🎯 ACCESS YOUR DASHBOARD:"
echo "   🌐 Main Dashboard: http://localhost:3000"
echo "   📊 API Documentation: http://localhost:8000/docs"
echo "   📈 MLflow: http://localhost:5000"
echo "   📊 Grafana: http://localhost:3001 (admin/admin)"
echo ""
echo "🔧 USEFUL COMMANDS:"
echo "   📋 View logs: docker-compose logs -f"
echo "   🛑 Stop services: docker-compose down"
echo "   🔄 Restart: docker-compose restart"
echo "   🧹 Clean up: docker-compose down -v"
echo ""
echo "📝 DEMO DATA:"
echo "   The system comes with sample data for Apple, Microsoft, Tesla, and others."
echo "   You can inject test news events using:"
echo "   python scripts/inject_demo_headline.py"
echo ""
echo "🎉 Your BlackSwan Credit Intelligence Platform is ready!"





