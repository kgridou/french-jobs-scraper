#!/bin/bash

# French Jobs Scraper - Startup Script
# This script initializes and starts all services

set -e

# Get the project root directory (two levels up from this script)
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$PROJECT_ROOT"

echo "🇫🇷 French Jobs Data Pipeline - Startup"
echo "========================================"
echo "Project root: $PROJECT_ROOT"
echo ""

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Check if Docker is running
if ! docker info > /dev/null 2>&1; then
    echo -e "${RED}❌ Docker is not running. Please start Docker first.${NC}"
    exit 1
fi

# Check if docker-compose is available
if ! command -v docker-compose &> /dev/null; then
    echo -e "${RED}❌ docker-compose not found. Please install docker-compose.${NC}"
    exit 1
fi

echo -e "${GREEN}✓ Docker is running${NC}"
echo ""

# Create .env file if it doesn't exist
if [ ! -f .env ]; then
    echo -e "${YELLOW}Creating .env file from template...${NC}"
    cp .env.example .env
    echo -e "${GREEN}✓ .env file created${NC}"
else
    echo -e "${GREEN}✓ .env file exists${NC}"
fi
echo ""

# Create necessary directories
echo "Creating data directories..."
mkdir -p data/raw data/processed data/analytics
mkdir -p logs
echo -e "${GREEN}✓ Directories created${NC}"
echo ""

# Create .gitkeep files
touch data/raw/.gitkeep data/processed/.gitkeep data/analytics/.gitkeep
touch logs/.gitkeep

# Build and start services
echo "Building Docker images..."
docker-compose build --no-cache

echo ""
echo "Starting services..."
docker-compose up -d

echo ""
echo "Waiting for services to be healthy..."
sleep 10

# Wait for PostgreSQL
echo "Waiting for PostgreSQL..."
until docker-compose exec -T postgres pg_isready -U airflow > /dev/null 2>&1; do
    echo -n "."
    sleep 2
done
echo -e "${GREEN}✓ PostgreSQL is ready${NC}"

# Wait for Airflow webserver
echo "Waiting for Airflow webserver..."
until curl -sf http://localhost:8080/health > /dev/null 2>&1; do
    echo -n "."
    sleep 3
done
echo -e "${GREEN}✓ Airflow webserver is ready${NC}"

echo ""
echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}✅ All services are running!${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""
echo "Access your services:"
echo ""
echo "  🌐 Airflow UI:     http://localhost:8080"
echo "     Username:       admin"
echo "     Password:       admin"
echo ""
echo "  ⚡ Spark Master:   http://localhost:8081"
echo ""
echo "  🐘 PostgreSQL:     localhost:5432"
echo "     Database:       jobs_db"
echo "     User:           airflow"
echo "     Password:       airflow"
echo ""
echo "Useful commands:"
echo ""
echo "  View logs:         docker-compose logs -f"
echo "  Stop services:     docker-compose down"
echo "  Restart:           docker-compose restart"
echo "  Enter Airflow:     docker-compose exec airflow-webserver bash"
echo ""
echo "To trigger the pipeline:"
echo "  1. Go to http://localhost:8080"
echo "  2. Enable the 'french_jobs_pipeline' DAG"
echo "  3. Click the play button to trigger"
echo ""
echo -e "${YELLOW}Note: First run may take a few minutes to initialize${NC}"
echo ""
