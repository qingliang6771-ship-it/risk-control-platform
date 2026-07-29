#!/bin/bash
set -e

# Remove default nginx config
rm -f /etc/nginx/sites-enabled/default

# Start nginx in background
nginx -g "daemon on;"

# Start FastAPI backend
cd /app/backend

# 确保数据库与数据目录存在（对应 docker 持久化卷）
mkdir -p /app/backend/db /app/backend/data

# 自动执行数据库迁移（为旧库补齐权限相关列，新库幂等无副作用）

echo "🔧 running db migration..."
python migrate_add_permissions.py || echo "⚠️ migration skipped/failed, continuing..."

exec uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 1
