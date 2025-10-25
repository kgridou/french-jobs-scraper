"""
Web Scraper for French Job Postings
Scrapes job listings from Indeed.fr and other French job boards
"""

import requests
from bs4 import BeautifulSoup
import pandas as pd
import yaml
import time
import random
import hashlib
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Optional
from fake_useragent import UserAgent
import psycopg2
from psycopg2.extras import execute_batch
import os

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class FrenchJobScraper:
    """Scrapes French job postings from various sources"""
    
    def __init__(self, config_path: str = '/opt/airflow/config/scraper_config.yaml'):
        """Initialize scraper with configuration"""
        with open(config_path, 'r', encoding='utf-8') as f:
            self.config = yaml.safe_load(f)
        
        self.ua = UserAgent()
        self.session = requests.Session()
        self.jobs_collected = []
        
    def get_headers(self) -> Dict[str, str]:
        """Get random headers for requests"""
        user_agents = self.config['scraping']['user_agents']
        return {
            'User-Agent': random.choice(user_agents),
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'fr-FR,fr;q=0.9,en;q=0.8',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1'
        }
    
    def generate_job_id(self, title: str, company: str, location: str) -> str:
        """Generate unique job ID from job details"""
        unique_string = f"{title}_{company}_{location}".lower()
        return hashlib.md5(unique_string.encode()).hexdigest()
    
    def scrape_indeed_fr(self, keyword: str, location: str, max_pages: int = 5) -> List[Dict]:
        """Scrape job listings from Indeed.fr"""
        jobs = []
        base_url = self.config['sources']['indeed']['base_url']
        rate_limit = self.config['sources']['indeed']['rate_limit']
        
        logger.info(f"Scraping Indeed.fr for '{keyword}' in '{location}'")
        
        for page in range(max_pages):
            try:
                # Build search URL
                start = page * 10
                search_url = f"{base_url}/jobs?q={keyword}&l={location}&start={start}"
                
                # Make request with rate limiting
                time.sleep(rate_limit + random.uniform(0, 1))
                response = self.session.get(search_url, headers=self.get_headers(), timeout=30)
                response.raise_for_status()
                
                # Parse HTML
                soup = BeautifulSoup(response.content, 'html.parser')
                
                # Find job cards (Indeed's structure as of 2024)
                job_cards = soup.find_all('div', class_='job_seen_beacon')
                
                if not job_cards:
                    # Try alternative selectors
                    job_cards = soup.find_all('td', class_='resultContent')
                
                logger.info(f"Found {len(job_cards)} jobs on page {page + 1}")
                
                for card in job_cards:
                    try:
                        job_data = self._parse_indeed_job_card(card, base_url)
                        if job_data:
                            jobs.append(job_data)
                    except Exception as e:
                        logger.warning(f"Error parsing job card: {str(e)}")
                        continue
                
                # Check if we reached the last page
                if len(job_cards) == 0:
                    break
                    
            except requests.exceptions.RequestException as e:
                logger.error(f"Request error on page {page + 1}: {str(e)}")
                break
            except Exception as e:
                logger.error(f"Unexpected error on page {page + 1}: {str(e)}")
                break
        
        logger.info(f"Collected {len(jobs)} jobs from Indeed.fr for '{keyword}' in '{location}'")
        return jobs
    
    def _parse_indeed_job_card(self, card, base_url: str) -> Optional[Dict]:
        """Parse individual Indeed job card"""
        try:
            # Extract title
            title_elem = card.find('h2', class_='jobTitle')
            if not title_elem:
                title_elem = card.find('a', class_='jcs-JobTitle')
            
            title = title_elem.get_text(strip=True) if title_elem else None
            
            # Extract job URL
            job_link = title_elem.find('a') if title_elem else None
            job_url = f"{base_url}{job_link['href']}" if job_link and 'href' in job_link.attrs else None
            
            # Extract company
            company_elem = card.find('span', class_='companyName')
            company = company_elem.get_text(strip=True) if company_elem else "Unknown"
            
            # Extract location
            location_elem = card.find('div', class_='companyLocation')
            location = location_elem.get_text(strip=True) if location_elem else "France"
            
            # Extract salary
            salary_elem = card.find('div', class_='salary-snippet')
            if not salary_elem:
                salary_elem = card.find('span', class_='salary-snippet-container')
            salary_text = salary_elem.get_text(strip=True) if salary_elem else None
            
            # Extract description snippet
            description_elem = card.find('div', class_='job-snippet')
            description = description_elem.get_text(strip=True) if description_elem else ""
            
            # Extract posting date
            date_elem = card.find('span', class_='date')
            posting_date = self._parse_french_date(date_elem.get_text(strip=True)) if date_elem else datetime.now().date()
            
            if not title:
                return None
            
            job_id = self.generate_job_id(title, company, location)
            
            return {
                'job_id': job_id,
                'source': 'indeed_fr',
                'url': job_url,
                'title': title,
                'company': company,
                'location': location,
                'salary_text': salary_text,
                'description': description,
                'posting_date': posting_date,
                'scraped_at': datetime.now()
            }
        except Exception as e:
            logger.warning(f"Error parsing job card: {str(e)}")
            return None
    
    def _parse_french_date(self, date_str: str) -> datetime.date:
        """Parse French relative dates (e.g., 'Il y a 2 jours')"""
        today = datetime.now().date()
        date_str = date_str.lower()
        
        if "aujourd'hui" in date_str or "aujourd hui" in date_str:
            return today
        elif "hier" in date_str:
            return today - timedelta(days=1)
        elif "jour" in date_str:
            # Extract number of days
            try:
                days = int(''.join(filter(str.isdigit, date_str)))
                return today - timedelta(days=days)
            except:
                return today
        elif "heure" in date_str:
            return today
        else:
            return today
    
    def scrape_all_sources(self) -> pd.DataFrame:
        """Scrape all configured sources"""
        all_jobs = []
        
        # Scrape Indeed.fr
        if self.config['sources']['indeed']['enabled']:
            for keyword in self.config['sources']['indeed']['search_params']['keywords']:
                for location in self.config['sources']['indeed']['search_params']['locations']:
                    jobs = self.scrape_indeed_fr(
                        keyword, 
                        location, 
                        self.config['sources']['indeed']['max_pages']
                    )
                    all_jobs.extend(jobs)
        
        # Convert to DataFrame
        if all_jobs:
            df = pd.DataFrame(all_jobs)
            
            # Remove duplicates based on job_id
            df = df.drop_duplicates(subset=['job_id'])
            
            logger.info(f"Total unique jobs scraped: {len(df)}")
            return df
        else:
            logger.warning("No jobs scraped!")
            return pd.DataFrame()
    
    def save_to_database(self, df: pd.DataFrame):
        """Save scraped jobs to PostgreSQL database"""
        if df.empty:
            logger.warning("No data to save")
            return
        
        # Database connection
        conn = psycopg2.connect(
            host=os.getenv('JOBS_DB_HOST', 'postgres'),
            port=os.getenv('JOBS_DB_PORT', 5432),
            database=os.getenv('JOBS_DB_NAME', 'jobs_db'),
            user=os.getenv('JOBS_DB_USER', 'airflow'),
            password=os.getenv('JOBS_DB_PASSWORD', 'airflow')
        )
        
        try:
            cursor = conn.cursor()
            
            # Prepare insert query
            insert_query = """
                INSERT INTO raw_jobs (
                    job_id, source, url, title, company, location, 
                    salary_text, description, posting_date, scraped_at
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (job_id) DO UPDATE SET
                    scraped_at = EXCLUDED.scraped_at,
                    description = EXCLUDED.description
            """
            
            # Prepare data for batch insert
            data = [
                (
                    row['job_id'],
                    row['source'],
                    row.get('url'),
                    row['title'],
                    row['company'],
                    row['location'],
                    row.get('salary_text'),
                    row['description'],
                    row['posting_date'],
                    row['scraped_at']
                )
                for _, row in df.iterrows()
            ]
            
            # Execute batch insert
            execute_batch(cursor, insert_query, data, page_size=100)
            conn.commit()
            
            logger.info(f"Successfully saved {len(df)} jobs to database")
            
        except Exception as e:
            logger.error(f"Database error: {str(e)}")
            conn.rollback()
            raise
        finally:
            cursor.close()
            conn.close()


def main():
    """Main execution function"""
    logger.info("Starting French job scraping process")
    
    scraper = FrenchJobScraper()
    df = scraper.scrape_all_sources()
    
    if not df.empty:
        scraper.save_to_database(df)
        logger.info(f"Scraping completed successfully. Total jobs: {len(df)}")
    else:
        logger.warning("No jobs were scraped")


if __name__ == "__main__":
    main()
