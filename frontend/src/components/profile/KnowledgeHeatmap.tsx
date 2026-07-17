"use client";

const CHAPTERS = [
  { id: "ch1", name: "复数与复平面", concepts: ["complex-1.1", "complex-1.2", "complex-1.3"] },
  { id: "ch2", name: "解析函数", concepts: ["complex-2.1", "complex-2.2", "complex-2.3"] },
  { id: "ch3", name: "初等复函数", concepts: ["complex-3.1", "complex-3.2"] },
  { id: "ch4", name: "复积分", concepts: ["complex-4.1", "complex-4.2", "complex-4.3"] },
  { id: "ch5", name: "级数展开", concepts: ["complex-5.1", "complex-5.2"] },
  { id: "ch6", name: "留数定理", concepts: ["complex-6.1", "complex-6.2", "complex-6.3"] },
  { id: "ch7", name: "共形映射", concepts: ["complex-7.1"] },
  { id: "ch8", name: "积分变换", concepts: ["complex-8.1", "complex-8.2"] },
];

const CONCEPT_LABELS: Record<string, string> = {
  "complex-1.1": "复数运算", "complex-1.2": "几何表示", "complex-1.3": "n次方根",
  "complex-2.1": "极限连续", "complex-2.2": "C-R方程", "complex-2.3": "调和函数",
  "complex-3.1": "指数对数", "complex-3.2": "三角幂",
  "complex-4.1": "积分定义", "complex-4.2": "Cauchy定理", "complex-4.3": "积分公式",
  "complex-5.1": "泰勒级数", "complex-5.2": "洛朗级数",
  "complex-6.1": "奇点分类", "complex-6.2": "留数定理", "complex-6.3": "实积分",
  "complex-7.1": "共形映射",
  "complex-8.1": "傅里叶变换", "complex-8.2": "拉普拉斯变换",
};

function scoreColor(score: number): string {
  if (score >= 0.7) return "bg-green-400";
  if (score >= 0.3) return "bg-yellow-400";
  return "bg-red-400";
}

interface HeatmapProps {
  mastery: { concept_id: string; score: number }[];
}

export default function KnowledgeHeatmap({ mastery }: HeatmapProps) {
  const scoreMap = Object.fromEntries(mastery.map((m) => [m.concept_id, m.score]));

  return (
    <div className="space-y-4">
      <div className="flex items-center gap-4 text-xs text-gray-500">
        <span className="flex items-center gap-1">
          <span className="w-3.5 h-3.5 rounded bg-red-400" /> 未掌握 (0-29%)
        </span>
        <span className="flex items-center gap-1">
          <span className="w-3.5 h-3.5 rounded bg-yellow-400" /> 部分掌握 (30-69%)
        </span>
        <span className="flex items-center gap-1">
          <span className="w-3.5 h-3.5 rounded bg-green-400" /> 已掌握 (70-100%)
        </span>
      </div>

      {CHAPTERS.map((ch) => (
        <div key={ch.id}>
          <h4 className="text-sm font-medium text-gray-700 mb-1.5">{ch.name}</h4>
          <div className="flex flex-wrap gap-1.5">
            {ch.concepts.map((cid) => {
              const s = scoreMap[cid] || 0;
              return (
                <div key={cid} className="flex items-center gap-1">
                  <div className={`w-5 h-5 rounded ${scoreColor(s)}`} title={`${Math.round(s * 100)}%`} />
                  <span className="text-xs text-gray-500">{CONCEPT_LABELS[cid] || cid}</span>
                </div>
              );
            })}
          </div>
        </div>
      ))}
    </div>
  );
}
