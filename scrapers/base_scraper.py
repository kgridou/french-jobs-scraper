"""
Base Scraper Class
Provides common functionality for all job scrapers
"""

import json
import time
import random
import logging
from abc import ABC, abstractmethod
from typing import List, Dict, Optional
from datetime import datetime
from pathlib import Path

import requests
from bs4 import BeautifulSoup
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry


class BaseScraper(ABC):
    """Abstract base class for job scrapers"""
    
    def __init__(
        self,
        source_name: str,
        base_url: str,
        delay_min: int = 2,
        delay_max: int = 5,
        max_retries: int = 3
    ):
        self.source_name = source_name
        self.base_url = base_url
        self.delay_min = delay_min
        self.delay_max = delay_max
        self.max_retries = max_retries
        
        # Setup logging
        self.logger = logging.getLogger(f"{__name__}.{source_name}")
        self.logger.setLevel(logging.INFO)
        
        # Setup session with retry strategy
        self.session = self._create_session()
        
        # Statistics
        self.stats = {
            'total_scraped': 0,
            'successful': 0,
            'failed': 0,
            'duplicates': 0
        }
        
    def _create_session(self) -> requests.Session:
        """Create a requests session with retry strategy"""
        session = requests.Session()
        
        retry_strategy = Retry(
            total=self.max_retries,
            backoff_factor=1,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["HEAD", "GET", "OPTIONS"]
        )
        
        adapter = HTTPAdapter(max_retries=retry_strategy)
        session.mount("http://", adapter)
        session.mount("https://", adapter)
        
        # Default headers
        session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'fr-FR,fr;q=0.9,en-US;q=0.8,en;q=0.7',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1'
        })
        
        return session
    
    def _random_delay(self):
        """Add random delay between requests to be respectful"""
        delay = random.uniform(self.delay_min, self.delay_max)
        time.sleep(delay)
        self.logger.debug(f"Delayed for {delay:.2f} seconds")
    
    def _get_soup(self, url: str) -> Optional[BeautifulSoup]:
        """Get BeautifulSoup object from URL"""
        try:
            self._random_delay()
            response = self.session.get(url, timeout=30)
            response.raise_for_status()
            return BeautifulSoup(response.content, 'html.parser')
        except requests.exceptions.RequestException as e:
            self.logger.error(f"Error fetching {url}: {e}")
            return None
    
    def _clean_text(self, text: Optional[str]) -> str:
        """Clean and normalize text"""
        if not text:
            return ""
        return " ".join(text.strip().split())
    
    def _extract_salary(self, salary_text: str) -> Dict[str, Optional[float]]:
        """Extract salary range from text"""
        # Basic implementation - override in specific scrapers
        return {
            'min': None,
            'max': None,
            'currency': 'EUR',
            'period': 'yearly'
        }
    
    def _save_jobs(self, jobs: List[Dict], output_path: Path):
        """Save scraped jobs to JSON file"""
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = output_path / f"{self.source_name}_{timestamp}.json"
        
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(jobs, f, ensure_ascii=False, indent=2)
        
        self.logger.info(f"Saved {len(jobs)} jobs to {filename}")
        return filename
    
    def _update_stats(self, success: bool = True, duplicate: bool = False):
        """Update scraping statistics"""
        self.stats['total_scraped'] += 1
        if success:
            self.stats['successful'] += 1
        else:
            self.stats['failed'] += 1
        if duplicate:
            self.stats['duplicates'] += 1
    
    def get_stats(self) -> Dict:
        """Return scraping statistics"""
        return self.stats.copy()
    
    @abstractmethod
    def scrape_list_page(self, page_num: int = 1) -> List[str]:
        """
        Scrape job listing page and return list of job URLs
        Must be implemented by child classes
        """
        pass
    
    @abstractmethod
    def scrape_job_details(self, job_url: str) -> Optional[Dict]:
        """
        Scrape individual job details
        Must be implemented by child classes
        """
        pass
    
    def scrape_all(
        self,
        max_pages: int = 10,
        output_path: Optional[Path] = None
    ) -> List[Dict]:
        """
        Main scraping method - scrape multiple pages of jobs
        """
        self.logger.info(f"Starting scrape for {self.source_name}")
        all_jobs = []
        seen_urls = set()
        
        for page in range(1, max_pages + 1):
            self.logger.info(f"Scraping page {page}/{max_pages}")
            
            # Get job URLs from listing page
            job_urls = self.scrape_list_page(page)
            
            if not job_urls:
                self.logger.warning(f"No jobs found on page {page}, stopping")
                break
            
            self.logger.info(f"Found {len(job_urls)} jobs on page {page}")
            
            # Scrape each job
            for url in job_urls:
                if url in seen_urls:
                    self._update_stats(success=True, duplicate=True)
                    continue
                
                job_data = self.scrape_job_details(url)
                
                if job_data:
                    job_data['scraped_at'] = datetime.now().isoformat()
                    all_jobs.append(job_data)
                    seen_urls.add(url)
                    self._update_stats(success=True)
                else:
                    self._update_stats(success=False)
            
            # Log progress
            self.logger.info(
                f"Progress: {len(all_jobs)} jobs scraped, "
                f"{self.stats['failed']} failed, "
                f"{self.stats['duplicates']} duplicates"
            )
        
        # Save results
        if output_path and all_jobs:
            self._save_jobs(all_jobs, output_path)
        
        self.logger.info(f"Scraping completed. Total jobs: {len(all_jobs)}")
        return all_jobs
    
    def close(self):
        """Clean up resources"""
        self.session.close()
        self.logger.info(f"Closed session for {self.source_name}")


class ScraperFactory:
    """Factory to create scraper instances"""
    
    _scrapers = {}
    
    @classmethod
    def register(cls, name: str, scraper_class):
        """Register a scraper class"""
        cls._scrapers[name] = scraper_class
    
    @classmethod
    def create(cls, name: str, **kwargs) -> BaseScraper:
        """Create a scraper instance"""
        if name not in cls._scrapers:
            raise ValueError(f"Unknown scraper: {name}")
        return cls._scrapers[name](**kwargs)
    
    @classmethod
    def list_scrapers(cls) -> List[str]:
        """List all registered scrapers"""
        return list(cls._scrapers.keys())
