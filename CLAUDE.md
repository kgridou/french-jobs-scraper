# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a French job postings data engineering pipeline that scrapes job boards (Indeed.fr, HelloWork), processes the data with Pandas/PySpark, and orchestrates everything with Apache Airflow. The entire stack runs in Docker containers with PostgreSQL for storage.

## Architecture

The pipeline follows this flow:
```
Web Scraping → PostgreSQL (raw_jobs) → Pandas Cleaning → PySpark Analytics → PostgreSQL (cleaned_jobs, analytics)
                                              ↑
                                         Airflow Orchestration
```

**Key Components:**
- **Airflow**: Orchestrates the ETL pipeline (webserver on :8080, scheduler)
- **PostgreSQL**: Stores raw scraped data, cleaned data, and analytics tables (port :5432)
- **Spark**: Distributed processing with master (:8081) and worker nodes
- **Python Scripts**: Scrapers (Indeed, HelloWork), Pandas processor, Spark enrichment

**Data Flow:**
1. Scrapers write JSON to `data/raw/`
2. Validation checks data quality
3. Pandas cleans data → Parquet in `data/processed/`
4. Spark enriches data → Parquet in `data/analytics/`
5. Data loaded to PostgreSQL tables
6. Analytics aggregations generated

## Development Commands

### Starting/Stopping Services
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

## Code Structure

```
french-jobs-scraper/
├── dags/
│   └── french_jobs_pipeline.py    # Main Airflow DAG
├── scrapers/
│   ├── __init__.py                # Package initialization
│   ├── base_scraper.py            # Abstract base with session management, rate limiting
│   ├── indeed_scraper.py          # Indeed.fr specific implementation
│   └── hellowork_scraper.py       # HelloWork.com implementation
├── scripts/
│   ├── scraper.py                 # Generic scraper base class
│   ├── pandas_processor.py        # Data cleaning with Pandas
│   ├── spark_processor.py         # PySpark analytics and enrichment
│   └── enrich_jobs.py             # Spark job for skill extraction and classification
├── sql/
│   ├── init.sql                   # Database schema initialization
│   ├── sample_queries.sql         # Example analytics queries
│   └── analytics_queries.sql      # Additional query examples
├── config/
│   └── scraper_config.yaml        # Scraping parameters, keywords, locations, rate limits
├── docs/                          # Additional documentation
│   ├── ARCHITECTURE.md            # System architecture details
│   ├── QUICKSTART.md              # Quick start guide
│   ├── STRUCTURE.md               # Project structure details
│   ├── PROJECT_SUMMARY.md         # Project overview
│   ├── PROJECT_ORGANIZATION.md    # Reorganization notes
│   ├── GETTING_STARTED.md         # Getting started guide
│   └── SETUP_NOTES.md             # Additional setup information
├── data/
│   ├── raw/                       # Scraped JSON files (gitignored)
│   ├── processed/                 # Cleaned Parquet files (gitignored)
│   └── analytics/                 # Analytics Parquet files (gitignored)
├── logs/                          # Airflow logs (gitignored)
├── docker-compose.yml             # Service orchestration
├── Dockerfile                     # Custom Airflow image
├── Dockerfile.airflow             # Alternative Airflow build
├── Dockerfile.spark               # Spark image definition
├── requirements.txt               # Python dependencies
├── Makefile                       # Convenience commands
├── .env.example                   # Environment variables template
├── .gitignore                     # Git ignore rules
├── CLAUDE.md                      # This file - AI development guide
└── README.md                      # Main project documentation
```

**Important:** The Docker volume mounts in docker-compose.yml map these local directories to container paths:
- `./dags` → `/opt/airflow/dags`
- `./scripts` → `/opt/airflow/scripts`
- `./scrapers` → `/opt/airflow/scrapers` (may need to be added to PYTHONPATH)
- `./config` → `/opt/airflow/config`
- `./data` → `/opt/airflow/data`

## Database Schema

**Main Tables:**
- `raw_jobs` - Scraped data with JSONB raw_data column
- `cleaned_jobs` - Processed jobs with foreign keys to dimensions
- `companies` - Company dimension with normalized names
- `locations` - French cities/regions with normalization
- `job_categories` - Job category dimension
- `job_analytics` - Pre-aggregated statistics by category/location
- `salary_trends` - Time-series salary analysis

**Important Indexes:**
- `raw_jobs`: source, posting_date, scraped_at
- `cleaned_jobs`: category, location_id, company_id, posting_date
- `job_analytics`: analysis_date, category

**Views:**
- `vw_job_summary` - Joins cleaned_jobs with companies and locations for easy querying

## Working with the DAG

**Main Pipeline Tasks (dags/french_jobs_pipeline.py):**
1. `scraping` TaskGroup:
   - `scrape_indeed` - Scrapes Indeed.fr
   - `scrape_hellowork` - Scrapes HelloWork
2. `validate_raw_data` - Quality checks on scraped JSON
3. `clean_with_pandas` - Deduplication, standardization, feature extraction
4. `process_with_spark` - SparkSubmitOperator for enrichment job
5. `load_to_postgres` - Bulk load cleaned data to database
6. `generate_analytics` - Create daily statistics
7. `data_quality_check` - Final validation

**DAG Configuration:**
- Schedule: Daily at 6 AM (`'0 6 * * *'`)
- Execution timeout: 2 hours
- Retries: 2 with 5-minute delay
- Connections required: `postgres_default`, `spark_default`

## Customizing the Pipeline

**Add New Job Sources:**
1. Create new scraper in `scrapers/new_source_scraper.py` inheriting from `BaseScraper`
2. Implement `scrape_list_page()` and `scrape_job_details()` methods
3. Add source configuration to `config/scraper_config.yaml`
4. Add scraping task to Airflow DAG in the `scraping` TaskGroup

**Modify Search Parameters:**
Edit `config/scraper_config.yaml`:
- `sources.indeed.search_params.keywords` - Add search terms
- `sources.indeed.search_params.locations` - Add cities
- `sources.indeed.max_pages` - Control scraping depth
- `sources.indeed.rate_limit` - Adjust delay between requests

**Change Processing Logic:**
- Data cleaning: Edit `scripts/pandas_processor.py` or the `clean_with_pandas()` function in DAG
- Feature extraction: Modify `scripts/spark_processor.py` or `scripts/enrich_jobs.py`
- Analytics: Update `generate_analytics()` function or add new tasks

**Adjust Schedule:**
In `dags/french_jobs_pipeline.py`, change `schedule_interval`:
- `'0 */6 * * *'` - Every 6 hours
- `'0 0 * * 1'` - Weekly on Monday
- `None` - Manual trigger only

## Important Notes

**Rate Limiting:**
The scrapers implement delays between requests (2-5 seconds by default). Always respect robots.txt and terms of service. This is an educational project.

**Database Connections:**
- Airflow uses `postgres_default` connection (configured in docker-compose.yml environment variables)
- Connection string: `postgresql+psycopg2://airflow:airflow@postgres/airflow`
- Jobs database: `jobs_db` on same server

**Spark Configuration:**
- Master URL: `spark://spark-master:7077`
- Worker memory: 2G
- Worker cores: 2
- Can be scaled by adding more worker services in docker-compose.yml

**Data Persistence:**
- PostgreSQL data: Stored in Docker volume `postgres-db-volume`
- Local data files: `data/raw/`, `data/processed/`, `data/analytics/`
- Airflow logs: `logs/`

**Environment Variables:**
Key variables set in docker-compose.yml:
- `AIRFLOW_UID` - User ID for file permissions (default: 50000)
- `JOBS_DB_*` - Jobs database connection parameters
- `SPARK_MASTER_URL` - Spark master connection

## Common Issues

**Airflow tasks fail with import errors:**
- Ensure Python files are in the correct mounted volumes
- Check `sys.path.insert(0, '/opt/airflow')` in DAG functions
- Verify requirements.txt includes all dependencies

**Scraper returns no results:**
- Website HTML structure may have changed (Indeed updates frequently)
- Check selectors in `scrape_indeed_fr()` or scraper classes
- Verify rate limiting isn't too aggressive
- Test with browser developer tools to inspect current HTML

**Spark job fails:**
- Check Spark UI at http://localhost:8081 for errors
- Verify data files exist in expected paths
- Ensure PostgreSQL JDBC driver is available for Spark-to-PostgreSQL writes
- Check memory allocation if processing large datasets

**Database connection errors:**
- Ensure PostgreSQL service is healthy: `docker-compose ps`
- Wait for initialization to complete (~30-60 seconds on first run)
- Check logs: `docker-compose logs postgres`

## Performance Tuning

**For Larger Datasets:**
- Increase `max_pages` in scraper configuration
- Add more Spark workers in docker-compose.yml
- Increase Spark worker memory/cores
- Add database indexes for common query patterns
- Partition large tables by date

**For Faster Processing:**
- Adjust batch_size in `load_to_postgres()` (currently 1000)
- Use Pandas chunking for very large files
- Increase Spark parallelism settings
- Consider materialized views for complex analytics

## Technology Versions

- Python: 3.11
- Apache Airflow: 2.8.0
- Apache Spark: 3.5
- PostgreSQL: 15
- Pandas: 2.1.4
- PySpark: 3.5.0
- BeautifulSoup4: 4.12.2
