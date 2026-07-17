# 苏格拉底教练 v3.0 — 扩展设计文档

2026-07-17 | 复变函数多智能体辅导系统

## 概述

在 v2.0 基础上做四个方向的扩展：

| 方向 | 范围 | 优先级 |
|------|------|--------|
| 1. Manim 动画模板扩展 | 新增 7 个模板 | Phase 1-2 |
| 2. 前端体验增强 | 仪表盘+动画浏览+资源中心+对话体验 | Phase 1-2 |
| 3. 知识库可见性改进 | Coach/Diagnostician 集成 KB + 来源显示 | Phase 1 |
| 4. 系统优化 | 性能优化 + 测试覆盖 | Phase 1-3 |

---

## 方向 1：7 个 Manim 动画模板

沿用现有 `BaseManimTemplate` → `validate()` → `build_scene_code()` 模式。

### 模板清单

| # | 模板名 | concept_id | 可视化设计 |
|---|--------|-----------|-----------|
| 1 | **CREquations** | complex-2.2 | 复平面上沿实轴和虚轴分别逼近同一点，展示导数方向无关性→C-R条件可视化 |
| 2 | **TaylorSeries** | complex-5.1 | 逐项叠加幂级数项逼近解析函数，收敛圆从圆心逐步扩大到收敛半径 |
| 3 | **LaurentSeries** | complex-5.2 | 环形区域：正幂项从内圆向外、负幂项从外圆向内逐项叠加 |
| 4 | **PoleClassification** | complex-6.1 | 三画面并排：可去奇点(极限存在)、极点(|f|→∞垂直柱)、本性奇点(震荡渐变色) |
| 5 | **BranchCut** | complex-3.1 | Ln(z)的螺旋面结构：绕原点一圈后过渡到下一分支，分支切割线可视化 |
| 6 | **RiemannSphere** | complex-1.2 | 球极投影动画：复平面上网格点投影到单位球面，展示∞收缩到北极 |
| 7 | **ComplexPlaneTransform** | complex-7.1 | 四种基本变换动画分解：平移→旋转→缩放→反演，展示几何意义 |

### 实施要点

- 每个模板 ~80-120 行 Manim 代码
- 注册到 `ALL_TEMPLATES` 列表
- 在 `TemplateSelector._describe_params()` 中注册参数 schema
- 中文文本使用 `Text()` (Pango/Cairo)，数学公式使用 `Tex()` (LaTeX)
- 继承 `scene_class_name` 命名约定：`{Concept}Scene`

### Manim 渲染集成

- 模板匹配：concept_id 在 profile_check_node 或被 coach_node 触发 `_animation_pending` 时匹配
- 参数提取：LLM 根据诊断上下文提取模板参数
- 渲染：`animation_render_node` → `AnimationGeneratorAgent` → Manim CLI → mp4

---

## 方向 2：前端体验增强

### 2.1 学习仪表盘增强 (`/profile`)

**新增组件**：

| 组件 | 实现 | 说明 |
|------|------|------|
| `RadarChart` | 纯 SVG 六边形雷达图 | 7 章掌握度，每轴 0-100% |
| `KnowledgeHeatmap` | CSS Grid 色块矩阵 | 17 概念节点，红/黄/绿渐变 |
| `BlindSpotAlert` | 警告卡片组件 | 高频错误概念置顶，附快捷入口 |
| `LearningTimeline` | 垂直时间线 | 最近诊断/学习事件列表 |

### 2.2 动画浏览页 (`/animations`)

**新页面**：`frontend/src/app/animations/page.tsx`

- 按 7 章分组折叠面板
- 动画卡片：缩略图(首帧) + 标题 + 概念标签 + 生成时间
- 点击弹出 Modal 视频播放器
- 空状态：引导用户去聊天页请求动画
- 数据源：`GET /api/animation/list?user_id=xxx`

### 2.3 资源中心 (`/resources`)

**新页面**：`frontend/src/app/resources/page.tsx`

- 顶部 Tabs：讲义 / 练习题 / 思维导图 / 拓展阅读
- 资源卡片带预览摘要和概念标签
- 思维导图使用 `MermaidBlock` 组件渲染
- 数据源：`GET /api/sessions/{user_id}/resources`

### 2.4 对话体验优化

**聊天页面改造**：

| 改动 | 说明 |
|------|------|
| 步骤条状态栏 | 顶部显示当前 Agent 阶段：`诊断中 → 追问 L2 → 生成资源` |
| 气泡样式区分 | 5 种：user(蓝)/coach(灰)/system(红)/animation(视频卡片)/resource(资源卡片) |
| 教练推理展开 | 教练消息下方可折叠 "🧠 推理过程" block |
| 快捷操作按钮 | 消息下方快捷按钮："追问为什么"/"给我看例子"/"生成练习题" |
| 来源引用渲染 | 消息底部渲染 "📚 参考来源" 引用列表（配合方向 3）|

### 技术约束

- 使用现有依赖：React 18 + Next.js 14 + Tailwind CSS + lucide-react + KaTeX
- 不引入重型图表库（recharts/echarts），图表用纯 SVG/CSS
- 兼容现有 SSE 协议，新增 `event: reference` 事件

---

## 方向 3：知识库可见性改进

### 现状问题

1. **只有 ResourceGeneratorAgent 使用 KB**，SocraticCoach 和 Diagnostician 完全不用
2. **使用 KB 时没有来源标注**，用户不知道内容来自教材

### 改进方案

#### 3.1 Coach 和 Diagnostician 集成 KB

在 `graph.py` 的 `coach_node` 和 `diagnose_node` 中注入 KB 检索结果：

```python
# 注入到 SocraticCoachAgent
kb_context = _retriever.search_all(concept, top_k=2)
state._kb_context = kb_context  # 随 state 传入 Agent
```

SocraticCoachAgent prompt 中增加：
```
## 知识库参考
{textbook_passages}
{handout_passages}

请确保你的追问基于以上教材定义，保持数学严谨性。
```

#### 3.2 SSE 来源引用事件

新增 SSE 事件类型 `reference`：

```
event: reference
data: {
  "sources": [
    {"type": "textbook", "source": "哈工大《复变函数与积分变换》", "chapter": "第2章 解析函数"},
    {"type": "handouts", "source": "哈工大复变课堂讲义", "chapter": "C-R方程"}
  ]
}
```

#### 3.3 ResourceGenerator 来源显示

在 `ResourceGeneratorAgent.run()` 中，为每次检索记录来源元数据，并在返回的 `messages` 末尾追加引用信息：

```markdown
---

📚 **参考来源**
- 哈工大《复变函数与积分变换》教材 — 第2章 解析函数
- 哈工大复变课堂讲义 — C-R方程
```

#### 3.4 前端渲染

在 `StreamingMarkdown` 和资源卡片中识别并渲染 `📚 参考来源` 引用块。

---

## 方向 4：系统优化

### 4.1 性能优化

| 优化项 | 文件 | 方案 |
|--------|------|------|
| 检索缓存 | `knowledge/retriever.py` | 添加 `functools.lru_cache(maxsize=128)`，相同 query 5min TTL |
| ChromaDB 批量查询 | `knowledge/retriever.py` | `search_all()` 合并 embedding 调用为一次 batch |
| 静态资源缓存 | `api/animation.py` | 动画 mp4 响应加 `Cache-Control: max-age=86400` |
| 前端骨架屏 | `chat/page.tsx` | 首屏加载用 Tailwind `animate-pulse` 骨架占位 |
| 图标 tree-shaking | 全前端 | 确保 lucide-react 按需导入，不打包未使用的图标 |

### 4.2 测试覆盖

**分层金字塔**：单元(25) + 集成(8) + E2E(3) = 36 个测试用例

#### 单元测试 (`backend/tests/`)

```
tests/
├── __init__.py
├── knowledge/
│   ├── __init__.py
│   ├── test_chunker.py        # LaTeX 切割精度、中英混合
│   ├── test_retriever.py      # top-k 召回、关键词回退、别名解析
│   └── test_loader.py         # curriculum.yaml 完整性验证
├── agents/
│   ├── __init__.py
│   ├── test_socratic_coach.py # Bloom 层级模板、prompt 渲染
│   ├── test_assessor.py       # 评估 schema 校验
│   └── test_resource_generator.py  # KB 富化、来源标注
├── services/
│   ├── __init__.py
│   ├── test_math_service.py   # SymPy 极限/等价无穷小验证
│   └── test_profile_service.py # 贝叶斯更新、画像合并
├── core/
│   ├── __init__.py
│   └── test_safety.py         # 安全过滤边界 case
└── animation/
    ├── __init__.py
    ├── test_selector.py       # 已有 — 扩展 7 个新模板的注册验证
    └── test_templates.py      # 新模板 validate/build 验证
```

#### 集成测试 (`backend/tests/integration/`)

| 测试场景 | 验证点 |
|---------|-------|
| `test_diagnose_to_coach` | 诊断→追问流转正确 |
| `test_resource_fanout` | 资源生成 Fan-out 聚合 |
| `test_sse_streaming` | 逐 token 传输、公式不截断 |
| `test_kb_rag` | 检索结果注入 prompt |
| `test_animation_pipeline` | 模板匹配→参数提取→渲染 |
| `test_profile_persistence` | 多轮画像保存/恢复 |
| `test_error_degradation` | LLM 超时→备用模型切换 |
| `test_safety_gate` | 非数学拦截、危险内容拒绝 |

#### E2E 测试 (`scripts/` 或 Playwright)

| 场景 | 描述 |
|------|------|
| Demo 完整流程 | 按 demo 脚本走诊断→追问→生成→评估 |
| 动画全链路 | 请求动画→参数提取→渲染→视频播放 |
| 多会话持久化 | 退出再进入，画像和历史恢复 |

**测试框架**：
- 后端：pytest + pytest-asyncio（已有）
- 前端：Vitest + @testing-library/react（新增 devDependency）

---

## 实施计划

### Phase 1（并行）

```
Manim 模板 1-4:
  ├── CREquations (complex-2.2)
  ├── TaylorSeries (complex-5.1)
  ├── LaurentSeries (complex-5.2)
  └── PoleClassification (complex-6.1)

前端:
  ├── 仪表盘增强 (RadarChart, KnowledgeHeatmap, BlindSpotAlert, Timeline)
  └── 资源中心页面 (/resources)

KB 可见性:
  ├── Coach/Diagnostician KB 集成
  ├── ResourceGenerator 来源标注
  └── SSE reference 事件 + 前端渲染

测试:
  └── 单元测试 25 个
```

### Phase 2（并行）

```
Manim 模板 5-7:
  ├── BranchCut (complex-3.1)
  ├── RiemannSphere (complex-1.2)
  └── ComplexPlaneTransform (complex-7.1)

前端:
  ├── 动画浏览页面 (/animations)
  └── 对话体验优化 (步骤条、气泡、推理展开、快捷按钮)

性能优化:
  ├── 检索缓存
  ├── ChromaDB 批量查询
  ├── 静态资源缓存
  └── 前端骨架屏

测试:
  └── 集成测试 8 个
```

### Phase 3

```
E2E 测试 3 个:
  ├── Demo 完整流程
  ├── 动画全链路
  └── 多会话持久化

收尾:
  ├── 代码审查
  ├── 前后端联调
  └── 文档更新
```

---

## 风险与约束

- **Manim 渲染**：单实例文件锁限制并发为 1，Phase 1-2 暂不引入 Celery
- **前端兼容**：不引入重型图表库，SVG 雷达图注意移动端适配
- **测试覆盖**：不要求 80%+，重点覆盖核心路径和边界 case
- **KB 可见性**：来源标注依赖 LLM 遵守 prompt 指令，不保证 100% 准确标注
- **已有功能不回退**：所有改动是对 v2.0 的增量扩展
