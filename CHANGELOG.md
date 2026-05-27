# Changelog

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
