#!/bin/bash

# French Jobs Scraper - Stop Script
# Gracefully stops all services

# Get the project root directory (two levels up from this script)
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$PROJECT_ROOT"

echo "🛑 Stopping French Jobs Pipeline services..."
echo ""

docker-compose down

echo ""
echo "✅ All services stopped"
echo ""
echo "To remove all data and start fresh, run: scripts/shell/cleanup.sh"
