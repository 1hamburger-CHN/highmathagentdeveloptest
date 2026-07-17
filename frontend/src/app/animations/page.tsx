"use client";

import { useEffect, useState, useMemo } from "react";
import { Film, ArrowLeft, ChevronDown, ChevronRight, Play, X, FileVideo, BookOpen } from "lucide-react";
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

const TEMPLATE_NAMES: Record<string, string> = {
  ResidueTheorem: "留数定理",
  ConformalMapping: "共形映射",
  ContourIntegration: "围道积分",
  CREquations: "C-R 方程",
  TaylorSeries: "泰勒级数",
  LaurentSeries: "洛朗级数",
  PoleClassification: "奇点分类",
  BranchCut: "分支切割",
  RiemannSphere: "黎曼球面",
  ComplexPlaneTransform: "复平面变换",
};

function formatTemplate(template: string): string {
  return TEMPLATE_NAMES[template] || template;
}

const TEMPLATE_EXPLANATIONS: Record<string, string> = {
  ResidueTheorem:
    "**留数定理**将闭合围道积分转化为围道内奇点的留数之和：$\\oint_C f(z)dz = 2\\pi i \\sum \\operatorname{Res}[f, z_k]$。动画中围道内的奇点（绿色）贡献留数，围道外的奇点（灰色）不参与计算。这是复分析中计算实积分的最强工具。",

  ConformalMapping:
    "**共形映射**保持曲线之间的夹角不变。动画展示 $f(z)=z^2$ 将复平面网格映射到像平面的变形过程。注意观察网格线在映射后仍保持正交（保角性），但在 $z=0$ 处导数 $f'(0)=0$，共形性破坏。",

  ContourIntegration:
    "**围道积分**是复积分的基本形式。红点沿闭合围道运动，模拟积分参数的遍历。复积分不仅取决于端点，还取决于路径；对于解析函数，在单连通区域内积分与路径无关（Cauchy-Goursat 定理）。",

  CREquations:
    "**Cauchy-Riemann 方程**是判断复变函数可导的充要条件：$\\frac{\\partial u}{\\partial x} = \\frac{\\partial v}{\\partial y},\\quad \\frac{\\partial u}{\\partial y} = -\\frac{\\partial v}{\\partial x}$。动画展示沿实轴（红）和虚轴（绿）分别趋近 $z_0$，两方向导数相等才是解析函数。",

  TaylorSeries:
    "**泰勒级数**将解析函数展开为幂级数：$f(z) = \\sum a_n (z-z_0)^n$。在收敛圆内逐项叠加逼近目标函数。收敛半径 = 展开点到最近奇点的距离，级数在收敛圆内可逐项求导和积分。",

  LaurentSeries:
    "**洛朗级数**允许负幂项：$f(z) = \\sum_{n=-\\infty}^{\\infty} a_n (z-z_0)^n$。正幂项从内圆向外展开，负幂项从外圆向内展开，在环形区域内收敛。是留数计算的理论基础。",

  PoleClassification:
    "**孤立奇点**分三种：可去奇点（极限存在有限，如 $\\sin z/z$）、极点（$|f|\\to\\infty$，如 $1/z$）、本性奇点（极限不存在，函数值在任意邻域内稠密）。区分类型是应用留数定理的第一步。",

  BranchCut:
    "**分支切割**处理多值函数的\"一对多\"问题。以 $\\operatorname{Ln}(z)$ 为例，绕原点旋转一周后虚部增加 $2\\pi$，进入下一个黎曼面。分支切割（红线）通常选在负实轴，割开复平面使函数单值化。",

  RiemannSphere:
    "**黎曼球面**通过球极投影将复平面一一映射到单位球面上。北极对应无穷远点 $\\infty$，南极对应原点。这种紧化处理使 $\\infty$ 成为一个\"正常的点\"，极大简化了复分析的许多定理。",

  ComplexPlaneTransform:
    "**复平面变换**研究复变函数如何改变复平面上的几何形状。四种基本变换为：平移 $z\\to z+a$、旋转 $z\\to e^{i\\theta}z$、缩放 $z\\to kz$、反演 $z\\to 1/z$。共形映射由这些基本变换复合而成。",
};

export default function AnimationsPage() {
  const [animations, setAnimations] = useState<Animation[]>([]);
  const [loading, setLoading] = useState(true);
  const [expandedGroups, setExpandedGroups] = useState<Set<string>>(new Set());
  const [expandedExplanations, setExpandedExplanations] = useState<Set<string>>(new Set());
  const [previewUrl, setPreviewUrl] = useState<string | null>(null);
  const [previewName, setPreviewName] = useState<string>("");

  useEffect(() => {
    fetch(`${API_BASE}/api/animation/list`)
      .then((r) => r.json())
      .then((data) => {
        const list = data.animations || [];
        setAnimations(list);
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

  function toggleExplanation(template: string) {
    setExpandedExplanations((prev) => {
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
                    <span className="font-semibold text-gray-900">{formatTemplate(template)}</span>
                    <span className="text-xs text-gray-400">({items.length})</span>
                  </div>
                </button>

                {expandedGroups.has(template) && (
                  <div className="border-t border-gray-100">
                    {/* Explanation toggle button */}
                    {TEMPLATE_EXPLANATIONS[template] && (
                      <>
                        <button
                          onClick={(e) => { e.stopPropagation(); toggleExplanation(template); }}
                          className="w-full flex items-center gap-2 px-5 py-2.5 text-sm text-primary-600 hover:bg-primary-50 transition-colors"
                        >
                          <BookOpen className="w-4 h-4" />
                          <span>查看讲解</span>
                          {expandedExplanations.has(template) ? (
                            <ChevronDown className="w-3.5 h-3.5 ml-auto" />
                          ) : (
                            <ChevronRight className="w-3.5 h-3.5 ml-auto" />
                          )}
                        </button>
                        {expandedExplanations.has(template) && (
                          <div className="px-5 py-3 bg-blue-50/50 border-y border-blue-100">
                            <p className="text-sm text-gray-700 leading-relaxed whitespace-pre-line">
                              {TEMPLATE_EXPLANATIONS[template]}
                            </p>
                          </div>
                        )}
                      </>
                    )}

                    {/* Video list */}
                    <div className="divide-y divide-gray-50">
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
