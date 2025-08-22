#!/bin/bash

echo "Setting up environment variables for BlackSwan Credit Intelligence Platform..."

# Create .env file with correct values
cat > .env << 'EOF'
# Database Configuration
POSTGRES_HOST=postgres
POSTGRES_PORT=5432
POSTGRES_DB=credtech
POSTGRES_USER=credtech
POSTGRES_PASSWORD=credtech_pass

# Redis Configuration
REDIS_URL=redis://redis:6379/0

# MLflow Configuration
MLFLOW_URI=http://mlflow:5000
MLFLOW_TRACKING_URI=http://localhost:5001

# External API Keys (optional for demo)
FRED_API_KEY=
WORLD_BANK_API_KEY=

# Data Ingestion Configuration
EDGAR_CACHE_DIR=/data/edgar_cache
YFINANCE_DELAY_MINUTES=15
RSS_UPDATE_INTERVAL_MINUTES=5
STRUCTURED_UPDATE_INTERVAL_MINUTES=15

# Model Configuration
MODEL_VERSION=v1.0
SCORING_WEIGHTS_BASE=0.55
SCORING_WEIGHTS_MARKET=0.25
SCORING_WEIGHTS_EVENT=0.12
SCORING_WEIGHTS_MACRO=0.08

# Event Classification Weights
EVENT_WEIGHT_DEFAULT=-7.0
EVENT_WEIGHT_BANKRUPTCY=-9.0
EVENT_WEIGHT_RESTRUCTURING=-4.0
EVENT_WEIGHT_DOWNGRADE=-5.0
EVENT_WEIGHT_EARNINGS_MISS=-2.5
EVENT_WEIGHT_GUIDANCE_CUT=-3.0
EVENT_WEIGHT_MANAGEMENT_CHANGE=-2.0
EVENT_WEIGHT_ACQUISITION=1.0
EVENT_WEIGHT_POSITIVE_EARNINGS_BEAT=2.0
EVENT_WEIGHT_DIVIDEND_CUT=-2.5
EVENT_WEIGHT_REGULATORY_INVESTIGATION=-3.5

# Decay Configuration
EVENT_HALF_LIFE_DAYS=7
MAX_DAILY_EVENT_IMPACT=15

# Alerting Configuration
ALERT_THRESHOLD_SCORE_CHANGE=5
ALERT_THRESHOLD_HOURS=24

# Frontend Configuration
NEXT_PUBLIC_API_URL=http://api:8000
NEXT_PUBLIC_APP_NAME=BlackSwan Credit Intelligence

# Monitoring Configuration
PROMETHEUS_ENABLED=true
SENTRY_DSN=

# Development Configuration
DEBUG=true
LOG_LEVEL=INFO
ENVIRONMENT=development

# Celery Configuration
CELERY_BROKER_URL=redis://redis:6379/0
CELERY_RESULT_BACKEND=redis://redis:6379/0
CELERY_TASK_SERIALIZER=json
CELERY_RESULT_SERIALIZER=json
CELERY_ACCEPT_CONTENT=json
CELERY_TIMEZONE=UTC
CELERY_ENABLE_UTC=True

# Security Configuration
SECRET_KEY=blackswan-credit-intelligence-secret-key-2024
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30
EOF

echo "✅ Environment file created successfully!"
echo ""
echo "Key changes made:"
echo "  - NEXT_PUBLIC_API_URL: http://api:8000 (Docker internal network)"
echo "  - MLFLOW_TRACKING_URI: http://localhost:5001 (external access)"
echo "  - SECRET_KEY: Set to secure value"
echo ""
echo "To apply changes, restart your containers:"
echo "  docker-compose down"
echo "  docker-compose up -d"





