# French Job Postings Data Engineering Pipeline

A production-ready, Docker-based data engineering portfolio project that demonstrates web scraping, data processing, and workflow orchestration for French job market analysis.

## 🎯 Project Overview

This project scrapes job postings from French job boards (Indeed.fr, LinkedIn), processes the data using Pandas and PySpark, and orchestrates the entire pipeline with Apache Airflow. The system stores structured data in PostgreSQL and provides analytics-ready datasets.

## 🏗️ Architecture

```
Web Scraping → Raw Data Storage → Data Processing → Analytics Database
    (Python)      (PostgreSQL)      (Pandas/PySpark)    (PostgreSQL)
                         ↑
                    Orchestration
                     (Airflow)
```

## 🚀 Features

- **Web Scraping**: Ethical scraping of French job postings with rate limiting
- **Data Processing**: ETL pipeline using Pandas for small datasets and PySpark for large-scale processing
- **Workflow Orchestration**: Automated daily scraping and processing with Airflow
- **Data Storage**: PostgreSQL database with normalized schema
- **Monitoring**: Airflow UI for pipeline monitoring and job status
- **Dockerized**: Fully containerized for easy deployment

## 📋 Prerequisites

- Docker & Docker Compose
- 4GB+ RAM available
- Internet connection

## 🔧 Quick Start

1. **Clone and navigate to project**:
```bash
cd french-jobs-scraper
```

2. **Start the entire stack**:
```bash
docker compose up -d
```

3. **Wait for services to initialize** (30-60 seconds):
```bash
docker compose logs -f airflow-init
```

4. **Access services**:
- Airflow UI: http://localhost:8080 (username: `airflow`, password: `airflow`)
- Spark Master UI: http://localhost:8081
- PostgreSQL: localhost:5432 (user: `airflow`, password: `airflow`, db: `jobs_db`)

5. **Trigger the pipeline to get data**:
- Navigate to Airflow UI → http://localhost:8080
- Find the `french_jobs_pipeline` DAG
- Toggle it ON to enable
- Click the ▶️ Play button to trigger manually
- **See [RUNNING_THE_SCRAPER.md](docs/RUNNING_THE_SCRAPER.md) for detailed instructions**

## 📂 Project Structure

```
french-jobs-scraper/
├── dags/                             # Airflow DAG definitions
│   └── french_jobs_pipeline.py
├── scrapers/                         # Web scraper implementations
│   ├── base_scraper.py
│   ├── indeed_scraper.py
│   └── hellowork_scraper.py
├── scripts/                          # Data processing and utility scripts
│   ├── scraper.py
│   ├── pandas_processor.py
│   ├── spark_processor.py
│   ├── enrich_jobs.py
│   └── shell/                        # Shell scripts
│       ├── start.sh
│       ├── stop.sh
│       └── cleanup.sh
├── sql/                              # Database schema and queries
│   ├── init.sql
│   ├── sample_queries.sql
│   └── analytics_queries.sql
├── config/                           # Configuration files
│   └── scraper_config.yaml
├── docs/                             # Additional documentation
│   ├── ARCHITECTURE.md
│   ├── QUICKSTART.md
│   └── ...
├── data/                             # Data storage (gitignored)
│   ├── raw/
│   ├── processed/
│   └── analytics/
├── docker-compose.yml                # Docker services orchestration
├── Dockerfile                        # Custom Airflow image
├── requirements.txt                  # Python dependencies
└── README.md                         # This file
```

## 🔍 Data Pipeline Details

### Stage 1: Web Scraping
- Scrapes Indeed.fr and LinkedIn France
- Extracts: job title, company, location, salary, description, posting date
- Implements rate limiting and user-agent rotation
- Handles French language and special characters

### Stage 2: Data Cleaning (Pandas)
- Removes duplicates
- Standardizes location names
- Parses salary ranges
- Extracts job categories
- Handles missing values

### Stage 3: Data Processing (PySpark)
- Aggregates job statistics by location and category
- Calculates salary trends
- Performs text analysis on job descriptions
- Creates analytics tables

### Stage 4: Storage
- Normalized database schema
- Fact and dimension tables
- Indexes for query performance

## 📊 Database Schema

```sql
raw_jobs:           Scraped job postings (raw data)
cleaned_jobs:       Processed job data
job_categories:     Dimension table for categories
locations:          Dimension table for locations
companies:          Dimension table for companies
job_analytics:      Aggregated statistics
salary_trends:      Salary analysis by role/location
```

## 🛠️ Technologies Used

- **Python 3.11**: Core programming language
- **Apache Airflow 2.8**: Workflow orchestration
- **Apache Spark 3.5.3**: Large-scale data processing
- **Pandas**: Data manipulation and analysis
- **BeautifulSoup4 & Requests**: Web scraping
- **PostgreSQL 15**: Data storage
- **Docker & Docker Compose**: Containerization

## 📈 Usage Examples

### Query Recent Jobs
```sql
SELECT title, company, location, salary_min, salary_max
FROM cleaned_jobs
WHERE posting_date >= CURRENT_DATE - INTERVAL '7 days'
ORDER BY posting_date DESC;
```

### Analyze Salary by City
```sql
SELECT location, AVG(salary_avg) as avg_salary, COUNT(*) as job_count
FROM job_analytics
GROUP BY location
ORDER BY avg_salary DESC;
```

### Top Hiring Companies
```sql
SELECT company, COUNT(*) as job_count
FROM cleaned_jobs
WHERE posting_date >= CURRENT_DATE - INTERVAL '30 days'
GROUP BY company
ORDER BY job_count DESC
LIMIT 10;
```

## 🔐 Configuration

Edit `config/scraper_config.yaml` to customize:
- Target job sites
- Search keywords
- Geographic filters
- Scraping frequency
- Data retention policies

## 🐛 Troubleshooting

**Airflow webserver not starting**:
```bash
docker compose logs airflow-webserver
docker compose restart airflow-webserver
```

**Database connection issues**:
```bash
docker compose exec postgres psql -U airflow -d jobs_db
```

**Check Spark jobs**:
Visit http://localhost:8081 for Spark Master UI

## 📚 Documentation

Additional documentation is available in the `docs/` directory:
- **[RUNNING_THE_SCRAPER.md](docs/RUNNING_THE_SCRAPER.md)** - 🚀 **How to actually run the scraper and get data**
- **[QUICKSTART.md](docs/QUICKSTART.md)** - Detailed step-by-step setup guide
- **[ARCHITECTURE.md](docs/ARCHITECTURE.md)** - System architecture and design
- **[CI_CD.md](docs/CI_CD.md)** - CI/CD pipeline with GitHub Actions
- **[DOCKER_COMPOSE_FIX.md](docs/DOCKER_COMPOSE_FIX.md)** - Docker Compose fixes and troubleshooting
- **[STRUCTURE.md](docs/STRUCTURE.md)** - Complete project structure details
- **[PROJECT_SUMMARY.md](docs/PROJECT_SUMMARY.md)** - Project overview and features

For AI-assisted development, see **[CLAUDE.md](CLAUDE.md)** in the root directory.

## 🔄 CI/CD

This project includes comprehensive GitHub Actions workflows:

- **CI Pipeline** - Linting, testing, security scanning
- **Pipeline Integration Test** - Full end-to-end testing with actual services (dogfooding 🐕)
- **Docker Build** - Automated container image builds and publishing

See [docs/CI_CD.md](docs/CI_CD.md) for details.

## 📝 Development

To add new scrapers or processors:

1. Create new scraper in `scrapers/` inheriting from `base_scraper.py`
2. Add processing scripts in `scripts/`
3. Update Airflow DAG in `dags/french_jobs_pipeline.py`
4. Rebuild containers: `docker compose up -d --build`

## 🤝 Portfolio Showcase

This project demonstrates:
- Modern data engineering practices
- ETL pipeline design
- Workflow orchestration
- Containerization
- Python best practices
- Data modeling
- Distributed computing with Spark

## ⚖️ Legal & Ethics

This project is for educational and portfolio purposes. When scraping:
- Respect robots.txt
- Implement rate limiting
- Don't overload servers
- Follow terms of service
- Consider using official APIs when available

## 📄 License

MIT License - Feel free to use for learning and portfolio purposes.
