export default function TopicsPage() {
  const topics = [
    { name: "复数与复平面", concepts: ["复数运算", "几何表示", "n次方根"] },
    { name: "解析函数", concepts: ["复极限与连续", "C-R方程", "调和函数"] },
    { name: "初等复函数", concepts: ["指数与对数", "三角与幂函数"] },
    { name: "复积分", concepts: ["积分定义", "Cauchy-Goursat定理", "Cauchy积分公式"] },
    { name: "级数展开", concepts: ["泰勒级数", "洛朗级数"] },
    { name: "留数定理", concepts: ["奇点分类", "留数计算", "实积分应用"] },
    { name: "共形映射", concepts: ["Mobius变换", "保角性"] },
  ];

  return (
    <main className="min-h-screen p-8">
      <h1 className="text-3xl font-bold text-primary-900 mb-8">知识树：复变函数</h1>
      <div className="grid gap-4 max-w-3xl">
        {topics.map((t, i) => (
          <div key={i} className="rounded-xl border border-gray-200 p-5 shadow-sm hover:border-primary-300 transition-colors">
            <h2 className="text-lg font-semibold text-primary-800 mb-2">{t.name}</h2>
            <div className="flex flex-wrap gap-2">
              {t.concepts.map((c, j) => (
                <span key={j} className="rounded-full bg-primary-50 px-3 py-1 text-sm text-primary-700">
                  {c}
                </span>
              ))}
            </div>
          </div>
        ))}
      </div>
    </main>
  );
}
