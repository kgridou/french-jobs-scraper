"""
Indeed.fr Job Scraper
Scrapes job postings from Indeed France
"""

import re
import logging
from typing import List, Dict, Optional
from urllib.parse import urljoin, urlparse, parse_qs
from datetime import datetime, timedelta

from bs4 import BeautifulSoup
from scrapers.base_scraper import BaseScraper, ScraperFactory


class IndeedScraper(BaseScraper):
    """Scraper for Indeed.fr job postings"""
    
    def __init__(self, search_query: str = "data engineer", location: str = "France", **kwargs):
        super().__init__(
            source_name="indeed_fr",
            base_url="https://fr.indeed.com",
            **kwargs
        )
        self.search_query = search_query
        self.location = location
        
    def _build_search_url(self, page_num: int = 1) -> str:
        """Build Indeed search URL"""
        start = (page_num - 1) * 10  # Indeed shows 10 jobs per page
        return (
            f"{self.base_url}/jobs?"
            f"q={self.search_query.replace(' ', '+')}&"
            f"l={self.location.replace(' ', '+')}&"
            f"start={start}"
        )
    
    def scrape_list_page(self, page_num: int = 1) -> List[str]:
        """Scrape job listing page and return job URLs"""
        url = self._build_search_url(page_num)
        self.logger.info(f"Scraping list page: {url}")
        
        soup = self._get_soup(url)
        if not soup:
            return []
        
        job_urls = []
        
        # Find job cards - Indeed uses various selectors
        job_cards = soup.find_all('div', class_='job_seen_beacon')
        if not job_cards:
            job_cards = soup.find_all('div', {'data-jk': True})
        
        for card in job_cards:
            try:
                # Extract job ID
                job_id = card.get('data-jk')
                if not job_id:
                    continue
                
                # Build full job URL
                job_url = f"{self.base_url}/viewjob?jk={job_id}"
                job_urls.append(job_url)
                
            except Exception as e:
                self.logger.warning(f"Error extracting job URL: {e}")
                continue
        
        return job_urls
    
    def scrape_job_details(self, job_url: str) -> Optional[Dict]:
        """Scrape individual job details"""
        self.logger.debug(f"Scraping job: {job_url}")
        
        soup = self._get_soup(job_url)
        if not soup:
            return None
        
        try:
            # Extract job details
            job_data = {
                'source': self.source_name,
                'url': job_url,
                'external_id': self._extract_job_id(job_url)
            }
            
            # Title
            title_elem = soup.find('h1', class_='jobsearch-JobInfoHeader-title')
            if not title_elem:
                title_elem = soup.find('h1')
            job_data['title'] = self._clean_text(title_elem.text) if title_elem else None
            
            # Company
            company_elem = soup.find('div', {'data-company-name': True})
            if not company_elem:
                company_elem = soup.find('div', class_='jobsearch-InlineCompanyRating')
            job_data['company'] = self._clean_text(company_elem.text) if company_elem else None
            
            # Location
            location_elem = soup.find('div', {'data-testid': 'job-location'})
            if not location_elem:
                location_elem = soup.find('div', class_='jobsearch-JobInfoHeader-subtitle')
            location_text = self._clean_text(location_elem.text) if location_elem else None
            job_data['location'] = location_text
            job_data.update(self._parse_location(location_text))
            
            # Salary
            salary_elem = soup.find('div', {'id': 'salaryInfoAndJobType'})
            if not salary_elem:
                salary_elem = soup.find('span', class_='salary')
            salary_text = self._clean_text(salary_elem.text) if salary_elem else None
            job_data.update(self._parse_salary(salary_text))
            
            # Contract type
            job_data['contract_type'] = self._extract_contract_type(soup)
            
            # Remote type
            job_data['remote_type'] = self._extract_remote_type(soup)
            
            # Description
            desc_elem = soup.find('div', {'id': 'jobDescriptionText'})
            if not desc_elem:
                desc_elem = soup.find('div', class_='jobsearch-jobDescriptionText')
            job_data['description'] = self._clean_text(desc_elem.text) if desc_elem else None
            
            # Requirements (often in description for Indeed)
            job_data['requirements'] = self._extract_requirements(job_data.get('description', ''))
            
            # Skills
            job_data['required_skills'] = self._extract_skills(job_data.get('description', ''))
            
            # Posted date
            date_elem = soup.find('span', class_='date')
            job_data['posted_date'] = self._parse_date(date_elem.text) if date_elem else None
            
            # Company URL
            company_link = soup.find('a', {'data-testid': 'viewJobCompanyLink'})
            if company_link:
                job_data['company_url'] = urljoin(self.base_url, company_link.get('href', ''))
            
            return job_data
            
        except Exception as e:
            self.logger.error(f"Error scraping job {job_url}: {e}")
            return None
    
    def _extract_job_id(self, url: str) -> Optional[str]:
        """Extract job ID from URL"""
        parsed = urlparse(url)
        params = parse_qs(parsed.query)
        return params.get('jk', [None])[0]
    
    def _parse_location(self, location_text: Optional[str]) -> Dict:
        """Parse location into components"""
        if not location_text:
            return {'city': None, 'department': None, 'region': None}
        
        # Simple parsing - can be enhanced with geocoding
        parts = [p.strip() for p in location_text.split(',')]
        
        return {
            'city': parts[0] if len(parts) > 0 else None,
            'department': parts[1] if len(parts) > 1 else None,
            'region': parts[2] if len(parts) > 2 else None
        }
    
    def _parse_salary(self, salary_text: Optional[str]) -> Dict:
        """Parse salary information"""
        result = {
            'salary_min': None,
            'salary_max': None,
            'salary_currency': 'EUR',
            'salary_period': None
        }
        
        if not salary_text:
            return result
        
        # Remove spaces and convert to lowercase
        salary_text = salary_text.replace(' ', '').lower()
        
        # Detect period
        if 'an' in salary_text or 'annuel' in salary_text:
            result['salary_period'] = 'yearly'
        elif 'mois' in salary_text or 'mensuel' in salary_text:
            result['salary_period'] = 'monthly'
        elif 'heure' in salary_text or 'horaire' in salary_text:
            result['salary_period'] = 'hourly'
        
        # Extract numbers
        numbers = re.findall(r'(\d+(?:\.\d+)?)', salary_text)
        if numbers:
            numbers = [float(n.replace(',', '.')) for n in numbers]
            if len(numbers) == 1:
                result['salary_min'] = numbers[0]
                result['salary_max'] = numbers[0]
            elif len(numbers) >= 2:
                result['salary_min'] = min(numbers)
                result['salary_max'] = max(numbers)
        
        return result
    
    def _extract_contract_type(self, soup: BeautifulSoup) -> Optional[str]:
        """Extract contract type from job page"""
        # Look for common French contract types
        contract_keywords = {
            'CDI': 'CDI',
            'CDD': 'CDD',
            'Stage': 'Stage',
            'Alternance': 'Alternance',
            'Intérim': 'Interim',
            'Freelance': 'Freelance',
            'Temps plein': 'Full-time',
            'Temps partiel': 'Part-time'
        }
        
        text = soup.get_text().lower()
        for keyword, contract_type in contract_keywords.items():
            if keyword.lower() in text:
                return contract_type
        
        return None
    
    def _extract_remote_type(self, soup: BeautifulSoup) -> Optional[str]:
        """Extract remote work type"""
        text = soup.get_text().lower()
        
        if 'télétravail' in text or 'remote' in text or '100% distanciel' in text:
            return 'Remote'
        elif 'hybride' in text or 'hybrid' in text:
            return 'Hybrid'
        else:
            return 'On-site'
    
    def _extract_requirements(self, description: str) -> Optional[str]:
        """Extract requirements section from description"""
        if not description:
            return None
        
        # Look for requirements section
        desc_lower = description.lower()
        req_keywords = ['exigences', 'requirements', 'qualifications', 'profil recherché']
        
        for keyword in req_keywords:
            if keyword in desc_lower:
                idx = desc_lower.find(keyword)
                # Return next 500 characters as requirements
                return description[idx:idx+500]
        
        return None
    
    def _extract_skills(self, description: str) -> List[str]:
        """Extract skills from job description"""
        if not description:
            return []
        
        # Common tech skills
        skills = [
            'Python', 'Java', 'JavaScript', 'TypeScript', 'C++', 'C#', 'Ruby', 'Go', 'Rust',
            'SQL', 'NoSQL', 'PostgreSQL', 'MySQL', 'MongoDB', 'Redis',
            'Docker', 'Kubernetes', 'Jenkins', 'GitLab', 'CI/CD',
            'AWS', 'Azure', 'GCP', 'Cloud',
            'React', 'Vue', 'Angular', 'Node.js', 'Django', 'Flask', 'Spring',
            'Machine Learning', 'Deep Learning', 'NLP', 'AI',
            'Spark', 'Hadoop', 'Kafka', 'Airflow',
            'Agile', 'Scrum', 'DevOps'
        ]
        
        found_skills = []
        desc_lower = description.lower()
        
        for skill in skills:
            if skill.lower() in desc_lower:
                found_skills.append(skill)
        
        return found_skills
    
    def _parse_date(self, date_text: str) -> Optional[str]:
        """Parse posted date"""
        if not date_text:
            return None
        
        date_text = date_text.lower()
        today = datetime.now().date()
        
        if "aujourd'hui" in date_text or 'today' in date_text:
            return today.isoformat()
        elif 'hier' in date_text or 'yesterday' in date_text:
            return (today - timedelta(days=1)).isoformat()
        else:
            # Try to extract number of days
            match = re.search(r'(\d+)', date_text)
            if match:
                days_ago = int(match.group(1))
                return (today - timedelta(days=days_ago)).isoformat()
        
        return None


# Register scraper with factory
ScraperFactory.register('indeed_fr', IndeedScraper)


if __name__ == '__main__':
    # Test the scraper
    logging.basicConfig(level=logging.INFO)
    
    scraper = IndeedScraper(
        search_query="data engineer",
        location="Paris",
        delay_min=2,
        delay_max=4
    )
    
    jobs = scraper.scrape_all(max_pages=2)
    print(f"\nScraped {len(jobs)} jobs")
    print(f"Stats: {scraper.get_stats()}")
    
    scraper.close()
