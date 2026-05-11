# 🚀 风控后台部署指南

## 一键部署到云服务器

### 前置要求
- 一台云服务器（推荐 2核4G 以上，Ubuntu 20.04+）
- 安装 Docker 和 Docker Compose
- 开放 80 端口（或你自定义的端口）

### 步骤 1：安装 Docker（如果还没装）

```bash
# Ubuntu/Debian
curl -fsSL https://get.docker.com | sh
sudo usermod -aG docker $USER

# 安装 docker-compose
sudo apt install docker-compose -y
```

### 步骤 2：上传代码到服务器

```bash
# 方法1: 用 git
git clone <your-repo-url> /opt/risk-control-platform
cd /opt/risk-control-platform

# 方法2: 用 scp 从本地上传
scp -r /Users/qing/Documents/risk-control-platform user@your-server:/opt/risk-control-platform
```

### 步骤 3：配置环境变量

```bash
cd /opt/risk-control-platform
cp backend/.env.example backend/.env
vim backend/.env
```

编辑 `.env` 文件，填入真实的配置：

```env
# AI 配置
AI_API_KEY=your-ai-api-key
AI_BASE_URL=https://api.openai.com/v1
AI_MODEL=gpt-4o

# 数数科技 ThinkingData
TA_API_URL=https://your-ta-instance.com
TA_API_TOKEN=your-ta-token

# Lark 飞书登录
LARK_APP_ID=your-lark-app-id
LARK_APP_SECRET=your-lark-app-secret

# JWT 密钥（随机生成一个）
JWT_SECRET=your-random-secret-key-change-this

# 前端地址（改为你的服务器IP或域名）
FRONTEND_URL=http://your-server-ip
```

### 步骤 4：修改 docker-compose.yml 中的 FRONTEND_URL

```bash
vim docker-compose.yml
# 把 FRONTEND_URL 改为你的服务器公网IP或域名
```

### 步骤 5：构建并启动

```bash
docker-compose up -d --build
```

等待构建完成（首次约 2-3 分钟），然后访问 `http://your-server-ip` 即可使用！

### 步骤 6：配置 Lark 飞书应用回调地址

在飞书开放平台中，将 OAuth 回调地址设置为：
```
http://your-server-ip/api/auth/lark/callback
```

---

## 常用运维命令

```bash
# 查看日志
docker-compose logs -f

# 重启服务
docker-compose restart

# 停止服务
docker-compose down

# 更新代码后重新部署
git pull
docker-compose up -d --build

# 查看容器状态
docker-compose ps
```

---

## 使用域名 + HTTPS（推荐）

如果你有域名，推荐配置 HTTPS：

### 方法1：使用 Caddy（最简单）

替换 docker-compose.yml：

```yaml
version: '3.8'

services:
  risk-platform:
    build: .
    container_name: risk-control-platform
    ports:
      - "8080:80"
    env_file:
      - backend/.env
    restart: unless-stopped

  caddy:
    image: caddy:2
    container_name: caddy
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./deploy/Caddyfile:/etc/caddy/Caddyfile
      - caddy_data:/data
    restart: unless-stopped

volumes:
  caddy_data:
```

创建 `deploy/Caddyfile`：
```
risk.yourdomain.com {
    reverse_proxy risk-platform:80
}
```

### 方法2：使用 Nginx + Let's Encrypt

参考 certbot 官方文档配置 SSL 证书。

---

## 架构说明

```
┌─────────────────────────────────────────┐
│              Cloud Server                │
│                                         │
│  ┌─────────┐     ┌──────────────────┐  │
│  │  Nginx  │────▶│  FastAPI Backend  │  │
│  │  :80    │     │  :8000           │  │
│  │         │     │                  │  │
│  │ 静态文件 │     │ - AI Report API  │  │
│  │ (前端)   │     │ - Risk Query API │  │
│  │         │     │ - Lark Auth API  │  │
│  └─────────┘     └──────────────────┘  │
│                          │              │
│                          ▼              │
│              ┌───────────────────┐      │
│              │  External APIs    │      │
│              │  - OpenAI/AI      │      │
│              │  - ThinkingData   │      │
│              │  - Lark OAuth     │      │
│              └───────────────────┘      │
└─────────────────────────────────────────┘
```

---

## 故障排查

| 问题 | 解决方案 |
|------|---------|
| 页面打不开 | 检查 80 端口是否开放，`docker-compose ps` 看容器状态 |
| API 报 502 | `docker-compose logs` 查看后端是否启动成功 |
| Lark 登录失败 | 检查 LARK_APP_ID/SECRET 和回调地址配置 |
| AI 查询超时 | 检查 AI_API_KEY 和网络连通性 |
| 数数查询失败 | 检查 TA_API_URL 和 TA_API_TOKEN |
