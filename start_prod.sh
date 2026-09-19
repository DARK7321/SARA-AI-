#!/bin/sh
set -e

echo "Starting Sara Background Worker..."
arq apps.worker.main.WorkerSettings &

echo "Starting Sara FastAPI Core on port ${PORT:-8000}..."
exec uvicorn apps.api.main:app --host 0.0.0.0 --port ${PORT:-8000}

