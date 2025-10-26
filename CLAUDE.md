# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a French job postings data engineering pipeline that scrapes job boards (Indeed.fr, HelloWork), processes the data with Pandas/PySpark, and orchestrates everything with Apache Airflow. The entire stack runs in Docker containers with PostgreSQL for storage.

## Architecture

The pipeline follows this flow:
```
Web Scraping → JSON Files → Pandas Cleaning → Parquet → Load to PostgreSQL
                 (raw/)       (processed/)                  (jobs_data.jobs)
                                    ↓
                           Spark Enrichment → Analytics
                             (analytics/)      (PostgreSQL)
                                    ↑
                             Airflow Orchestration
```

**Key Components:**
- **Airflow**: Orchestrates the ETL pipeline (webserver on :8080, scheduler)
- **PostgreSQL**: Two databases - `airflow` (metadata) and `jobs_db` (data warehouse with `jobs_data` schema)
- **Spark**: Distributed processing with master (:8081) and worker nodes
- **Scrapers**: Object-oriented scraper classes inheriting from `BaseScraper` with session management and rate limiting

**Data Flow:**
1. Scraper classes write JSON files to `data/raw/` with timestamps
2. `validate_raw_data` task checks data quality
3. `clean_with_pandas` deduplicates and cleans → Parquet in `data/processed/`
4. `process_with_spark` enriches data (SparkSubmitOperator) → Parquet in `data/analytics/`
5. `load_to_postgres` bulk loads cleaned data to `jobs_data.jobs` table
6. `generate_analytics` creates daily statistics in `jobs_data.daily_job_stats`

## Development Commands

### Starting/Stopping Services

**Using Makefile (Recommended):**
```bash
# First time setup
make init          # Creates directories, copies .env.example to .env
make build         # Build Docker images
make up            # Start all services

# Regular use
make down          # Stop services
make restart       # Restart all services
make clean         # Remove containers, volumes, and data files
```

**Using Shell Scripts (Alternative):**
```bash
# From project root
scripts/shell/start.sh    # Complete initialization and startup
scripts/shell/stop.sh     # Gracefully stop all services
scripts/shell/cleanup.sh  # Remove containers, volumes, and data (WARNING: destructive)
```

**Note:** Shell scripts automatically navigate to project root, so they work from any directory.

### Testing and Development
```bash
# Test individual components
make test-scraper  # Run scraper standalone
make test-pandas   # Run pandas processor

# Access shells
make shell-airflow # Bash shell in Airflow container
make db-shell      # PostgreSQL shell connected to jobs_db

# View logs
make logs          # All services
make logs-airflow  # Just Airflow
make logs-spark    # Just Spark
```

### Airflow DAG Management
```bash
# Inside Airflow container (make shell-airflow)
airflow dags list
airflow dags trigger french_jobs_pipeline
airflow tasks list french_jobs_pipeline

# Or access Airflow UI: http://localhost:8080 (airflow/airflow)
```

### Database Operations
```bash
# Connect to database
make db-shell

# Or via connection string
psql -h localhost -U airflow -d jobs_db
# Password: airflow
```

## Code Architecture

### Scraper Design Pattern

All scrapers inherit from `BaseScraper` (scrapers/base_scraper.py):
- **Abstract methods**: `scrape_list_page()` and `scrape_job_details()` must be implemented by child classes
- **Built-in features**: Session management with retry strategy, random delays (2-5s), user-agent rotation
- **Statistics tracking**: Counts successful/failed/duplicate scrapes via `self.stats`
- **File output**: `scrape_all()` method orchestrates pagination and saves JSON to timestamped files

**Creating a new scraper:**
```python
from scrapers.base_scraper import BaseScraper

class NewSiteScraper(BaseScraper):
    def __init__(self, search_query, location, **kwargs):
        super().__init__(
            source_name="newsite",
            base_url="https://example.com",
            **kwargs
        )

    def scrape_list_page(self, page_num: int) -> List[str]:
        # Return list of job URLs
        pass

    def scrape_job_details(self, job_url: str) -> Optional[Dict]:
        # Return job data dict with required fields
        pass
```

### DAG Function Pattern

All Python callable functions in `dags/french_jobs_pipeline.py` must add the scrapers directory to the Python path:

```python
def my_dag_function(**kwargs):
    import sys
    sys.path.insert(0, '/opt/airflow')  # Critical for imports to work

    from scrapers.indeed_scraper import IndeedScraper
    # ... rest of function
```

This is required because the `scrapers/` directory is mounted but not automatically in PYTHONPATH.

### Docker Volume Mounts

Local directories map to container paths (defined in docker-compose.yml):
- `./dags` → `/opt/airflow/dags`
- `./scripts` → `/opt/airflow/scripts` (includes Spark jobs like enrich_jobs.py)
- `./scrapers` → `/opt/airflow/scrapers`
- `./config` → `/opt/airflow/config`
- `./data` → `/opt/airflow/data`

**Important**: When running Spark jobs via SparkSubmitOperator, use paths like `/opt/airflow/scripts/enrich_jobs.py` and set `master='spark://spark-master:7077'` explicitly (not in conf dict to avoid conflicts with default YARN master).

## Database Schema

The schema is initialized by `sql/init.sql` on first container startup.

**Key Tables (all in `public` schema):**
- `raw_jobs` - Scraped data with JSONB raw_data column, unique constraint on job_id
- `cleaned_jobs` - Processed jobs with foreign keys to companies and locations
- `companies` - Company dimension with normalized names
- `locations` - French cities/regions with normalized_location unique constraint
- `job_categories` - Job category dimension pre-populated with French tech categories
- `job_analytics` - Pre-aggregated statistics (unique on analysis_date, category, location)
- `salary_trends` - Time-series salary analysis by period, category, location, experience

**Important Indexes:**
- `raw_jobs`: source, posting_date, scraped_at
- `cleaned_jobs`: category, location_id, company_id, posting_date
- `companies`: normalized_name
- `locations`: city, region

**Views:**
- `vw_job_summary` - Joins cleaned_jobs with companies and locations for analytics queries

**Note**: The DAG loads data to `jobs_data.jobs` table which may be created dynamically. Check DAG's `load_to_postgres()` function for actual table structure.

## Working with the DAG

**Main Pipeline Tasks (dags/french_jobs_pipeline.py):**
1. `scraping` TaskGroup:
   - `scrape_indeed` - Scrapes Indeed.fr
   - `scrape_hellowork` - Scrapes HelloWork
2. `validate_raw_data` - Quality checks on scraped JSON
3. `clean_with_pandas` - Deduplication, standardization, feature extraction
4. `process_with_spark` - SparkSubmitOperator running `/opt/airflow/scripts/enrich_jobs.py`
5. `load_to_postgres` - Bulk load cleaned data to database
6. `generate_analytics` - Create daily statistics
7. `data_quality_check` - Final validation

**DAG Configuration:**
- Schedule: Daily at 6 AM (`'0 6 * * *'`)
- Execution timeout: 2 hours
- Retries: 2 with 5-minute delay
- Connections required: `postgres_default`, `spark_default`

**Spark Task Configuration:**
```python
SparkSubmitOperator(
    application='/opt/airflow/scripts/enrich_jobs.py',
    master='spark://spark-master:7077',  # Set explicitly, not in conf
    deploy_mode='client',
    conf={'spark.driver.memory': '2g', 'spark.executor.memory': '2g'}
)
```

## Customizing the Pipeline

### Adding a New Job Source

1. **Create scraper class** in `scrapers/new_source_scraper.py`:
   ```python
   from scrapers.base_scraper import BaseScraper

   class NewSourceScraper(BaseScraper):
       def __init__(self, search_query, **kwargs):
           super().__init__(
               source_name="newsource",
               base_url="https://newsource.com",
               delay_min=kwargs.get('delay_min', 2),
               delay_max=kwargs.get('delay_max', 5)
           )
           self.search_query = search_query

       def scrape_list_page(self, page_num: int) -> List[str]:
           # Implement listing page scraping
           # Return list of job URLs

       def scrape_job_details(self, job_url: str) -> Optional[Dict]:
           # Implement job detail scraping
           # Return dict with keys: title, company, location, url, etc.
   ```

2. **Add configuration** to `config/scraper_config.yaml`:
   ```yaml
   sources:
     newsource:
       enabled: true
       base_url: "https://newsource.com"
       search_params:
         keywords: ["data engineer"]
         locations: ["Paris"]
       max_pages: 5
       rate_limit: 2
   ```

3. **Add DAG task** in `dags/french_jobs_pipeline.py` to the `scraping` TaskGroup:
   ```python
   def scrape_newsource(**kwargs):
       import sys
       sys.path.insert(0, '/opt/airflow')
       from scrapers.new_source_scraper import NewSourceScraper
       # ... implement scraping logic similar to scrape_indeed()

   scrape_newsource_task = PythonOperator(
       task_id='scrape_newsource',
       python_callable=scrape_newsource,
       dag=dag,
   )
   ```

### Modifying Search Parameters

Edit `config/scraper_config.yaml` (changes take effect on next DAG run):
- `sources.indeed.search_params.keywords` - Job search terms
- `sources.indeed.search_params.locations` - French cities to search
- `sources.indeed.max_pages` - Number of pages to scrape (5 pages ≈ 75-150 jobs)
- `sources.indeed.rate_limit` - Delay between requests in seconds

### Changing Processing Logic

- **Data cleaning**: Modify `clean_with_pandas()` function in `dags/french_jobs_pipeline.py` (around line 177-246)
- **Spark processing**: Edit `scripts/enrich_jobs.py` for feature extraction (mounted to `/opt/airflow/scripts/`)
- **Analytics**: Update `generate_analytics()` function (around line 292-318) for custom metrics

### Adjusting DAG Schedule

In `dags/french_jobs_pipeline.py` line 36, change `schedule_interval`:
- `'0 */6 * * *'` - Every 6 hours
- `'0 0 * * 1'` - Weekly on Monday at midnight
- `None` - Manual trigger only (recommended for development)

## Important Technical Details

### Rate Limiting and Ethics
The scrapers implement delays between requests (2-5 seconds by default) via `BaseScraper._random_delay()`. This is an educational project - always respect robots.txt and terms of service.

### Database Connections
- **Airflow metadata**: `postgres_default` connection → `postgresql+psycopg2://airflow:airflow@postgres/airflow`
- **Jobs database**: `jobs_db` on same PostgreSQL server
- **Environment variables**: `JOBS_DB_HOST`, `JOBS_DB_PORT`, `JOBS_DB_NAME`, `JOBS_DB_USER`, `JOBS_DB_PASSWORD`
- **Connection in code**: Use `PostgresHook(postgres_conn_id='postgres_default')` for database operations

### Spark Configuration
- **Master URL**: `spark://spark-master:7077` (container hostname)
- **Worker resources**: 2G memory, 2 cores (configurable in docker-compose.yml)
- **UI access**: http://localhost:8081 for Spark Master UI
- **Scaling**: Add more `spark-worker` services in docker-compose.yml with unique names

### Data Persistence
- **PostgreSQL**: Named volume `postgres-db-volume` (survives `docker compose down`)
- **Local files**: `data/raw/`, `data/processed/`, `data/analytics/` (gitignored, persist on host)
- **Airflow logs**: `logs/` directory (gitignored)
- **Cleanup**: `make clean` removes volumes and local files (destructive!)

### Container Execution Context
- **Airflow user**: UID 50000 (set via `AIRFLOW_UID` env var)
- **File permissions**: Files created in containers may have ownership issues on host (use `chown` if needed)
- **Rebuilding**: After changing Python dependencies in requirements.txt, run `docker compose up -d --build`

## Troubleshooting Common Issues

### Import Errors in Airflow Tasks
```
ModuleNotFoundError: No module named 'scrapers'
```
**Solution**: Add `sys.path.insert(0, '/opt/airflow')` at the start of DAG functions before importing custom modules.

### Scraper Returns Zero Results
**Causes**:
- HTML structure changed (job sites update frequently)
- Rate limiting too aggressive / IP blocked
- Incorrect CSS selectors

**Debugging**:
1. Test scraper standalone: `make test-scraper`
2. Check scraper stats: Look for `self.stats['failed']` count in logs
3. Inspect HTML manually: Use browser DevTools on target site
4. Verify selectors in `scrapers/indeed_scraper.py` or `scrapers/hellowork_scraper.py`

### Spark Job Failures
**Common errors**:
- `Cannot execute: spark-submit --master yarn` - Conflicting master configuration
- Application file not found - Wrong path in SparkSubmitOperator

**Solutions**:
1. Verify application path is correct: `/opt/airflow/scripts/enrich_jobs.py` (not `/opt/airflow/spark_jobs/`)
2. Set `master='spark://spark-master:7077'` as parameter, NOT in conf dict
3. Check Spark UI at http://localhost:8081 for executor errors
4. Verify input files exist: `ls data/processed/`
5. Check Spark logs: `make logs-spark`
6. Ensure sufficient memory allocation (default 2G per worker)

### Database Connection Refused
**Solution**:
1. Check PostgreSQL health: `docker compose ps postgres` (should be "healthy")
2. Wait for initialization: First run takes 30-60 seconds
3. View initialization logs: `docker compose logs postgres | grep -i "database system is ready"`
4. Verify network: `docker compose exec airflow-webserver ping postgres`

### File Permission Errors
When files created in containers can't be accessed on host:
```bash
sudo chown -R $USER:$USER data/ logs/
```

### DAG Not Appearing in Airflow UI
1. Check DAG syntax: `docker compose exec airflow-webserver airflow dags list`
2. View scheduler logs: `make logs-airflow`
3. Verify file is in `dags/` directory and ends with `.py`
4. Check for Python syntax errors in DAG file

## Performance Tuning

### Scraping More Jobs
- Increase `max_pages` in `config/scraper_config.yaml` (5 pages → 10+ pages)
- Decrease `rate_limit` carefully (respect site limits)
- Add more keywords to `search_params.keywords`

### Faster Data Processing
- **Pandas**: Use chunking in `clean_with_pandas()` for files >100MB
- **Spark**: Increase parallelism in `process_with_spark` task configuration
- **Database**: Adjust `chunksize=1000` in `load_to_postgres()` to higher values for bulk inserts

### Scaling Spark Cluster
In `docker-compose.yml`, add more workers:
```yaml
spark-worker-2:
  image: apache/spark:3.5.3
  environment:
    - SPARK_MODE=worker
    - SPARK_MASTER_URL=spark://spark-master:7077
    - SPARK_WORKER_MEMORY=2G
    - SPARK_WORKER_CORES=2
  # ... same config as spark-worker
```

### Database Query Optimization
- Add indexes for frequent queries: `CREATE INDEX idx_name ON table(column);`
- Use `vw_job_summary` view for joins instead of manual JOINs
- Consider partitioning `raw_jobs` by `scraped_at` date for time-series queries

## CI/CD and Testing

### GitHub Actions Workflows

**CI Pipeline (`.github/workflows/ci.yml`)**:
- Linting: Black, Flake8
- Testing: pytest with coverage
- Validation: YAML/SQL syntax
- Security: Safety (dependencies), Bandit (code)
- Triggered on: push, pull requests to main

**Integration Tests (`.github/workflows/pipeline-test.yml`)**:
- Starts full docker-compose stack in GitHub Actions
- Tests PostgreSQL, Airflow, Spark integration
- Validates DAG parsing and database schema
- Note: Scraping may show 403 errors in CI (job sites block cloud IPs - expected)

**Docker Publishing (`.github/workflows/docker-publish.yml`)**:
- Builds images and publishes to GitHub Container Registry
- Security scanning with Trivy
- Tagged with commit SHA and version

### Local Testing

```bash
# Code quality
black --check scrapers/ scripts/ dags/
flake8 scrapers/ scripts/ dags/

# Run unit tests
pytest tests/ -v --cov=scrapers --cov=scripts

# Validate configuration
docker compose config  # Check docker-compose.yml syntax
yamllint config/scraper_config.yaml

# Test individual components
make test-scraper   # Run scraper standalone
make test-pandas    # Run pandas processor
```

### Adding Tests

Create pytest test files in `tests/`:
```python
# tests/test_indeed_scraper.py
from scrapers.indeed_scraper import IndeedScraper

def test_scraper_initialization():
    scraper = IndeedScraper(search_query="test", location="Paris")
    assert scraper.source_name == "indeed"
    assert scraper.stats['total_scraped'] == 0
```

Run tests: `pytest tests/test_indeed_scraper.py -v`

## Key Development Workflows

### First-Time Setup
```bash
make init           # Create directories, copy .env
make build          # Build Docker images
make up             # Start all services
# Wait 60 seconds for initialization
# Access http://localhost:8080 (airflow/airflow)
# Trigger DAG manually or wait for scheduled run
```

### Daily Development
```bash
# Start services
make up

# Make code changes in scrapers/, scripts/, or dags/
# Changes are live-mounted, no rebuild needed (except requirements.txt)

# View logs
make logs-airflow   # Watch Airflow logs
make shell-airflow  # Interactive shell for debugging

# Stop services (keeps data)
make down
```

### After Changing Dependencies
```bash
# Update requirements.txt
make build          # Rebuild images
make up             # Restart with new dependencies
```

### Testing Changes
```bash
# Validate DAG syntax
docker compose exec airflow-webserver airflow dags list

# Trigger DAG manually
docker compose exec airflow-webserver airflow dags trigger french_jobs_pipeline

# Check task status
docker compose exec airflow-webserver airflow dags state french_jobs_pipeline

# Query database to verify data
make db-shell
# In psql: SELECT COUNT(*) FROM jobs_data.jobs;
```

### Complete Cleanup (Destructive)
```bash
make clean          # Removes all containers, volumes, and local data files
# Use this to reset to fresh state
```

## Technology Stack

- **Python**: 3.11
- **Apache Airflow**: 2.8.0 (LocalExecutor with PostgreSQL backend)
- **Apache Spark**: 3.5.3 (standalone cluster mode)
- **PostgreSQL**: 15
- **Pandas**: 2.1.4
- **PySpark**: 3.5.0
- **BeautifulSoup4**: 4.12.2
- **Docker**: Compose V2
