"use client";

import { Suspense, useCallback, useEffect, useRef, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { api, errorText, TERMINAL_ANALYSIS } from "@/lib/api";
import { PUBLIC_DEPLOYMENT } from "@/lib/features";
import { LearnPanel } from "@/components/LearnPanel";

const RETENTION_TEXT = "24시간";
// Extensions (not MIME types): Windows file dialogs open much faster, and this matches the server's allow-list.
const VIDEO_SUFFIXES = [".mp4", ".mov", ".avi", ".mkv", ".webm", ".m4v"];
const IMAGE_SUFFIXES = [".jpg", ".jpeg", ".png", ".webp", ".bmp"];
const MEDIA_SUFFIXES = [...VIDEO_SUFFIXES, ...IMAGE_SUFFIXES];
const ARTIFACT_LABELS: Record<string, string> = {
  cam_spatial: "공간 히트맵 (얼굴)",
  cam_temporal: "시간 히트맵 (입 주변)",
  spatial_original: "분석한 얼굴",
  temporal_original: "분석한 입 주변",
};
import type { AnalysisDetail, AnalysisSummary } from "@/lib/types";

function AnalysisContent() {
  const router = useRouter();
  const params = useSearchParams();
  const queryId = params.get("id");
  const [items, setItems] = useState<AnalysisSummary[]>([]);
  const [selected, setSelected] = useState<AnalysisDetail | null>(null);
  const [message, setMessage] = useState("백엔드에 연결한 뒤 영상을 업로드하세요.");
  const [busy, setBusy] = useState(false);
  const [artifactUrls, setArtifactUrls] = useState<{ kind: string; url: string }[]>([]);
  const timer = useRef<number | null>(null);
  const generation = useRef(0);
  const fileInput = useRef<HTMLInputElement>(null);
  const [dragging, setDragging] = useState(false);

  const clearArtifacts = useCallback(() => {
    setArtifactUrls((current) => {
      current.forEach((item) => URL.revokeObjectURL(item.url));
      return [];
    });
  }, []);

  const loadHistory = useCallback(async () => {
    const data = await api.analyses();
    setItems(data.items);
  }, []);

  const loadArtifacts = useCallback(async (item: AnalysisDetail, version: number) => {
    const next: { kind: string; url: string }[] = [];
    for (const artifact of item.artifacts) {
      try {
        const blob = await api.call<Blob>(artifact.url, { blob: true });
        if (generation.current !== version) return next.forEach((entry) => URL.revokeObjectURL(entry.url));
        if (blob.type.startsWith("image/")) next.push({ kind: artifact.kind, url: URL.createObjectURL(blob) });
      } catch (error) {
        if (generation.current === version) setMessage(`XAI 이미지 조회 실패: ${errorText(error)}`);
      }
    }
    if (generation.current === version) setArtifactUrls(next);
  }, []);

  const openAnalysis = useCallback(async (id: string) => {
    if (timer.current) window.clearTimeout(timer.current);
    const version = ++generation.current;
    clearArtifacts();
    setSelected(null);
    setMessage("분석 상태를 조회하는 중입니다…");
    let failures = 0;
    const poll = async () => {
      try {
        const item = await api.analysis(id);
        if (generation.current !== version) return;
        failures = 0;
        setSelected(item);
        setMessage(TERMINAL_ANALYSIS.has(item.status) ? "서버의 최종 분석 상태입니다." : `${item.stage} 단계 처리 중…`);
        if (TERMINAL_ANALYSIS.has(item.status)) {
          await loadHistory();
          await loadArtifacts(item, version);
        } else {
          timer.current = window.setTimeout(poll, 1800);
        }
      } catch (error) {
        if (generation.current === version) {
          setMessage(errorText(error));
          failures += 1;
          if (failures <= 5) timer.current = window.setTimeout(poll, Math.min(1000 * 2 ** failures, 15000));
        }
      }
    };
    await poll();
  }, [clearArtifacts, loadArtifacts, loadHistory]);

  useEffect(() => {
    const connectAndLoad = async () => {
      try {
        await api.connect();
        await loadHistory();
        if (queryId) await openAnalysis(queryId);
        else setMessage("연결되었습니다. 50 MiB 이하 영상을 선택하세요.");
      } catch (error) { setMessage(errorText(error)); }
    };
    void connectAndLoad();
    return () => {
      generation.current += 1;
      if (timer.current) window.clearTimeout(timer.current);
      clearArtifacts();
    };
  }, [clearArtifacts, loadHistory, openAnalysis, queryId]);

  async function upload(file: File) {
    if (busy) return;
    if (!file.size) return setMessage("비어 있지 않은 영상 파일을 선택하세요.");
    const suffix = file.name.slice(file.name.lastIndexOf(".")).toLowerCase();
    if (!MEDIA_SUFFIXES.includes(suffix)) return setMessage(`지원하지 않는 형식입니다. 영상(${VIDEO_SUFFIXES.join(", ")}) 또는 사진(${IMAGE_SUFFIXES.join(", ")})을 선택하세요.`);
    if (file.size > 50 * 1024 * 1024) return setMessage("업로드 한도는 50 MiB입니다. 더 짧은 영상을 선택하세요.");
    setBusy(true);
    setMessage("업로드 중입니다. 중복 제출하지 말고 기다려 주세요…");
    try {
      await api.connect();
      const body = new FormData();
      body.append("video", file);
      const item = await api.call<AnalysisSummary>("/api/v1/analyses", { method: "POST", body });
      router.replace(`/analysis/?id=${encodeURIComponent(item.id)}`);
    } catch (error) { setMessage(errorText(error)); }
    finally {
      setBusy(false);
      // Allow picking the same file again.
      if (fileInput.current) fileInput.current.value = "";
    }
  }

  async function remove() {
    if (!selected || !TERMINAL_ANALYSIS.has(selected.status) || !window.confirm("이 분석 기록과 결과 파일을 삭제할까요? 복구할 수 없습니다.")) return;
    setBusy(true);
    try {
      await api.call(`/api/v1/analyses/${encodeURIComponent(selected.id)}`, { method: "DELETE" });
      generation.current += 1;
      clearArtifacts();
      setSelected(null);
      await loadHistory();
      router.replace("/analysis/");
      setMessage("분석 기록과 결과 파일을 삭제했습니다.");
    } catch (error) { setMessage(errorText(error)); }
    finally { setBusy(false); }
  }

  const result = selected?.result;
  const policy = result?.policy;
  const isImage = result != null && result.temporal == null;

  return (
    <div>
      <header className="page-head">
        <div><p className="kicker">VIDEO ANALYSIS</p><h1>영상 포렌식 분석</h1><p className="muted">실제 서버 상태와 모델 신호, 제공된 XAI artifact만 표시합니다.</p></div>
        {selected && <span className="status-chip">{selected.status} · {selected.stage}</span>}
      </header>
      {PUBLIC_DEPLOYMENT && <p className="notice">개인정보 안내 · 업로드한 원본 영상은 분석이 끝나면 즉시 삭제되고, 분석 결과와 이미지는 {RETENTION_TEXT} 후 자동 삭제됩니다. 본인이 촬영했거나 사용 권한이 있는 영상만 올려 주세요.</p>}
      <p className={`notice ${message.includes("실패") || message.includes("못했습니다") ? "error" : ""}`} role="status" aria-live="polite">{message}</p>

      <div className="grid-2">
        <section className="card">
          <h2>분석 요청</h2>
          <input ref={fileInput} id="video" name="video" type="file" className="visually-hidden" accept={MEDIA_SUFFIXES.join(",")} disabled={busy}
            onChange={(event) => { const file = event.target.files?.[0]; if (file) void upload(file); }} />
          <label
            htmlFor="video"
            className={`upload-drop${dragging ? " dragging" : ""}${busy ? " busy" : ""}`}
            onDragOver={(event) => { event.preventDefault(); setDragging(true); }}
            onDragLeave={() => setDragging(false)}
            onDrop={(event) => { event.preventDefault(); setDragging(false); const file = event.dataTransfer.files[0]; if (file) void upload(file); }}
          >
            <b>{busy ? "업로드 중…" : "영상·사진 선택해서 분석하기"}</b>
            <span>{busy ? "창을 닫지 말고 기다려 주세요" : "클릭하거나 파일을 여기로 끌어다 놓으세요"}</span>
            <small>영상 MP4 · MOV · AVI · MKV · WEBM · M4V / 사진 JPG · PNG · WEBP · BMP · 최대 50 MiB</small>
            <small>사진은 얼굴 외형(공간) 모델만 사용해 영상보다 신뢰도가 낮습니다.</small>
          </label>
          <h3 style={{ marginTop: 28 }}>최근 분석</h3>
          <div className="list">
            {items.length === 0 && <div className="empty">이 세션에 저장된 분석이 없습니다.</div>}
            {items.slice(0, 8).map((item) => (
              <button key={item.id} className="list-item" onClick={() => router.push(`/analysis/?id=${encodeURIComponent(item.id)}`)}>
                <span style={{ textAlign: "left" }}><b>{item.filename}</b><span className="id" style={{ display: "block" }}>{item.id}</span></span>
                <span className="status-chip">{item.status}</span>
              </button>
            ))}
          </div>
        </section>

        <section className="card">
          {!selected && <div className="empty">분석 항목을 선택하면 진행 상태와 결과가 여기에 표시됩니다.</div>}
          {selected && <>
            <div className="button-row" style={{ justifyContent: "space-between" }}>
              <div><h2>{selected.filename}</h2><p className="id">{selected.id}</p></div>
              <button className="secondary" onClick={() => void openAnalysis(selected.id)}>상태 다시 확인</button>
              <button className="danger" disabled={busy || !TERMINAL_ANALYSIS.has(selected.status)} onClick={remove}>삭제</button>
            </div>
            {!TERMINAL_ANALYSIS.has(selected.status) && <div style={{ display: "flex", gap: 12, alignItems: "center", marginTop: 28 }}><span className="spinner" /><span>{selected.stage}</span></div>}
            {selected.error && <div className="notice error"><b>{selected.error.code || "ANALYSIS_FAILED"}</b><br />{selected.error.message || "분석에 실패했습니다."}</div>}
            {result && policy && <>
              {result.is_demo && <p className="notice">DEMO · 아래 값은 시연 응답이며 실제 탐지 결과가 아닙니다.</p>}
              {isImage && <p className="notice">사진 분석 · 얼굴 외형(공간) 모델만 사용했습니다. 사진에는 움직임이 없어 시간 모델은 쓰지 않으며, 영상 분석보다 신뢰도가 낮습니다. AI가 처음부터 생성한 인물 사진에 대한 정확도는 검증되지 않았습니다.</p>}
              <div className={`traffic ${policy.traffic_light}`}>
                <p className="kicker">{policy.traffic_light} · {policy.verdict}</p>
                <div className="traffic-score">{policy.signal_score.toFixed(1)}<small> / 100</small></div>
                <p className="muted">모델 신호 점수이며 조작 확률이나 확정적 증거가 아닙니다.</p>
              </div>
              <div className="metric-grid" style={{ marginTop: 16 }}>
                <div className="metric"><b>{(result.spatial * 100).toFixed(1)}</b><span>SPATIAL</span></div>
                <div className="metric"><b>{isImage ? "—" : ((result.temporal ?? 0) * 100).toFixed(1)}</b><span>{isImage ? "TEMPORAL · 사진 없음" : "TEMPORAL"}</span></div>
                <div className="metric"><b>{(result.fused * 100).toFixed(1)}</b><span>{isImage ? "FUSED · 공간만" : "FUSED"}</span></div>
                <div className="metric"><b>{result.n_faces}</b><span>{isImage ? "FACE · 사진 1장" : "FACE SAMPLES"}</span></div>
              </div>
              <p className="muted">{result.faithfulness}</p>
              <details><summary>모델 및 판단 기준</summary><p className="id">{result.model_version} · {policy.policy_version}</p><p>주요 신호: {policy.primary_signal} · 기준: {policy.reason}</p><p className="muted">{JSON.stringify(policy.thresholds)}</p></details>
              {result.warnings.length > 0 && <p className="notice">주의: {result.warnings.join(" · ")}</p>}
              {artifactUrls.length === 0 && <div className="empty">서버가 제공한 XAI 이미지가 없습니다.</div>}
              <div className="artifact-grid">{artifactUrls.map((item) => <figure key={item.kind}><img src={item.url} alt={`${item.kind} XAI 시각화`} /><figcaption>{ARTIFACT_LABELS[item.kind] ?? item.kind}</figcaption></figure>)}</div>
            </>}
          </>}
        </section>
      </div>
      {result && policy && <LearnPanel intro={policy.verdict === "FAKE"
        ? "조작 신호가 감지됐습니다. 아래 체크리스트로 직접 확인해 보고, 출처가 확인되기 전에는 공유하지 마세요."
        : "조작 신호가 낮게 나왔지만 진짜라는 보증은 아닙니다. 모델이 학습하지 않은 방식(예: 처음부터 AI로 생성한 영상)은 놓칠 수 있습니다."} />}
    </div>
  );
}

export default function AnalysisPage() {
  return <Suspense fallback={<div className="empty">분석 화면을 불러오는 중…</div>}><AnalysisContent /></Suspense>;
}
