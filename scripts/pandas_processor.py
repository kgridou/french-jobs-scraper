"""
Pandas Data Processor for French Job Postings
Cleans and processes raw job data using Pandas
"""

import pandas as pd
import numpy as np
import re
import logging
from datetime import datetime
from typing import Optional, List, Tuple
import psycopg2
from psycopg2.extras import execute_batch
import yaml
import os

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class JobDataProcessor:
    """Process and clean job posting data using Pandas"""
    
    def __init__(self, config_path: str = '/opt/airflow/config/scraper_config.yaml'):
        """Initialize processor with configuration"""
        with open(config_path, 'r', encoding='utf-8') as f:
            self.config = yaml.safe_load(f)
        
        self.db_params = {
            'host': os.getenv('JOBS_DB_HOST', 'postgres'),
            'port': os.getenv('JOBS_DB_PORT', 5432),
            'database': os.getenv('JOBS_DB_NAME', 'jobs_db'),
            'user': os.getenv('JOBS_DB_USER', 'airflow'),
            'password': os.getenv('JOBS_DB_PASSWORD', 'airflow')
        }
    
    def get_db_connection(self):
        """Create database connection"""
        return psycopg2.connect(**self.db_params)
    
    def load_raw_jobs(self, days_back: int = 1) -> pd.DataFrame:
        """Load raw jobs from database"""
        query = """
            SELECT * FROM raw_jobs
            WHERE scraped_at >= CURRENT_TIMESTAMP - INTERVAL '%s days'
            ORDER BY scraped_at DESC
        """
        
        conn = self.get_db_connection()
        try:
            df = pd.read_sql_query(query, conn, params=(days_back,))
            logger.info(f"Loaded {len(df)} raw jobs from database")
            return df
        finally:
            conn.close()
    
    def clean_location(self, location: str) -> Tuple[str, str, str]:
        """
        Clean and standardize location data
        Returns: (city, region, normalized_location)
        """
        if pd.isna(location):
            return None, None, None
        
        location = location.strip()
        
        # Remove postal codes
        location = re.sub(r'\(\d{5}\)', '', location)
        location = re.sub(r'\d{5}', '', location)
        
        # Common French location patterns
        parts = location.split(',')
        city = parts[0].strip() if parts else location
        
        # Map to regions (simplified)
        region_mapping = {
            'paris': 'Île-de-France',
            'lyon': 'Auvergne-Rhône-Alpes',
            'marseille': 'Provence-Alpes-Côte d\'Azur',
            'toulouse': 'Occitanie',
            'nice': 'Provence-Alpes-Côte d\'Azur',
            'nantes': 'Pays de la Loire',
            'bordeaux': 'Nouvelle-Aquitaine',
            'lille': 'Hauts-de-France',
            'strasbourg': 'Grand Est',
            'rennes': 'Bretagne'
        }
        
        city_lower = city.lower()
        region = region_mapping.get(city_lower, 'Unknown')
        
        normalized = f"{city.lower()}-{region.lower()}-france".replace(' ', '-').replace('\'', '')
        
        return city, region, normalized
    
    def parse_salary(self, salary_text: str) -> Tuple[Optional[float], Optional[float], str]:
        """
        Parse salary information from text
        Returns: (min_salary, max_salary, currency)
        """
        if pd.isna(salary_text) or not salary_text:
            return None, None, 'EUR'
        
        salary_text = salary_text.lower()
        
        # Extract numbers
        numbers = re.findall(r'[\d\s]+(?:[\.,]\d+)?', salary_text)
        numbers = [float(n.replace(' ', '').replace(',', '.')) for n in numbers if n.strip()]
        
        # Determine if annual or monthly
        multiplier = 1
        if 'mois' in salary_text or 'mensuel' in salary_text or '/mois' in salary_text:
            multiplier = 12
        elif 'heure' in salary_text or 'horaire' in salary_text:
            multiplier = 12 * 35 * 4  # Approximate annual
        
        # Apply multiplier
        numbers = [n * multiplier for n in numbers]
        
        # Handle K notation (e.g., "40K")
        if 'k' in salary_text.lower() and numbers:
            numbers = [n * 1000 if n < 1000 else n for n in numbers]
        
        min_salary = min(numbers) if numbers else None
        max_salary = max(numbers) if len(numbers) > 1 else min_salary
        
        # Validate salary range
        if min_salary:
            min_salary = max(min_salary, self.config['processing']['min_salary'])
            min_salary = min(min_salary, self.config['processing']['max_salary'])
        if max_salary:
            max_salary = min(max_salary, self.config['processing']['max_salary'])
        
        return min_salary, max_salary, 'EUR'
    
    def classify_job_category(self, title: str, description: str) -> str:
        """Classify job into category based on title and description"""
        text = f"{title} {description}".lower()
        
        categories = self.config['categories']['tech_keywords']
        
        # Score each category
        scores = {}
        for category, keywords in categories.items():
            score = sum(1 for keyword in keywords if keyword.lower() in text)
            if score > 0:
                scores[category] = score
        
        # Return category with highest score
        if scores:
            return max(scores.items(), key=lambda x: x[1])[0]
        else:
            return 'Autre'
    
    def extract_contract_type(self, title: str, description: str) -> str:
        """Extract contract type from job posting"""
        text = f"{title} {description}".lower()
        
        contract_types = self.config['contract_types']
        
        for contract in contract_types:
            if contract.lower() in text:
                return contract
        
        return 'Non spécifié'
    
    def extract_experience_level(self, title: str, description: str) -> str:
        """Extract experience level from job posting"""
        text = f"{title} {description}".lower()
        
        experience_levels = self.config['experience_levels']
        
        for level in experience_levels:
            if level.lower() in text:
                return level
        
        # Check for years of experience
        years_match = re.search(r'(\d+)\s*(?:ans?|années?)', text)
        if years_match:
            years = int(years_match.group(1))
            if years < 2:
                return 'Junior'
            elif years < 5:
                return 'Confirmé'
            else:
                return 'Senior'
        
        return 'Non spécifié'
    
    def extract_remote_type(self, title: str, description: str) -> str:
        """Extract remote work type"""
        text = f"{title} {description}".lower()
        
        if any(keyword in text for keyword in ['full remote', '100% remote', 'télétravail complet']):
            return 'Full Remote'
        elif any(keyword in text for keyword in ['hybrid', 'hybride', 'télétravail partiel']):
            return 'Hybrid'
        elif any(keyword in text for keyword in ['télétravail', 'remote']):
            return 'Télétravail partiel'
        else:
            return 'On-site'
    
    def extract_skills(self, title: str, description: str) -> List[str]:
        """Extract technical skills from job posting"""
        text = f"{title} {description}".lower()
        
        # Common tech skills
        skills_list = [
            'python', 'java', 'javascript', 'typescript', 'c++', 'c#', 'go', 'rust',
            'react', 'angular', 'vue', 'node.js', 'django', 'flask', 'spring',
            'sql', 'postgresql', 'mysql', 'mongodb', 'redis', 'elasticsearch',
            'docker', 'kubernetes', 'aws', 'azure', 'gcp', 'terraform',
            'spark', 'hadoop', 'airflow', 'kafka', 'pandas', 'numpy',
            'machine learning', 'deep learning', 'nlp', 'computer vision',
            'git', 'ci/cd', 'jenkins', 'gitlab', 'github'
        ]
        
        found_skills = [skill for skill in skills_list if skill in text]
        return found_skills[:10]  # Limit to top 10
    
    def process_jobs(self, df: pd.DataFrame) -> pd.DataFrame:
        """Main processing pipeline"""
        logger.info(f"Processing {len(df)} jobs")
        
        if df.empty:
            return df
        
        # Create copy for processing
        processed = df.copy()
        
        # Clean and parse location
        location_data = processed['location'].apply(self.clean_location)
        processed['city'] = location_data.apply(lambda x: x[0])
        processed['region'] = location_data.apply(lambda x: x[1])
        processed['normalized_location'] = location_data.apply(lambda x: x[2])
        
        # Parse salary
        salary_data = processed['salary_text'].apply(self.parse_salary)
        processed['salary_min'] = salary_data.apply(lambda x: x[0])
        processed['salary_max'] = salary_data.apply(lambda x: x[1])
        processed['salary_currency'] = salary_data.apply(lambda x: x[2])
        processed['salary_avg'] = (processed['salary_min'] + processed['salary_max']) / 2
        
        # Classify and extract features
        processed['category'] = processed.apply(
            lambda row: self.classify_job_category(row['title'], row['description'] or ''), 
            axis=1
        )
        
        processed['contract_type'] = processed.apply(
            lambda row: self.extract_contract_type(row['title'], row['description'] or ''),
            axis=1
        )
        
        processed['experience_level'] = processed.apply(
            lambda row: self.extract_experience_level(row['title'], row['description'] or ''),
            axis=1
        )
        
        processed['remote_type'] = processed.apply(
            lambda row: self.extract_remote_type(row['title'], row['description'] or ''),
            axis=1
        )
        
        processed['skills'] = processed.apply(
            lambda row: self.extract_skills(row['title'], row['description'] or ''),
            axis=1
        )
        
        # Clean company names
        processed['company_normalized'] = processed['company'].str.strip().str.lower()
        
        # Add processing timestamp
        processed['processed_at'] = datetime.now()
        
        logger.info(f"Successfully processed {len(processed)} jobs")
        
        return processed
    
    def save_to_database(self, df: pd.DataFrame):
        """Save processed jobs to database"""
        if df.empty:
            logger.warning("No data to save")
            return
        
        conn = self.get_db_connection()
        
        try:
            cursor = conn.cursor()
            
            # Insert companies
            companies = df[['company', 'company_normalized']].drop_duplicates()
            company_query = """
                INSERT INTO companies (name, normalized_name)
                VALUES (%s, %s)
                ON CONFLICT (name) DO NOTHING
                RETURNING id
            """
            
            for _, row in companies.iterrows():
                cursor.execute(company_query, (row['company'], row['company_normalized']))
            
            # Insert locations
            locations = df[['city', 'region', 'normalized_location']].drop_duplicates()
            location_query = """
                INSERT INTO locations (city, region, normalized_location, country)
                VALUES (%s, %s, %s, 'France')
                ON CONFLICT (normalized_location) DO NOTHING
            """
            
            location_data = [
                (row['city'], row['region'], row['normalized_location'])
                for _, row in locations.iterrows()
                if row['normalized_location'] is not None
            ]
            execute_batch(cursor, location_query, location_data)
            
            conn.commit()
            
            # Get company and location IDs
            cursor.execute("SELECT id, normalized_name FROM companies")
            company_map = {row[1]: row[0] for row in cursor.fetchall()}
            
            cursor.execute("SELECT id, normalized_location FROM locations")
            location_map = {row[1]: row[0] for row in cursor.fetchall()}
            
            # Insert cleaned jobs
            insert_query = """
                INSERT INTO cleaned_jobs (
                    raw_job_id, job_id, title, company_id, location_id, category,
                    contract_type, experience_level, salary_min, salary_max, salary_avg,
                    salary_currency, description_clean, skills, remote_type, posting_date, processed_at
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (job_id) DO UPDATE SET
                    processed_at = EXCLUDED.processed_at
            """
            
            data = []
            for _, row in df.iterrows():
                company_id = company_map.get(row['company_normalized'])
                location_id = location_map.get(row['normalized_location'])
                
                data.append((
                    row['id'],
                    row['job_id'],
                    row['title'],
                    company_id,
                    location_id,
                    row['category'],
                    row['contract_type'],
                    row['experience_level'],
                    row['salary_min'],
                    row['salary_max'],
                    row['salary_avg'],
                    row['salary_currency'],
                    row['description'],
                    row['skills'],
                    row['remote_type'],
                    row['posting_date'],
                    row['processed_at']
                ))
            
            execute_batch(cursor, insert_query, data, page_size=100)
            conn.commit()
            
            logger.info(f"Successfully saved {len(df)} processed jobs to database")
            
        except Exception as e:
            logger.error(f"Database error: {str(e)}")
            conn.rollback()
            raise
        finally:
            cursor.close()
            conn.close()


def main():
    """Main execution function"""
    logger.info("Starting Pandas data processing")
    
    processor = JobDataProcessor()
    
    # Load raw jobs
    raw_df = processor.load_raw_jobs(days_back=1)
    
    if not raw_df.empty:
        # Process jobs
        processed_df = processor.process_jobs(raw_df)
        
        # Save to database
        processor.save_to_database(processed_df)
        
        logger.info("Processing completed successfully")
    else:
        logger.warning("No raw jobs to process")


if __name__ == "__main__":
    main()
