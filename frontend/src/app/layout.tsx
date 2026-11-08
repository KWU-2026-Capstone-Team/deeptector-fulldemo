import type { Metadata } from "next";
import "./globals.css";
import { AppShell } from "@/components/AppShell";
import { GAMES_ENABLED } from "@/lib/features";

export const metadata: Metadata = {
  title: "DeepTector · 딥페이크 포렌식",
  description: GAMES_ENABLED
    ? "로컬 영상 분석과 딥페이크 판별 훈련을 위한 통합 포렌식 도구"
    : "딥페이크 의심 영상을 분석하고 XAI 근거 이미지를 보여주는 포렌식 도구",
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="ko">
      <body><AppShell>{children}</AppShell></body>
    </html>
  );
}
