FROM apache/airflow:2.8.0-python3.11

USER root

# Install system dependencies
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    gcc \
    g++ \
    build-essential \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

USER airflow

# Copy requirements file
COPY requirements.txt /requirements.txt

# Install Python dependencies
RUN pip install --no-cache-dir --user -r /requirements.txt

# Copy application files
COPY --chown=airflow:root ./dags /opt/airflow/dags
COPY --chown=airflow:root ./scripts /opt/airflow/scripts
COPY --chown=airflow:root ./config /opt/airflow/config
