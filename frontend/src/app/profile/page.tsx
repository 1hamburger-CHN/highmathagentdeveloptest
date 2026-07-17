"use client";

import { useEffect, useState, useMemo } from "react";
import { Brain, Target, Activity, ArrowLeft, TrendingUp, AlertTriangle } from "lucide-react";
import Link from "next/link";
import RadarChart from "@/components/profile/RadarChart";
import KnowledgeHeatmap from "@/components/profile/KnowledgeHeatmap";
import BlindSpotAlert from "@/components/profile/BlindSpotAlert";

const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? "";

type Profile = {
  knowledge_mastery: { concept_id: string; score: number; confidence: number }[];
  blind_spots: { concept_id: string; error_type: string; frequency: number }[];
  behavior: { response_style: string; resource_preference: string };
};

const CONCEPT_NAMES: Record<string, string> = {
  "complex-1.1": "复数定义与运算",
  "complex-1.2": "几何表示与棣莫弗公式",
  "complex-1.3": "复数的n次方根",
  "complex-2.1": "复变函数的极限与连续",
  "complex-2.2": "C-R方程",
  "complex-2.3": "调和函数",
  "complex-3.1": "指数与对数函数",
  "complex-3.2": "幂函数与三角函数",
  "complex-4.1": "复积分定义与性质",
  "complex-4.2": "Cauchy-Goursat定理",
  "complex-4.3": "Cauchy积分与高阶导数",
  "complex-5.1": "泰勒级数",
  "complex-5.2": "洛朗级数",
  "complex-6.1": "孤立奇点分类",
  "complex-6.2": "留数与留数定理",
  "complex-6.3": "留数在实积分中的应用",
  "complex-7.1": "共形映射与Mobius变换",
};

const ERROR_TYPE_LABELS: Record<string, string> = {
  concept: "概念理解",
  calculation: "计算错误",
  symbol: "符号使用",
  logic: "逻辑推理",
  prerequisite: "前置缺失",
};

const CHAPTER_MAP: { label: string; concepts: string[] }[] = [
  { label: "复数与复平面", concepts: ["complex-1.1", "complex-1.2", "complex-1.3"] },
  { label: "解析函数", concepts: ["complex-2.1", "complex-2.2", "complex-2.3"] },
  { label: "初等复函数", concepts: ["complex-3.1", "complex-3.2"] },
  { label: "复积分", concepts: ["complex-4.1", "complex-4.2", "complex-4.3"] },
  { label: "级数展开", concepts: ["complex-5.1", "complex-5.2"] },
  { label: "留数定理", concepts: ["complex-6.1", "complex-6.2", "complex-6.3"] },
  { label: "共形映射", concepts: ["complex-7.1"] },
];

function buildRadarData(mastery: { concept_id: string; score: number }[]) {
  const scoreMap = Object.fromEntries(mastery.map((m) => [m.concept_id, m.score]));
  return CHAPTER_MAP.map((ch) => {
    const avg = ch.concepts.length > 0
      ? ch.concepts.reduce((sum, cid) => sum + (scoreMap[cid] || 0), 0) / ch.concepts.length
      : 0;
    return { label: ch.label, value: avg };
  });
}

export default function ProfilePage() {
  const [profile, setProfile] = useState<Profile | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const uid = typeof window !== "undefined"
      ? localStorage.getItem("tutor_user_id") || "anonymous"
      : "anonymous";
    fetch(`${API_BASE}/api/profile/${uid}`)
      .then((r) => r.json())
      .then((data) => setProfile(data.profile || data))
      .catch(() => {})
      .finally(() => setLoading(false));
  }, []);

  const radarData = useMemo(
    () => (profile?.knowledge_mastery ? buildRadarData(profile.knowledge_mastery) : []),
    [profile],
  );

  if (loading) {
    return (
      <div className="flex h-screen items-center justify-center">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary-600" />
      </div>
    );
  }

  return (
    <main className="min-h-screen bg-gray-50 p-6">
      <div className="max-w-3xl mx-auto">
        <Link href="/" className="inline-flex items-center gap-1 text-sm text-gray-500 hover:text-primary-600 mb-6">
          <ArrowLeft className="w-4 h-4" /> 返回首页
        </Link>

        <h1 className="text-2xl font-bold text-primary-900 mb-8">学习画像</h1>

        {!profile ? (
          <div className="rounded-2xl bg-white p-12 text-center text-gray-400 shadow-sm">
            <Brain className="w-12 h-12 mx-auto mb-3 text-primary-200" />
            <p>还没有学习数据</p>
            <p className="text-sm mt-1">完成一次诊断对话后，你的画像会在这里显示</p>
          </div>
        ) : (
          <div className="grid gap-6">
            {/* Knowledge Mastery */}
            <SectionCard icon={<TrendingUp className="w-5 h-5" />} title="知识掌握度">
              <div className="space-y-6">
                {/* Radar chart: chapter-level overview */}
                <div className="flex justify-center">
                  <RadarChart data={radarData} />
                </div>
                {profile.knowledge_mastery?.length > 0 ? (
                  <div className="space-y-3">
                    {profile.knowledge_mastery.map((km) => (
                      <div key={km.concept_id} className="flex items-center gap-3">
                        <span className="w-32 text-sm text-gray-700 truncate">
                          {CONCEPT_NAMES[km.concept_id] || km.concept_id}
                        </span>
                        <div className="flex-1 h-2.5 rounded-full bg-gray-200 overflow-hidden">
                          <div
                            className="h-full rounded-full bg-primary-500 transition-all"
                            style={{ width: `${km.score * 100}%` }}
                          />
                        </div>
                        <span className="text-sm text-gray-500 w-12 text-right">
                          {Math.round(km.score * 100)}%
                        </span>
                      </div>
                    ))}
                  </div>
                ) : (
                  <p className="text-sm text-gray-400 py-4 text-center">完成诊断后将显示这里</p>
                )}
            </SectionCard>

            {/* Knowledge Heatmap */}
            <SectionCard icon={<Target className="w-5 h-5" />} title="知识热力图">
              {profile.knowledge_mastery?.length > 0 ? (
                <KnowledgeHeatmap mastery={profile.knowledge_mastery} />
              ) : (
                <EmptyHint text="完成诊断后将显示知识热力图" />
              )}
            </SectionCard>

            {/* Blind Spots */}
            <SectionCard icon={<AlertTriangle className="w-5 h-5" />} title="盲区图谱">
              {profile.blind_spots?.length > 0 ? (
                <BlindSpotAlert spots={profile.blind_spots} />
              ) : (
                <EmptyHint text="尚未发现明显盲区" />
              )}
            </SectionCard>

            {/* Behavior */}
            <SectionCard icon={<Activity className="w-5 h-5" />} title="学习行为">
              <div className="grid grid-cols-2 gap-4 text-sm">
                <div>
                  <span className="text-gray-500">回答风格</span>
                  <p className="font-medium text-gray-800 mt-0.5">
                    {!profile.behavior?.response_style
                      ? "暂无数据"
                      : profile.behavior.response_style === "exploratory"
                      ? "探索型"
                      : profile.behavior.response_style === "impulsive"
                      ? "冲动型"
                      : "谨慎型"}
                  </p>
                </div>
                <div>
                  <span className="text-gray-500">资源偏好</span>
                  <p className="font-medium text-gray-800 mt-0.5">
                    {!profile.behavior?.resource_preference
                      ? "暂无数据"
                      : profile.behavior.resource_preference === "visual"
                      ? "可视化"
                      : profile.behavior.resource_preference === "interactive"
                      ? "互动式"
                      : "文本型"}
                  </p>
                </div>
              </div>
            </SectionCard>
          </div>
        )}
      </div>
    </main>
  );
}

function SectionCard({ icon, title, children }: { icon: JSX.Element; title: string; children: React.ReactNode }) {
  return (
    <div className="rounded-2xl bg-white p-6 shadow-sm">
      <div className="flex items-center gap-2 mb-4">
        <span className="text-primary-600">{icon}</span>
        <h2 className="font-semibold text-gray-900">{title}</h2>
      </div>
      {children}
    </div>
  );
}

function EmptyHint({ text }: { text: string }) {
  return <p className="text-sm text-gray-400 py-4 text-center">{text}</p>;
}
