# 苏格拉底教练 2.0 — 多智能体复变函数辅导系统

第十五届中国软件杯（科大讯飞出题）参赛项目。基于 LangGraph 的 8 Agent 多智能体架构，通过苏格拉底式追问诊断学习盲区，自动生成针对性补救资源。

## 核心特性

- **8 Agent 多智能体协作**：安全审查 → 画像构建 → 学习诊断 → 苏格拉底追问 → 资源生成 → 评估 → 质量把关 → 动画渲染
- **三层追问体系**：L0 概念讲解 → L1 概念复述 → L2 边界追问 → L3 反例挑战
- **RAG 增强知识库**：4 个 ChromaDB 集合（知识图谱 + 教材全文 + 课堂讲义 + 习题库），872 个检索分块
- **Manim 数学动画**：留数定理、围道积分、共形映射可视化
- **图片理解**：支持上传数学公式/图表，自动识别并辅导
- **SSE 流式对话**：实时响应，支持停止生成

## 架构

```
User → FastAPI/SSE → LangGraph Supervisor Pipeline
                       ├── Safety Check
                       ├── Profile Builder Agent
                       ├── Diagnostician Agent
                       ├── Socratic Coach Agent (L0-L3 追问)
                       ├── Animation Generator (Manim)
                       ├── Resource Generator Agent
                       │     ├── 知识图谱 (19 节点)
                       │     ├── 教材全文 (哈工大, 631 chunks)
                       │     ├── 课堂讲义 (5 章, 178 chunks)
                       │     └── 习题库 (薪火, 23 chunks)
                       ├── Assessor Agent
                       └── Quality Gate Agent
                            ↓
                       Spark API / DeepSeek
                       ChromaDB + all-MiniLM-L6-v2
                       Turso (libsql/SQLite)
```

## 快速开始

```bash
# 1. 配置环境变量
cp backend/.env.example backend/.env
# 编辑 backend/.env，填入 API 密钥

# 2. Docker 启动
docker compose up -d

# 3. 访问
open http://localhost:80
```

## 本地开发

```bash
# Backend (Python 3.11+)
cd backend
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000

# Frontend (Node.js 20+)
cd frontend
npm install
npm run dev
```

## 项目结构

```
├── backend/app/
│   ├── main.py                   # FastAPI 入口 + SSE + 自动索引
│   ├── config.py                 # 配置管理
│   ├── api/                      # chat, profile, generate, assess, animation, path
│   ├── agents/                   # 8 Agent + LangGraph state graph
│   │   ├── graph.py              # LangGraph supervisor pipeline
│   │   ├── socratic_coach.py     # L0-L3 苏格拉底追问引擎
│   │   ├── resource_generator.py # RAG 增强资源生成
│   │   ├── diagnostician.py      # 学习盲区诊断
│   │   ├── assessor.py          # 回答评估
│   │   ├── profile_builder.py   # 用户画像构建
│   │   ├── quality_gate.py      # 内容质量把关
│   │   ├── animation_generator.py # Manim 动画生成
│   │   └── state.py             # LangGraph 状态定义
│   ├── knowledge/               # 知识库模块
│   │   ├── schema.py            # 知识节点数据模型
│   │   ├── loader.py            # YAML 课程大纲加载
│   │   ├── chunker.py           # LaTeX 感知分块
│   │   ├── embedder.py          # BGE-M3/all-MiniLM 嵌入
│   │   ├── retriever.py         # 混合检索（4 集合）
│   │   ├── textbook_schema.py   # 教材分块模型
│   │   └── textbook_loader.py   # OCR 教材加载
│   ├── animation/               # Manim 动画子系统
│   ├── core/                    # LLM 路由, 安全管线, 图片理解
│   └── models/                  # 数据库模型
├── backend/data/seed/
│   └── curriculum.yaml          # 19 个知识节点（复变+积分变换）
├── backend/scripts/
│   ├── index_kb.py              # 知识图谱索引
│   ├── index_textbook.py        # 教材索引
│   └── index_handouts.py        # 讲义+习题索引
├── frontend/src/
│   ├── app/                     # Next.js 页面 (chat, profile, topics)
│   └── components/              # StreamingMarkdown, MermaidBlock
├── data/                        # 知识源文本（OCR 提取）
├── 复变/                        # 原始 PDF 教材 + 讲义 + 习题
├── docs/                        # 设计文档
├── docker-compose.yml
├── README.md
└── CHANGELOG.md
```

## 知识库

| 集合 | 分块 | 来源 |
|---|---|---|
| complex_analysis | 40 | 19 个结构化知识节点 |
| textbook | 631 | 哈工大《复变函数与积分变换》教材 |
| handouts | 178 | 5 章课堂讲义 |
| exercises | 23 | 薪火综合训练选择填空解析 |

## 技术栈

- **后端**: FastAPI + LangGraph + ChromaDB + Turso + Manim
- **前端**: Next.js 14 + Tailwind CSS + SSE streaming
- **LLM**: 讯飞 Spark API / DeepSeek 降级
- **部署**: Docker + Nginx + 腾讯云 Lighthouse
