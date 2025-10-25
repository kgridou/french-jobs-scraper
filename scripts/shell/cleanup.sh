#!/bin/bash

# French Jobs Scraper - Cleanup Script
# Removes all containers, volumes, and data

set -e

# Get the project root directory (two levels up from this script)
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$PROJECT_ROOT"

echo "🗑️  French Jobs Pipeline - Cleanup"
echo "================================="
echo "Project root: $PROJECT_ROOT"
echo ""
echo "⚠️  WARNING: This will remove:"
echo "  - All Docker containers"
echo "  - All Docker volumes (database data will be lost)"
echo "  - All scraped and processed data"
echo ""
read -p "Are you sure? (yes/no): " -r
echo ""

if [[ ! $REPLY =~ ^[Yy][Ee][Ss]$ ]]; then
    echo "Cleanup cancelled"
    exit 1
fi

echo "Stopping and removing containers..."
docker-compose down -v

echo "Removing data directories..."
rm -rf data/raw/*
rm -rf data/processed/*
rm -rf data/analytics/*
rm -rf logs/*

echo "Cleaning up temporary files..."
find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
find . -type f -name "*.pyc" -delete 2>/dev/null || true

echo ""
echo "✅ Cleanup complete!"
echo ""
echo "To start fresh, run: scripts/shell/start.sh"
