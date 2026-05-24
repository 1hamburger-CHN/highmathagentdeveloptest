"use client";

import Link from "next/link";
import { ArrowLeft, Sparkles, Brain, BookOpen, Bot, Palette, Database, Wrench, Zap, MessageCircle, CheckCircle } from "lucide-react";

interface ChangeEntry {
  date: string;
  title: string;
  items: string[];
  icon: JSX.Element;
}

const changelog: ChangeEntry[] = [
  {
    date: "2026-05-24",
    title: "复变函数内容转向",
    icon: <BookOpen className="w-4 h-4" />,
    items: [
      "知识库完全重写：高等数学极限与连续 → 复变函数，17 个知识节点覆盖 7 章",
      "所有 Agent Prompt 重构：Diagnostician / Coach / Profile Builder 知识树全面更新",
      "前端全页面文案替换：首页、聊天、画像、知识树、更新日志",
      "Safety Pipeline 关键词和问候语适配复变函数领域",
    ],
  },
  {
    date: "2026-05-24",
    title: "Railway 部署优化",
    icon: <Zap className="w-4 h-4" />,
    items: [
      "嵌入模型切换：BGE-M3 (2GB) → MiniLM-L6-v2 (80MB)，适配 Railway 512MB 免费档",
      "容器启动自动重建知识库索引，重启不再丢数据",
      "索引放入后台线程，避免启动超时被健康检查 kill",
      "ChromaDB + sentence-transformers + jieba 依赖补全",
    ],
  },
  {
    date: "2026-05-23",
    title: "LaTeX 数学公式渲染",
    icon: <Sparkles className="w-4 h-4" />,
    items: [
      "所有 Agent 强制使用 $...$ / $$...$$ LaTeX 格式输出数学公式",
      "前端 KaTeX 实时渲染数学符号，告别纯文本拼凑",
      "新增 safe_json_parse 自动修复 LLM 忘记转义 LaTeX 反斜杠的问题",
      "Streaming 和历史消息 CSS 颜色统一，不再出现紫色文本",
    ],
  },
  {
    date: "2026-05-22",
    title: "学习资源生成系统",
    icon: <BookOpen className="w-4 h-4" />,
    items: [
      "支持直接请求生成思维导图、分层练习题、教学讲义",
      "Mermaid 思维导图支持 SVG 渲染、鼠标拖拽平移、滚轮缩放",
      "生成思维导图后自动追问要不要详细讲解",
      "资源内容走 Markdown 渲染，KaTeX 公式正确显示",
    ],
  },
  {
    date: "2026-05-21",
    title: "持久化与用户系统",
    icon: <Database className="w-4 h-4" />,
    items: [
      "接入 Turso (libSQL) 远程数据库，会话和画像跨设备持久化",
      "新老用户自动识别：新用户构建学习画像，老用户加载历史对话",
      "「加载历史对话」和「清除全部记录」按钮上线",
      "每条消息增加「复制」按钮，支持一键复制回答",
    ],
  },
  {
    date: "2026-05-20",
    title: "苏格拉底教练核心引擎",
    icon: <Brain className="w-4 h-4" />,
    items: [
      "LangGraph 多智能体状态机架构：Coach / Diagnostician / Assessor / Resource Generator / Quality Gate",
      "L0-L3 四层苏格拉底追问体系（概念讲解→复述→边界追问→反例挑战）",
      "五类错误诊断：概念/计算/符号/逻辑/前置知识",
      "Spark API 模型路由，质量把关自动验证数学正确性",
    ],
  },
  {
    date: "2026-05-19",
    title: "项目初始化",
    icon: <Zap className="w-4 h-4" />,
    items: [
      "FastAPI + Next.js + LangGraph 技术栈搭建",
      "Railway + Nixpacks 自动化部署",
      "SSE 流式对话，实时显示 Agent 处理节点",
      "学习画像页面：知识掌握度、盲区图谱、学习行为分析",
    ],
  },
];

export default function ChangelogPage() {
  return (
    <div className="min-h-screen bg-gradient-to-br from-primary-50 via-white to-purple-50">
      <div className="max-w-3xl mx-auto px-6 py-12">
        {/* Header */}
        <div className="mb-10">
          <Link
            href="/"
            className="inline-flex items-center gap-1.5 text-sm text-gray-500 hover:text-primary-600 transition-colors mb-6"
          >
            <ArrowLeft className="w-4 h-4" />
            返回首页
          </Link>
          <h1 className="text-3xl font-bold text-primary-900 mb-2">更新日志</h1>
          <p className="text-gray-500">苏格拉底教练 — 多智能体复变函数辅导系统</p>
          <div className="mt-3 inline-flex rounded-md bg-amber-100 px-2 py-0.5 text-xs font-medium text-amber-700">
            测试版
          </div>
        </div>

        {/* Timeline */}
        <div className="relative">
          {/* Vertical line */}
          <div className="absolute left-[19px] top-2 bottom-2 w-px bg-primary-200" />

          <div className="space-y-8">
            {changelog.map((entry, i) => (
              <div key={i} className="relative pl-12">
                {/* Timeline dot */}
                <div className="absolute left-[11px] top-1 w-[17px] h-[17px] rounded-full bg-primary-100 border-2 border-primary-400 flex items-center justify-center">
                  {entry.icon}
                </div>

                {/* Card */}
                <div className="bg-white/70 rounded-xl border border-gray-100 shadow-sm p-5">
                  <div className="flex items-center gap-2 mb-3">
                    <span className="text-xs text-gray-400 font-mono">{entry.date}</span>
                    <h2 className="text-lg font-semibold text-gray-900">{entry.title}</h2>
                  </div>
                  <ul className="space-y-1.5">
                    {entry.items.map((item, j) => (
                      <li key={j} className="flex items-start gap-2 text-sm text-gray-700">
                        <CheckCircle className="w-4 h-4 text-primary-400 mt-0.5 shrink-0" />
                        <span>{item}</span>
                      </li>
                    ))}
                  </ul>
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Footer */}
        <div className="mt-12 pt-6 border-t border-primary-100 text-center text-xs text-gray-400">
          第十五届中国软件杯 · 科大讯飞出题
        </div>
      </div>
    </div>
  );
}
