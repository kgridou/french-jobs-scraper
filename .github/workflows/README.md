# GitHub Actions Workflows

## Workflows

### CI (`ci.yml`)
**Runs on:** Push and PR to `main`

**What it does:**
1. Validates Python syntax for all `.py` files
2. Validates YAML configuration files
3. Checks that required files exist
4. Builds Docker image
5. Tests Docker image runs correctly
6. Validates docker-compose configuration

**Duration:** ~3-5 minutes

### Pipeline Test (`pipeline-test.yml`)
**Runs on:** Manual trigger or weekly (Monday 6 AM UTC)

**What it does:**
1. Starts full docker-compose stack
2. Waits for PostgreSQL to be ready
3. Waits for Airflow to be ready
4. Lists DAGs
5. Checks for import errors
6. Collects logs on failure

**Duration:** ~8-12 minutes

**Note:** This is resource-intensive. Run manually to test integration.

### Docker (`docker-publish.yml`)
**Runs on:** Push to `main`, version tags, manual trigger

**What it does:**
1. Builds Docker image with Buildx
2. Publishes to GitHub Container Registry (ghcr.io)
3. Tags: main, version (if tagged), SHA

**Duration:** ~4-6 minutes

## Running Workflows

### Automatic
Workflows run automatically on push to `main` branch.

### Manual
1. Go to Actions tab
2. Select workflow
3. Click "Run workflow"
4. Choose branch
5. Click "Run workflow" button

## Troubleshooting

### CI fails on "Check Python syntax"
- Run locally: `python -m py_compile dags/*.py scrapers/*.py scripts/*.py`
- Fix syntax errors before pushing

### Docker build fails
- Test locally: `docker build -f Dockerfile -t test .`
- Check Dockerfile for errors

### Pipeline test times out
- Increase timeout in workflow (default: 20 minutes)
- Check service health locally with `docker-compose up`

## Local Testing

Before pushing, test locally:

```bash
# Python syntax
python -m py_compile dags/*.py scrapers/*.py scripts/*.py

# YAML validation
python -c "import yaml; yaml.safe_load(open('config/scraper_config.yaml'))"
python -c "import yaml; yaml.safe_load(open('docker-compose.yml'))"

# Docker build
docker build -f Dockerfile -t test .

# docker-compose validation
docker-compose config
```

## Workflow Status

Check workflow status:
- Repository → Actions tab
- Or add badges to README.md:

```markdown
![CI](https://github.com/kgridou/french-jobs-scraper/workflows/CI/badge.svg)
![Pipeline Test](https://github.com/kgridou/french-jobs-scraper/workflows/Pipeline%20Test/badge.svg)
![Docker](https://github.com/kgridou/french-jobs-scraper/workflows/Docker/badge.svg)
```
