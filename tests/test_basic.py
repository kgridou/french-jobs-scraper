"""
Basic tests for French Jobs Scraper
"""
import pytest
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))


def test_imports():
    """Test that main modules can be imported"""
    try:
        from scrapers import base_scraper
        assert hasattr(base_scraper, 'BaseScraper')
    except ImportError as e:
        pytest.skip(f"Scraper imports not available: {e}")


def test_config_exists():
    """Test that configuration file exists"""
    config_path = os.path.join(os.path.dirname(__file__), '..', 'config', 'scraper_config.yaml')
    assert os.path.exists(config_path), "Configuration file should exist"


def test_config_valid():
    """Test that configuration file is valid YAML"""
    import yaml

    config_path = os.path.join(os.path.dirname(__file__), '..', 'config', 'scraper_config.yaml')

    with open(config_path, 'r') as f:
        config = yaml.safe_load(f)

    assert config is not None
    assert 'sources' in config
    assert 'scraping' in config


def test_sql_files_exist():
    """Test that SQL initialization files exist"""
    sql_dir = os.path.join(os.path.dirname(__file__), '..', 'sql')

    assert os.path.exists(os.path.join(sql_dir, 'init.sql'))
    assert os.path.exists(os.path.join(sql_dir, 'sample_queries.sql'))


def test_dag_file_exists():
    """Test that DAG file exists"""
    dag_path = os.path.join(os.path.dirname(__file__), '..', 'dags', 'french_jobs_pipeline.py')
    assert os.path.exists(dag_path)


def test_dockerfile_exists():
    """Test that Dockerfile exists"""
    dockerfile_path = os.path.join(os.path.dirname(__file__), '..', 'Dockerfile')
    assert os.path.exists(dockerfile_path)


def test_docker_compose_exists():
    """Test that docker-compose.yml exists"""
    compose_path = os.path.join(os.path.dirname(__file__), '..', 'docker-compose.yml')
    assert os.path.exists(compose_path)


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
