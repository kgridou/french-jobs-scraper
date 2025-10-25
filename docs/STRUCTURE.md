# Project Structure

```
french-jobs-scraper/
│
├── README.md                          # Main documentation
├── QUICKSTART.md                      # Quick start guide
├── LICENSE                            # MIT License
├── Makefile                           # Convenient shortcuts
├── .gitignore                         # Git ignore rules
├── .env.example                       # Environment variables template
│
├── docker-compose.yml                 # Docker orchestration
├── Dockerfile.airflow                 # Airflow container definition
├── Dockerfile.spark                   # Spark container definition
├── requirements.txt                   # Python dependencies
│
├── start.sh                           # Startup script
├── stop.sh                            # Stop script
├── cleanup.sh                         # Cleanup script
│
├── airflow/                           # Airflow configuration
│   ├── dags/                         # DAG definitions
│   │   └── french_jobs_pipeline.py   # Main pipeline DAG
│   ├── plugins/                      # Custom Airflow plugins
│   └── logs/                         # Airflow logs (generated)
│
├── scrapers/                          # Web scraping modules
│   ├── __init__.py                   # Package initialization
│   ├── base_scraper.py               # Base scraper class
│   ├── indeed_scraper.py             # Indeed.fr scraper
│   └── hellowork_scraper.py          # HelloWork scraper
│
├── spark/                             # PySpark jobs
│   ├── jobs/                         # Spark job scripts
│   │   └── enrich_jobs.py           # Data enrichment job
│   └── config/                       # Spark configuration
│
├── data/                              # Data storage
│   ├── raw/                          # Raw scraped data (JSON)
│   ├── processed/                    # Cleaned data (Parquet)
│   └── analytics/                    # Analytics-ready data
│
├── sql/                               # SQL scripts
│   ├── init.sql                      # Database initialization
│   └── analytics_queries.sql         # Pre-made analytics queries
│
└── notebooks/                         # Jupyter notebooks (optional)
    └── analysis.ipynb                # Data analysis examples
```

## Key Files Explained

### Configuration
- **docker-compose.yml**: Orchestrates all services (Airflow, Spark, PostgreSQL, Redis)
- **Dockerfile.airflow**: Custom Airflow image with all dependencies
- **Dockerfile.spark**: Spark image with PySpark and data science libraries
- **requirements.txt**: Python packages for scraping, processing, and analysis
- **.env.example**: Template for environment variables (copy to .env)

### Scripts
- **start.sh**: One-command startup (recommended for first-time setup)
- **stop.sh**: Gracefully stops all services
- **cleanup.sh**: Removes all data and containers for fresh start
- **Makefile**: Shortcuts for common operations (type `make help`)

### Airflow
- **dags/french_jobs_pipeline.py**: Main ETL pipeline
  - Scrapes Indeed.fr and HelloWork
  - Validates data quality
  - Cleans with Pandas
  - Enriches with PySpark
  - Loads to PostgreSQL
  - Generates analytics

### Scrapers
- **base_scraper.py**: Abstract base class with common functionality
  - Session management with retry logic
  - Rate limiting
  - Error handling
  - Statistics tracking

- **indeed_scraper.py**: Scrapes Indeed.fr
  - Search results pagination
  - Job detail extraction
  - Salary parsing
  - Skill detection

- **hellowork_scraper.py**: Scrapes HelloWork.com
  - Similar structure to Indeed scraper
  - Adapted for HelloWork's HTML structure

### Spark Jobs
- **enrich_jobs.py**: PySpark data enrichment
  - Skill extraction using NLP patterns
  - Experience level classification
  - Location enrichment
  - Salary normalization
  - Quality scoring
  - Skill demand aggregation

### SQL
- **init.sql**: Creates database schema
  - Tables: jobs, companies, skills, job_skills, scraping_runs
  - Indexes for query optimization
  - Views for common queries
  - Triggers for timestamp updates

- **analytics_queries.sql**: 18 pre-made analytics queries
  - Top hiring companies
  - Salary trends
  - Skill demand
  - Regional analysis
  - Remote work stats
  - And more...

### Data Directories
- **data/raw/**: JSON files from scrapers (timestamped)
- **data/processed/**: Parquet files after Pandas cleaning
- **data/analytics/**: Final enriched data from Spark

## Service Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                     Docker Network                          │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  ┌──────────────┐    ┌──────────────┐    ┌─────────────┐ │
│  │   Airflow    │───▶│  PostgreSQL  │◀───│   Spark     │ │
│  │  (Scheduler) │    │   (jobs_db)  │    │  (Master +  │ │
│  │              │    │              │    │   Worker)   │ │
│  └──────────────┘    └──────────────┘    └─────────────┘ │
│         │                    │                    │        │
│         ▼                    │                    │        │
│  ┌──────────────┐           │                    │        │
│  │   Airflow    │           │                    │        │
│  │  (Webserver) │           │                    │        │
│  │   :8080      │           │                    │        │
│  └──────────────┘           │                    │        │
│         │                    │                    │        │
│         ▼                    ▼                    ▼        │
│  ┌──────────────┐    ┌──────────────┐    ┌─────────────┐ │
│  │    Redis     │    │  Mounted     │    │   Mounted   │ │
│  │   (Backend)  │    │   Volumes    │    │   Volumes   │ │
│  └──────────────┘    └──────────────┘    └─────────────┘ │
│                             │                    │         │
└─────────────────────────────┼────────────────────┼─────────┘
                              │                    │
                              ▼                    ▼
                      ┌──────────────┐    ┌─────────────┐
                      │  ./data/     │    │  ./spark/   │
                      │  ./scrapers/ │    │    jobs/    │
                      │  ./sql/      │    └─────────────┘
                      └──────────────┘
```

## Data Flow

```
1. Scraping Phase
   Web Sources → Scrapers → Raw JSON (data/raw/)

2. Validation Phase
   Raw JSON → Data Quality Checks → Validation Report

3. Cleaning Phase
   Raw JSON → Pandas Processing → Cleaned Parquet (data/processed/)

4. Enrichment Phase
   Cleaned Parquet → PySpark → Enriched Parquet (data/analytics/)

5. Loading Phase
   Enriched Parquet → PostgreSQL → jobs_data schema

6. Analytics Phase
   PostgreSQL → Aggregations → Analytics Tables
```

## Port Mappings

| Service          | Internal Port | External Port | Access                |
|------------------|---------------|---------------|-----------------------|
| Airflow Web      | 8080         | 8080         | http://localhost:8080 |
| Spark Master UI  | 8080         | 8081         | http://localhost:8081 |
| Spark Master     | 7077         | 7077         | spark://localhost:7077|
| PostgreSQL       | 5432         | 5432         | localhost:5432        |
| Redis            | 6379         | (internal)   | N/A                   |

## Environment Variables

Key variables in `.env`:
- `AIRFLOW_UID`: User ID for Airflow (default: 50000)
- `POSTGRES_*`: Database credentials
- `SPARK_*`: Spark configuration
- `SCRAPING_DELAY_*`: Rate limiting settings
- `DATA_*_PATH`: Data directory paths

## Dependencies

### Python Packages
- **Scraping**: beautifulsoup4, scrapy, requests, selenium
- **Data Processing**: pandas, numpy, pyspark
- **Database**: psycopg2-binary, sqlalchemy
- **NLP**: nltk, spacy
- **Workflow**: apache-airflow + providers

### System Dependencies
- Docker 20.10+
- Docker Compose 2.0+
- 8GB RAM minimum
- 10GB disk space

## Extending the Project

### Add a New Scraper
1. Create `scrapers/new_site_scraper.py`
2. Inherit from `BaseScraper`
3. Implement `scrape_list_page()` and `scrape_job_details()`
4. Register with `ScraperFactory`
5. Add task to Airflow DAG

### Add Custom Analytics
1. Add queries to `sql/analytics_queries.sql`
2. Or create views in PostgreSQL
3. Or create materialized views for performance

### Modify Pipeline Schedule
Edit `french_jobs_pipeline.py`:
```python
schedule_interval='0 6 * * *'  # Daily at 6 AM
# Change to:
schedule_interval='0 */6 * * *'  # Every 6 hours
```

## Performance Tuning

### For More Data
- Increase `max_pages` in scraper tasks
- Add more Spark workers in docker-compose.yml
- Increase memory allocation for Spark

### For Faster Processing
- Reduce `SCRAPING_DELAY` (be respectful!)
- Increase Spark parallelism
- Add database indexes for common queries

### For Production Use
- Add authentication to Airflow
- Use external PostgreSQL (not container)
- Implement proper secrets management
- Add monitoring (Prometheus/Grafana)
- Set up CI/CD pipeline
