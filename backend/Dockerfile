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

# Worker count: keep at 1 on Render's free tier (512 MB RAM).
# Each gunicorn worker forks a full copy of the model in memory, so 2 workers
# can easily exceed 512 MB. Upgrade your Render plan before increasing this.
# Override at runtime: docker run -e WEB_CONCURRENCY=2 ...
ENV WEB_CONCURRENCY=1

# Run with gunicorn + uvicorn workers for production throughput
CMD ["sh", "-c", "gunicorn main:app -k uvicorn.workers.UvicornWorker --workers $WEB_CONCURRENCY --bind 0.0.0.0:8000 --timeout 120 --graceful-timeout 30"]
