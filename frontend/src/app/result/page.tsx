"use client";

import { Suspense, useEffect, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { api, errorText } from "@/lib/api";
import { GAMES_ENABLED } from "@/lib/features";
import { GamesDisabled } from "@/components/GamesDisabled";
import type { AnswerReveal, GameResult } from "@/lib/types";
import { LearnPanel } from "@/components/LearnPanel";

function MyReport({ rounds }: { rounds: AnswerReveal[] }) {
  const played = rounds.filter((item) => !item.skipped);
  const missedFakes = played.filter((item) => item.ground_truth === "FAKE" && !item.user_correct);
  const falseAlarms = played.filter((item) => item.ground_truth === "REAL" && !item.user_correct);
  const cueCounts = new Map<string, number>();
  missedFakes.forEach((item) => item.cues.forEach((cue) => cueCounts.set(cue, (cueCounts.get(cue) ?? 0) + 1)));
  const topCues = [...cueCounts.entries()].sort((a, b) => b[1] - a[1]).slice(0, 5);
  const aiJudged = played.filter((item) => item.ai_correct != null);
  const aiFalseAlarms = aiJudged.filter((item) => item.ground_truth === "REAL" && !item.ai_correct).length;
  const aiMisses = aiJudged.filter((item) => item.ground_truth === "FAKE" && !item.ai_correct).length;

  const lessons: string[] = [];
  if (missedFakes.length === 0 && falseAlarms.length === 0) lessons.push("모든 영상을 정확히 판별했습니다. 실제 SNS 영상은 더 짧고 화질이 낮아 훨씬 어렵다는 점도 기억하세요.");
  if (missedFakes.length > 0) lessons.push(`가짜 영상 ${missedFakes.length}개를 진짜로 믿었습니다. 실제로 이런 영상이 공유되면 사람들은 대부분 의심하지 않고 퍼뜨립니다.`);
  if (falseAlarms.length > 0) lessons.push(`진짜 영상 ${falseAlarms.length}개를 가짜로 의심했습니다. 지나친 의심도 문제입니다. 진짜 증거를 "딥페이크"라며 부정하는 일도 실제로 일어납니다.`);
  if (aiFalseAlarms > 0) lessons.push(`탐지 AI도 진짜 영상 ${aiFalseAlarms}개를 가짜로 판정했습니다. AI 결과는 참고 자료일 뿐, 판단의 근거는 출처 확인입니다.`);
  else if (aiMisses > 0) lessons.push(`탐지 AI도 가짜 영상 ${aiMisses}개를 놓쳤습니다. 도구 하나만 믿지 말고 여러 단서를 함께 보세요.`);

  return (
    <section className="card my-report">
      <p className="kicker">MY DETECTION REPORT</p>
      <h2>나의 판별 리포트</h2>
      <ul className="lessons">{lessons.map((text) => <li key={text}>{text}</li>)}</ul>
      {topCues.length > 0 && <>
        <h3>내가 놓친 단서</h3>
        <div className="tags">{topCues.map(([cue, count]) => <span key={cue}>{cue}{count > 1 ? ` ×${count}` : ""}</span>)}</div>
      </>}
      {[...missedFakes, ...falseAlarms].length > 0 && <details>
        <summary>틀린 영상 해설 다시 보기 ({missedFakes.length + falseAlarms.length}개)</summary>
        <div className="report-rounds">
          {[...missedFakes, ...falseAlarms].sort((a, b) => a.round - b.round).map((item) => (
            <article key={item.round}>
              <b>{String(item.round).padStart(2, "0")} · 정답 {item.ground_truth} · 내 답 {item.answer}</b>
              <p>{item.explanation}</p>
              {item.cues.length > 0 && <div className="tags">{item.cues.map((cue) => <span key={cue}>{cue}</span>)}</div>}
            </article>
          ))}
        </div>
      </details>}
    </section>
  );
}

function ResultContent() {
  const router = useRouter();
  const id = useSearchParams().get("id");
  const [result, setResult] = useState<GameResult | null>(null);
  const [message, setMessage] = useState("서버의 최종 결과를 불러오는 중입니다…");

  useEffect(() => {
    if (!id) return;
    let active = true;
    void api.connect().then(() => api.result(id)).then(value => { if (active) setResult(value); }).catch((error) => { if (active) setMessage(errorText(error)); });
    return () => { active = false; };
  }, [id]);

  if (!id) return <div className="empty">게임 ID가 없습니다. 이력에서 결과를 다시 열어 주세요.</div>;
  if (!result) return <div className="empty">{message}</div>;
  const userAccuracy = result.user_accuracy == null ? null : `${(result.user_accuracy * 100).toFixed(1)}%`;
  const aiAccuracy = result.ai_accuracy == null ? null : `${(result.ai_accuracy * 100).toFixed(1)}%`;
  // Compare only rounds both sides actually judged (played and model-evaluated).
  const judged = result.rounds.filter((item) => !item.skipped && item.ai_correct != null);
  const me = judged.filter((item) => item.user_correct).length;
  const ai = judged.filter((item) => item.ai_correct).length;
  const versus = {
    rounds: judged.length, me, ai,
    tone: me > ai ? "win" : me < ai ? "lose" : "draw",
    banner: me > ai ? "🏆 AI를 이겼습니다!" : me < ai ? "🤖 AI의 승리" : "🤝 무승부",
  };
  const cats = result.categories ?? { human_only: [], ai_only: [], both_correct: [], both_wrong: [] };

  return (
    <div className="result-page">
      <header className="page-head"><div><p className="kicker">FORENSIC REPORT</p><h1>게임 결과</h1><p className="muted id">{id}</p></div><div className="grade">{result.grade}</div></header>
      <div className="score-hero"><b>{result.score.toLocaleString()}</b><span>SERVER SCORE</span></div>
      <div className="metric-grid">
        <div className="metric"><b>{result.played_rounds}</b><span>PLAYED</span></div>
        <div className="metric"><b>{result.skipped_rounds}</b><span>SKIPPED</span></div>
        <div className="metric"><b>{userAccuracy ?? "—"}</b><span>MY ACCURACY</span></div>
        <div className="metric"><b>×{result.max_streak}</b><span>MAX COMBO</span></div>
      </div>
      {versus.rounds > 0 ? <section className={`card versus-board ${versus.tone}`}>
        <p className="kicker">HUMAN VS AI</p>
        <h2 className="versus-banner">{versus.banner}</h2>
        <div className="versus-score">
          <div className="me"><span>나</span><b>{versus.me}</b><small>정확도 {userAccuracy ?? "—"}</small></div>
          <i>VS</i>
          <div className="ai"><span>AI 모델</span><b>{versus.ai}</b><small>정확도 {aiAccuracy ?? "—"}</small></div>
        </div>
        <div className="versus-cats">
          <div><b>{cats.human_only.length}</b><span>나만 맞힘</span></div>
          <div><b>{cats.ai_only.length}</b><span>AI만 맞힘</span></div>
          <div><b>{cats.both_correct.length}</b><span>둘 다 정답</span></div>
          <div><b>{cats.both_wrong.length}</b><span>둘 다 오답</span></div>
        </div>
        {versus.rounds < result.played_rounds && <p className="muted">AI 평가가 있는 {versus.rounds}개 라운드만 비교했습니다.</p>}
      </section> : <section className="card ai-summary">
        <div><p className="kicker">AI EVALUATION</p><h2>AI 평가 없음</h2></div>
        <div><b>—</b><span>점수 없음</span></div>
        <p className="muted">이 게임의 영상들은 AI 모델 평가가 기록되기 전에 출제되어 비교할 수 없습니다. 새 게임을 시작해 보세요.</p>
      </section>}
      <MyReport rounds={result.rounds} />
      <section>
        <h2>라운드 기록</h2>
        <div className="evidence-list">
          {result.rounds.map((item) => <article key={item.round} className={`evidence ${item.skipped ? "skipped" : item.user_correct ? "correct" : "wrong"}`}>
            <span>{String(item.round).padStart(2, "0")}</span>
            <div><b>{item.skipped ? "SKIPPED" : item.ground_truth}</b><p>{item.skipped ? "미디어 재생 불가로 건너뜀" : `내 답 ${item.answer} · ${item.user_correct ? "정답" : "오답"}`}{!item.skipped && item.ai_correct != null && <> <span className={`ai-chip ${item.ai_correct ? "ok" : "no"}`}>AI {item.ai?.verdict} · {item.ai_correct ? "정답" : "오답"}</span></>}</p></div>
            <strong>{item.skipped ? "—" : item.points > 0 ? `+${item.points}` : "0"}</strong>
          </article>)}
        </div>
      </section>
      <LearnPanel intro="게임에서 본 단서들은 실제 영상에서도 그대로 쓸 수 있습니다." />
      <div className="button-row"><button onClick={() => router.push("/")}>새 게임</button><button className="secondary" onClick={() => router.push("/history/")}>이력 보기</button></div>
    </div>
  );
}

export default function ResultPage() {
  if (!GAMES_ENABLED) return <GamesDisabled />;
  return <Suspense fallback={<div className="empty">결과를 불러오는 중…</div>}><ResultContent /></Suspense>;
}
