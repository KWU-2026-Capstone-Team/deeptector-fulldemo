import Link from "next/link";

export function GamesDisabled() {
  return (
    <div className="empty">
      이 배포에서는 판별 게임을 제공하지 않습니다. <Link href="/analysis/">영상 분석</Link>을 이용해 주세요.
    </div>
  );
}
