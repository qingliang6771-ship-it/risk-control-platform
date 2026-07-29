#!/bin/bash
# ============================================================
# 风控后台 · 服务器一键部署 / 更新脚本 (基于 Git + Docker)
#
# 首次部署：
#   1) 修改下方 REPO_URL 为你的 git 仓库地址
#   2) 在服务器执行：  bash server_deploy.sh
#
# 日常更新（拉最新代码并重建）：
#   进入项目目录后执行： bash deploy/server_deploy.sh
# ============================================================
set -e

# ---------- 可配置项 ----------
REPO_URL="${REPO_URL:-git@github.com:your-org/risk-control-platform.git}"
PROJECT_DIR="${PROJECT_DIR:-/opt/risk-control-platform}"
BRANCH="${BRANCH:-main}"
# 服务器对外访问地址（用于 Lark 回调），例如 http://1.2.3.4 或 https://risk.yourcompany.com
SERVER_URL="${SERVER_URL:-http://your-server-ip}"
# --------------------------------

echo "🚀 风控后台部署开始..."
echo "   仓库: $REPO_URL"
echo "   目录: $PROJECT_DIR"
echo "   分支: $BRANCH"

# 1. 安装 Docker（如缺失）
if ! command -v docker &>/dev/null; then
  echo "📦 安装 Docker..."
  curl -fsSL https://get.docker.com | sh
  sudo usermod -aG docker "$USER" || true
fi

# 兼容 docker compose / docker-compose
if docker compose version &>/dev/null; then
  DC="docker compose"
elif command -v docker-compose &>/dev/null; then
  DC="docker-compose"
else
  echo "📦 安装 Docker Compose 插件..."
  sudo apt-get update && sudo apt-get install -y docker-compose-plugin
  DC="docker compose"
fi

# 2. 拉取 / 更新代码
if [ -d "$PROJECT_DIR/.git" ]; then
  echo "🔄 更新已有代码..."
  cd "$PROJECT_DIR"
  git fetch --all
  git reset --hard "origin/$BRANCH"
else
  echo "📥 首次克隆代码..."
  sudo mkdir -p "$PROJECT_DIR"
  sudo chown "$USER":"$USER" "$PROJECT_DIR"
  git clone -b "$BRANCH" "$REPO_URL" "$PROJECT_DIR"
  cd "$PROJECT_DIR"
fi

# 3. 检查环境变量文件
if [ ! -f "backend/.env" ]; then
  echo ""
  echo "⚠️  未找到 backend/.env，请先根据 backend/.env.example 创建并填写："
  echo "    - LARK_APP_ID / LARK_APP_SECRET"
  echo "    - LARK_REDIRECT_URI=$SERVER_URL/api/auth/lark/callback"
  echo "    - SECRET_KEY (随机字符串)"
  echo "    - AI / 数数 API 相关密钥"
  echo ""
  if [ -f "backend/.env.example" ]; then
    cp backend/.env.example backend/.env
    echo "已从 .env.example 复制一份模板到 backend/.env，请编辑后重新运行本脚本。"
  fi
  exit 1
fi

# 4. 覆盖 FRONTEND_URL（供后端登录回调重定向前端）
export FRONTEND_URL="$SERVER_URL"

# 5. 构建并启动
echo "🐳 构建并启动容器..."
$DC up -d --build

# 6. 健康检查
echo "⏳ 等待服务启动..."
sleep 8
if curl -fsS "http://localhost/health" >/dev/null 2>&1; then
  echo "✅ 部署成功！访问: $SERVER_URL"
else
  echo "⚠️ 健康检查未通过，请查看日志：$DC logs -f"
fi

echo ""
echo "常用命令："
echo "  查看日志:  $DC logs -f"
echo "  重启:      $DC restart"
echo "  停止:      $DC down"
