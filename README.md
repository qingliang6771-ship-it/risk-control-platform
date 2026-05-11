# 风控后台系统

公司内部风控数据平台，集成 AI 数据报告、Lark登录、风控模型查询。

## 功能模块

### 1. AI 数据报告（接入 AI + 数数API）
- 自然语言查询数数平台数据
- AI 自动分析并生成报告
- 支持流式对话，实时返回结果
- 历史对话上下文保持

### 2. Lark OAuth 登录
- 仅支持通过Lark账号登录
- 自动获取用户信息（姓名、邮箱、头像）
- JWT Token 认证机制
- 未授权人员无法访问

### 3. 风控模型查询
- 综合风控评分
- 欺诈检测
- 信用评估
- 行为分析
- 设备指纹分析
- 支持批量查询所有模型结果

## 技术栈

### 后端
- **Python 3.11+** + **FastAPI**
- **SQLAlchemy** (异步 ORM)
- **SQLite / PostgreSQL**
- **python-jose** (JWT)
- **httpx** (异步 HTTP 客户端)
- **openai** (AI 接口)

### 前端
- **React 18** + **Vite**
- **Ant Design 5** (UI 组件库)
- **React Router 6** (路由)
- **Axios** (HTTP 请求)
- **React Markdown** (Markdown 渲染)

## 快速开始

### 后端

```bash
cd backend

# 创建虚拟环境
python -m venv venv
source venv/bin/activate  # macOS/Linux

# 安装依赖
pip install -r requirements.txt

# 配置环境变量
cp .env.example .env
# 编辑 .env 填入实际配置

# 启动服务
uvicorn app.main:app --reload --port 8000
```

### 前端

```bash
cd frontend

# 安装依赖
npm install

# 启动开发服务器
npm run dev
```

访问 http://localhost:3000

## 环境变量配置

| 变量 | 说明 |
|------|------|
| `LARK_APP_ID` | Lark应用 App ID |
| `LARK_APP_SECRET` | Lark应用 App Secret |
| `AI_API_KEY` | AI 服务 API Key |
| `AI_API_BASE_URL` | AI 服务地址 |
| `TD_API_URL` | 数数平台 API 地址 |
| `TD_API_TOKEN` | 数数平台 Token |
| `RISK_MODEL_API_URL` | 风控模型服务地址 |
| `SECRET_KEY` | JWT 签名密钥 |

## 项目结构

```
risk-control-platform/
├── backend/
│   ├── app/
│   │   ├── main.py          # FastAPI 入口
│   │   ├── config.py        # 配置管理
│   │   ├── database.py      # 数据库连接
│   │   ├── models/          # 数据模型
│   │   ├── routers/         # API 路由
│   │   │   ├── auth.py      # 认证路由
│   │   │   ├── report.py    # AI报告路由
│   │   │   └── risk.py      # 风控查询路由
│   │   └── services/        # 业务服务
│   │       ├── lark_auth.py # Lark认证
│   │       ├── ai_report.py # AI+数数服务
│   │       └── risk_model.py# 风控模型服务
│   ├── requirements.txt
│   └── .env.example
├── frontend/
│   ├── src/
│   │   ├── App.jsx          # 主应用
│   │   ├── pages/           # 页面组件
│   │   │   ├── Login.jsx    # 登录页
│   │   │   ├── AIReport.jsx # AI报告页
│   │   │   ├── RiskQuery.jsx# 风控查询页
│   │   │   └── Dashboard.jsx# 工作台
│   │   └── services/
│   │       └── api.js       # API 封装
│   ├── package.json
│   └── vite.config.js
└── README.md
```

## Lark应用配置

1. 在[Lark开放平台](https://open.larksuite.com/)创建应用
2. 添加「网页应用」能力
3. 配置重定向 URL: `http://your-domain/api/auth/lark/callback`
4. 申请权限: `contact:user.email:readonly`, `contact:user.base:readonly`
5. 将 App ID 和 App Secret 填入 `.env`

## API 文档

启动后端后访问: http://localhost:8000/docs
