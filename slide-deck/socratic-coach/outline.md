# Outline: 苏格拉底教练 — 多智能体复变函数辅导系统

**Style**: corporate (clean + professional + geometric + balanced)
**Audience**: competition judges (中国软件杯)
**Language**: zh
**Slides**: 12

---

| # | Title | Type | Layout | Content |
|---|-------|------|--------|---------|
| 01 | 苏格拉底教练 — 多智能体复变函数辅导系统 | cover | centered-title | 项目名称 / 第十五届中国软件杯 / 科大讯飞赛道 |
| 02 | 复变函数学习的三大痛点 | content | two-column | 概念抽象难理解 / 盲区隐蔽难发现 / 学习资料分散难查找 |
| 03 | 8 Agent 智能体协作流程 | workflow | horizontal-pipeline | 用户输入 → ①安全审查(过滤非数学内容) → ②画像检查(意图路由) → ③诊断专家(识别盲区+错误模式) → ④苏格拉底教练(L0-L3追问) → ⑤资源生成(RAG检索+4种资源) → ⑥评估专家(正确性+错误归类) → ⑦质量把关(SymPy验证+内容审查) → ⑧动画渲染(Manim生成视频) → 响应用户。每个Agent各司其职，通过LangGraph状态图串联 |
| 04 | LangGraph 架构设计 | diagram | centered-title | 基于LangGraph的有向状态图 / 9节点+条件路由 / FastAPI SSE流式输出 / 每轮对话经历完整管道 |
| 05 | 苏格拉底追问引擎：L0-L3 四层递进 | content | three-column | L0概念讲解(完全不懂时先教) / L1复述确认 / L2边界追问(测试概念边界) / L3反例挑战(加深理解) |
| 06 | RAG 增强知识库：让AI站在教材的肩膀上 | content | image-right | 4个ChromaDB集合/872个分块/混合检索 / 哈工大教材+课堂讲义+薪火习题库 / 诊断+追问+资源生成均注入知识库 |
| 07 | 四维学习画像：比学生更懂学生 | content | four-quadrant | 雷达图(8章掌握度) / 知识热力图(19概念红黄绿) / 盲区图谱(5类错误) / 学习概览(统计+风格) |
| 08 | Manim 数学动画 + 图片理解 | content | two-column | 10个动画模板自动匹配+LLM参数提取+渲染 / Spark星火API图片识别 / 拍照上传数学公式即答疑 |
| 09 | 资源中心：生成的内容不再淹没在聊天里 | content | image-right | 讲义/练习题/思维导图/拓展阅读集中存放 / 分类筛选+展开折叠+一键删除 / 不用翻聊天记录 |
| 10 | 便捷功能提升学习效率 | content | grid-2x2 | 历史对话加载免重复 / 一键复制消息 / 数学符号面板(5组符号快捷输入) / SSE流式+随时停止生成 |
| 11 | 创新点与竞赛优势 | content | three-column | 苏格拉底主动追问(非被动答疑) / RAG知识库驱动的精准补救 / 雷达图+热力图+盲区+动画四位一体可视化 |
| 12 | 感谢聆听 | back-cover | centered-title | 项目地址 / 联系方式 |
