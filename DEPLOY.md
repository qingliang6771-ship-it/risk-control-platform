# 风控后台 · 服务器部署指南

本项目采用 **单容器（Docker）** 部署：一个镜像内同时包含 Nginx（托管前端静态资源 + 反向代理）与 FastAPI 后端，数据用 SQLite 持久化到 Docker 卷。

---

## 一、部署架构

```
                 ┌─────────────────────────────────────────┐
  用户浏览器  ──▶ │  Docker 容器 (risk-control-platform)      │
   :80           │   ├─ Nginx  →  /        前端静态资源(dist) │
                 │   │          →  /api/*   反向代理到后端     │
                 │   └─ Uvicorn(FastAPI) :8000               │
                 │        └─ SQLite (挂载卷 kyc-data)          │
                 └─────────────────────────────────────────┘
```

---

## 二、准备工作

### 1. 服务器要求
- Linux（Ubuntu 20.04+ / Debian 推荐），2C4G 起步
- 已开放 80 端口（如需 HTTPS 另开 443）
- 已安装 git（脚本会自动装 Docker）

### 2. Lark（飞书）开放平台配置
1. 进入 [Lark 开放平台](https://open.larksuite.com/) 创建企业自建应用
2. 记录 **App ID** 与 **App Secret**
3. 在「安全设置 → 重定向 URL」添加：
   ```
   http://你的服务器地址/api/auth/lark/callback
   ```
4. 开通权限：获取用户基本信息（`contact:user.base:readonly` 等）
5. 发布应用并在企业内可用

---

## 三、一键部署（推荐）

### 首次部署

```bash
# 1. 下载部署脚本（或直接 clone 仓库）
curl -O https://你的仓库/raw/main/deploy/server_deploy.sh

# 2. 用环境变量指定仓库、访问地址后执行
REPO_URL=git@github.com:your-org/risk-control-platform.git \
SERVER_URL=http://1.2.3.4 \
bash server_deploy.sh
```

首次运行时脚本会：
1. 自动安装 Docker / Docker Compose（如缺失）
2. 克隆代码到 `/opt/risk-control-platform`
3. 若无 `backend/.env`，自动从 `.env.example` 复制模板并**中止**，提示你去填写

### 填写环境变量

```bash
cd /opt/risk-control-platform
vim backend/.env      # 填入 Lark / AI / 数数 / 风控模型 等密钥
```

关键项：
| 变量 | 说明 |
|------|------|
| `LARK_APP_ID` / `LARK_APP_SECRET` | 飞书应用凭证 |
| `LARK_REDIRECT_URI` | 必须与开放平台配置完全一致 |
| `SECRET_KEY` | JWT 密钥，用 `openssl rand -hex 32` 生成 |
| `AI_API_KEY` | AI 服务密钥 |
| `TA_API_TOKEN` / `TA_APP_ID` | 数数 ThinkingData |
| `RISK_MODEL_BASE_URL` / `RISK_MODEL_API_KEY` | 风控模型接口 |

### 再次运行部署脚本完成启动

```bash
SERVER_URL=http://1.2.3.4 bash deploy/server_deploy.sh
```

看到 `✅ 部署成功！` 即可访问 `http://你的服务器地址`。

---

## 四、日常更新

代码更新后，直接用你熟悉的三行命令即可（推荐）：

```bash
cd /opt/risk-control-platform
git pull origin main
docker compose up -d --build
```

说明：
- 配置全部从 `backend/.env` 读取（含 `FRONTEND_URL`），无需再带环境变量。
- 容器启动时 `start.sh` 会**自动执行**数据库迁移，补齐权限新字段，无需手动操作。
- 数据库与 KYC 数据已挂载到 Docker 卷（`risk-db` / `kyc-data`），`--build` 重建容器不会丢数据。

或者用一键脚本（自动拉代码 + 校验 .env + 健康检查）：

```bash
cd /opt/risk-control-platform
bash deploy/server_deploy.sh
```

> ⚠️⚠️ 重要：修复「每次更新后数据丢失」的一次性迁移
>
> **历史根因**：旧配置里数据库用的是相对路径 `sqlite+aiosqlite:///./db/...`，
> 由于运行时工作目录的关系，SQLite 实际被写到了容器内 `/app/backend/risk_control.db`
> （**backend 根目录，未被卷挂载**），而 docker 卷只挂了 `/app/backend/db`。
> 结果每次 `docker compose up -d --build` 重建容器，数据库都被重置，历史数据丢失。
>
> **本版本修复**：`DATABASE_URL` 改为**绝对路径** `sqlite+aiosqlite:////app/backend/db/risk_control.db`，
> 让数据库始终落在被 `risk-db` 卷挂载的目录里，从此重建容器不再丢数据。
>
> **升级步骤（务必按顺序，先抢救旧数据再更新）：**
> ```bash
> cd /opt/risk-control-platform
>
> # 1) 先把当前容器里的旧数据库导出到宿主机（趁容器还在运行、数据还在）
> docker cp risk-control-platform:/app/backend/risk_control.db ./old_risk_control.db || \
>   echo "旧库不在根目录，尝试 db 子目录：" && \
>   docker cp risk-control-platform:/app/backend/db/risk_control.db ./old_risk_control.db || true
>
> # 2) 修改服务器上的 backend/.env，把 DATABASE_URL 改成绝对路径：
> #    DATABASE_URL=sqlite+aiosqlite:////app/backend/db/risk_control.db
> #    （注意是 4 条斜杠：sqlite+aiosqlite://// 表示绝对路径 /app/...）
> sed -i 's#^DATABASE_URL=.*#DATABASE_URL=sqlite+aiosqlite:////app/backend/db/risk_control.db#' backend/.env
> grep DATABASE_URL backend/.env    # 确认已是 4 斜杠的绝对路径
>
> # 3) 拉新代码并重建（此步会确保 risk-db 卷挂到 /app/backend/db）
> git pull origin main
> docker compose up -d --build
>
> # 4) 把旧数据库放进卷内的新位置，然后重启加载
> docker cp ./old_risk_control.db risk-control-platform:/app/backend/db/risk_control.db
> docker compose restart
> ```
> 完成后，历史封禁数据即恢复，且之后每次更新都会保留。
>
> 若确认历史数据可放弃（重新登录/重传即可），可跳过 1、4 两步，只做 2、3。



---

## 五、手动部署（不使用脚本）

```bash
git clone <repo> /opt/risk-control-platform
cd /opt/risk-control-platform
cp backend/.env.example backend/.env && vim backend/.env

# 构建 + 启动（FRONTEND_URL 用于登录回调重定向）
FRONTEND_URL=http://1.2.3.4 docker compose up -d --build
```

---

## 六、权限管理说明

- **首位** 通过 Lark 登录的同事会被自动设为**管理员**，并拥有全部模块权限。
- 管理员在左侧「权限管理」中可以：
  - 搜索/查看所有用户
  - 勾选授予各模块权限（AI 数据报告 / 风控查询 / KYC 报告 / 权限管理）
  - 启用/停用账号、设置或取消管理员
  - 预先添加尚未登录过的 Lark 同事并预配权限
- 数据库结构变更由容器启动脚本 `start.sh` **自动执行** `migrate_add_permissions.py` 补齐（旧库升级无需手动操作，新库幂等无副作用）。

---

## 七、运维常用命令

```bash
docker compose logs -f          # 查看实时日志
docker compose restart          # 重启
docker compose down             # 停止并移除容器（数据卷保留）
docker compose ps               # 查看运行状态
docker volume ls | grep kyc     # 查看数据卷
```

### 数据备份（SQLite）
```bash
# 备份数据库文件
docker cp risk-control-platform:/app/backend/data/risk_control.db ./backup-$(date +%F).db
```

---

## 八、配置 HTTPS（可选，推荐生产使用）

建议在容器外用宿主机 Nginx 或 Caddy 做 TLS 终止，反代到容器 80 端口；
并把 `SERVER_URL` 与 `LARK_REDIRECT_URI` 改为 `https://` 地址，同步更新 Lark 后台重定向 URL。

```nginx
server {
    listen 443 ssl;
    server_name risk.yourcompany.com;
    ssl_certificate     /etc/ssl/xxx.crt;
    ssl_certificate_key /etc/ssl/xxx.key;
    location / { proxy_pass http://127.0.0.1:80; proxy_set_header Host $host; }
}
```

---

## 九、故障排查

| 现象 | 排查方向 |
|------|----------|
| 登录跳转报错 | 检查 `LARK_REDIRECT_URI` 与 Lark 后台是否**完全一致** |
| 登录后一直转圈 | `docker compose logs -f` 看后端是否 401/500 |
| 健康检查失败 | `curl localhost/health`，查看容器是否起来 |
| 权限菜单不显示 | 确认该用户在「权限管理」中已被授予对应模块 |
| 数据丢失 | 确认 `kyc-data` 卷未被删除；用备份恢复 |
```
