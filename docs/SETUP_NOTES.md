# Setup Notes

## PostgreSQL JDBC Driver for Spark

The Spark processor requires the PostgreSQL JDBC driver to connect to the database. The driver is referenced in the Spark submit command but needs to be available in the Spark environment.

### Option 1: Download Manually (Recommended for Production)

Download the PostgreSQL JDBC driver and place it in the Spark jars directory:

```bash
# From your host machine
wget https://jdbc.postgresql.org/download/postgresql-42.7.0.jar -O postgresql-42.7.0.jar

# Copy to a location accessible by Spark
# This will be mounted when you start the containers
```

### Option 2: Pre-configured in Docker Image

You can modify the `docker-compose.yml` to download the driver at startup:

```yaml
spark-master:
  image: bitnami/spark:3.5
  entrypoint: >
    bash -c "
    cd /opt/bitnami/spark/jars &&
    [ ! -f postgresql-42.7.0.jar ] && 
    wget -q https://jdbc.postgresql.org/download/postgresql-42.7.0.jar || true &&
    /opt/bitnami/scripts/spark/entrypoint.sh /opt/bitnami/scripts/spark/run.sh
    "
```

### Option 3: Use Package from Maven

Modify the Spark submit command in the DAG to use packages:

```python
--packages org.postgresql:postgresql:42.7.0
```

## Current Implementation

The current implementation assumes the JDBC driver is available in the default Spark classpath. For a fully production-ready setup, implement Option 1 or 2 above.

## Testing Spark Connectivity

To test if Spark can connect to PostgreSQL:

```bash
# Access Spark master container
docker exec -it $(docker ps -qf "name=spark-master") bash

# Run a simple PySpark test
pyspark --packages org.postgresql:postgresql:42.7.0
```

Then in PySpark shell:
```python
from pyspark.sql import SparkSession

spark = SparkSession.builder.appName("test").getOrCreate()

df = spark.read.format("jdbc") \
    .option("url", "jdbc:postgresql://postgres:5432/jobs_db") \
    .option("dbtable", "cleaned_jobs") \
    .option("user", "airflow") \
    .option("password", "airflow") \
    .option("driver", "org.postgresql.Driver") \
    .load()

df.show()
```

## Alternative: Use CSV Files

If JDBC connectivity is challenging, you can modify the pipeline to use CSV files:

1. Export from PostgreSQL to CSV
2. Process with Spark using CSV reader
3. Write results back to CSV
4. Import CSV to PostgreSQL

This is less efficient but avoids JDBC dependencies.
