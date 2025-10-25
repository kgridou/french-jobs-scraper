.PHONY: help build up down restart logs clean test check-services

help:
	@echo "French Job Scraper - Available Commands:"
	@echo "  make build          - Build Docker images"
	@echo "  make up             - Start all services"
	@echo "  make down           - Stop all services"
	@echo "  make restart        - Restart all services"
	@echo "  make logs           - View logs (all services)"
	@echo "  make logs-airflow   - View Airflow logs"
	@echo "  make logs-spark     - View Spark logs"
	@echo "  make clean          - Remove containers and volumes"
	@echo "  make check-services - Check status of all services"
	@echo "  make shell-airflow  - Open bash shell in Airflow container"
	@echo "  make db-shell       - Connect to PostgreSQL database"
	@echo "  make init           - Initialize project (first time setup)"

init:
	@echo "Initializing project..."
	@mkdir -p logs data/raw data/processed data/analytics
	@cp .env.example .env
	@echo "export AIRFLOW_UID=$$(id -u)" >> .env
	@echo "Project initialized! You can now run 'make up'"

build:
	@echo "Building Docker images..."
	docker-compose build

up:
	@echo "Starting all services..."
	docker-compose up -d
	@echo "Services started!"
	@echo "Airflow UI: http://localhost:8080 (airflow/airflow)"
	@echo "Spark UI: http://localhost:8081"

down:
	@echo "Stopping all services..."
	docker-compose down

restart:
	@echo "Restarting all services..."
	docker-compose restart

logs:
	docker-compose logs -f

logs-airflow:
	docker-compose logs -f airflow-webserver airflow-scheduler

logs-spark:
	docker-compose logs -f spark-master spark-worker

clean:
	@echo "Removing all containers, volumes, and temporary files..."
	docker-compose down -v
	rm -rf logs/* data/raw/* data/processed/* data/analytics/*
	@echo "Clean complete!"

check-services:
	@echo "Checking service status..."
	@docker-compose ps

shell-airflow:
	docker-compose exec airflow-webserver bash

db-shell:
	docker-compose exec postgres psql -U airflow -d jobs_db

test-scraper:
	docker-compose exec airflow-webserver python /opt/airflow/scripts/scraper.py

test-pandas:
	docker-compose exec airflow-webserver python /opt/airflow/scripts/pandas_processor.py
