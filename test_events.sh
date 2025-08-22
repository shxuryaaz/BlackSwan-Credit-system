#!/bin/bash

echo "🎯 BlackSwan Event Testing Script"
echo "=================================="

# Function to test an event
test_event() {
    local ticker=$1
    local headline=$2
    echo "📰 Testing: $ticker - $headline"
    docker-compose exec api python tasks_ingest_unstructured.py "$ticker" "$headline"
    echo ""
}

echo "Testing negative events (should decrease scores):"
test_event "AAPL" "Apple faces major lawsuit over privacy violations"
test_event "MSFT" "Microsoft reports disappointing quarterly earnings"
test_event "GOOGL" "Google fined billions for antitrust violations"

echo "Testing positive events (should increase scores):"
test_event "TSLA" "Tesla announces revolutionary new technology"
test_event "JPM" "JPMorgan reports record-breaking profits"
test_event "WMT" "Walmart expands into new markets successfully"

echo "Testing neutral events:"
test_event "AMZN" "Amazon announces new product line"
test_event "XOM" "Exxon announces quarterly results"

echo "✅ Event testing completed! Check your dashboard for live updates."
echo "🌐 Dashboard: http://localhost:3000"
