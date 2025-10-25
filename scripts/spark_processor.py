"""
PySpark Data Processor for French Job Postings
Performs large-scale analytics and aggregations using PySpark
"""

from pyspark.sql import SparkSession
from pyspark.sql import functions as F
from pyspark.sql.types import *
from pyspark.sql.window import Window
import logging
import os
from datetime import datetime, timedelta

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class SparkJobAnalyzer:
    """Analyze job data using PySpark for large-scale processing"""
    
    def __init__(self):
        """Initialize Spark session"""
        self.spark = SparkSession.builder \
            .appName("FrenchJobAnalytics") \
            .config("spark.jars", "/opt/spark/jars/postgresql-42.7.0.jar") \
            .config("spark.driver.memory", "2g") \
            .config("spark.executor.memory", "2g") \
            .getOrCreate()
        
        self.jdbc_url = f"jdbc:postgresql://{os.getenv('JOBS_DB_HOST', 'postgres')}:5432/{os.getenv('JOBS_DB_NAME', 'jobs_db')}"
        self.connection_properties = {
            "user": os.getenv('JOBS_DB_USER', 'airflow'),
            "password": os.getenv('JOBS_DB_PASSWORD', 'airflow'),
            "driver": "org.postgresql.Driver"
        }
        
        logger.info("Spark session initialized")
    
    def load_data(self) -> tuple:
        """Load cleaned jobs and related data from PostgreSQL"""
        logger.info("Loading data from PostgreSQL")
        
        # Load cleaned jobs
        jobs_df = self.spark.read.jdbc(
            url=self.jdbc_url,
            table="cleaned_jobs",
            properties=self.connection_properties
        )
        
        # Load companies
        companies_df = self.spark.read.jdbc(
            url=self.jdbc_url,
            table="companies",
            properties=self.connection_properties
        )
        
        # Load locations
        locations_df = self.spark.read.jdbc(
            url=self.jdbc_url,
            table="locations",
            properties=self.connection_properties
        )
        
        logger.info(f"Loaded {jobs_df.count()} jobs, {companies_df.count()} companies, {locations_df.count()} locations")
        
        return jobs_df, companies_df, locations_df
    
    def enrich_jobs_data(self, jobs_df, companies_df, locations_df):
        """Join jobs with dimension tables"""
        logger.info("Enriching jobs data with dimensions")
        
        # Join with companies
        enriched_df = jobs_df.join(
            companies_df.select("id", F.col("name").alias("company_name")),
            jobs_df.company_id == companies_df.id,
            "left"
        )
        
        # Join with locations
        enriched_df = enriched_df.join(
            locations_df.select("id", "city", "region"),
            enriched_df.location_id == locations_df.id,
            "left"
        )
        
        return enriched_df
    
    def calculate_job_analytics(self, enriched_df):
        """Calculate aggregated job analytics"""
        logger.info("Calculating job analytics")
        
        # Get current date for filtering
        current_date = datetime.now().date()
        thirty_days_ago = current_date - timedelta(days=30)
        
        # Filter recent jobs
        recent_jobs = enriched_df.filter(
            F.col("posting_date") >= F.lit(thirty_days_ago)
        )
        
        # Calculate analytics by category and location
        analytics_df = recent_jobs.groupBy("category", "city") \
            .agg(
                F.count("*").alias("job_count"),
                F.avg("salary_avg").alias("avg_salary"),
                F.min("salary_min").alias("min_salary"),
                F.max("salary_max").alias("max_salary"),
                F.expr("percentile_approx(salary_avg, 0.5)").alias("median_salary"),
                F.sum(F.when(F.col("remote_type").isin(["Full Remote", "Hybrid"]), 1).otherwise(0)).alias("remote_count")
            ) \
            .withColumn("remote_percentage", 
                       (F.col("remote_count") / F.col("job_count") * 100).cast("decimal(5,2)")
            ) \
            .withColumn("analysis_date", F.lit(current_date))
        
        # Get top skills by category
        skills_df = recent_jobs.select("category", F.explode("skills").alias("skill")) \
            .groupBy("category", "skill") \
            .count() \
            .withColumn("rank", F.row_number().over(
                Window.partitionBy("category").orderBy(F.desc("count"))
            )) \
            .filter(F.col("rank") <= 10) \
            .groupBy("category") \
            .agg(F.collect_list("skill").alias("top_skills"))
        
        # Join analytics with top skills
        analytics_df = analytics_df.join(
            skills_df,
            "category",
            "left"
        )
        
        logger.info(f"Generated {analytics_df.count()} analytics records")
        
        return analytics_df
    
    def calculate_salary_trends(self, enriched_df):
        """Calculate salary trends over time"""
        logger.info("Calculating salary trends")
        
        # Define time periods (monthly for the last 6 months)
        current_date = datetime.now().date()
        
        # Add month column
        trends_df = enriched_df.filter(F.col("salary_avg").isNotNull()) \
            .withColumn("month", F.trunc(F.col("posting_date"), "month")) \
            .filter(F.col("month") >= F.add_months(F.lit(current_date), -6))
        
        # Calculate trends by category, location, and experience level
        salary_trends = trends_df.groupBy("month", "category", "city", "experience_level") \
            .agg(
                F.avg("salary_avg").alias("avg_salary"),
                F.count("*").alias("sample_size")
            ) \
            .filter(F.col("sample_size") >= 3)  # Minimum sample size
        
        # Calculate trend direction
        window_spec = Window.partitionBy("category", "city", "experience_level") \
            .orderBy("month")
        
        salary_trends = salary_trends.withColumn(
            "prev_salary",
            F.lag("avg_salary").over(window_spec)
        ).withColumn(
            "trend_direction",
            F.when(F.col("avg_salary") > F.col("prev_salary") * 1.05, "up")
            .when(F.col("avg_salary") < F.col("prev_salary") * 0.95, "down")
            .otherwise("stable")
        ).withColumn(
            "period_start", F.col("month")
        ).withColumn(
            "period_end", F.last_day(F.col("month"))
        )
        
        logger.info(f"Generated {salary_trends.count()} salary trend records")
        
        return salary_trends
    
    def calculate_market_insights(self, enriched_df):
        """Calculate market insights and statistics"""
        logger.info("Calculating market insights")
        
        # Most in-demand skills
        top_skills = enriched_df.select(F.explode("skills").alias("skill")) \
            .groupBy("skill") \
            .count() \
            .orderBy(F.desc("count")) \
            .limit(20)
        
        logger.info("Top 20 skills:")
        top_skills.show()
        
        # Top hiring companies
        top_companies = enriched_df.groupBy("company_name") \
            .count() \
            .orderBy(F.desc("count")) \
            .limit(20)
        
        logger.info("Top 20 hiring companies:")
        top_companies.show()
        
        # Jobs by category
        category_dist = enriched_df.groupBy("category") \
            .count() \
            .orderBy(F.desc("count"))
        
        logger.info("Job distribution by category:")
        category_dist.show()
        
        # Remote work statistics
        remote_stats = enriched_df.groupBy("remote_type") \
            .count() \
            .withColumn("percentage", 
                       (F.col("count") / enriched_df.count() * 100).cast("decimal(5,2)"))
        
        logger.info("Remote work distribution:")
        remote_stats.show()
        
        return {
            "top_skills": top_skills,
            "top_companies": top_companies,
            "category_distribution": category_dist,
            "remote_stats": remote_stats
        }
    
    def save_analytics_to_db(self, analytics_df, table_name: str):
        """Save analytics results to PostgreSQL"""
        logger.info(f"Saving analytics to {table_name}")
        
        try:
            # Convert location to string for compatibility
            if "city" in analytics_df.columns:
                analytics_df = analytics_df.withColumnRenamed("city", "location")
            
            # Write to database
            analytics_df.write.jdbc(
                url=self.jdbc_url,
                table=table_name,
                mode="append",
                properties=self.connection_properties
            )
            
            logger.info(f"Successfully saved analytics to {table_name}")
            
        except Exception as e:
            logger.error(f"Error saving to database: {str(e)}")
            raise
    
    def run_analytics_pipeline(self):
        """Run the complete analytics pipeline"""
        logger.info("Starting Spark analytics pipeline")
        
        try:
            # Load data
            jobs_df, companies_df, locations_df = self.load_data()
            
            # Enrich data
            enriched_df = self.enrich_jobs_data(jobs_df, companies_df, locations_df)
            
            # Cache enriched data for multiple operations
            enriched_df.cache()
            
            # Calculate job analytics
            analytics_df = self.calculate_job_analytics(enriched_df)
            
            # Save job analytics
            self.save_analytics_to_db(analytics_df, "job_analytics")
            
            # Calculate salary trends
            salary_trends_df = self.calculate_salary_trends(enriched_df)
            
            # Prepare salary trends for saving
            salary_trends_final = salary_trends_df.select(
                "period_start",
                "period_end",
                F.col("category").alias("category"),
                F.col("city").alias("location"),
                "experience_level",
                F.col("avg_salary").cast("decimal(10,2)").alias("avg_salary"),
                "sample_size",
                "trend_direction"
            )
            
            # Save salary trends
            self.save_analytics_to_db(salary_trends_final, "salary_trends")
            
            # Calculate and display market insights
            insights = self.calculate_market_insights(enriched_df)
            
            # Unpersist cached data
            enriched_df.unpersist()
            
            logger.info("Spark analytics pipeline completed successfully")
            
        except Exception as e:
            logger.error(f"Error in analytics pipeline: {str(e)}")
            raise
        finally:
            self.spark.stop()


def main():
    """Main execution function"""
    logger.info("Starting PySpark analytics job")
    
    analyzer = SparkJobAnalyzer()
    analyzer.run_analytics_pipeline()
    
    logger.info("PySpark analytics completed")


if __name__ == "__main__":
    main()
