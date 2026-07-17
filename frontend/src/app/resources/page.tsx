"use client";

import { useEffect, useState } from "react";
import { BookOpen, FileText, GitBranch, Library, ArrowLeft } from "lucide-react";
import Link from "next/link";
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

export default function ResourcesPage() {
  const [resources, setResources] = useState<Resource[]>([]);
  const [tab, setTab] = useState("all");
  const [loading, setLoading] = useState(true);

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
            {filtered.map((r, i) => (
              <div key={i} className="rounded-xl bg-white p-5 shadow-sm hover:shadow-md transition-shadow">
                <div className="flex items-center gap-2 mb-2">
                  <span className="text-xs rounded-full bg-primary-50 px-2 py-0.5 text-primary-700">{r.type}</span>
                  {r.concept && <span className="text-xs text-gray-400">{r.concept}</span>}
                </div>
                <h3 className="font-semibold text-gray-900 mb-2">{r.title}</h3>
                {r.type === "mindmap" ? (
                  <MermaidBlock code={r.content} />
                ) : (
                  <p className="text-sm text-gray-600 line-clamp-3">{r.content.slice(0, 200)}</p>
                )}
                {r.created_at && (
                  <p className="text-xs text-gray-400 mt-2">
                    {new Date(r.created_at).toLocaleDateString("zh-CN")}
                  </p>
                )}
              </div>
            ))}
          </div>
        )}
      </div>
    </main>
  );
}
