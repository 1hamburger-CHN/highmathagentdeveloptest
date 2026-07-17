"use client";

import Link from "next/link";
import { ArrowLeft, Sparkles, Brain, BookOpen, Bot, Palette, Database, Wrench, Zap, MessageCircle, CheckCircle, Film } from "lucide-react";

interface ChangeEntry {
  date: string;
  title: string;
  items: string[];
  icon: JSX.Element;
}

const changelog: ChangeEntry[] = [
  {
    date: "2026-07-17",
    title: "v3.0 — 7 个新动画 + 画像全面升级 + 聊天体验优化",
    icon: <Sparkles className="w-4 h-4" />,
    items: [
      "数学动画从 3 个扩展到 10 个，新增 C-R 方程、泰勒级数、洛朗级数、奇点分类、分支切割、黎曼球面、复平面变换",
      "动画页面支持中文讲解面板、多视频标注示例编号、点击卡片播放",
      "学习画像全新改版：雷达图展示 7 章掌握度、知识热力图 19 概念三色标识、盲区图谱点击去诊断",
      "画像评分改为实际回答质量驱动——正确回答逐步加分，只看不回答不评分",
      "资源中心上线：讲义/练习题/思维导图/拓展阅读分类浏览，生成时标注参考来源",
      "数学符号输入面板：Σ 按钮支持积分、求和、希腊字母等符号，输入时实时预览渲染",
      "快捷操作按钮：教练讲解后出现追问/例子/练习按钮",
    ],
  },
  {
    date: "2026-05-27",
    title: "v2.0 — 数学动画 + 图片理解 + 持久化",
    icon: <Film className="w-4 h-4" />,
    items: [
      "上线 3 个数学动画：留数定理、共形映射、围道积分",
      "支持图片上传分析：拍照上传数学题目，AI 识别后辅导",
      "数学公式全平台 KaTeX 渲染，告别纯文本拼凑",
      "聊天支持流式输出，逐字显示回复内容",
      "对话历史持久化：跨设备保存，刷新不丢失，支持加载/清除",
      "知识库覆盖全部 19 个复变函数概念，自动判断概念是否在范围内",
    ],
  },
  {
    date: "2026-05-24",
    title: "学习资源生成 + 复变函数内容转向",
    icon: <BookOpen className="w-4 h-4" />,
    items: [
      "支持直接请求生成思维导图、分层练习题、教学讲义",
      "Mermaid 思维导图支持 SVG 渲染、拖拽平移、滚轮缩放",
      "知识库完全重写为复变函数，19 个知识节点覆盖 8 章",
      "所有页面和 Agent 全面转向复变函数领域",
    ],
  },
  {
    date: "2026-05-23",
    title: "LaTeX 数学公式渲染",
    icon: <Sparkles className="w-4 h-4" />,
    items: [
      "教练和资源生成的所有数学内容均使用 LaTeX 格式输出",
      "前端 KaTeX 实时渲染，数学符号不再出现纯文本乱码",
    ],
  },
  {
    date: "2026-05-20",
    title: "苏格拉底教练核心引擎",
    icon: <Brain className="w-4 h-4" />,
    items: [
      "L0-L3 四层苏格拉底追问体系（讲解→复述→边界追问→反例挑战）",
      "五类错误诊断：概念理解、计算错误、符号使用、逻辑推理、尚未评估",
      "学习画像页面：知识掌握度、盲区图谱",
    ],
  },
  {
    date: "2026-05-19",
    title: "项目启动",
    icon: <Zap className="w-4 h-4" />,
    items: [
      "苏格拉底教练 v1.0 上线",
      "聊天对话、学习画像、知识树浏览",
      "SSE 流式对话，实时显示处理进度",
    ],
  },
];

export default function ChangelogPage() {
  return (
    <div className="min-h-screen bg-gradient-to-br from-primary-50 via-white to-purple-50">
      <div className="max-w-3xl mx-auto px-6 py-12">
        <div className="mb-10">
          <Link href="/" className="inline-flex items-center gap-1.5 text-sm text-gray-500 hover:text-primary-600 transition-colors mb-6">
            <ArrowLeft className="w-4 h-4" />
            返回首页
          </Link>
          <h1 className="text-3xl font-bold text-primary-900 mb-2">更新日志</h1>
          <p className="text-gray-500">苏格拉底教练 — 多智能体复变函数辅导系统</p>
          <div className="mt-3 inline-flex rounded-md bg-primary-100 px-2 py-0.5 text-xs font-medium text-primary-700">
            v3.0
          </div>
        </div>

        <div className="relative">
          <div className="absolute left-[19px] top-2 bottom-2 w-px bg-primary-200" />
          <div className="space-y-8">
            {changelog.map((entry, i) => (
              <div key={i} className="relative pl-12">
                <div className="absolute left-[11px] top-1 w-[17px] h-[17px] rounded-full bg-primary-100 border-2 border-primary-400 flex items-center justify-center">
                  {entry.icon}
                </div>
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

        <div className="mt-12 pt-6 border-t border-primary-100 text-center text-xs text-gray-400">
          第十五届中国软件杯 · 科大讯飞出题
        </div>
      </div>
    </div>
  );
}
