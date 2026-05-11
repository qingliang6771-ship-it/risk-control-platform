#!/bin/bash
set -e

# Remove default nginx config
rm -f /etc/nginx/sites-enabled/default

# Start nginx in background
nginx -g "daemon on;"

# Start FastAPI backend
cd /app/backend
exec uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 2
