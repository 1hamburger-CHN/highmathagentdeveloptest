"use client";

import { Trophy, Target, BarChart3, BookOpen, Compass, Zap, Search } from "lucide-react";

interface KnowledgeItem {
  concept_id: string;
  score: number;
  confidence: number;
}

interface BlindSpot {
  concept_id: string;
  error_type: string;
  frequency: number;
}

interface Behavior {
  response_style: string;
  resource_preference: string;
}

interface ResourceStats {
  total_resources: number;
  resource_counts: Record<string, number>;
}

interface ProfileSummaryCardProps {
  knowledgeMastery: KnowledgeItem[];
  blindSpots: BlindSpot[];
  behavior?: Behavior;
  resourceStats?: ResourceStats;
  conceptNames: Record<string, string>;
}

const STYLE_LABELS: Record<string, { icon: JSX.Element; label: string; desc: string }> = {
  cautious: {
    icon: <Search className="w-4 h-4" />,
    label: "谨慎型",
    desc: "倾向于确认后再作答",
  },
  exploratory: {
    icon: <Compass className="w-4 h-4" />,
    label: "探索型",
    desc: "喜欢尝试不同思路",
  },
  impulsive: {
    icon: <Zap className="w-4 h-4" />,
    label: "冲动型",
    desc: "快速作答，偶有疏漏",
  },
};

const PREFERENCE_LABELS: Record<string, { icon: JSX.Element; label: string }> = {
  visual: { icon: <BarChart3 className="w-4 h-4" />, label: "偏好可视化" },
  textual: { icon: <BookOpen className="w-4 h-4" />, label: "偏好文本" },
  interactive: { icon: <Target className="w-4 h-4" />, label: "偏好互动练习" },
};

const RESOURCE_TYPE_LABELS: Record<string, string> = {
  lecture: "讲义",
  exercise: "练习题",
  mindmap: "思维导图",
  intro: "介绍",
  reading: "拓展阅读",
};

/** Derive resource preference from actual generation counts, falling back to LLM label. */
function derivePreference(
  resourceStats?: ResourceStats,
  llmPreference?: string,
): { icon: JSX.Element; label: string; source: "behavior" | "llm" } | null {
  // Prefer real behavioral data
  if (resourceStats?.resource_counts) {
    const counts = resourceStats.resource_counts;
    const entries = Object.entries(counts);
    if (entries.length > 0) {
      const [top] = entries.sort((a, b) => b[1] - a[1]);
      const typeLabel = RESOURCE_TYPE_LABELS[top[0]] || top[0];
      return {
        icon: <BookOpen className="w-4 h-4" />,
        label: `最常生成：${typeLabel} (${top[1]}次)`,
        source: "behavior",
      };
    }
  }
  // Fallback to LLM-inferred preference
  if (llmPreference && PREFERENCE_LABELS[llmPreference]) {
    const p = PREFERENCE_LABELS[llmPreference];
    return { ...p, source: "llm" };
  }
  return null;
}

export default function ProfileSummaryCard({
  knowledgeMastery,
  blindSpots,
  behavior,
  resourceStats,
  conceptNames,
}: ProfileSummaryCardProps) {
  // Computed stats
  const assessed = knowledgeMastery.filter((k) => k.score > 0);
  const avgScore =
    assessed.length > 0
      ? assessed.reduce((s, k) => s + k.score, 0) / assessed.length
      : 0;
  const sorted = [...knowledgeMastery].sort((a, b) => b.score - a.score);
  const strongest = sorted[0];
  const weakest = [...sorted].reverse().find((k) => k.score > 0);

  // Behavior
  const style = behavior?.response_style ? STYLE_LABELS[behavior.response_style] : null;
  const preference = derivePreference(resourceStats, behavior?.resource_preference);

  const hasData = assessed.length > 0;

  return (
    <div className="rounded-2xl bg-white shadow-sm border border-gray-100 overflow-hidden">
      {/* Header */}
      <div className="px-5 py-4 border-b border-gray-100">
        <h3 className="font-semibold text-gray-900 flex items-center gap-2">
          <BarChart3 className="w-5 h-5 text-primary-500" />
          学习概览
        </h3>
      </div>

      {!hasData ? (
        <div className="px-5 py-10 text-center text-gray-400 text-sm">
          完成诊断后将自动生成概览
        </div>
      ) : (
        <div className="p-5 space-y-5">
          {/* Stats row */}
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
            <StatBox
              value={`${assessed.length}/19`}
              label="已评估概念"
              color="text-primary-600"
              bg="bg-primary-50"
            />
            <StatBox
              value={`${Math.round(avgScore * 100)}%`}
              label="平均掌握度"
              color="text-emerald-600"
              bg="bg-emerald-50"
            />
            <StatBox
              value={String(blindSpots.length)}
              label="发现盲区"
              color="text-amber-600"
              bg="bg-amber-50"
            />
            <StatBox
              value={String(resourceStats?.total_resources ?? 0)}
              label="生成资源"
              color="text-indigo-600"
              bg="bg-indigo-50"
            />
          </div>

          {/* Highlights: strongest & weakest */}
          {(strongest || weakest) && (
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
              {strongest && strongest.score > 0 && (
                <div className="flex items-center gap-3 rounded-xl bg-emerald-50 px-4 py-3">
                  <Trophy className="w-5 h-5 text-emerald-500 flex-shrink-0" />
                  <div className="min-w-0">
                    <p className="text-xs text-emerald-600 font-medium">最强概念</p>
                    <p className="text-sm text-emerald-900 font-semibold truncate">
                      {conceptNames[strongest.concept_id] || strongest.concept_id}
                      <span className="ml-1.5 text-emerald-600">
                        {Math.round(strongest.score * 100)}%
                      </span>
                    </p>
                  </div>
                </div>
              )}
              {weakest && weakest.score > 0 && weakest.concept_id !== strongest?.concept_id && (
                <div className="flex items-center gap-3 rounded-xl bg-amber-50 px-4 py-3">
                  <Target className="w-5 h-5 text-amber-500 flex-shrink-0" />
                  <div className="min-w-0">
                    <p className="text-xs text-amber-600 font-medium">待加强</p>
                    <p className="text-sm text-amber-900 font-semibold truncate">
                      {conceptNames[weakest.concept_id] || weakest.concept_id}
                      <span className="ml-1.5 text-amber-600">
                        {Math.round(weakest.score * 100)}%
                      </span>
                    </p>
                  </div>
                </div>
              )}
            </div>
          )}

          {/* Resource distribution mini bar */}
          {resourceStats?.resource_counts &&
            Object.keys(resourceStats.resource_counts).length > 0 && (
              <div className="space-y-1.5">
                <p className="text-xs text-gray-500 font-medium">资源生成分布</p>
                <div className="flex h-2 rounded-full overflow-hidden bg-gray-100">
                  {Object.entries(resourceStats.resource_counts).map(([type, count]) => {
                    const total = Object.values(resourceStats.resource_counts).reduce(
                      (a, b) => a + b,
                      0,
                    );
                    const pct = total > 0 ? (count / total) * 100 : 0;
                    const colors: Record<string, string> = {
                      lecture: "bg-blue-400",
                      exercise: "bg-amber-400",
                      mindmap: "bg-purple-400",
                      intro: "bg-emerald-400",
                      reading: "bg-cyan-400",
                    };
                    return (
                      <div
                        key={type}
                        className={`${colors[type] || "bg-gray-400"} h-full transition-all`}
                        style={{ width: `${pct}%` }}
                        title={`${RESOURCE_TYPE_LABELS[type] || type}: ${count}`}
                      />
                    );
                  })}
                </div>
                <div className="flex flex-wrap gap-x-3 gap-y-0.5">
                  {Object.entries(resourceStats.resource_counts).map(([type, count]) => (
                    <span key={type} className="text-xs text-gray-500">
                      {RESOURCE_TYPE_LABELS[type] || type} {count}
                    </span>
                  ))}
                </div>
              </div>
            )}

          {/* Learning style + preference badges */}
          {(style || preference) && (
            <div className="flex flex-wrap gap-2">
              {style && (
                <div
                  className="inline-flex items-center gap-1.5 rounded-full bg-purple-50 border border-purple-200 px-3 py-1.5"
                  title={style.desc}
                >
                  <span className="text-purple-500">{style.icon}</span>
                  <span className="text-sm font-medium text-purple-800">{style.label}</span>
                  <span className="text-xs text-purple-500 hidden sm:inline">· {style.desc}</span>
                </div>
              )}
              {preference && (
                <div
                  className="inline-flex items-center gap-1.5 rounded-full bg-indigo-50 border border-indigo-200 px-3 py-1.5"
                  title={
                    preference.source === "behavior" ? "基于实际生成记录" : "基于对话推断"
                  }
                >
                  <span className="text-indigo-500">{preference.icon}</span>
                  <span className="text-sm font-medium text-indigo-800">{preference.label}</span>
                  {preference.source === "llm" && (
                    <span className="text-xs text-indigo-400 hidden sm:inline">· 推断</span>
                  )}
                </div>
              )}
            </div>
          )}
        </div>
      )}
    </div>
  );
}

function StatBox({
  value,
  label,
  color,
  bg,
}: {
  value: string;
  label: string;
  color: string;
  bg: string;
}) {
  return (
    <div className={`rounded-xl ${bg} px-3 py-3 text-center`}>
      <p className={`text-xl font-bold ${color}`}>{value}</p>
      <p className="text-xs text-gray-500 mt-0.5">{label}</p>
    </div>
  );
}
