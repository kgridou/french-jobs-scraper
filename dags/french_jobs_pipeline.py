"""
French Jobs Pipeline DAG
Main orchestration for scraping, processing, and loading job data
"""

from datetime import datetime, timedelta
from pathlib import Path
import json
import logging

from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.operators.bash import BashOperator
from airflow.providers.postgres.operators.postgres import PostgresOperator
from airflow.providers.postgres.hooks.postgres import PostgresHook
from airflow.providers.apache.spark.operators.spark_submit import SparkSubmitOperator
from airflow.utils.task_group import TaskGroup


# Default arguments
default_args = {
    'owner': 'data_team',
    'depends_on_past': False,
    'email_on_failure': False,
    'email_on_retry': False,
    'retries': 2,
    'retry_delay': timedelta(minutes=5),
    'execution_timeout': timedelta(hours=2),
}

# DAG definition
dag = DAG(
    'french_jobs_pipeline',
    default_args=default_args,
    description='Scrape, process, and load French job postings',
    schedule_interval='0 6 * * *',  # Daily at 6 AM Paris time
    start_date=datetime(2024, 1, 1),
    catchup=False,
    tags=['jobs', 'scraping', 'etl', 'france'],
)


# Helper functions
def log_scraping_run(source, status, jobs_count=0, **kwargs):
    """Log scraping run to database"""
    pg_hook = PostgresHook(postgres_conn_id='postgres_default')
    
    sql = """
    INSERT INTO jobs_data.scraping_runs 
    (source, started_at, completed_at, status, jobs_scraped, jobs_new)
    VALUES (%s, %s, %s, %s, %s, %s)
    """
    
    pg_hook.run(
        sql,
        parameters=(
            source,
            kwargs['ti'].xcom_pull(task_ids=f'scrape_{source}', key='start_time'),
            datetime.now(),
            status,
            jobs_count,
            jobs_count
        )
    )


def scrape_indeed(**kwargs):
    """Scrape Indeed.fr"""
    import sys
    sys.path.insert(0, '/opt/airflow')
    
    from scrapers.indeed_scraper import IndeedScraper
    
    # Record start time
    start_time = datetime.now()
    kwargs['ti'].xcom_push(key='start_time', value=start_time.isoformat())
    
    logging.info("Starting Indeed.fr scraping")
    
    scraper = IndeedScraper(
        search_query="data engineer",
        location="France",
        delay_min=2,
        delay_max=5
    )
    
    output_path = Path('/opt/airflow/data/raw')
    jobs = scraper.scrape_all(max_pages=5, output_path=output_path)
    
    stats = scraper.get_stats()
    scraper.close()
    
    logging.info(f"Indeed scraping completed: {stats}")
    
    # Push results to XCom
    kwargs['ti'].xcom_push(key='jobs_count', value=len(jobs))
    kwargs['ti'].xcom_push(key='stats', value=stats)
    
    return len(jobs)


def scrape_hellowork(**kwargs):
    """Scrape HelloWork.com"""
    import sys
    sys.path.insert(0, '/opt/airflow')
    
    from scrapers.hellowork_scraper import HelloWorkScraper
    
    # Record start time
    start_time = datetime.now()
    kwargs['ti'].xcom_push(key='start_time', value=start_time.isoformat())
    
    logging.info("Starting HelloWork scraping")
    
    scraper = HelloWorkScraper(
        search_query="data engineer",
        delay_min=2,
        delay_max=5
    )
    
    output_path = Path('/opt/airflow/data/raw')
    jobs = scraper.scrape_all(max_pages=5, output_path=output_path)
    
    stats = scraper.get_stats()
    scraper.close()
    
    logging.info(f"HelloWork scraping completed: {stats}")
    
    # Push results to XCom
    kwargs['ti'].xcom_push(key='jobs_count', value=len(jobs))
    kwargs['ti'].xcom_push(key='stats', value=stats)
    
    return len(jobs)


def validate_raw_data(**kwargs):
    """Validate scraped data quality"""
    import pandas as pd
    
    raw_path = Path('/opt/airflow/data/raw')
    issues = []
    
    # Get latest files
    json_files = sorted(raw_path.glob('*.json'), key=lambda x: x.stat().st_mtime, reverse=True)[:10]
    
    total_jobs = 0
    for file_path in json_files:
        with open(file_path, 'r', encoding='utf-8') as f:
            jobs = json.load(f)
            total_jobs += len(jobs)
            
            # Basic validation
            for i, job in enumerate(jobs):
                if not job.get('title'):
                    issues.append(f"Missing title in {file_path.name}:{i}")
                if not job.get('company'):
                    issues.append(f"Missing company in {file_path.name}:{i}")
                if not job.get('url'):
                    issues.append(f"Missing URL in {file_path.name}:{i}")
    
    logging.info(f"Validated {total_jobs} jobs from {len(json_files)} files")
    
    if issues:
        logging.warning(f"Found {len(issues)} validation issues")
        for issue in issues[:10]:  # Log first 10
            logging.warning(issue)
    
    if len(issues) > total_jobs * 0.1:  # More than 10% have issues
        raise ValueError(f"Too many validation issues: {len(issues)}/{total_jobs}")
    
    kwargs['ti'].xcom_push(key='total_jobs', value=total_jobs)
    kwargs['ti'].xcom_push(key='issues_count', value=len(issues))
    
    return total_jobs


def clean_with_pandas(**kwargs):
    """Clean data using Pandas"""
    import pandas as pd
    import numpy as np
    
    logging.info("Starting Pandas cleaning")
    
    raw_path = Path('/opt/airflow/data/raw')
    processed_path = Path('/opt/airflow/data/processed')
    processed_path.mkdir(parents=True, exist_ok=True)
    
    # Load all recent JSON files
    json_files = sorted(raw_path.glob('*.json'), key=lambda x: x.stat().st_mtime, reverse=True)[:10]
    
    all_jobs = []
    for file_path in json_files:
        with open(file_path, 'r', encoding='utf-8') as f:
            jobs = json.load(f)
            all_jobs.extend(jobs)
    
    df = pd.DataFrame(all_jobs)
    logging.info(f"Loaded {len(df)} jobs for cleaning")
    
    # Remove duplicates based on URL
    df = df.drop_duplicates(subset=['url'], keep='first')
    logging.info(f"After deduplication: {len(df)} jobs")
    
    # Clean text fields
    text_columns = ['title', 'company', 'location', 'description']
    for col in text_columns:
        if col in df.columns:
            df[col] = df[col].str.strip()
            df[col] = df[col].replace('', np.nan)
    
    # Standardize contract types
    contract_mapping = {
        'CDI': 'CDI',
        'CDD': 'CDD',
        'Stage': 'Internship',
        'Alternance': 'Apprenticeship',
        'Interim': 'Temporary',
        'Freelance': 'Freelance',
        'Full-time': 'Full-time',
        'Part-time': 'Part-time'
    }
    if 'contract_type' in df.columns:
        df['contract_type'] = df['contract_type'].map(contract_mapping).fillna('Other')
    
    # Standardize remote types
    if 'remote_type' in df.columns:
        df['remote_type'] = df['remote_type'].fillna('On-site')
    
    # Convert dates
    date_columns = ['posted_date', 'scraped_at']
    for col in date_columns:
        if col in df.columns:
            df[col] = pd.to_datetime(df[col], errors='coerce')
    
    # Save cleaned data
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    output_file = processed_path / f'cleaned_jobs_{timestamp}.parquet'
    df.to_parquet(output_file, index=False)
    
    logging.info(f"Cleaned data saved to {output_file}")
    logging.info(f"Final dataset: {len(df)} jobs")
    
    kwargs['ti'].xcom_push(key='cleaned_file', value=str(output_file))
    kwargs['ti'].xcom_push(key='cleaned_count', value=len(df))
    
    return str(output_file)


def load_to_postgres(**kwargs):
    """Load processed data to PostgreSQL"""
    import pandas as pd
    from sqlalchemy import create_engine
    
    logging.info("Loading data to PostgreSQL")
    
    # Get cleaned file path
    cleaned_file = kwargs['ti'].xcom_pull(task_ids='clean_with_pandas', key='cleaned_file')
    
    # Read cleaned data
    df = pd.read_parquet(cleaned_file)
    logging.info(f"Loading {len(df)} jobs to database")
    
    # Create database connection
    pg_hook = PostgresHook(postgres_conn_id='postgres_default')
    engine = pg_hook.get_sqlalchemy_engine()
    
    # Prepare data for insertion
    df_to_load = df.copy()
    
    # Convert lists to JSON strings for JSONB columns
    if 'required_skills' in df_to_load.columns:
        df_to_load['required_skills'] = df_to_load['required_skills'].apply(
            lambda x: json.dumps(x) if isinstance(x, list) else x
        )
    
    # Load to database (append mode to avoid overwriting)
    df_to_load.to_sql(
        'jobs',
        engine,
        schema='jobs_data',
        if_exists='append',
        index=False,
        method='multi',
        chunksize=1000
    )
    
    logging.info(f"Successfully loaded {len(df)} jobs to database")
    
    return len(df)


def generate_analytics(**kwargs):
    """Generate analytics tables"""
    pg_hook = PostgresHook(postgres_conn_id='postgres_default')
    
    # Daily stats
    daily_stats_sql = """
    INSERT INTO jobs_data.daily_job_stats (
        stat_date, total_jobs, new_jobs, active_jobs, avg_salary
    )
    SELECT 
        CURRENT_DATE,
        COUNT(*) as total_jobs,
        COUNT(CASE WHEN DATE(created_at) = CURRENT_DATE THEN 1 END) as new_jobs,
        COUNT(CASE WHEN is_active = TRUE THEN 1 END) as active_jobs,
        AVG((salary_min + salary_max) / 2) as avg_salary
    FROM jobs_data.jobs
    ON CONFLICT (stat_date) DO UPDATE SET
        total_jobs = EXCLUDED.total_jobs,
        new_jobs = EXCLUDED.new_jobs,
        active_jobs = EXCLUDED.active_jobs,
        avg_salary = EXCLUDED.avg_salary
    """
    
    pg_hook.run(daily_stats_sql)
    logging.info("Generated daily statistics")
    
    return "Analytics generated successfully"


# Task definitions

with TaskGroup("scraping", dag=dag) as scraping_group:
    scrape_indeed_task = PythonOperator(
        task_id='scrape_indeed',
        python_callable=scrape_indeed,
        dag=dag,
    )
    
    scrape_hellowork_task = PythonOperator(
        task_id='scrape_hellowork',
        python_callable=scrape_hellowork,
        dag=dag,
    )

validate_data_task = PythonOperator(
    task_id='validate_raw_data',
    python_callable=validate_raw_data,
    dag=dag,
)

clean_data_task = PythonOperator(
    task_id='clean_with_pandas',
    python_callable=clean_with_pandas,
    dag=dag,
)

process_spark_task = SparkSubmitOperator(
    task_id='process_with_spark',
    application='/opt/airflow/scripts/enrich_jobs.py',
    conn_id='spark_default',
    conf={
        'spark.driver.memory': '2g',
        'spark.executor.memory': '2g'
    },
    deploy_mode='client',
    master='spark://spark-master:7077',
    dag=dag,
)

load_data_task = PythonOperator(
    task_id='load_to_postgres',
    python_callable=load_to_postgres,
    dag=dag,
)

generate_analytics_task = PythonOperator(
    task_id='generate_analytics',
    python_callable=generate_analytics,
    dag=dag,
)

data_quality_check_task = PostgresOperator(
    task_id='data_quality_check',
    postgres_conn_id='postgres_default',
    sql="""
    SELECT 
        COUNT(*) as total_jobs,
        COUNT(CASE WHEN title IS NULL THEN 1 END) as missing_titles,
        COUNT(CASE WHEN company IS NULL THEN 1 END) as missing_companies
    FROM jobs_data.jobs
    WHERE DATE(created_at) = CURRENT_DATE;
    """,
    dag=dag,
)

# Task dependencies
scraping_group >> validate_data_task >> clean_data_task >> process_spark_task
process_spark_task >> load_data_task >> generate_analytics_task >> data_quality_check_task
