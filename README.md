# 苏格拉底教练 — 多智能体高等数学辅导系统

第十五届中国软件杯（科大讯飞出题）参赛项目。基于 LangGraph 的 6 Agent 多智能体架构，通过苏格拉底式追问诊断学习盲区，自动生成针对性补救资源。

## 架构

```
User → FastAPI/SSE → Orchestrator (LangGraph Supervisor)
                         ├── Profile Builder Agent
                         ├── Diagnostician Agent
                         ├── Socratic Coach Agent (L1/L2/L3 追问)
                         ├── Resource Generator Agent (讲义/练习/思维导图/阅读)
                         ├── Assessor Agent
                         └── Quality Gate Agent
                              ↓
                         Spark API / DeepSeek
                         ChromaDB + BGE-M3
                         SymPy 数学验证
```

## 快速开始

```bash
# 1. 配置 API 密钥
cp backend/.env backend/.env.local
# 编辑 backend/.env.local，填入 Spark API 凭证

# 2. 启动
docker compose up -d

# 3. 访问
open http://localhost:3000
```

## 本地开发

```bash
# Backend
cd backend
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000

# Frontend
cd frontend
npm install
npm run dev
```

## 项目结构

```
math-intelligent-tutor/
├── backend/app/
│   ├── main.py              # FastAPI + SSE
│   ├── api/                  # REST + SSE endpoints
│   ├── agents/               # 6 Agent + Orchestrator + LangGraph
│   ├── knowledge/            # KB schema, loader, chunker, embedder, retriever
│   ├── models/               # Pydantic + SQLAlchemy
│   ├── services/             # SymPy math, profile logic
│   └── core/                 # LLM router, safety pipeline
├── frontend/src/
│   ├── app/                  # Next.js App Router pages
│   └── components/           # Chat UI, StreamingMarkdown
└── docker-compose.yml
```
