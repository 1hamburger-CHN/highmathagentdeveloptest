"use client";
import { AlertTriangle, ArrowRight } from "lucide-react";
import Link from "next/link";

const ERROR_LABELS: Record<string, string> = {
  concept: "概念理解", calculation: "计算错误", symbol: "符号使用",
  logic: "逻辑推理", prerequisite: "尚未评估",
};
const CONCEPT_NAMES: Record<string, string> = {
  "complex-1.1": "复数定义与运算", "complex-1.2": "几何表示与棣莫弗公式",
  "complex-1.3": "复数的n次方根", "complex-2.1": "复变函数的极限与连续",
  "complex-2.2": "C-R方程", "complex-2.3": "调和函数",
  "complex-3.1": "指数与对数函数", "complex-3.2": "幂函数与三角函数",
  "complex-4.1": "复积分定义与性质", "complex-4.2": "Cauchy-Goursat定理",
  "complex-4.3": "Cauchy积分与高阶导数", "complex-5.1": "泰勒级数",
  "complex-5.2": "洛朗级数", "complex-6.1": "孤立奇点分类",
  "complex-6.2": "留数与留数定理", "complex-6.3": "留数在实积分中的应用",
  "complex-7.1": "共形映射与Mobius变换",
  "complex-8.1": "傅里叶变换", "complex-8.2": "拉普拉斯变换",
};

interface BlindSpot { concept_id: string; error_type: string; frequency: number; }

export default function BlindSpotAlert({ spots }: { spots: BlindSpot[] }) {
  if (!spots.length) return null;
  const sorted = [...spots].sort((a, b) => b.frequency - a.frequency);
  return (
    <div className="rounded-xl bg-amber-50 border border-amber-200 p-4">
      <div className="flex items-center gap-2 mb-3">
        <AlertTriangle className="w-5 h-5 text-amber-600" />
        <h3 className="font-semibold text-amber-900">需要关注的盲区</h3>
      </div>
      <div className="space-y-2">
        {sorted.slice(0, 3).map((bs, i) => {
          const name = CONCEPT_NAMES[bs.concept_id] || bs.concept_id;
          const diagnoseUrl = `/chat?diagnose=${encodeURIComponent(name)}`;
          return (
            <div key={i} className="flex items-center justify-between bg-white/60 rounded-lg px-3 py-2">
              <div>
                <span className="font-medium text-amber-800 text-sm">{name}</span>
                <span className="text-amber-600 text-xs ml-2">
                  · {ERROR_LABELS[bs.error_type] || bs.error_type}
                </span>
                {bs.frequency > 1 && (
                  <span className="ml-1.5 inline-flex items-center rounded-full bg-amber-200 px-1.5 py-0.5 text-[10px] font-medium text-amber-800">
                    ×{bs.frequency}
                  </span>
                )}
              </div>
              <Link href={diagnoseUrl} className="text-xs text-primary-600 hover:underline flex items-center gap-0.5 whitespace-nowrap">
                去诊断 <ArrowRight className="w-3 h-3" />
              </Link>
            </div>
          );
        })}
      </div>
    </div>
  );
}
