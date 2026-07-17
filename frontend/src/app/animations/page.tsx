"use client";

import { useEffect, useState, useMemo } from "react";
import { Film, ArrowLeft, ChevronDown, ChevronRight, Play, X, FileVideo, BookOpen, Info } from "lucide-react";
import Link from "next/link";
import StreamingMarkdown from "@/components/chat/StreamingMarkdown";

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
    year: "numeric", month: "2-digit", day: "2-digit",
    hour: "2-digit", minute: "2-digit",
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
    "**留数定理**将闭合围道积分转化为围道内奇点的留数之和：$\\oint_C f(z)dz = 2\\pi i \\sum \\operatorname{Res}[f, z_k]$。围道内的奇点贡献留数，围道外的奇点不参与计算。这是复分析中计算实积分的最强工具。",
  ConformalMapping:
    "**共形映射**保持曲线间夹角不变。动画展示 $f(z)=z^2$ 将复平面网格映射到像平面。注意网格线在映射后仍保持正交（保角性），但在 $z=0$ 处导数 $f'(0)=0$ 导致共形性破坏。",
  ContourIntegration:
    "**围道积分**是复积分的基本形式。红点沿闭合围道运动，模拟积分参数遍历。对于解析函数，在单连通区域内积分与路径无关（Cauchy-Goursat 定理）。",
  CREquations:
    "**Cauchy-Riemann 方程**是判断复变函数可导的充要条件：$\\frac{\\partial u}{\\partial x} = \\frac{\\partial v}{\\partial y},\\quad \\frac{\\partial u}{\\partial y} = -\\frac{\\partial v}{\\partial x}$。动画展示沿实轴（红）和虚轴（绿）分别趋近，两方向导数相等才解析。",
  TaylorSeries:
    "**泰勒级数**将解析函数展开为幂级数：$f(z) = \\sum a_n (z-z_0)^n$。在收敛圆内逐项叠加逼近目标函数。收敛半径 = 展开点到最近奇点的距离。",
  LaurentSeries:
    "**洛朗级数**允许负幂项：$f(z) = \\sum_{n=-\\infty}^{\\infty} a_n (z-z_0)^n$。正幂项从内向外、负幂项从外向内，在环形区域内收敛。是留数计算的理论基础。",
  PoleClassification:
    "**孤立奇点**分三种：可去奇点（极限有限，如 $\\sin z/z$）、极点（$|f|\\to\\infty$，如 $1/z$）、本性奇点（极限不存在，函数值稠密）。区分类型是应用留数定理的第一步。",
  BranchCut:
    "**分支切割**处理多值函数。以 $\\operatorname{Ln}(z)$ 为例，绕原点一周虚部增加 $2\\pi$，进入下一个黎曼面。分支切割（红线）选在负实轴，使函数单值化。",
  RiemannSphere:
    "**黎曼球面**通过球极投影将复平面映射到单位球面。北极对应 $\\infty$，南极对应原点。使 $\\infty$ 成为\"正常点\"，简化复分析定理。",
  ComplexPlaneTransform:
    "**复平面变换**的四种基本形式：平移 $z\\to z+a$、旋转 $z\\to e^{i\\theta}z$、缩放 $z\\to kz$、反演 $z\\to 1/z$。共形映射由这些基本变换复合而成。",
};

// Per-video explanations for templates with multiple videos
const PER_VIDEO_DETAILS: Record<string, string[]> = {
  ResidueTheorem: [
    "示例 1：极点 $z=i$ 和 $z=-i$，其中 $z=i$ 在围道内。验证 $\\oint_C \\frac{1}{z^2+1}dz = 2\\pi i \\cdot \\operatorname{Res}[f, i]$。",
    "示例 2：同上极点配置，围道半径不同。对比不同围道下留数计算的一致性。",
    "示例 3：单极点在围道内的基础演示，$z=i$ 为围道内唯一奇点。",
  ],
  ContourIntegration: [
    "示例 1：圆形围道 $|z|=2$，展示参数化路径 $z(t)=2e^{it}$ 上的积分遍历过程。",
    "示例 2：另一个圆形围道配置，对比不同半径下的积分行为。",
  ],
};

export default function AnimationsPage() {
  const [animations, setAnimations] = useState<Animation[]>([]);
  const [loading, setLoading] = useState(true);
  const [expandedGroups, setExpandedGroups] = useState<Set<string>>(new Set());
  const [expandedExplanations, setExpandedExplanations] = useState<Set<string>>(new Set());
  const [expandedVideoInfo, setExpandedVideoInfo] = useState<Set<string>>(new Set());
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

  function toggleVideoInfo(animKey: string) {
    setExpandedVideoInfo((prev) => {
      const next = new Set(prev);
      if (next.has(animKey)) next.delete(animKey);
      else next.add(animKey);
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

  function getDisplayName(anim: Animation, index: number, total: number): string {
    const cnName = formatTemplate(anim.template);
    if (total <= 1) return cnName;
    const details = PER_VIDEO_DETAILS[anim.template];
    if (details && index < details.length) {
      return `${cnName} · 示例 ${index + 1}`;
    }
    return `${cnName} · 视频 ${index + 1}`;
  }

  function getVideoDetail(anim: Animation, index: number, total: number): string | null {
    if (total <= 1) return null;
    const details = PER_VIDEO_DETAILS[anim.template];
    if (details && index < details.length) return details[index];
    return `${formatTemplate(anim.template)}的第 ${index + 1} 个动画演示。`;
  }

  return (
    <main className="min-h-screen bg-gray-50 p-6">
      <div className="max-w-4xl mx-auto">
        <Link href="/" className="inline-flex items-center gap-1 text-sm text-gray-500 hover:text-primary-600 mb-6">
          <ArrowLeft className="w-4 h-4" /> 返回首页
        </Link>
        <h1 className="text-2xl font-bold text-primary-900 mb-6">动画浏览</h1>

        {loading ? (
          <div className="animate-pulse space-y-4">
            {[1, 2, 3].map((i) => <div key={i} className="h-24 rounded-xl bg-gray-200" />)}
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
                    {expandedGroups.has(template) ? <ChevronDown className="w-4 h-4 text-gray-400" /> : <ChevronRight className="w-4 h-4 text-gray-400" />}
                    <span className="font-semibold text-gray-900">{formatTemplate(template)}</span>
                    <span className="text-xs text-gray-400">({items.length})</span>
                  </div>
                </button>

                {expandedGroups.has(template) && (
                  <div className="border-t border-gray-100">
                    {/* Overall concept explanation */}
                    {TEMPLATE_EXPLANATIONS[template] && (
                      <>
                        <button
                          onClick={(e) => { e.stopPropagation(); toggleExplanation(template); }}
                          className="w-full flex items-center gap-2 px-5 py-2.5 text-sm text-primary-600 hover:bg-primary-50 transition-colors"
                        >
                          <BookOpen className="w-4 h-4" />
                          <span>查看讲解</span>
                          {expandedExplanations.has(template) ? <ChevronDown className="w-3.5 h-3.5 ml-auto" /> : <ChevronRight className="w-3.5 h-3.5 ml-auto" />}
                        </button>
                        {expandedExplanations.has(template) && (
                          <div className="px-5 py-3 bg-blue-50/50 border-y border-blue-100">
                            <div className="text-sm text-gray-700 leading-relaxed prose prose-sm max-w-none prose-p:text-gray-700 prose-strong:text-gray-900">
                              <StreamingMarkdown content={TEMPLATE_EXPLANATIONS[template]} />
                            </div>
                          </div>
                        )}
                      </>
                    )}

                    {/* Video list */}
                    <div className="divide-y divide-gray-50">
                      {items.map((anim, idx) => {
                        const displayName = getDisplayName(anim, idx, items.length);
                        const videoDetail = getVideoDetail(anim, idx, items.length);
                        const animKey = anim.name;

                        return (
                          <div key={animKey}>
                            <div
                              className="flex items-center gap-4 px-5 py-3 hover:bg-gray-50 transition-colors cursor-pointer"
                              onClick={() => openPreview(anim)}
                            >
                              <div className="flex-shrink-0 w-10 h-10 rounded-lg bg-primary-100 flex items-center justify-center">
                                <Play className="w-5 h-5 text-primary-600" />
                              </div>
                              <div className="flex-1 min-w-0">
                                <p className="text-sm font-medium text-gray-900 truncate">{displayName}</p>
                                <p className="text-xs text-gray-400 mt-0.5">
                                  {formatSize(anim.size_kb)} · {formatDate(anim.created_at)}
                                </p>
                              </div>
                              {videoDetail && (
                                <button
                                  onClick={(e) => { e.stopPropagation(); toggleVideoInfo(animKey); }}
                                  className="flex-shrink-0 p-1.5 rounded-lg hover:bg-amber-50 text-amber-500 transition-colors"
                                  title="查看本视频内容"
                                >
                                  <Info className="w-4 h-4" />
                                </button>
                              )}
                              <FileVideo className="w-4 h-4 text-gray-300 flex-shrink-0" />
                            </div>
                            {/* Per-video detail dropdown */}
                            {videoDetail && expandedVideoInfo.has(animKey) && (
                              <div className="px-5 py-2.5 bg-amber-50/50 border-t border-amber-100 mx-5 mb-2 rounded-lg">
                                <p className="text-xs text-gray-600">{videoDetail}</p>
                              </div>
                            )}
                          </div>
                        );
                      })}
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
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm" onClick={closePreview}>
          <div className="relative bg-white rounded-2xl shadow-2xl max-w-3xl w-full mx-4 overflow-hidden" onClick={(e) => e.stopPropagation()}>
            <div className="flex items-center justify-between px-5 py-3 border-b border-gray-100">
              <h3 className="font-semibold text-gray-900 truncate">{previewName}</h3>
              <button onClick={closePreview} className="p-1 rounded-lg hover:bg-gray-100 transition-colors">
                <X className="w-5 h-5 text-gray-500" />
              </button>
            </div>
            <div className="bg-black">
              <video src={previewUrl} controls autoPlay className="w-full max-h-[70vh]" style={{ aspectRatio: "16/9" }} />
            </div>
          </div>
        </div>
      )}
    </main>
  );
}
