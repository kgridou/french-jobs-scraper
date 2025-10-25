"""
PySpark Job: Enrich Jobs Data
Distributed processing and enrichment of job postings
"""

import sys
import re
import logging
from pathlib import Path
from datetime import datetime

from pyspark.sql import SparkSession
from pyspark.sql.functions import (
    col, udf, explode, array, lit, lower, trim,
    regexp_extract, when, size, collect_list, avg
)
from pyspark.sql.types import (
    StringType, ArrayType, IntegerType, StructType, 
    StructField, FloatType
)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class JobEnricher:
    """PySpark-based job data enrichment"""
    
    def __init__(self, spark):
        self.spark = spark
        
    def load_data(self, input_path):
        """Load cleaned data"""
        logger.info(f"Loading data from {input_path}")
        
        # Find most recent parquet file
        data_path = Path(input_path)
        parquet_files = sorted(data_path.glob('cleaned_jobs_*.parquet'), 
                              key=lambda x: x.stat().st_mtime, 
                              reverse=True)
        
        if not parquet_files:
            raise FileNotFoundError(f"No parquet files found in {input_path}")
        
        latest_file = str(parquet_files[0])
        logger.info(f"Loading: {latest_file}")
        
        df = self.spark.read.parquet(latest_file)
        logger.info(f"Loaded {df.count()} records")
        
        return df
    
    def extract_skills(self, df):
        """Extract and categorize skills using NLP"""
        
        # Define comprehensive skill dictionary
        skills_dict = {
            'Programming': [
                'Python', 'Java', 'JavaScript', 'TypeScript', 'C++', 'C#', 
                'Ruby', 'Go', 'Rust', 'PHP', 'Scala', 'R', 'Swift', 'Kotlin'
            ],
            'Database': [
                'SQL', 'PostgreSQL', 'MySQL', 'MongoDB', 'Redis', 'Cassandra',
                'Oracle', 'MS SQL', 'DynamoDB', 'Elasticsearch', 'Neo4j'
            ],
            'Cloud': [
                'AWS', 'Azure', 'GCP', 'Google Cloud', 'Cloud Computing',
                'S3', 'EC2', 'Lambda', 'Cloud Functions', 'Heroku'
            ],
            'DevOps': [
                'Docker', 'Kubernetes', 'Jenkins', 'GitLab CI', 'CI/CD',
                'Terraform', 'Ansible', 'Chef', 'Puppet', 'CircleCI'
            ],
            'Big Data': [
                'Spark', 'Hadoop', 'Kafka', 'Airflow', 'Databricks',
                'Hive', 'Presto', 'Flink', 'Storm', 'Snowflake'
            ],
            'Web': [
                'React', 'Vue', 'Angular', 'Node.js', 'Django', 'Flask',
                'Spring', 'Express', 'FastAPI', 'Laravel', 'Rails'
            ],
            'ML/AI': [
                'Machine Learning', 'Deep Learning', 'TensorFlow', 'PyTorch',
                'Scikit-learn', 'Keras', 'NLP', 'Computer Vision', 'MLflow'
            ],
            'Data': [
                'Pandas', 'NumPy', 'Tableau', 'Power BI', 'Looker',
                'Data Analysis', 'Data Engineering', 'ETL', 'Data Warehouse'
            ]
        }
        
        def find_skills(text):
            """Find skills in text"""
            if not text:
                return []
            
            text_lower = text.lower()
            found = []
            
            for category, skills in skills_dict.items():
                for skill in skills:
                    pattern = r'\b' + re.escape(skill.lower()) + r'\b'
                    if re.search(pattern, text_lower):
                        found.append({
                            'skill': skill,
                            'category': category
                        })
            
            return found
        
        # Register UDF
        skill_schema = StructType([
            StructField('skill', StringType(), True),
            StructField('category', StringType(), True)
        ])
        
        find_skills_udf = udf(find_skills, ArrayType(skill_schema))
        
        # Apply skill extraction
        df = df.withColumn(
            'extracted_skills',
            find_skills_udf(col('description'))
        )
        
        logger.info("Extracted skills from job descriptions")
        return df
    
    def classify_experience_level(self, df):
        """Classify experience level from description"""
        
        def determine_experience(title, description):
            """Determine experience level"""
            if not title and not description:
                return 'Not Specified'
            
            text = (title or '').lower() + ' ' + (description or '').lower()
            
            # Keywords for experience levels
            junior_keywords = ['junior', 'débutant', 'entry level', 'graduate', 
                             'stage', 'stagiaire', 'apprenti']
            mid_keywords = ['confirmé', 'expérimenté', '2-5 ans', '3-5 ans']
            senior_keywords = ['senior', 'expert', 'lead', 'principal', 
                             '5+ ans', '10+ ans', 'architecte']
            
            if any(kw in text for kw in senior_keywords):
                return 'Senior'
            elif any(kw in text for kw in junior_keywords):
                return 'Junior'
            elif any(kw in text for kw in mid_keywords):
                return 'Mid-level'
            
            # Check for years of experience
            years_match = re.search(r'(\d+)\s*(?:ans?|years?)', text)
            if years_match:
                years = int(years_match.group(1))
                if years >= 5:
                    return 'Senior'
                elif years >= 2:
                    return 'Mid-level'
                else:
                    return 'Junior'
            
            return 'Not Specified'
        
        exp_udf = udf(determine_experience, StringType())
        
        df = df.withColumn(
            'experience_classification',
            exp_udf(col('title'), col('description'))
        )
        
        logger.info("Classified experience levels")
        return df
    
    def enrich_location(self, df):
        """Enrich location data with regions"""
        
        # Major French cities to regions mapping
        city_to_region = {
            'paris': 'Île-de-France',
            'lyon': 'Auvergne-Rhône-Alpes',
            'marseille': 'Provence-Alpes-Côte d\'Azur',
            'toulouse': 'Occitanie',
            'nantes': 'Pays de la Loire',
            'strasbourg': 'Grand Est',
            'bordeaux': 'Nouvelle-Aquitaine',
            'lille': 'Hauts-de-France',
            'rennes': 'Bretagne',
            'montpellier': 'Occitanie',
            'nice': 'Provence-Alpes-Côte d\'Azur'
        }
        
        def get_region(city):
            """Get region from city"""
            if not city:
                return None
            city_lower = city.lower().strip()
            return city_to_region.get(city_lower)
        
        region_udf = udf(get_region, StringType())
        
        df = df.withColumn(
            'region_enriched',
            when(col('region').isNull(), region_udf(col('city')))
            .otherwise(col('region'))
        )
        
        logger.info("Enriched location data")
        return df
    
    def calculate_salary_score(self, df):
        """Calculate normalized salary score"""
        
        # Calculate average salary per job
        df = df.withColumn(
            'avg_salary',
            when(
                col('salary_min').isNotNull() & col('salary_max').isNotNull(),
                (col('salary_min') + col('salary_max')) / 2
            ).otherwise(col('salary_min'))
        )
        
        # Get overall statistics
        salary_stats = df.select(
            avg('avg_salary').alias('mean_salary')
        ).first()
        
        mean_salary = salary_stats['mean_salary'] or 40000
        
        # Calculate salary score (0-100)
        df = df.withColumn(
            'salary_score',
            when(
                col('avg_salary').isNotNull(),
                ((col('avg_salary') / mean_salary) * 50).cast(IntegerType())
            ).otherwise(lit(50))
        )
        
        logger.info(f"Calculated salary scores (mean: €{mean_salary:,.2f})")
        return df
    
    def add_job_quality_score(self, df):
        """Calculate overall job quality score"""
        
        # Quality factors
        df = df.withColumn(
            'quality_score',
            (
                # Has salary info
                when(col('salary_min').isNotNull(), 20).otherwise(0) +
                # Remote options
                when(col('remote_type').isin(['Remote', 'Hybrid']), 15).otherwise(0) +
                # CDI contract
                when(col('contract_type') == 'CDI', 20).otherwise(10) +
                # Has skills listed
                when(size(col('extracted_skills')) > 0, 15).otherwise(0) +
                # Recent posting
                when(col('posted_date').isNotNull(), 10).otherwise(0) +
                # Description quality (length)
                when(col('description').isNotNull(), 20).otherwise(0)
            )
        )
        
        logger.info("Calculated job quality scores")
        return df
    
    def aggregate_skill_demand(self, df):
        """Aggregate skill demand statistics"""
        
        # Explode skills array
        skills_df = df.select(
            'source',
            'region_enriched',
            'avg_salary',
            explode('extracted_skills').alias('skill_info')
        )
        
        # Extract skill name and category
        skills_df = skills_df.select(
            'source',
            'region_enriched',
            'avg_salary',
            col('skill_info.skill').alias('skill_name'),
            col('skill_info.category').alias('skill_category')
        )
        
        # Aggregate by skill
        skill_stats = skills_df.groupBy('skill_name', 'skill_category').agg(
            col('skill_name').alias('skill'),
            col('skill_category').alias('category'),
            col('skill_name').alias('count'),
            avg('avg_salary').alias('avg_salary_for_skill')
        )
        
        logger.info("Aggregated skill demand statistics")
        return skill_stats
    
    def save_enriched_data(self, df, output_path):
        """Save enriched data"""
        logger.info(f"Saving enriched data to {output_path}")
        
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        output_file = f"{output_path}/enriched_jobs_{timestamp}.parquet"
        
        df.write.mode('overwrite').parquet(output_file)
        logger.info(f"Saved to {output_file}")
        
        return output_file
    
    def run(self, input_path, output_path):
        """Run the complete enrichment pipeline"""
        logger.info("Starting job enrichment pipeline")
        
        # Load data
        df = self.load_data(input_path)
        
        # Apply enrichments
        df = self.extract_skills(df)
        df = self.classify_experience_level(df)
        df = self.enrich_location(df)
        df = self.calculate_salary_score(df)
        df = self.add_job_quality_score(df)
        
        # Show sample
        logger.info("Sample of enriched data:")
        df.select(
            'title', 'company', 'experience_classification', 
            'quality_score', 'salary_score'
        ).show(5, truncate=False)
        
        # Save enriched data
        output_file = self.save_enriched_data(df, output_path)
        
        # Generate skill statistics
        skill_stats = self.aggregate_skill_demand(df)
        skill_output = f"{output_path}/skill_demand_{datetime.now().strftime('%Y%m%d_%H%M%S')}.parquet"
        skill_stats.write.mode('overwrite').parquet(skill_output)
        
        logger.info("Job enrichment pipeline completed successfully")
        
        return output_file


def main():
    """Main execution"""
    
    # Create Spark session
    spark = SparkSession.builder \
        .appName("French Jobs Enrichment") \
        .config("spark.sql.adaptive.enabled", "true") \
        .config("spark.sql.adaptive.coalescePartitions.enabled", "true") \
        .getOrCreate()
    
    logger.info(f"Spark version: {spark.version}")
    
    # Set log level
    spark.sparkContext.setLogLevel("WARN")
    
    # Paths
    input_path = "/opt/data/processed"
    output_path = "/opt/data/analytics"
    
    # Run enrichment
    enricher = JobEnricher(spark)
    enricher.run(input_path, output_path)
    
    # Stop Spark
    spark.stop()
    logger.info("Spark session stopped")


if __name__ == "__main__":
    main()
