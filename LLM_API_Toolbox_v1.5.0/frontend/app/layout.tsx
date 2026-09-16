import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "LLM API Toolbox",
  description: "在一个本地工作台中调用和比较不同大模型服务。",
  icons: { icon: "/favicon.svg" },
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="zh-CN">
      <body>{children}</body>
    </html>
  );
}

