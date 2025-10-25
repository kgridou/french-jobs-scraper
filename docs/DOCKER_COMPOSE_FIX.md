# docker-compose.yml Fixes

## Issues Fixed

### 1. Obsolete Version Directive
**Warning:**
```
the attribute `version` is obsolete, it will be ignored, please remove it to avoid potential confusion
```

**Fix:**
Removed `version: '3.8'` from the top of the file.

**Why:**
- Docker Compose V2 no longer requires or uses the version field
- Keeping it causes warnings and confusion
- Modern practice is to omit it

### 2. Spark Image Tag Not Found
**Error:**
```
manifest for bitnami/spark:3.5 not found: manifest unknown
manifest for bitnami/spark:3.5.1 not found: manifest unknown
manifest for bitnami/spark:3.5.3 not found: manifest unknown
```

**Fix:**
Switched from Bitnami to official Apache Spark image:
```yaml
# Before
image: bitnami/spark:3.5

# After
image: apache/spark:3.5.3
```

**Why:**
- Bitnami Spark tags were not accessible or don't exist in Docker Hub
- The official Apache Spark images (`apache/spark`) are more reliable
- Using `apache/spark:3.5.3` which is confirmed available
- Version 3.5.3 is used (avoiding version 4.x for compatibility)
- Updated environment variables and commands to match Apache Spark image requirements

## Updated docker-compose.yml Structure

```yaml
# No version field (removed)
x-airflow-common:
  &airflow-common
  build: .
  ...

services:
  postgres:
    image: postgres:15
    ...

  spark-master:
    image: apache/spark:3.5.3  # Fixed - using official Apache image
    command: /opt/spark/bin/spark-class org.apache.spark.deploy.master.Master
    ...

  spark-worker:
    image: apache/spark:3.5.3  # Fixed - using official Apache image
    command: /opt/spark/bin/spark-class org.apache.spark.deploy.worker.Worker spark://spark-master:7077
    ...
```

## Verification

Test the config:
```bash
docker compose config
```

Should show no warnings or errors.

### 3. Missing Airflow Providers
**Error:**
```
ModuleNotFoundError: No module named 'airflow.providers.apache'
```

**Fix:**
Uncommented Airflow provider packages in requirements.txt:
```python
# Before (commented out)
# apache-airflow-providers-postgres==5.10.0
# apache-airflow-providers-apache-spark==4.7.0

# After (active)
apache-airflow-providers-postgres==5.10.0
apache-airflow-providers-apache-spark==4.7.0
```

**Why:**
- The DAG uses SparkSubmitOperator which requires the Apache Spark provider
- PostgreSQL operator also needs the Postgres provider
- These were commented out assuming they were in the base image, but they need to be explicitly installed

### 4. Missing Scrapers Directory
**Fix:**
Added scrapers directory to Dockerfile:
```dockerfile
COPY --chown=airflow:root ./scrapers /opt/airflow/scrapers
```

**Why:**
- The DAG imports scraper classes from the `scrapers/` directory
- Without copying this directory, imports fail at runtime

### 5. Missing Java for Spark
**Error:**
```
JAVA_HOME is not set
```

**Fix:**
Added Java installation to Dockerfile:
```dockerfile
# Install Java for Spark
RUN apt-get install -y openjdk-17-jdk-headless procps

# Set JAVA_HOME
ENV JAVA_HOME=/usr/lib/jvm/java-17-openjdk-amd64
ENV PATH=$PATH:$JAVA_HOME/bin
```

**Why:**
- PySpark requires Java to run
- The `SparkSubmitOperator` needs Java to execute spark-submit commands
- Also installed `procps` for ps command needed by Spark

## Impact on GitHub Actions

These fixes will allow the Pipeline Test workflow to:
✅ Pull all Docker images successfully
✅ Start all services without manifest errors
✅ Load DAGs without import errors
✅ Run the full integration test

## Commit

```bash
git add docker-compose.yml Dockerfile requirements.txt docs/DOCKER_COMPOSE_FIX.md
git commit -m "Fix Docker and Airflow configuration

- Remove obsolete version directive from docker-compose.yml
- Switch from bitnami/spark to apache/spark:3.5.3
- Add Airflow providers (apache-spark, postgres) to requirements.txt
- Copy scrapers directory in Dockerfile
- Update Spark commands for official Apache image"
git push origin main
```
