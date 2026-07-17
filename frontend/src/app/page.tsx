import Link from "next/link";
import { Brain, BookOpen, MessageCircle, TrendingUp, FileText, Library, Film } from "lucide-react";

export default function LandingPage() {
  return (
    <main className="flex min-h-screen flex-col items-center justify-center bg-gradient-to-br from-primary-50 via-white to-purple-50 p-8">
      <div className="max-w-2xl text-center">
        <div className="mb-6 inline-flex rounded-2xl bg-primary-100 px-4 py-1.5 text-sm font-medium text-primary-700">
          第十五届中国软件杯 · 科大讯飞出题
        </div>
        <h1 className="mb-3 text-5xl font-bold tracking-tight text-primary-900">
          苏格拉底教练
          <span className="ml-3 inline-flex rounded-lg bg-primary-100 px-3 py-1 text-sm font-medium text-primary-700 align-middle">
            v3.0
          </span>
        </h1>
        <p className="mb-2 text-xl text-primary-700">多智能体复变函数辅导系统</p>
        <p className="mb-12 text-gray-500">
          通过苏格拉底式追问，发现你不知道自己哪里不懂，追问直到你真的懂了
        </p>

        <div className="flex gap-4 justify-center mb-16">
          <Link
            href="/chat"
            className="inline-flex items-center gap-2 rounded-xl bg-primary-600 px-8 py-3.5 text-lg font-semibold text-white shadow-lg hover:bg-primary-700 transition-colors"
          >
            <MessageCircle className="w-5 h-5" />
            开始学习
          </Link>
          <Link
            href="/profile"
            className="inline-flex items-center gap-2 rounded-xl border border-primary-300 px-8 py-3.5 text-lg font-semibold text-primary-700 hover:bg-primary-50 transition-colors"
          >
            <Brain className="w-5 h-5" />
            我的画像
          </Link>
          <Link
            href="/resources"
            className="inline-flex items-center gap-2 rounded-xl border border-primary-300 px-8 py-3.5 text-lg font-semibold text-primary-700 hover:bg-primary-50 transition-colors"
          >
            <Library className="w-5 h-5" />
            资源中心
          </Link>
          <Link
            href="/animations"
            className="inline-flex items-center gap-2 rounded-xl border border-primary-300 px-8 py-3.5 text-lg font-semibold text-primary-700 hover:bg-primary-50 transition-colors"
          >
            <Film className="w-5 h-5" />
            动画浏览
          </Link>
        </div>

        {/* Feature cards */}
        <div className="grid grid-cols-3 gap-4 text-left">
          <div className="rounded-xl bg-white/60 p-4 shadow-sm">
            <Brain className="w-6 h-6 text-primary-500 mb-2" />
            <h3 className="font-semibold text-gray-900 text-sm">诊断盲区</h3>
            <p className="text-xs text-gray-500 mt-1">多Agent协作，精准定位你的知识漏洞</p>
          </div>
          <div className="rounded-xl bg-white/60 p-4 shadow-sm">
            <MessageCircle className="w-6 h-6 text-primary-500 mb-2" />
            <h3 className="font-semibold text-gray-900 text-sm">苏格拉底追问</h3>
            <p className="text-xs text-gray-500 mt-1">L1/L2/L3三层追问，逼迫你直面"装懂"的概念</p>
          </div>
          <div className="rounded-xl bg-white/60 p-4 shadow-sm">
            <BookOpen className="w-6 h-6 text-primary-500 mb-2" />
            <h3 className="font-semibold text-gray-900 text-sm">靶向补救</h3>
            <p className="text-xs text-gray-500 mt-1">针对盲区自动生成讲义、练习、思维导图</p>
          </div>
        </div>

        {/* Changelog link */}
        <div className="mt-12">
          <Link
            href="/changelog"
            className="inline-flex items-center gap-1.5 text-sm text-gray-400 hover:text-primary-500 transition-colors"
          >
            <FileText className="w-4 h-4" />
            更新日志
          </Link>
        </div>
      </div>
    </main>
  );
}
