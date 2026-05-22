import Link from "next/link";

export default function LandingPage() {
  return (
    <main className="flex min-h-screen flex-col items-center justify-center bg-gradient-to-br from-primary-50 to-white p-8">
      <div className="max-w-2xl text-center">
        <h1 className="mb-4 text-5xl font-bold tracking-tight text-primary-900">
          苏格拉底教练
        </h1>
        <p className="mb-2 text-xl text-primary-700">多智能体高等数学辅导系统</p>
        <p className="mb-12 text-gray-500">
          发现你不知道自己哪里不懂 — 追问直到你真的懂了
        </p>
        <div className="flex gap-4 justify-center">
          <Link
            href="/chat"
            className="rounded-xl bg-primary-600 px-8 py-3 text-lg font-semibold text-white shadow-lg hover:bg-primary-700 transition-colors"
          >
            开始学习
          </Link>
          <Link
            href="/profile"
            className="rounded-xl border border-primary-300 px-8 py-3 text-lg font-semibold text-primary-700 hover:bg-primary-50 transition-colors"
          >
            我的画像
          </Link>
        </div>
      </div>
    </main>
  );
}
