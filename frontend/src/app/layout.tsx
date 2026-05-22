import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "苏格拉底教练 — 多智能体辅导系统",
  description: "高等数学苏格拉底式AI辅导系统",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="zh-CN">
      <body className="min-h-screen">{children}</body>
    </html>
  );
}
