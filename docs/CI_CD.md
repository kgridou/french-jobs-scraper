# CI/CD Pipeline Documentation

This document describes the Continuous Integration and Continuous Deployment (CI/CD) setup for the French Jobs Scraper project using GitHub Actions.

## Overview

The project uses three simplified, working GitHub Actions workflows:

1. **CI** - File validation, syntax checking, and Docker builds
2. **Pipeline Test** - Integration testing (manual trigger recommended)
3. **Docker** - Container image building and publishing to GitHub Container Registry

**Status:** ✅ Workflows are configured to run reliably without external dependencies

## Workflows

### 1. CI Workflow (`.github/workflows/ci.yml`)

**Trigger:** Push or Pull Request to `main` branch

**Jobs:**

#### Lint
- Runs Black (code formatting check)
- Runs Flake8 (Python linting)
- Checks Python syntax errors

#### Test
- Runs pytest with coverage
- Uploads coverage reports to Codecov
- Tests are in `tests/` directory

#### Validate Config
- Validates YAML files (scraper_config.yaml, docker-compose.yml)
- Checks SQL file syntax

#### Docker Build
- Builds Airflow Docker image
- Smoke tests the image
- Validates docker-compose configuration

#### Security Scan
- Runs Safety check for vulnerable dependencies
- Runs Bandit security scanner on Python code
- Uploads security reports as artifacts

**Example:**
```yaml
on:
  push:
    branches: [ main ]
  pull_request:
    branches: [ main ]
```

### 2. Pipeline Integration Test (`.github/workflows/pipeline-test.yml`)

**Trigger:**
- Push or Pull Request to `main` branch
- Weekly schedule (Monday 6 AM UTC)
- Manual trigger (workflow_dispatch)

**Jobs:**

#### Test Pipeline (Dogfooding 🐕)
- Starts full Docker Compose stack
- Waits for all services (PostgreSQL, Airflow, Spark)
- Verifies database schema
- Lists and validates Airflow DAGs
- Tests scraper execution
- Triggers DAG dry run
- Collects logs on failure

**Key Features:**
- Full integration testing with actual services
- 30-minute timeout for complete pipeline test
- Service health checks with timeouts
- Comprehensive logging on failure

#### Test Scripts
- Tests individual Python script imports
- Validates configuration loading
- Checks Python syntax of all files

**Example Service Check:**
```bash
# Wait for PostgreSQL
while ! docker-compose exec -T postgres pg_isready -U airflow; do
  echo "Waiting for PostgreSQL..."
  sleep 2
done
```

### 3. Docker Build and Push (`.github/workflows/docker-publish.yml`)

**Trigger:**
- Push to `main` branch
- Git tags matching `v*.*.*`
- Pull Requests to `main`
- Manual trigger

**Jobs:**

#### Build and Push
- Builds Docker image with Buildx
- Pushes to GitHub Container Registry (ghcr.io)
- Uses layer caching for faster builds
- Scans for vulnerabilities with Trivy
- Uploads security results to GitHub Security

**Image Tags:**
- `main` - Latest from main branch
- `v1.0.0` - Semantic version tags
- `sha-abc123` - Git commit SHA tags
- `pr-123` - Pull request tags

**Registry:**
```
ghcr.io/your-username/french-jobs-scraper/airflow:main
ghcr.io/your-username/french-jobs-scraper/airflow:v1.0.0
```

## Running Workflows Locally

### Test Linting Locally
```bash
# Install dev dependencies
pip install black flake8 pylint

# Run Black
black --check scrapers/ scripts/ dags/

# Run Flake8
flake8 scrapers/ scripts/ dags/ --max-line-length=127
```

### Test Docker Build Locally
```bash
# Build image
docker build -f Dockerfile -t french-jobs-scraper:test .

# Test image
docker run --rm french-jobs-scraper:test python --version
docker run --rm french-jobs-scraper:test airflow version

# Validate docker-compose
docker-compose config
```

### Run Tests Locally
```bash
# Install test dependencies
pip install pytest pytest-cov pytest-mock

# Run tests
pytest tests/ -v --cov=scrapers --cov=scripts
```

### Full Pipeline Test Locally
```bash
# Use the shell script
scripts/shell/start.sh

# Or manually
docker-compose up -d
docker-compose exec airflow-webserver airflow dags list
docker-compose exec postgres psql -U airflow -d jobs_db -c "\dt"
```

## GitHub Actions Setup

### Required Secrets

No secrets are required for basic CI/CD. Optional secrets:

- `CODECOV_TOKEN` - For code coverage reporting (optional)
- `GITHUB_TOKEN` - Automatically provided by GitHub

### Enabling Workflows

1. Push the `.github/workflows/` directory to your repository
2. Go to GitHub → Actions tab
3. Workflows will run automatically on push/PR
4. Manual runs: Actions → Select workflow → Run workflow

## Status Badges

Add these to your README.md:

```markdown
![CI](https://github.com/your-username/french-jobs-scraper/workflows/CI%20-%20Continuous%20Integration/badge.svg)
![Pipeline Test](https://github.com/your-username/french-jobs-scraper/workflows/Pipeline%20Integration%20Test/badge.svg)
![Docker](https://github.com/your-username/french-jobs-scraper/workflows/Docker%20Build%20and%20Push/badge.svg)
```

## Best Practices

### 1. Dogfooding Strategy
- The pipeline tests actually run the scraper and DAGs
- Uses the same docker-compose.yml as production
- Validates real service integrations

### 2. Fail Fast
- Syntax and linting checks run first
- Quick feedback on code quality issues
- Full integration tests run last

### 3. Caching
- pip dependencies cached by GitHub Actions
- Docker layer caching enabled
- Speeds up CI/CD runs

### 4. Security
- Dependency vulnerability scanning
- Code security analysis with Bandit
- Container image scanning with Trivy

### 5. Comprehensive Logging
- Logs captured on failure
- Service status displayed
- Easy debugging of CI issues

## Troubleshooting

### Workflow Failures

**Linting Failures:**
```bash
# Fix locally before pushing
black scrapers/ scripts/ dags/
flake8 scrapers/ scripts/ dags/ --max-line-length=127
```

**Docker Build Failures:**
```bash
# Test locally
docker build -f Dockerfile .
docker-compose config
```

**Pipeline Test Failures:**
- Check service logs in GitHub Actions artifacts
- Ensure docker-compose.yml is valid
- Verify all required files exist

**Security Scan Warnings:**
- Review Bandit report in artifacts
- Update vulnerable dependencies
- Fix security issues before merging

### Common Issues

1. **Timeout in service startup**
   - Increase timeout values in workflow
   - Check resource limits

2. **Import errors in tests**
   - Verify all dependencies in requirements.txt
   - Check Python path configuration

3. **Docker image too large**
   - Use .dockerignore
   - Multi-stage builds
   - Remove unnecessary files

## Maintenance

### Weekly Tasks
- Review security scan reports
- Update dependencies
- Check workflow run times

### Monthly Tasks
- Update GitHub Actions versions
- Review and optimize caching
- Clean up old Docker images

## Future Enhancements

Potential improvements:
- [ ] Add performance benchmarking
- [ ] Implement canary deployments
- [ ] Add E2E tests with real scraping
- [ ] Set up staging environment
- [ ] Add Slack/Discord notifications
- [ ] Implement blue/green deployments
- [ ] Add more comprehensive test coverage
- [ ] Set up automated dependency updates (Dependabot)

## Resources

- [GitHub Actions Documentation](https://docs.github.com/en/actions)
- [Docker Build Push Action](https://github.com/docker/build-push-action)
- [GitHub Container Registry](https://docs.github.com/en/packages/working-with-a-github-packages-registry/working-with-the-container-registry)
