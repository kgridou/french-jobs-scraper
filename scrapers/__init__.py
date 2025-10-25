"""
French Jobs Scrapers Package
Web scrapers for French job boards
"""

from scrapers.base_scraper import BaseScraper, ScraperFactory
from scrapers.indeed_scraper import IndeedScraper
from scrapers.hellowork_scraper import HelloWorkScraper

__all__ = [
    'BaseScraper',
    'ScraperFactory',
    'IndeedScraper',
    'HelloWorkScraper',
]

__version__ = '1.0.0'
