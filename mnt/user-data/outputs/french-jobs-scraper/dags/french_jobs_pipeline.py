"""
Airflow DAG for French Job Postings ETL Pipeline
Orchestrates web scraping, data processing, and analytics
"""

from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.operators.bash import BashOperator
from airflow.providers.postgres.operators.postgres import PostgresOperator
from airflow.providers.postgres.hooks.postgres import PostgresHook
from airflow.utils.dates import days_ago
from datetime import datetime, timedelta
import sys
import os

# Add scripts directory to path
sys.path.insert(0, '/opt/airflow/scripts')

# Import processing modules
from scraper import FrenchJobScraper
from pandas_processor import JobDataProcessor

# Default DAG arguments
default_args = {
    'owner': 'airflow',
    'depends_on_past': False,
    'start_date': days_ago(1),
    'email_on_failure': False,
    'email_on_retry': False,
    'retries': 1,
    'retry_delay': timedelta(minutes=5),
}

# Create DAG
dag = DAG(
    'french_jobs_pipeline',
    default_args=default_args,
    description='ETL pipeline for French job postings',
    schedule_interval='0 2 * * *',  # Daily at 2 AM
    catchup=False,
    tags=['jobs', 'scraping', 'etl', 'french'],
)


def scrape_jobs(**context):
    """Task to scrape job postings"""
    import logging
    logger = logging.getLogger(__name__)
    
    logger.info("Starting job scraping task")
    
    scraper = FrenchJobScraper()
    df = scraper.scrape_all_sources()
    
    if not df.empty:
        scraper.save_to_database(df)
        logger.info(f"Successfully scraped and saved {len(df)} jobs")
        
        # Push metrics to XCom
        context['task_instance'].xcom_push(key='jobs_scraped', value=len(df))
    else:
        logger.warning("No jobs were scraped")
        context['task_instance'].xcom_push(key='jobs_scraped', value=0)


def process_with_pandas(**context):
    """Task to process jobs with Pandas"""
    import logging
    logger = logging.getLogger(__name__)
    
    logger.info("Starting Pandas processing task")
    
    processor = JobDataProcessor()
    
    # Load raw jobs from the last day
    raw_df = processor.load_raw_jobs(days_back=1)
    
    if not raw_df.empty:
        # Process jobs
        processed_df = processor.process_jobs(raw_df)
        
        # Save to database
        processor.save_to_database(processed_df)
        
        logger.info(f"Successfully processed {len(processed_df)} jobs")
        
        # Push metrics to XCom
        context['task_instance'].xcom_push(key='jobs_processed', value=len(processed_df))
    else:
        logger.warning("No raw jobs to process")
        context['task_instance'].xcom_push(key='jobs_processed', value=0)


def check_data_quality(**context):
    """Task to check data quality"""
    import logging
    logger = logging.getLogger(__name__)
    
    logger.info("Checking data quality")
    
    # Get PostgreSQL connection
    hook = PostgresHook(postgres_conn_id='postgres_default')
    conn = hook.get_conn()
    cursor = conn.cursor()
    
    # Check for duplicates
    cursor.execute("""
        SELECT COUNT(*) FROM (
            SELECT job_id, COUNT(*) 
            FROM cleaned_jobs 
            GROUP BY job_id 
            HAVING COUNT(*) > 1
        ) duplicates
    """)
    duplicate_count = cursor.fetchone()[0]
    
    # Check for null values in critical fields
    cursor.execute("""
        SELECT COUNT(*) FROM cleaned_jobs
        WHERE title IS NULL OR company_id IS NULL
    """)
    null_count = cursor.fetchone()[0]
    
    # Check recent data
    cursor.execute("""
        SELECT COUNT(*) FROM cleaned_jobs
        WHERE processed_at >= CURRENT_TIMESTAMP - INTERVAL '1 day'
    """)
    recent_count = cursor.fetchone()[0]
    
    cursor.close()
    conn.close()
    
    logger.info(f"Data quality check results:")
    logger.info(f"  - Duplicates: {duplicate_count}")
    logger.info(f"  - Null values: {null_count}")
    logger.info(f"  - Recent records: {recent_count}")
    
    # Push metrics to XCom
    context['task_instance'].xcom_push(key='duplicates', value=duplicate_count)
    context['task_instance'].xcom_push(key='null_values', value=null_count)
    context['task_instance'].xcom_push(key='recent_records', value=recent_count)
    
    # Raise error if data quality issues found
    if duplicate_count > 0:
        logger.warning(f"Found {duplicate_count} duplicate records")
    if null_count > 10:
        raise ValueError(f"Found {null_count} records with null values in critical fields")


def generate_summary_report(**context):
    """Task to generate summary report"""
    import logging
    logger = logging.getLogger(__name__)
    
    logger.info("Generating pipeline summary report")
    
    # Get metrics from XCom
    ti = context['task_instance']
    jobs_scraped = ti.xcom_pull(task_ids='scrape_jobs_task', key='jobs_scraped') or 0
    jobs_processed = ti.xcom_pull(task_ids='process_with_pandas_task', key='jobs_processed') or 0
    recent_records = ti.xcom_pull(task_ids='check_data_quality_task', key='recent_records') or 0
    
    # Get statistics from database
    hook = PostgresHook(postgres_conn_id='postgres_default')
    conn = hook.get_conn()
    cursor = conn.cursor()
    
    # Total jobs in database
    cursor.execute("SELECT COUNT(*) FROM cleaned_jobs")
    total_jobs = cursor.fetchone()[0]
    
    # Top categories
    cursor.execute("""
        SELECT category, COUNT(*) as count
        FROM cleaned_jobs
        WHERE processed_at >= CURRENT_TIMESTAMP - INTERVAL '30 days'
        GROUP BY category
        ORDER BY count DESC
        LIMIT 5
    """)
    top_categories = cursor.fetchall()
    
    # Top locations
    cursor.execute("""
        SELECT l.city, COUNT(*) as count
        FROM cleaned_jobs cj
        JOIN locations l ON cj.location_id = l.id
        WHERE cj.processed_at >= CURRENT_TIMESTAMP - INTERVAL '30 days'
        GROUP BY l.city
        ORDER BY count DESC
        LIMIT 5
    """)
    top_locations = cursor.fetchall()
    
    cursor.close()
    conn.close()
    
    # Generate report
    report = f"""
    ========================================
    French Jobs Pipeline - Summary Report
    ========================================
    Run Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
    
    Pipeline Metrics:
    -----------------
    - Jobs Scraped: {jobs_scraped}
    - Jobs Processed: {jobs_processed}
    - Recent Records (24h): {recent_records}
    - Total Jobs in DB: {total_jobs}
    
    Top Job Categories (Last 30 Days):
    ----------------------------------
    """
    
    for category, count in top_categories:
        report += f"    {category}: {count}\n"
    
    report += """
    Top Locations (Last 30 Days):
    -----------------------------
    """
    
    for city, count in top_locations:
        report += f"    {city}: {count}\n"
    
    report += """
    ========================================
    Pipeline Status: SUCCESS
    ========================================
    """
    
    logger.info(report)
    
    # Save report to file
    report_path = f"/opt/airflow/logs/pipeline_report_{datetime.now().strftime('%Y%m%d')}.txt"
    with open(report_path, 'w') as f:
        f.write(report)
    
    logger.info(f"Report saved to {report_path}")


# Define tasks
start_task = BashOperator(
    task_id='start_pipeline',
    bash_command='echo "Starting French Jobs ETL Pipeline"',
    dag=dag,
)

scrape_jobs_task = PythonOperator(
    task_id='scrape_jobs_task',
    python_callable=scrape_jobs,
    provide_context=True,
    dag=dag,
)

process_with_pandas_task = PythonOperator(
    task_id='process_with_pandas_task',
    python_callable=process_with_pandas,
    provide_context=True,
    dag=dag,
)

# Spark processing task using BashOperator
# Note: In production, you might use SparkSubmitOperator
process_with_spark_task = BashOperator(
    task_id='process_with_spark_task',
    bash_command="""
    spark-submit \
        --master spark://spark-master:7077 \
        --deploy-mode client \
        --driver-memory 1g \
        --executor-memory 2g \
        --jars /opt/spark/jars/postgresql-42.7.0.jar \
        /opt/airflow/scripts/spark_processor.py
    """,
    dag=dag,
)

check_data_quality_task = PythonOperator(
    task_id='check_data_quality_task',
    python_callable=check_data_quality,
    provide_context=True,
    dag=dag,
)

# Clean old data (retention policy)
cleanup_task = PostgresOperator(
    task_id='cleanup_old_data',
    postgres_conn_id='postgres_default',
    sql="""
        DELETE FROM raw_jobs
        WHERE scraped_at < CURRENT_TIMESTAMP - INTERVAL '365 days';
        
        DELETE FROM salary_trends
        WHERE created_at < CURRENT_TIMESTAMP - INTERVAL '180 days';
    """,
    dag=dag,
)

generate_report_task = PythonOperator(
    task_id='generate_summary_report',
    python_callable=generate_summary_report,
    provide_context=True,
    dag=dag,
)

end_task = BashOperator(
    task_id='end_pipeline',
    bash_command='echo "French Jobs ETL Pipeline completed successfully"',
    dag=dag,
)

# Define task dependencies
start_task >> scrape_jobs_task >> process_with_pandas_task >> process_with_spark_task
process_with_spark_task >> check_data_quality_task >> cleanup_task >> generate_report_task >> end_task
