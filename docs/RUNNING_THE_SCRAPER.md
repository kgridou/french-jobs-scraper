# Running the Scraper - Getting Real Data

This guide shows you how to actually run the French job scraper and collect real data.

## Quick Start - Get Data Now!

### Step 1: Start All Services

```bash
docker compose up -d
```

Wait 30-60 seconds for all services to initialize.

### Step 2: Check Services are Running

```bash
docker compose ps
```

You should see all services with status "Up":
- postgres
- airflow-webserver
- airflow-scheduler
- spark-master
- spark-worker

### Step 3: Access Airflow UI

Open your browser: http://localhost:8080

**Login credentials:**
- Username: `airflow`
- Password: `airflow`

### Step 4: Trigger the Pipeline

**Option A: Via Airflow UI (Recommended)**

1. Go to http://localhost:8080
2. Find the DAG named **`french_jobs_pipeline`**
3. Toggle it to **ON** (click the toggle switch to unpause)
4. Click the **▶️ Play button** on the right side
5. Select **"Trigger DAG"**
6. Watch the tasks execute in real-time!

**Option B: Via Command Line**

```bash
# Trigger the DAG
docker compose exec airflow-scheduler airflow dags trigger french_jobs_pipeline

# Watch the logs
docker compose logs -f airflow-scheduler
```

### Step 5: Monitor Progress

In the Airflow UI:
1. Click on the DAG name `french_jobs_pipeline`
2. Click on the latest run (top row)
3. Switch to **Graph view** to see task progress
4. Click on any task to see logs

**Expected tasks:**
1. ✅ **scraping.scrape_indeed** - Scrapes Indeed.fr (5 pages)
2. ✅ **scraping.scrape_hellowork** - Scrapes HelloWork.com (5 pages)
3. ✅ **validate_raw_data** - Validates scraped JSON files
4. ✅ **clean_with_pandas** - Cleans and deduplicates data
5. ✅ **process_with_spark** - Enriches data with Spark
6. ✅ **load_to_postgres** - Loads to database
7. ✅ **generate_analytics** - Creates analytics tables
8. ✅ **data_quality_check** - Validates data quality

### Step 6: Verify Data was Collected

**Check raw scraped data:**
```bash
# List raw JSON files
ls -lh data/raw/

# Count jobs in raw files
cat data/raw/*.json | grep -c '"title"'
```

**Check processed data:**
```bash
# List processed Parquet files
ls -lh data/processed/

# Or from inside Airflow container
docker compose exec airflow-webserver ls -la /opt/airflow/data/raw
docker compose exec airflow-webserver ls -la /opt/airflow/data/processed
```

**Check database:**
```bash
# Connect to database
docker compose exec -it postgres psql -U airflow -d jobs_db

# Then run SQL queries:
```

```sql
-- Count total jobs
SELECT COUNT(*) FROM jobs_data.jobs;

-- See recent jobs
SELECT title, company, location, contract_type
FROM jobs_data.jobs
ORDER BY created_at DESC
LIMIT 10;

-- Jobs by source
SELECT source, COUNT(*)
FROM jobs_data.jobs
GROUP BY source;

-- Jobs by location
SELECT location, COUNT(*)
FROM jobs_data.jobs
GROUP BY location
ORDER BY COUNT(*) DESC
LIMIT 10;

-- Exit psql
\q
```

## Expected Results

After a successful run, you should have:

✅ **Raw Data**: 50-250 job postings in JSON format
- Location: `data/raw/indeed_YYYYMMDD_HHMMSS.json`
- Location: `data/raw/hellowork_YYYYMMDD_HHMMSS.json`

✅ **Processed Data**: Cleaned Parquet file
- Location: `data/processed/cleaned_jobs_YYYYMMDD_HHMMSS.parquet`

✅ **Database Records**: Jobs loaded into PostgreSQL
- Table: `jobs_data.jobs`
- Typical count: 40-200 unique jobs (after deduplication)

## Troubleshooting

### No data in database?

1. **Check if DAG ran successfully**
   ```bash
   docker compose exec airflow-webserver airflow dags list
   docker compose exec airflow-webserver airflow dags state french_jobs_pipeline
   ```

2. **Check task logs**
   - Go to Airflow UI → DAG → Graph view
   - Click on failed tasks (red squares)
   - View logs to see error messages

3. **Manually test scraper**
   ```bash
   # Enter Airflow container
   docker compose exec -it airflow-webserver bash

   # Run scraper manually
   cd /opt/airflow
   python scripts/scraper.py

   # Check output
   ls -la data/raw/
   ```

### Scraping takes too long?

The pipeline scrapes 5 pages from each site with rate limiting (2-5 seconds delay between requests). This is intentional to be respectful to the job boards.

**To adjust:**
- Edit `dags/french_jobs_pipeline.py`
- Change `max_pages=5` to `max_pages=2` for faster testing
- Change `delay_min=2, delay_max=5` for different rate limiting

### Database connection errors?

```bash
# Check PostgreSQL is running
docker compose exec postgres pg_isready -U airflow

# Check database exists
docker compose exec postgres psql -U airflow -d jobs_db -c "SELECT version();"

# Restart if needed
docker compose restart postgres airflow-scheduler airflow-webserver
```

### Spark errors?

```bash
# Check Spark is running
docker compose logs spark-master
docker compose logs spark-worker

# Check Spark UI
# Open http://localhost:8081 in browser

# Restart Spark
docker compose restart spark-master spark-worker
```

## Customizing the Scraper

### Change search terms

Edit `dags/french_jobs_pipeline.py`:

```python
# Line 81-82 and 116-117
scraper = IndeedScraper(
    search_query="python developer",  # Change this
    location="Paris",  # Change this
    delay_min=2,
    delay_max=5
)
```

### Change schedule

Edit `dags/french_jobs_pipeline.py`:

```python
# Line 36
schedule_interval='0 6 * * *',  # Daily at 6 AM

# Change to:
schedule_interval='0 */6 * * *',  # Every 6 hours
schedule_interval='0 0 * * 0',  # Weekly on Sunday
schedule_interval=None,  # Manual trigger only
```

After making changes:
```bash
docker compose restart airflow-scheduler airflow-webserver
```

## Sample Queries

Once you have data, try these analytics queries:

```sql
-- Average salary by location
SELECT
    location,
    COUNT(*) as job_count,
    AVG((salary_min + salary_max) / 2) as avg_salary
FROM jobs_data.jobs
WHERE salary_min IS NOT NULL
GROUP BY location
ORDER BY job_count DESC;

-- Top hiring companies
SELECT
    company,
    COUNT(*) as open_positions
FROM jobs_data.jobs
WHERE created_at >= CURRENT_DATE - INTERVAL '30 days'
GROUP BY company
ORDER BY open_positions DESC
LIMIT 20;

-- Contract type distribution
SELECT
    contract_type,
    COUNT(*) as count,
    ROUND(100.0 * COUNT(*) / SUM(COUNT(*)) OVER (), 2) as percentage
FROM jobs_data.jobs
GROUP BY contract_type
ORDER BY count DESC;

-- Remote vs On-site
SELECT
    remote_type,
    COUNT(*) as count
FROM jobs_data.jobs
GROUP BY remote_type;

-- Daily scraping stats
SELECT * FROM jobs_data.daily_job_stats
ORDER BY stat_date DESC
LIMIT 7;
```

## Next Steps

1. **Schedule regular runs**: Keep the DAG enabled to run daily
2. **Add more sources**: Create scrapers for LinkedIn, Glassdoor, etc.
3. **Build dashboards**: Connect Superset, Metabase, or Tableau
4. **Export data**: Use the Parquet files for analysis in Python/R
5. **API endpoint**: Build a REST API to serve the data

## Getting Help

- Check logs: `docker compose logs -f`
- View Airflow logs: Go to UI → Browse → Task Instance Logs
- Database shell: `docker compose exec -it postgres psql -U airflow -d jobs_db`
- Airflow shell: `docker compose exec -it airflow-webserver bash`

Happy scraping! 🚀
