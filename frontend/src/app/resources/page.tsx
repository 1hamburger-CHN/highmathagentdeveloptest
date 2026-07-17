"use client";

import { useEffect, useState } from "react";
import { BookOpen, FileText, GitBranch, Library, ArrowLeft, Plus } from "lucide-react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import StreamingMarkdown from "@/components/chat/StreamingMarkdown";
import MermaidBlock from "@/components/chat/MermaidBlock";

const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? "";

type Resource = { type: string; title: string; content: string; concept: string; created_at: string };

const TABS = [
  { key: "all", label: "全部", icon: Library },
  { key: "lecture", label: "讲义", icon: BookOpen },
  { key: "exercise", label: "练习题", icon: FileText },
  { key: "mindmap", label: "思维导图", icon: GitBranch },
  { key: "reading", label: "拓展阅读", icon: BookOpen },
];

const CONCEPTS = [
  "复数定义与运算", "C-R方程", "调和函数", "指数与对数函数",
  "复积分定义与性质", "Cauchy-Goursat定理", "Cauchy积分与高阶导数",
  "泰勒级数", "洛朗级数", "孤立奇点分类", "留数与留数定理",
  "共形映射与Mobius变换", "傅里叶变换", "拉普拉斯变换",
];

export default function ResourcesPage() {
  const [resources, setResources] = useState<Resource[]>([]);
  const [tab, setTab] = useState("all");
  const [loading, setLoading] = useState(true);
  const [showGenerate, setShowGenerate] = useState(false);
  const [genConcept, setGenConcept] = useState("");
  const [expandedIds, setExpandedIds] = useState<Set<number>>(new Set());
  const router = useRouter();

  const quickGenerate = (type: string) => {
    const concept = genConcept || "复变函数";
    const prompts: Record<string, string> = {
      lecture: `帮我生成${concept}的教学讲义`,
      exercise: `帮我生成${concept}的分层练习题`,
      mindmap: `帮我生成${concept}的思维导图`,
      reading: `帮我生成${concept}的拓展阅读材料`,
    };
    const msg = prompts[type] || `帮我生成${concept}的学习资源`;
    router.push(`/chat?msg=${encodeURIComponent(msg)}`);
  };

  useEffect(() => {
    const uid = localStorage.getItem("tutor_user_id") || "anonymous";
    fetch(`${API_BASE}/api/sessions/${uid}/resources`)
      .then((r) => r.json())
      .then((data) => setResources(data.resources || []))
      .catch(() => {})
      .finally(() => setLoading(false));
  }, []);

  const filtered = tab === "all" ? resources : resources.filter((r) => r.type === tab);

  return (
    <main className="min-h-screen bg-gray-50 p-6">
      <div className="max-w-4xl mx-auto">
        <Link href="/" className="inline-flex items-center gap-1 text-sm text-gray-500 hover:text-primary-600 mb-6">
          <ArrowLeft className="w-4 h-4" /> 返回首页
        </Link>
        <h1 className="text-2xl font-bold text-primary-900 mb-6">资源中心</h1>

        {/* Quick Generate */}
        <div className="mb-6 rounded-xl bg-white border border-gray-200 p-4">
          <button onClick={() => setShowGenerate(!showGenerate)}
            className="flex items-center gap-1.5 text-sm font-medium text-primary-600 hover:text-primary-700">
            <Plus className="w-4 h-4" /> 快速生成新资源
          </button>
          {showGenerate && (
            <div className="mt-3 pt-3 border-t border-gray-100">
              <div className="flex items-center gap-3 mb-3">
                <span className="text-xs text-gray-500 whitespace-nowrap">知识点：</span>
                <select value={genConcept} onChange={(e) => setGenConcept(e.target.value)}
                  className="flex-1 rounded-lg border border-gray-300 px-3 py-1.5 text-sm text-gray-700 focus:border-primary-400 focus:outline-none">
                  <option value="">选一个知识点（或留空默认）</option>
                  {CONCEPTS.map((c) => <option key={c} value={c}>{c}</option>)}
                </select>
              </div>
              <div className="flex flex-wrap gap-2">
                {TABS.filter(t => t.key !== "all").map((t) => (
                  <button key={t.key} onClick={() => quickGenerate(t.key)}
                    className="inline-flex items-center gap-1.5 rounded-lg border border-primary-200 bg-primary-50 px-3 py-1.5 text-xs font-medium text-primary-700 hover:bg-primary-100 transition-colors"
                  >
                    <t.icon className="w-3.5 h-3.5" /> 生成{t.label}
                  </button>
                ))}
              </div>
            </div>
          )}
        </div>

        <div className="flex gap-2 mb-6 overflow-x-auto">
          {TABS.map((t) => (
            <button key={t.key} onClick={() => setTab(t.key)}
              className={`flex items-center gap-1.5 rounded-lg px-4 py-2 text-sm font-medium transition-colors ${
                tab === t.key ? "bg-primary-600 text-white" : "bg-white text-gray-600 hover:bg-gray-100"
              }`}>
              <t.icon className="w-4 h-4" /> {t.label}
            </button>
          ))}
        </div>

        {loading ? (
          <div className="animate-pulse space-y-4">
            {[1,2,3].map((i) => <div key={i} className="h-24 rounded-xl bg-gray-200" />)}
          </div>
        ) : filtered.length === 0 ? (
          <div className="text-center py-16 text-gray-400">
            <Library className="w-12 h-12 mx-auto mb-3 text-gray-300" />
            <p>还没有资源</p>
            <p className="text-sm mt-1">去聊天页面请求生成学习资源吧</p>
          </div>
        ) : (
          <div className="grid gap-4">
            {filtered.map((r, i) => {
              const isExpanded = expandedIds.has(i);
              const isLong = r.content.length > 400;
              return (
              <div key={i} className="rounded-xl bg-white p-5 shadow-sm hover:shadow-md transition-shadow">
                <div className="flex items-center gap-2 mb-2">
                  <span className="text-xs rounded-full bg-primary-50 px-2 py-0.5 text-primary-700">{r.type}</span>
                  {r.concept && <span className="text-xs text-gray-400">{r.concept}</span>}
                </div>
                <h3 className="font-semibold text-gray-900 mb-2">{r.title}</h3>
                <div className={`${isExpanded || !isLong ? "" : "max-h-[200px] overflow-hidden relative"} prose prose-sm max-w-none text-gray-700 prose-headings:text-gray-900 prose-a:text-primary-600 prose-code:text-primary-700 prose-strong:text-gray-900`}>
                  {r.type === "mindmap" ? (
                    <MermaidBlock code={r.content} />
                  ) : (
                    <StreamingMarkdown content={r.content} />
                  )}
                  {isLong && !isExpanded && (
                    <div className="absolute bottom-0 left-0 right-0 h-16 bg-gradient-to-t from-white to-transparent" />
                  )}
                </div>
                {isLong && (
                  <button onClick={() => {
                    setExpandedIds(prev => {
                      const next = new Set(prev);
                      if (next.has(i)) next.delete(i); else next.add(i);
                      return next;
                    });
                  }}
                    className="mt-2 text-xs text-primary-600 hover:text-primary-700 font-medium"
                  >
                    {isExpanded ? "收起 ▲" : "展开全部 ▼"}
                  </button>
                )}
                {r.created_at && (
                  <p className="text-xs text-gray-400 mt-2">
                    {new Date(r.created_at).toLocaleDateString("zh-CN")}
                  </p>
                )}
              </div>
            )})}
          </div>
        )}
      </div>
    </main>
  );
}
