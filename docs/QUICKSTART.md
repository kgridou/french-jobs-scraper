# Quick Start Guide

This guide will help you get the French Job Scraper pipeline up and running in minutes.

## Prerequisites

Make sure you have installed:
- Docker (version 20.10 or higher)
- Docker Compose (version 2.0 or higher)
- At least 4GB of free RAM

Check your versions:
```bash
docker --version
docker-compose --version
```

## Step 1: Initial Setup

Navigate to the project directory and run initialization:

```bash
cd french-jobs-scraper
make init
```

This creates necessary directories and environment files.

## Step 2: Build and Start Services

Build the Docker images:
```bash
make build
```

Start all services:
```bash
make up
```

Wait 30-60 seconds for services to initialize. You can monitor the startup:
```bash
make logs
```

## Step 3: Access Services

Once services are running:

### Airflow Web UI
- URL: http://localhost:8080
- Username: `airflow`
- Password: `airflow`

### Spark Master UI
- URL: http://localhost:8081

### PostgreSQL Database
Connect using:
```bash
make db-shell
```
Or use any PostgreSQL client:
- Host: localhost
- Port: 5432
- Database: jobs_db
- Username: airflow
- Password: airflow

## Step 4: Run the Pipeline

### Option A: Via Airflow UI (Recommended)
1. Go to http://localhost:8080
2. Find the `french_jobs_pipeline` DAG
3. Toggle it to ON (unpause)
4. Click the "Play" button to trigger manually

### Option B: Via Command Line
```bash
# Test individual components
make test-scraper    # Test the scraper
make test-pandas     # Test pandas processor

# Or trigger the full pipeline via Airflow CLI
docker-compose exec airflow-scheduler airflow dags trigger french_jobs_pipeline
```

## Step 5: Monitor Progress

Watch the pipeline execution:
```bash
make logs-airflow
```

In the Airflow UI, you can:
- See task progress in the Graph or Gantt views
- Check logs for each task
- View execution history

## Step 6: Query the Data

Once the pipeline completes, query your data:

```bash
make db-shell
```

Then run SQL queries:
```sql
-- See recent jobs
SELECT title, company, location, salary_avg 
FROM vw_job_summary 
ORDER BY posting_date DESC 
LIMIT 10;

-- Job count by category
SELECT category, COUNT(*) 
FROM cleaned_jobs 
GROUP BY category 
ORDER BY COUNT(*) DESC;

-- Average salary by city
SELECT location, AVG(salary_avg) as avg_salary
FROM job_analytics
GROUP BY location
ORDER BY avg_salary DESC;
```

## Common Commands

```bash
make up              # Start services
make down            # Stop services
make restart         # Restart services
make logs            # View all logs
make check-services  # Check service status
make clean           # Clean all data and containers
```

## Troubleshooting

### Services won't start
```bash
# Check Docker resources
docker system df

# Remove old containers
make clean
make up
```

### "Port already in use" error
Check if ports 5432, 8080, or 8081 are already in use:
```bash
# On Linux/Mac
sudo lsof -i :8080
sudo lsof -i :5432

# On Windows
netstat -ano | findstr :8080
```

### Airflow shows "No data" in DAGs
Wait 1-2 minutes for Airflow to scan the DAGs directory. Refresh the page.

### Database connection errors
Ensure PostgreSQL is fully started:
```bash
docker-compose logs postgres
```

## Next Steps

1. **Customize Scraping**: Edit `config/scraper_config.yaml` to add search terms or locations
2. **Schedule Changes**: Modify the DAG schedule in `dags/french_jobs_pipeline.py`
3. **Add Visualizations**: Connect to the database with Tableau, PowerBI, or Superset
4. **Scale Up**: Add more Spark workers in `docker-compose.yml`

## Getting Help

- Check logs: `make logs`
- View service status: `make check-services`
- Database shell: `make db-shell`
- Airflow shell: `make shell-airflow`

For issues, check:
1. All services are running: `make check-services`
2. No port conflicts
3. Sufficient disk space and RAM
4. Docker daemon is running

Happy scraping! 🚀
