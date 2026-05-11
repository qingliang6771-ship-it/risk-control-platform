#!/bin/bash
# ============================================
# 风控后台一键部署脚本
# 在服务器上执行此脚本
# ============================================

set -e

echo "🚀 开始部署风控后台..."

# 1. 安装 Docker（如果没有）
if ! command -v docker &> /dev/null; then
    echo "📦 安装 Docker..."
    curl -fsSL https://get.docker.com | sh
    sudo usermod -aG docker $USER
    echo "Docker 安装完成"
fi

if ! command -v docker-compose &> /dev/null && ! docker compose version &> /dev/null; then
    echo "📦 安装 Docker Compose..."
    sudo apt-get update && sudo apt-get install -y docker-compose-plugin
fi

# 2. 创建项目目录
PROJECT_DIR=/opt/risk-control-platform
sudo mkdir -p $PROJECT_DIR
sudo chown $USER:$USER $PROJECT_DIR
cd $PROJECT_DIR

echo "📁 创建项目结构..."

# 3. 创建目录结构
mkdir -p backend/app/models
mkdir -p backend/app/routers
mkdir -p backend/app/services
mkdir -p frontend/src/pages
mkdir -p frontend/src/services
mkdir -p deploy

echo "✅ 目录结构创建完成"
echo ""
echo "================================================"
echo "接下来请按顺序执行以下脚本（分段粘贴）："
echo "  1. deploy_part1_backend.sh  (后端代码)"
echo "  2. deploy_part2_frontend.sh (前端代码)"
echo "  3. deploy_part3_docker.sh   (Docker配置+启动)"
echo "================================================"
