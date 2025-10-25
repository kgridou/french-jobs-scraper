"""
HelloWork Job Scraper
Scrapes job postings from HelloWork.com (formerly RegionsJob)
"""

import re
import logging
from typing import List, Dict, Optional
from urllib.parse import urljoin
from datetime import datetime

from bs4 import BeautifulSoup
from scrapers.base_scraper import BaseScraper, ScraperFactory


class HelloWorkScraper(BaseScraper):
    """Scraper for HelloWork.com job postings"""
    
    def __init__(self, search_query: str = "data engineer", **kwargs):
        super().__init__(
            source_name="hellowork",
            base_url="https://www.hellowork.com",
            **kwargs
        )
        self.search_query = search_query
        
    def _build_search_url(self, page_num: int = 1) -> str:
        """Build HelloWork search URL"""
        return (
            f"{self.base_url}/fr-fr/emplois.html?"
            f"k={self.search_query.replace(' ', '+')}&"
            f"p={page_num}"
        )
    
    def scrape_list_page(self, page_num: int = 1) -> List[str]:
        """Scrape job listing page and return job URLs"""
        url = self._build_search_url(page_num)
        self.logger.info(f"Scraping list page: {url}")
        
        soup = self._get_soup(url)
        if not soup:
            return []
        
        job_urls = []
        
        # Find job listings
        job_items = soup.find_all('article', class_='job-card')
        if not job_items:
            job_items = soup.find_all('li', class_='job-list-item')
        
        for item in job_items:
            try:
                # Find link to job
                link = item.find('a', class_='job-link')
                if not link:
                    link = item.find('a', href=re.compile(r'/emplois/detail/'))
                
                if link and link.get('href'):
                    job_url = urljoin(self.base_url, link['href'])
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
            job_data = {
                'source': self.source_name,
                'url': job_url,
                'external_id': self._extract_job_id(job_url)
            }
            
            # Title
            title_elem = soup.find('h1', class_='job-title')
            if not title_elem:
                title_elem = soup.find('h1')
            job_data['title'] = self._clean_text(title_elem.text) if title_elem else None
            
            # Company
            company_elem = soup.find('span', class_='company-name')
            if not company_elem:
                company_elem = soup.find('a', class_='company-link')
            job_data['company'] = self._clean_text(company_elem.text) if company_elem else None
            
            # Location
            location_elem = soup.find('span', class_='job-location')
            if not location_elem:
                location_elem = soup.find('div', class_='location')
            location_text = self._clean_text(location_elem.text) if location_elem else None
            job_data['location'] = location_text
            job_data.update(self._parse_location(location_text))
            
            # Contract type
            contract_elem = soup.find('span', class_='contract-type')
            job_data['contract_type'] = self._clean_text(contract_elem.text) if contract_elem else None
            
            # Salary
            salary_elem = soup.find('span', class_='salary')
            if not salary_elem:
                salary_elem = soup.find('div', class_='salary-info')
            salary_text = self._clean_text(salary_elem.text) if salary_elem else None
            job_data.update(self._parse_salary(salary_text))
            
            # Experience level
            exp_elem = soup.find('span', class_='experience')
            job_data['experience_level'] = self._clean_text(exp_elem.text) if exp_elem else None
            
            # Remote type
            remote_elem = soup.find('span', class_='remote-work')
            if remote_elem:
                job_data['remote_type'] = self._clean_text(remote_elem.text)
            else:
                job_data['remote_type'] = 'On-site'
            
            # Description
            desc_elem = soup.find('div', class_='job-description')
            if not desc_elem:
                desc_elem = soup.find('div', {'itemprop': 'description'})
            job_data['description'] = self._clean_text(desc_elem.text) if desc_elem else None
            
            # Requirements
            req_elem = soup.find('div', class_='job-requirements')
            job_data['requirements'] = self._clean_text(req_elem.text) if req_elem else None
            
            # Benefits
            benefits_elem = soup.find('div', class_='job-benefits')
            job_data['benefits'] = self._clean_text(benefits_elem.text) if benefits_elem else None
            
            # Skills
            skills_container = soup.find('div', class_='skills-list')
            if skills_container:
                skills = [self._clean_text(s.text) for s in skills_container.find_all('span', class_='skill')]
                job_data['required_skills'] = skills
            else:
                job_data['required_skills'] = self._extract_skills_from_text(
                    job_data.get('description', '') + ' ' + job_data.get('requirements', '')
                )
            
            # Posted date
            date_elem = soup.find('time', {'datetime': True})
            if date_elem:
                job_data['posted_date'] = date_elem.get('datetime', '').split('T')[0]
            else:
                date_elem = soup.find('span', class_='posted-date')
                job_data['posted_date'] = self._parse_relative_date(
                    self._clean_text(date_elem.text)
                ) if date_elem else None
            
            # Company info
            company_info = self._extract_company_info(soup)
            job_data.update(company_info)
            
            return job_data
            
        except Exception as e:
            self.logger.error(f"Error scraping job {job_url}: {e}")
            return None
    
    def _extract_job_id(self, url: str) -> Optional[str]:
        """Extract job ID from URL"""
        match = re.search(r'/([0-9]+)/?$', url)
        return match.group(1) if match else None
    
    def _parse_location(self, location_text: Optional[str]) -> Dict:
        """Parse location into components"""
        if not location_text:
            return {'city': None, 'department': None, 'region': None}
        
        # HelloWork often uses format: "City (Department)"
        match = re.match(r'([^(]+)\s*\((\d+)\)', location_text)
        if match:
            city = match.group(1).strip()
            dept = match.group(2).strip()
            return {
                'city': city,
                'department': dept,
                'region': self._department_to_region(dept)
            }
        
        return {
            'city': location_text,
            'department': None,
            'region': None
        }
    
    def _department_to_region(self, dept: str) -> Optional[str]:
        """Map department number to region"""
        dept_map = {
            '75': 'Île-de-France',
            '92': 'Île-de-France',
            '93': 'Île-de-France',
            '94': 'Île-de-France',
            '77': 'Île-de-France',
            '78': 'Île-de-France',
            '91': 'Île-de-France',
            '95': 'Île-de-France',
            '13': 'Provence-Alpes-Côte d\'Azur',
            '69': 'Auvergne-Rhône-Alpes',
            '31': 'Occitanie',
            '33': 'Nouvelle-Aquitaine',
            '44': 'Pays de la Loire',
            '59': 'Hauts-de-France',
            '67': 'Grand Est',
        }
        return dept_map.get(dept)
    
    def _parse_salary(self, salary_text: Optional[str]) -> Dict:
        """Parse salary information"""
        result = {
            'salary_min': None,
            'salary_max': None,
            'salary_currency': 'EUR',
            'salary_period': 'yearly'
        }
        
        if not salary_text:
            return result
        
        salary_text = salary_text.lower().replace(' ', '')
        
        # Detect period
        if 'mois' in salary_text or 'mensuel' in salary_text:
            result['salary_period'] = 'monthly'
        elif 'heure' in salary_text or 'horaire' in salary_text:
            result['salary_period'] = 'hourly'
        
        # Extract numbers (format: "30K€ - 45K€" or "30000€")
        numbers = re.findall(r'(\d+(?:[.,]\d+)?)\s*k?€?', salary_text)
        if numbers:
            numbers = [float(n.replace(',', '.')) for n in numbers]
            # If 'k' or 'K' present, multiply by 1000
            if 'k' in salary_text:
                numbers = [n * 1000 if n < 1000 else n for n in numbers]
            
            if len(numbers) == 1:
                result['salary_min'] = numbers[0]
                result['salary_max'] = numbers[0]
            elif len(numbers) >= 2:
                result['salary_min'] = min(numbers)
                result['salary_max'] = max(numbers)
        
        return result
    
    def _extract_skills_from_text(self, text: str) -> List[str]:
        """Extract skills from text"""
        if not text:
            return []
        
        skills = [
            'Python', 'Java', 'JavaScript', 'TypeScript', 'C++', 'C#', 'Ruby', 'PHP', 'Go',
            'SQL', 'PostgreSQL', 'MySQL', 'MongoDB', 'Oracle', 'Redis',
            'Docker', 'Kubernetes', 'Jenkins', 'GitLab CI', 'CI/CD',
            'AWS', 'Azure', 'GCP', 'Terraform', 'Ansible',
            'React', 'Vue.js', 'Angular', 'Node.js', 'Django', 'Flask', 'Spring Boot',
            'Machine Learning', 'Deep Learning', 'TensorFlow', 'PyTorch',
            'Spark', 'Hadoop', 'Kafka', 'Airflow', 'Pandas',
            'Linux', 'Git', 'Agile', 'Scrum', 'DevOps'
        ]
        
        found_skills = []
        text_lower = text.lower()
        
        for skill in skills:
            # Look for skill with word boundaries
            pattern = r'\b' + re.escape(skill.lower()) + r'\b'
            if re.search(pattern, text_lower):
                found_skills.append(skill)
        
        return found_skills
    
    def _parse_relative_date(self, date_text: str) -> Optional[str]:
        """Parse relative date like 'il y a 2 jours'"""
        if not date_text:
            return None
        
        from datetime import timedelta
        today = datetime.now().date()
        
        date_text = date_text.lower()
        
        if "aujourd'hui" in date_text:
            return today.isoformat()
        elif 'hier' in date_text:
            return (today - timedelta(days=1)).isoformat()
        else:
            match = re.search(r'(\d+)\s*(jour|jours|semaine|semaines|mois)', date_text)
            if match:
                number = int(match.group(1))
                unit = match.group(2)
                
                if 'jour' in unit:
                    return (today - timedelta(days=number)).isoformat()
                elif 'semaine' in unit:
                    return (today - timedelta(weeks=number)).isoformat()
                elif 'mois' in unit:
                    return (today - timedelta(days=number*30)).isoformat()
        
        return None
    
    def _extract_company_info(self, soup: BeautifulSoup) -> Dict:
        """Extract company information"""
        info = {}
        
        # Company size
        size_elem = soup.find('span', class_='company-size')
        if size_elem:
            info['company_size'] = self._clean_text(size_elem.text)
        
        # Industry
        industry_elem = soup.find('span', class_='company-industry')
        if industry_elem:
            info['industry'] = self._clean_text(industry_elem.text)
        
        # Company URL
        company_link = soup.find('a', class_='company-profile-link')
        if company_link:
            info['company_url'] = urljoin(self.base_url, company_link.get('href', ''))
        
        return info


# Register scraper with factory
ScraperFactory.register('hellowork', HelloWorkScraper)


if __name__ == '__main__':
    # Test the scraper
    logging.basicConfig(level=logging.INFO)
    
    scraper = HelloWorkScraper(
        search_query="data engineer",
        delay_min=2,
        delay_max=4
    )
    
    jobs = scraper.scrape_all(max_pages=2)
    print(f"\nScraped {len(jobs)} jobs")
    print(f"Stats: {scraper.get_stats()}")
    
    scraper.close()
