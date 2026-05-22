export default function ProfilePage() {
  return (
    <main className="flex min-h-screen flex-col items-center justify-center p-8">
      <h1 className="text-3xl font-bold text-primary-900 mb-8">学习画像</h1>
      <div className="grid gap-6 w-full max-w-2xl">
        <ProfileCard title="知识掌握度" items={["极限定义: 85%", "连续函数: 72%", "无穷小比较: 45%"]} />
        <ProfileCard title="盲区图谱" items={["等价无穷小替换 (概念理解)", "ε-δ 语言 (计算)"]} />
        <ProfileCard title="学习行为" items={["风格: exploratory", "偏好: visual + interactive"]} />
      </div>
    </main>
  );
}

function ProfileCard({ title, items }: { title: string; items: string[] }) {
  return (
    <div className="rounded-2xl border border-gray-200 p-6 shadow-sm">
      <h2 className="text-lg font-semibold text-primary-700 mb-3">{title}</h2>
      <ul className="space-y-2">
        {items.map((item, i) => (
          <li key={i} className="flex items-center gap-2 text-gray-700">
            <span className="h-2 w-2 rounded-full bg-primary-400" />
            {item}
          </li>
        ))}
      </ul>
    </div>
  );
}
