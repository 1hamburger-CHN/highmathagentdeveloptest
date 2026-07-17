"use client";

import { useEffect, useState, useMemo } from "react";
import { Film, ArrowLeft, ChevronDown, ChevronRight, Play, X, FileVideo } from "lucide-react";
import Link from "next/link";

const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? "";

type Animation = {
  name: string;
  url: string;
  template: string;
  size_kb: number;
  created_at: number;
};

function formatDate(ts: number): string {
  return new Date(ts * 1000).toLocaleDateString("zh-CN", {
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
  });
}

function formatSize(kb: number): string {
  if (kb >= 1024) return `${(kb / 1024).toFixed(1)} MB`;
  return `${kb} KB`;
}

export default function AnimationsPage() {
  const [animations, setAnimations] = useState<Animation[]>([]);
  const [loading, setLoading] = useState(true);
  const [expandedGroups, setExpandedGroups] = useState<Set<string>>(new Set());
  const [previewUrl, setPreviewUrl] = useState<string | null>(null);
  const [previewName, setPreviewName] = useState<string>("");

  useEffect(() => {
    fetch(`${API_BASE}/api/animation/list`)
      .then((r) => r.json())
      .then((data) => {
        const list = data.animations || [];
        setAnimations(list);
        // Expand all groups by default
        setExpandedGroups(new Set(list.map((a: Animation) => a.template)));
      })
      .catch(() => {})
      .finally(() => setLoading(false));
  }, []);

  const grouped = useMemo(() => {
    const groups = new Map<string, Animation[]>();
    for (const a of animations) {
      const key = a.template || "其他";
      if (!groups.has(key)) groups.set(key, []);
      groups.get(key)!.push(a);
    }
    return Array.from(groups.entries());
  }, [animations]);

  function toggleGroup(template: string) {
    setExpandedGroups((prev) => {
      const next = new Set(prev);
      if (next.has(template)) next.delete(template);
      else next.add(template);
      return next;
    });
  }

  function openPreview(anim: Animation) {
    setPreviewUrl(anim.url);
    setPreviewName(anim.name);
  }

  function closePreview() {
    setPreviewUrl(null);
    setPreviewName("");
  }

  return (
    <main className="min-h-screen bg-gray-50 p-6">
      <div className="max-w-4xl mx-auto">
        <Link
          href="/"
          className="inline-flex items-center gap-1 text-sm text-gray-500 hover:text-primary-600 mb-6"
        >
          <ArrowLeft className="w-4 h-4" /> 返回首页
        </Link>

        <h1 className="text-2xl font-bold text-primary-900 mb-6">动画浏览</h1>

        {loading ? (
          <div className="animate-pulse space-y-4">
            {[1, 2, 3].map((i) => (
              <div key={i} className="h-24 rounded-xl bg-gray-200" />
            ))}
          </div>
        ) : animations.length === 0 ? (
          <div className="text-center py-16 text-gray-400">
            <Film className="w-12 h-12 mx-auto mb-3 text-gray-300" />
            <p>还没有动画</p>
            <p className="text-sm mt-1">去聊天页面请求吧</p>
          </div>
        ) : (
          <div className="grid gap-4">
            {grouped.map(([template, items]) => (
              <div key={template} className="rounded-xl bg-white shadow-sm overflow-hidden">
                <button
                  onClick={() => toggleGroup(template)}
                  className="w-full flex items-center justify-between px-5 py-3.5 hover:bg-gray-50 transition-colors"
                >
                  <div className="flex items-center gap-2">
                    {expandedGroups.has(template) ? (
                      <ChevronDown className="w-4 h-4 text-gray-400" />
                    ) : (
                      <ChevronRight className="w-4 h-4 text-gray-400" />
                    )}
                    <span className="font-semibold text-gray-900">{template}</span>
                    <span className="text-xs text-gray-400">({items.length})</span>
                  </div>
                </button>

                {expandedGroups.has(template) && (
                  <div className="border-t border-gray-100 divide-y divide-gray-50">
                    {items.map((anim) => (
                      <div
                        key={anim.name}
                        className="flex items-center gap-4 px-5 py-3 hover:bg-gray-50 transition-colors cursor-pointer"
                        onClick={() => openPreview(anim)}
                      >
                        <div className="flex-shrink-0 w-10 h-10 rounded-lg bg-primary-100 flex items-center justify-center">
                          <Play className="w-5 h-5 text-primary-600" />
                        </div>
                        <div className="flex-1 min-w-0">
                          <p className="text-sm font-medium text-gray-900 truncate">
                            {anim.name}
                          </p>
                          <p className="text-xs text-gray-400 mt-0.5">
                            {formatSize(anim.size_kb)} · {formatDate(anim.created_at)}
                          </p>
                        </div>
                        <FileVideo className="w-4 h-4 text-gray-300 flex-shrink-0" />
                      </div>
                    ))}
                  </div>
                )}
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Preview Modal */}
      {previewUrl && (
        <div
          className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm"
          onClick={closePreview}
        >
          <div
            className="relative bg-white rounded-2xl shadow-2xl max-w-3xl w-full mx-4 overflow-hidden"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="flex items-center justify-between px-5 py-3 border-b border-gray-100">
              <h3 className="font-semibold text-gray-900 truncate">{previewName}</h3>
              <button
                onClick={closePreview}
                className="p-1 rounded-lg hover:bg-gray-100 transition-colors"
              >
                <X className="w-5 h-5 text-gray-500" />
              </button>
            </div>
            <div className="bg-black">
              <video
                src={previewUrl}
                controls
                autoPlay
                className="w-full max-h-[70vh]"
                style={{ aspectRatio: "16/9" }}
              />
            </div>
          </div>
        </div>
      )}
    </main>
  );
}
