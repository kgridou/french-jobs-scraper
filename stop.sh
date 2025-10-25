#!/bin/bash

# French Jobs Scraper - Stop Script
# Gracefully stops all services

echo "🛑 Stopping French Jobs Pipeline services..."
echo ""

docker-compose down

echo ""
echo "✅ All services stopped"
echo ""
echo "To remove all data and start fresh, run: ./cleanup.sh"
