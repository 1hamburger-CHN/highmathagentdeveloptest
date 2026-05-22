export default function TopicsPage() {
  const topics = [
    { name: "数列极限", concepts: ["ε-N 定义", "收敛性判别", "夹逼准则"] },
    { name: "函数极限", concepts: ["ε-δ 定义", "左右极限", "无穷小比较"] },
    { name: "两个重要极限", concepts: ["lim sinx/x", "lim (1+1/x)^x", "等价无穷小替换"] },
    { name: "连续性", concepts: ["连续定义", "间断点分类", "闭区间性质"] },
    { name: "极限的应用", concepts: ["渐近线", "函数作图"] },
  ];

  return (
    <main className="min-h-screen p-8">
      <h1 className="text-3xl font-bold text-primary-900 mb-8">知识树：极限与连续</h1>
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
