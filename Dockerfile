FROM apache/airflow:2.8.0-python3.11

USER root

# Install system dependencies including Java for Spark
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    gcc \
    g++ \
    build-essential \
    openjdk-17-jdk-headless \
    procps \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Set JAVA_HOME
ENV JAVA_HOME=/usr/lib/jvm/java-17-openjdk-amd64
ENV PATH=$PATH:$JAVA_HOME/bin

USER airflow

# Copy requirements file
COPY requirements.txt /requirements.txt

# Install Python dependencies
RUN pip install --no-cache-dir --user -r /requirements.txt

# Copy application files
COPY --chown=airflow:root ./dags /opt/airflow/dags
COPY --chown=airflow:root ./scripts /opt/airflow/scripts
COPY --chown=airflow:root ./scrapers /opt/airflow/scrapers
COPY --chown=airflow:root ./config /opt/airflow/config
