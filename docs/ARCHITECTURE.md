# Architecture Documentation

## System Architecture

The French Job Scraper is a modern data engineering pipeline built on a microservices architecture using Docker containers.

```
┌─────────────────────────────────────────────────────────────┐
│                     ORCHESTRATION LAYER                     │
│                    Apache Airflow 2.8                       │
│  ┌──────────┐  ┌────────────┐  ┌─────────────────────┐    │
│  │ Scheduler│  │ Webserver  │  │  DAG Definitions    │    │
│  └──────────┘  └────────────┘  └─────────────────────┘    │
└─────────────────────────────────────────────────────────────┘
                            │
                            ├──────────┬──────────┬──────────┐
                            ▼          ▼          ▼          ▼
                    ┌──────────┐ ┌─────────┐ ┌────────┐ ┌──────────┐
                    │ Scraping │ │ Pandas  │ │ Spark  │ │ Quality  │
                    │  Task    │ │ Process │ │ Process│ │  Check   │
                    └──────────┘ └─────────┘ └────────┘ └──────────┘
                            │          │          │          │
                            └──────────┼──────────┼──────────┘
                                      ▼          ▼
┌─────────────────────────────────────────────────────────────┐
│                      STORAGE LAYER                          │
│                    PostgreSQL 15                            │
│  ┌──────────┐  ┌────────────┐  ┌─────────────────────┐    │
│  │ Raw Jobs │  │ Cleaned    │  │  Analytics          │    │
│  │  Table   │  │ Jobs Table │  │  Tables             │    │
│  └──────────┘  └────────────┘  └─────────────────────┘    │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│                   PROCESSING LAYER                          │
│              Apache Spark 3.5 Cluster                       │
│  ┌──────────┐  ┌────────────┐  ┌─────────────────────┐    │
│  │  Master  │  │  Worker    │  │  Distributed        │    │
│  │   Node   │  │   Nodes    │  │  Computing          │    │
│  └──────────┘  └────────────┘  └─────────────────────┘    │
└─────────────────────────────────────────────────────────────┘
```

## Component Details

### 1. Apache Airflow (Orchestration)

**Purpose**: Workflow orchestration and scheduling

**Components**:
- **Webserver**: UI for monitoring and managing workflows (Port 8080)
- **Scheduler**: Triggers tasks based on schedules and dependencies
- **Database**: PostgreSQL backend for metadata storage

**Responsibilities**:
- Schedule daily scraping jobs
- Manage task dependencies
- Retry failed tasks
- Monitor pipeline health
- Generate execution reports

### 2. PostgreSQL (Data Storage)

**Purpose**: Persistent data storage and querying

**Databases**:
- `airflow`: Airflow metadata
- `jobs_db`: Job postings data

**Schema Design**:
```
raw_jobs (fact table)
  ├─ Scraped job postings
  └─ Source, URL, timestamps

cleaned_jobs (fact table)
  ├─ Processed job data
  ├─ Foreign keys to dimensions
  └─ Extracted features

companies (dimension)
  └─ Company master data

locations (dimension)
  └─ Geographic information

job_analytics (aggregated)
  └─ Pre-computed statistics

salary_trends (time-series)
  └─ Historical salary data
```

### 3. Apache Spark (Distributed Processing)

**Purpose**: Large-scale data processing and analytics

**Components**:
- **Master Node**: Cluster coordinator (Port 8081)
- **Worker Nodes**: Computation executors
- **Driver**: Application orchestrator

**Responsibilities**:
- Aggregate job statistics
- Calculate salary trends
- Perform text analysis
- Generate analytics tables

### 4. Python Scripts (Data Processing)

**scraper.py**:
- Web scraping with BeautifulSoup
- Rate limiting and error handling
- Multiple source support
- Database persistence

**pandas_processor.py**:
- Data cleaning and validation
- Feature extraction
- Text processing
- Categorical classification

**spark_processor.py**:
- Distributed aggregations
- Time-series analysis
- Market insights
- Analytics generation

## Data Flow

### 1. Ingestion Phase
```
Web Sources → HTTP Requests → BeautifulSoup Parser → raw_jobs table
                    ↓
              Rate Limiting
              User-Agent Rotation
              Error Handling
```

### 2. Processing Phase
```
raw_jobs → Pandas → Data Cleaning → Feature Extraction → cleaned_jobs
                         ↓
                   Standardization
                   Categorization
                   Enrichment
```

### 3. Analytics Phase
```
cleaned_jobs → Spark → Aggregations → Analytics Tables
                         ↓
                   Distributed Computing
                   Statistical Analysis
                   Trend Detection
```

## Technology Stack

| Layer | Technology | Version | Purpose |
|-------|-----------|---------|---------|
| Orchestration | Apache Airflow | 2.8 | Workflow management |
| Processing | Apache Spark | 3.5 | Distributed computing |
| Database | PostgreSQL | 15 | Data storage |
| Data Processing | Pandas | 2.1.4 | Data manipulation |
| Web Scraping | BeautifulSoup4 | 4.12.2 | HTML parsing |
| HTTP | Requests | 2.31.0 | Web requests |
| Containerization | Docker | 20.10+ | Environment isolation |
| Orchestration | Docker Compose | 2.0+ | Multi-container apps |

## Scalability Considerations

### Horizontal Scaling
- **Add Spark Workers**: Increase parallelism for data processing
- **Add Airflow Workers**: Use CeleryExecutor for distributed task execution
- **Database Replication**: Read replicas for query performance

### Vertical Scaling
- Increase memory for Spark workers
- Allocate more CPU cores
- Expand PostgreSQL storage

### Performance Optimization
- Partition large tables by date
- Add database indexes on query columns
- Cache frequently accessed data
- Batch database operations
- Use connection pooling

## Security Considerations

### Network Security
- Services communicate via Docker network
- No external exposure except web UIs
- Database credentials via environment variables

### Data Security
- SQL injection prevention via parameterized queries
- Input validation and sanitization
- Regular security updates

### Access Control
- Airflow authentication required
- Database user permissions
- Read-only analytics views

## Monitoring and Observability

### Logs
- Application logs in `/logs` directory
- Airflow task logs in UI
- Spark job logs in Master UI

### Metrics
- Job success/failure rates
- Processing duration
- Data quality metrics
- Resource utilization

### Alerting
- Airflow task failure notifications
- Data quality threshold alerts
- Disk space monitoring

## Maintenance

### Daily Operations
- Monitor Airflow DAG runs
- Check data quality metrics
- Review scraping success rates

### Weekly Tasks
- Review storage usage
- Analyze pipeline performance
- Update scraping configurations

### Monthly Tasks
- Database maintenance (VACUUM, ANALYZE)
- Review and update dependencies
- Backup critical data
- Performance tuning

## Future Enhancements

### Potential Improvements
1. **Real-time Processing**: Implement Kafka for streaming
2. **Machine Learning**: Job categorization models
3. **API Layer**: REST API for data access
4. **Visualization**: Integrate Superset or Metabase
5. **Multi-language**: Support for other European languages
6. **NLP Analysis**: Job description text analysis
7. **Alerting**: Job market change notifications
8. **Data Quality**: Automated data validation framework

## Troubleshooting

### Common Issues

**Airflow Tasks Failing**:
- Check logs in Airflow UI
- Verify database connectivity
- Review Python script errors

**Spark Job Slow**:
- Increase worker memory
- Add more workers
- Optimize data partitioning

**Database Connection Issues**:
- Verify PostgreSQL is running
- Check connection parameters
- Review network connectivity

**Scraping Failures**:
- Check website structure changes
- Verify rate limits not exceeded
- Review error logs

## References

- [Apache Airflow Documentation](https://airflow.apache.org/docs/)
- [Apache Spark Documentation](https://spark.apache.org/docs/latest/)
- [PostgreSQL Documentation](https://www.postgresql.org/docs/)
- [Docker Documentation](https://docs.docker.com/)
