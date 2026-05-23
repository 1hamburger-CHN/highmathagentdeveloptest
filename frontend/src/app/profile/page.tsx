"use client";

import { useEffect, useState } from "react";
import { Brain, Target, Activity, ArrowLeft, TrendingUp, AlertTriangle } from "lucide-react";
import Link from "next/link";

const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? "";

type Profile = {
  knowledge_mastery: { concept_id: string; score: number; confidence: number }[];
  blind_spots: { concept_id: string; error_type: string; frequency: number }[];
  behavior: { response_style: string; resource_preference: string };
};

const CONCEPT_NAMES: Record<string, string> = {
  "limit-1.1.1": "数列极限 ε-N",
  "limit-1.1.2": "收敛数列性质",
  "limit-1.1.3": "极限四则运算",
  "limit-1.1.4": "夹逼准则",
  "limit-1.1.5": "单调有界定理",
  "limit-1.2.1": "函数极限 ε-δ",
  "limit-1.2.2": "左右极限",
  "limit-1.2.3": "无穷小",
  "limit-1.2.4": "无穷大",
  "limit-1.2.5": "无穷小比较",
  "limit-1.2.6": "函数极限运算法则",
  "limit-1.3.1": "lim sin x/x",
  "limit-1.3.2": "lim (1+1/x)^x=e",
  "limit-1.3.3": "等价无穷小替换",
  "limit-1.3.4": "泰勒展开",
  "limit-1.2.7": "洛必达法则",
  "limit-1.5.1": "渐近线",
  "limit-1.5.2": "极限存在性判别",
  "limit-1.4.1": "连续性",
};

const ERROR_TYPE_LABELS: Record<string, string> = {
  concept: "概念理解",
  calculation: "计算错误",
  symbol: "符号使用",
  logic: "逻辑推理",
  prerequisite: "前置缺失",
};

export default function ProfilePage() {
  const [profile, setProfile] = useState<Profile | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetch(`${API_BASE}/api/profile/anonymous`)
      .then((r) => r.json())
      .then((data) => setProfile(data.profile || data))
      .catch(() => {})
      .finally(() => setLoading(false));
  }, []);

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
                <EmptyHint text="完成诊断后将显示各概念的掌握程度" />
              )}
            </SectionCard>

            {/* Blind Spots */}
            <SectionCard icon={<AlertTriangle className="w-5 h-5" />} title="盲区图谱">
              {profile.blind_spots?.length > 0 ? (
                <div className="space-y-2">
                  {profile.blind_spots.map((bs, i) => (
                    <div key={i} className="flex items-center gap-2 rounded-lg bg-amber-50 px-3 py-2 text-sm">
                      <span className="font-medium text-amber-800">
                        {CONCEPT_NAMES[bs.concept_id] || bs.concept_id}
                      </span>
                      <span className="text-amber-600">
                        · {ERROR_TYPE_LABELS[bs.error_type] || bs.error_type}
                      </span>
                      {bs.frequency > 1 && (
                        <span className="text-amber-400 text-xs">×{bs.frequency}</span>
                      )}
                    </div>
                  ))}
                </div>
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
