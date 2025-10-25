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
```

**Fix:**
Changed Spark image tags:
```yaml
# Before
image: bitnami/spark:3.5

# After  
image: bitnami/spark:3.5.1
```

**Why:**
- The `bitnami/spark:3.5` tag doesn't exist in Docker Hub
- Available versions are like 3.5.1, 3.5.0, etc.
- This prevents the "manifest unknown" error

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
    image: bitnami/spark:3.5.1  # Fixed
    ...

  spark-worker:
    image: bitnami/spark:3.5.1  # Fixed
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
git add docker-compose.yml
git commit -m "Fix docker-compose.yml

- Remove obsolete version directive
- Fix Spark image tag (3.5 → 3.5.1)"
git push origin main
```
