# Changelog

## 3.0.0 (2026-07-17)

### 新增 — 7 个 Manim 动画模板

完整覆盖复变函数核心概念：

- **CREquations** (C-R 方程) — 实轴/虚轴方向导数可视化
- **TaylorSeries** (泰勒级数) — 逐项叠加逼近，收敛圆展示
- **LaurentSeries** (洛朗级数) — 环形区域正负幂项展开
- **PoleClassification** (奇点分类) — 可去/极点/本性三画面并排
- **BranchCut** (分支切割) — Ln(z) 黎曼面 3D 螺旋结构
- **RiemannSphere** (黎曼球面) — 球极投影，∞ 可视化
- **ComplexPlaneTransform** (复平面变换) — 平移/旋转/缩放/反演

### 新增 — 前端体验增强

- **仪表盘增强**：SVG 雷达图 + 知识热力图 + 盲区警告卡片
- **资源中心** (`/resources`)：讲义/练习/思维导图/阅读 分类浏览
- **动画浏览** (`/animations`)：按模板分组、Modal 视频播放
- **对话优化**：Agent 阶段步骤条、5 种气泡样式、推理折叠、快捷操作、KB 引用渲染

### 新增 — 知识库可见性

- Coach 和 Diagnostician Agent 集成教材/讲义检索
- 资源生成自动标注 📚 参考来源
- SSE `reference` 事件传递来源信息

### 优化 — 性能与测试

- 知识库检索缓存 (5min TTL) + 静态资源 24h 缓存 + 骨架屏
- **50+ 测试用例**：25 单元测试 + 22 集成测试 + 3 E2E 测试

---

## 2.0.0 (2026-05-27)

### 新增 — Manim 数学动画子系统

基于模板库 + LLM 参数提取的混合架构，为复变函数学习自动生成数学动画。当前覆盖 3 个概念：

- **ResidueTheorem** (留数定理) — 围道 + 极点可视化
- **ConformalMapping** (共形映射) — z-平面 → w-平面网格变形
- **ContourIntegration** (围道积分) — 参数化路径 + 移动质点

技术栈：Manim Community v0.20.1 + LangGraph SSE 流式 + FastAPI StaticFiles 分发。

### 修复 — 模板渲染管线 (6 bugs)

- f-string 转义错误：外层 `f'''...'''` 错误求值内层变量，4 处修复
- params 注入断裂：`json.loads(sys.argv[1])` 读到 `-pql`，改为直接嵌入生成代码
- 中文 LaTeX 崩溃：`Tex()` (pdfLaTeX) 不支持中文，改用 `Text()` (Pango/Cairo)
- 缺少 `dvisvgm`：DVI→SVG 转换依赖缺失
- 静态文件路径双写 `static`：`/static/static/animations/` → `/animations/`
- Nginx `/animations/` 路由缺失

### 优化 — Docker 镜像体积

- **7.42 GB → 3.38 GB (-54%)**
- 移除 2.7GB NVIDIA CUDA 包 → PyTorch CPU 版 (2.12.0+cpu)
- 服务器磁盘 36GB → 7.8GB (回收 14GB 旧镜像)

### 部署

- 平台：腾讯云 Lighthouse 2核2GB (Railway → Lighthouse 迁移)
- CI/CD：GitHub Actions `git pull && docker compose up -d --build`
- 前端：Next.js 静态导出 + nginx
- API 代理：nginx → backend:8000

### 测试

- 3 个模板全部渲染通过 (120/115/98 KB mp4)
- E2E 管线：coach → animation_render → Manim 渲染 → HTTP 200 → `<video>` 播放
- 独立测试脚本：`scripts/test_manim_render.py`, `scripts/test_animation_e2e.py`
