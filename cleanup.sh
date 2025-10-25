#!/bin/bash

# French Jobs Scraper - Cleanup Script
# Removes all containers, volumes, and data

set -e

echo "🗑️  French Jobs Pipeline - Cleanup"
echo "================================="
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
rm -rf airflow/logs/*

echo "Cleaning up Airflow metadata..."
rm -f airflow/*.pid
rm -f airflow/*.db

echo ""
echo "✅ Cleanup complete!"
echo ""
echo "To start fresh, run: ./start.sh"
