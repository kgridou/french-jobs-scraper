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

## Impact on GitHub Actions

These fixes will allow the Pipeline Test workflow to:
✅ Pull all Docker images successfully
✅ Start all services without manifest errors
✅ Run the full integration test

## Commit

```bash
git add docker-compose.yml docs/DOCKER_COMPOSE_FIX.md
git commit -m "Fix docker-compose.yml: switch to Apache Spark image

- Remove obsolete version directive
- Switch from bitnami/spark to apache/spark:3.5.3
- Update Spark commands for official Apache image
- Avoid Spark 4.x for compatibility"
git push origin main
```
