# ============================================================
# WatchTower Backend — Dockerfile
# ============================================================
FROM python:3.11-slim

WORKDIR /app

# Install system dependencies for numpy/pandas + curl (used by healthcheck)
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc g++ curl \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies first (layer caching)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy source
COPY . .

# Expose the API port
EXPOSE 8000

# IMPORTANT: Keep workers=1 on Render's free tier (512 MB RAM limit).
# Each gunicorn worker is a separate OS process that loads a full copy of the
# TF-IDF model + DataFrames into memory (~200–250 MB). Two workers = OOM.
# To scale up, upgrade your Render plan and change --workers below.
CMD ["gunicorn", "main:app", "-k", "uvicorn.workers.UvicornWorker", "--workers", "1", "--bind", "0.0.0.0:8000", "--timeout", "120", "--graceful-timeout", "30"]
