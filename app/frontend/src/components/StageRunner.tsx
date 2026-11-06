import { useEffect, useState, useSyncExternalStore } from "react";
import {
  api,
  type ProviderInfo,
  type StageStatus,
} from "../api";
import StageReview from "./StageReview";
import { IssueList, Note } from "./ui";
import { STATE_LABEL, stageState } from "../lib/steps";
import { getRun, runKey, setRun, subscribeRun } from "../lib/runState";

/**
 * One stage, runnable.
 *
 * The step screen for any of the model stages: the run, what the run wrote,
 * then the review (what it made · whether it is sound · what to redo) and the
 * rules that stage runs by. Block stages (conti, pages) work four pages at a
 * time, so they carry a block stepper.
 */

export const STAGE_LABEL: Record<string, string> = {
  "manga-1-source": "스토리",
  "manga-2-project": "프로젝트 설정",
  "manga-3-bible": "캐스트",
  "manga-4-refsheets": "레퍼런스 시트",
  "manga-5-plan": "페이지 계획",
  "manga-6-conti": "콘티 — 장면 · 대사 · 내레이션 · 효과음 (KO/EN/JA)",
  "manga-7-sheets": "컷 시트 — 좌표 · 시트 생성",
  "manga-8-prompts": "프롬프트 — 최종 컴파일",
};

export default function StageRunner({  slug,
  ep,
  stage,
  block,
  blocks,
  onBlock,
  episodePages,
  onRan,
  onProviders,
  onPickCut,
}: {
  slug: string;
  ep: string | null;
  stage: string;
  block: number;
  blocks: number;
  onBlock: (b: number) => void;
  episodePages?: number;
  onRan?: () => void;
  onProviders?: () => void;
  onPickCut?: (page: number) => void;
}) {
  const [status, setStatus] = useState<StageStatus | null>(null);
  const [providers, setProviders] = useState<ProviderInfo[] | null>(null);
  const [selectedPages, setSelectedPages] = useState<number[]>([]);
  const [feedback, setFeedback] = useState("");
  const [planPages, setPlanPages] = useState<number>(episodePages ?? 12);
  const [promptOpen, setPromptOpen] = useState(false);
  const [promptBusy, setPromptBusy] = useState(false);
  const [promptData, setPromptData] = useState<{ system: string; user: string } | null>(null);
  const [promptError, setPromptError] = useState<string | null>(null);
  const [reviewTick, setReviewTick] = useState(0);
  type BatchItem = { block: number; pages: string; ok: boolean; note?: string; error?: string };
  const [batch, setBatch] = useState<{ running: boolean; mode: "run" | "retake"; current: number; total: number; items: BatchItem[] } | null>(null);

  const perBlock = stage === "manga-6-conti" || stage === "manga-7-sheets" || stage === "manga-8-prompts";
  const pageScoped = stage === "manga-5-plan" || perBlock;
  const isPlan = stage === "manga-5-plan";
  const isModelStage = stage === "manga-1-source" || stage === "manga-3-bible" || stage === "manga-5-plan" || stage === "manga-6-conti";
  const rkey = runKey(slug, ep, stage, perBlock ? block : 1);
  const runState = useSyncExternalStore(subscribeRun, () => getRun(rkey), () => getRun(rkey));
  const { busy: runBusy, result, error } = runState;
  const busy = runBusy || !!batch?.running;

  useEffect(() => {
    setPlanPages(episodePages ?? 12);
  }, [episodePages, slug, stage]);

  const reload = () => {
    api
      .stages(slug, ep)
      .then((rows) => setStatus(rows.find((r) => r.id === stage) ?? null))
      .catch(() => setStatus(null));
    api
      .providers()
      .then((r) => setProviders(r.providers))
      .catch(() => setProviders(null));
  };

  useEffect(() => {
    const key = runKey(slug, ep, stage, perBlock ? block : 1);
    if (!getRun(key).busy) setRun(key, { result: null, dry: null, error: null });
    setSelectedPages([]);
    setFeedback("");
    reload();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [slug, ep, stage, block]);

  async function fetchPrompt() {
    setPromptBusy(true);
    setPromptError(null);
    setPromptData(null);
    setPromptOpen(true);
    try {
      const r = await api.runStage({
        slug,
        stage,
        episode: ep,
        block: perBlock ? block : 1,
        dry: true,
        ...(isPlan ? { episode_pages: planPages } : {}),
      });
      setPromptData({
        system: String((r as unknown as { system?: string }).system ?? ""),
        user: String((r as unknown as { user?: string }).user ?? ""),
      });
    } catch (e) {
      setPromptError(String(e));
    } finally {
      setPromptBusy(false);
    }
  }

  function blockRange(b: number) {
    return `${(b - 1) * 4 + 1}–${b * 4}p`;
  }

  async function run(dryRun: boolean) {
    if (dryRun) {
      await fetchPrompt();
      return;
    }
    if (perBlock && blocks > 1) {
      await runAllBlocks("run");
      return;
    }
    setRun(rkey, { busy: true, error: null });
    try {
      const r = await api.runStage({
        slug,
        stage,
        episode: ep,
        block: perBlock ? block : 1,
        dry: false,
        ...(isPlan ? { episode_pages: planPages } : {}),
      });
      setRun(rkey, { busy: false, result: r, dry: null });
      reload();
      setReviewTick((t) => t + 1);
      onRan?.();
    } catch (e) {
      setRun(rkey, { busy: false, error: String(e) });
    }
  }

  async function runAllBlocks(mode: "run" | "retake") {
    const total = Math.max(1, blocks);
    const items: BatchItem[] = [];
    setBatch({ running: true, mode, current: 1, total, items: [] });
    setRun(rkey, { error: null, result: null });
    const fb = feedback.trim() || (mode === "retake" ? "전체 다시 실행" : "실행");
    try {
      for (let b = 1; b <= total; b++) {
        setBatch({ running: true, mode, current: b, total, items: [...items] });
        onBlock(b);
        try {
          if (mode === "retake") {
            await api.retakeStage({ slug, stage, episode: ep, block: b, feedback: fb });
          } else {
            await api.runStage({ slug, stage, episode: ep, block: b, dry: false });
          }
          items.push({ block: b, pages: blockRange(b), ok: true, note: "완료" });
        } catch (e) {
          items.push({ block: b, pages: blockRange(b), ok: false, error: String(e) });
          setBatch({ running: false, mode, current: b, total, items: [...items] });
          setRun(rkey, { error: `블록 ${b} (${blockRange(b)}) 실패: ${String(e)}` });
          reload();
          setReviewTick((t) => t + 1);
          onRan?.();
          return;
        }
        setBatch({ running: true, mode, current: b, total, items: [...items] });
        setReviewTick((t) => t + 1);
      }
      setBatch({ running: false, mode, current: total, total, items: [...items] });
      setRun(rkey, { result: { stage, note: `전체 블록 완료 (${total}개, ${total * 4}p 범위 기준)` } as any });
      setFeedback("");
      setSelectedPages([]);
      reload();
      setReviewTick((t) => t + 1);
      onRan?.();
    } catch (e) {
      setBatch((prev) => (prev ? { ...prev, running: false } : prev));
      setRun(rkey, { error: String(e) });
    }
  }

  async function rerunWhole() {
    if (perBlock && blocks > 1) {
      await runAllBlocks("retake");
      return;
    }
    setRun(rkey, { busy: true, error: null, result: null });
    try {
      const r = await api.retakeStage({
        slug,
        stage,
        episode: ep,
        block: perBlock ? block : 1,
        feedback: feedback.trim() || "전체 다시 실행",
        ...(isPlan ? { episode_pages: planPages } : {}),
      });
      setRun(rkey, { busy: false, result: { stage, note: r.note ?? "이 단계를 다시 실행했습니다" } });
      setFeedback("");
      setSelectedPages([]);
      reload();
      setReviewTick((t) => t + 1);
      onRan?.();
    } catch (e) {
      setRun(rkey, { busy: false, error: String(e) });
    }
  }

  async function rerunSelected() {
    if (selectedPages.length === 0) return;
    // group by block for per-block stages
    if (perBlock) {
      const byBlock = new Map<number, number[]>();
      for (const p of selectedPages) {
        const b = Math.max(1, Math.ceil(p / 4));
        if (!byBlock.has(b)) byBlock.set(b, []);
        byBlock.get(b)!.push(p);
      }
      const blockList = Array.from(byBlock.keys()).sort((a, b) => a - b);
      const items: BatchItem[] = [];
      setBatch({ running: true, mode: "retake", current: blockList[0] ?? 1, total: blockList.length, items: [] });
      setRun(rkey, { error: null, result: null });
      const fb = feedback.trim() || "선택 페이지 다시 실행";
      for (const b of blockList) {
        setBatch({ running: true, mode: "retake", current: b, total: blockList.length, items: [...items] });
        onBlock(b);
        try {
          await api.retakeStage({ slug, stage, episode: ep, block: b, feedback: fb, pages: byBlock.get(b) });
          items.push({ block: b, pages: (byBlock.get(b) || []).join(",") + "p", ok: true, note: "완료" });
        } catch (e) {
          items.push({ block: b, pages: (byBlock.get(b) || []).join(",") + "p", ok: false, error: String(e) });
          setBatch({ running: false, mode: "retake", current: b, total: blockList.length, items: [...items] });
          setRun(rkey, { error: `블록 ${b} 선택 페이지 실패: ${String(e)}` });
          reload(); setReviewTick((t) => t + 1); onRan?.();
          return;
        }
        setBatch({ running: true, mode: "retake", current: b, total: blockList.length, items: [...items] });
        setReviewTick((t) => t + 1);
      }
      setBatch({ running: false, mode: "retake", current: blockList[blockList.length - 1] ?? 1, total: blockList.length, items: [...items] });
      setRun(rkey, { result: { stage, note: `선택한 페이지 ${selectedPages.length}개 다시 실행 완료` } as any });
      setFeedback(""); setSelectedPages([]); reload(); setReviewTick((t) => t + 1); onRan?.();
      return;
    }
    setRun(rkey, { busy: true, error: null, result: null });
    try {
      const r = await api.retakeStage({
        slug,
        stage,
        episode: ep,
        block: perBlock ? block : 1,
        feedback: feedback.trim() || "선택 페이지 다시 실행",
        pages: selectedPages,
      });
      setRun(rkey, { busy: false, result: { stage, note: r.note ?? "선택한 페이지를 다시 실행했습니다" } });
      setFeedback("");
      setSelectedPages([]);
      reload();
      setReviewTick((t) => t + 1);
      onRan?.();
    } catch (e) {
      setRun(rkey, { busy: false, error: String(e) });
    }
  }

  function togglePage(p: number) {
    setSelectedPages((cur) => (cur.includes(p) ? cur.filter((x) => x !== p) : [...cur, p].sort((a, b) => a - b)));
  }

  const hasProvider = (providers?.length ?? 0) > 0;
  const meta = status ? STATE_LABEL[stageState(status.state)] : null;

  return (
    <div className="stack" style={{ gap: "var(--s-4)" }}>
      <div className="card between">
        <div className="stack-tight">
          <div className="row" style={{ flexWrap: "wrap" }}>
            <strong style={{ fontSize: "var(--text-lg)" }}>{STAGE_LABEL[stage] ?? stage}</strong>
            {meta && <span className={`chip ${meta.cls}`}>{meta.text}</span>}
            <span className="mono muted">{stage}</span>
          </div>
          {status?.reason ? (
            <p className="muted" style={{ margin: 0, fontSize: "var(--text-sm)" }}>
              {status.reason}
            </p>
          ) : (
            <p className="muted" style={{ margin: 0, fontSize: "var(--text-sm)" }}>
              {isModelStage ? "모델을 한 번 부르고, 검증기를 통과해야 저장합니다." : "결정적(코드) 단계입니다. 입력 아티팩트를 읽어 결과를 생성합니다."}
            </p>
          )}
        </div>

        <div className="stack" style={{ gap: "var(--s-2)", alignItems: "flex-end" }}>
          <div className="row" style={{ flexWrap: "wrap", justifyContent: "flex-end", alignItems: "center" }}>
            {perBlock && (() => {
              const pStart = (block - 1) * 4 + 1;
              const pEnd = block * 4;
              return (
                <div className="stepper" role="group" aria-label="블록">
                  <button className="btn" style={{ minHeight: 32 }} onClick={() => onBlock(Math.max(1, block - 1))} disabled={block <= 1 || busy} aria-label="이전 블록">◀</button>
                  <span className="stepper-value">{block}<span className="muted" style={{ fontWeight: 400 }}>/{blocks}</span></span>
                  <button className="btn" style={{ minHeight: 32 }} onClick={() => onBlock(Math.min(blocks, block + 1))} disabled={block >= blocks || busy} aria-label="다음 블록">▶</button>
                  <span className="muted" style={{ fontSize: "var(--text-sm)" }}>{pStart}–{pEnd}p (보기)</span>
                </div>
              );
            })()}
            <button
              className="btn"
              onClick={() => void fetchPrompt()}
              disabled={busy || promptBusy || (status ? stageState(status.state) === "waiting" || stageState(status.state) === "skip" : true)}
              title={isModelStage ? "이 단계에서 AI에 보내는 프롬프트를 봅니다" : "이 단계가 무엇을 하는지 미리 봅니다"}
            >
              {promptBusy ? "불러오는 중…" : isModelStage ? "AI 프롬프트 보기" : "단계 정보 보기"}
            </button>
            {pageScoped && (
              <button className="btn" onClick={rerunSelected} disabled={busy || selectedPages.length === 0} title={perBlock ? "선택한 페이지가 포함된 블록을 순서대로 다시 실행합니다" : "아래 카드에서 선택한 페이지만 다시 실행"}>
                {batch?.running && selectedPages.length > 0 ? `실행 중… ${batch.current}/${batch.total}` : `선택한 페이지만 다시${selectedPages.length > 0 ? ` (${selectedPages.length})` : ""}`}
              </button>
            )}
            {status && (stageState(status.state) === "done" || stageState(status.state) === "stale") ? (
              <button className="btn btn--primary" onClick={rerunWhole} disabled={busy} title={perBlock && blocks > 1 ? "모든 블록을 1번부터 순서대로 다시 실행합니다" : undefined}>
                {batch?.running ? `실행 중… ${batch.current}/${batch.total} (${blockRange(batch.current)})` : busy ? "실행 중…" : perBlock && blocks > 1 ? `전체 블록 다시 실행 (1–${blocks})` : "이 단계 다시 실행"}
              </button>
            ) : (
              <button
                className="btn btn--primary"
                onClick={() => run(false)}
                disabled={busy || (status ? stageState(status.state) !== "ready" && stageState(status.state) !== "stale" : true)}
                title={perBlock && blocks > 1 ? "모든 블록을 1번부터 순서대로 실행합니다" : undefined}
              >
                {batch?.running ? `실행 중… ${batch.current}/${batch.total} (${blockRange(batch.current)})` : busy ? "실행 중…" : perBlock && blocks > 1 ? `전체 블록 실행 (1–${blocks})` : "이 단계 실행"}
              </button>
            )}
          </div>
          {pageScoped && (
            <div className="row" style={{ gap: "var(--s-2)", alignItems: "center", justifyContent: "flex-end", flexWrap: "wrap", width: "100%" }}>
              {isPlan && (
                <label className="row" style={{ gap: "var(--s-2)", alignItems: "center", fontSize: "var(--text-sm)", margin: 0, flex: "0 0 auto" }}>
                  <span className="muted" style={{ whiteSpace: "nowrap" }}>에피소드 페이지 수</span>
                  <input
                    type="range"
                    min={1}
                    max={32}
                    step={1}
                    value={planPages}
                    onChange={(e) => setPlanPages(Math.max(1, Math.min(32, Math.round(Number(e.target.value)))))}
                    style={{ width: 360, minWidth: 240 }}
                    aria-label="에피소드 페이지 수"
                    disabled={busy}
                  />
                  <span className="chip chip--ok" style={{ minWidth: 44, justifyContent: "center" }}>{planPages}p</span>
                </label>
              )}
              <input
                value={feedback}
                onChange={(e) => setFeedback(e.target.value)}
                placeholder="다시 실행 시 메모 (선택) — 예: 2페이지 대사 짧게"
                style={{ flex: "0 1 320px", width: 320, minWidth: 180, minHeight: 36, fontSize: "var(--text-sm)" }}
                aria-label="다시 실행 메모"
              />
            </div>
          )}
        </div>
      </div>

      {status && stageState(status.state) === "stale" && (
        <Note tone="warn">
          {status.reason || "이전 단계가 변경되어 아래 결과는 낡았습니다."} 다시 실행하면 최신 결과로 교체됩니다.
        </Note>
      )}

      {!hasProvider && providers !== null && (status?.state === "ready" || status?.state === "stale") && (
        <Note tone="warn">
          프로바이더가 설정되어 있지 않아 모델을 부를 수 없습니다.{" "}
          {onProviders && (
            <button className="btn" style={{ marginLeft: "var(--s-2)" }} onClick={onProviders}>
              프로바이더 설정
            </button>
          )}
        </Note>
      )}

      {batch && batch.items.length > 0 && (
        <div className="card stack-tight">
          <strong style={{ fontSize: "var(--text-sm)" }}>
            {batch.running ? `진행 중: 블록 ${batch.current}/${batch.total} (${blockRange(batch.current)})` : `처리 결과 (${batch.items.length}/${batch.total} 블록)`}
          </strong>
          <div className="rows">
            {Array.from({ length: batch.total }, (_, i) => i + 1).map((b) => {
              const it = batch.items.find((x) => x.block === b);
              const isCurrent = batch.running && batch.current === b;
              return (
                <div key={b} className={`card ${it ? (it.ok ? "chip--ok" : "chip--bad") : isCurrent ? "chip--warn" : ""}`} style={{ padding: "6px 10px", fontSize: "var(--text-sm)" }}>
                  {it ? (it.ok ? "✓" : "✕") : isCurrent ? "…" : "·"} <span className="mono">{blockRange(b)}</span> — {it ? (it.ok ? "완료" : it.error) : isCurrent ? "실행 중" : "대기"}
                </div>
              );
            })}
          </div>
        </div>
      )}
      {error && <Note tone="bad">{error}</Note>}

      {result && (
        <div className="card stack-tight">
          {result.note && <Note tone="ok">{result.note}</Note>}
          {result.warnings?.map((w, i) => (
            <Note key={i} tone="warn">
              {w}
            </Note>
          ))}
          <IssueList issues={result.issues ?? []} />
          {result.files && result.files.length > 0 && (
            <details>
              <summary className="muted" style={{ fontSize: "var(--text-sm)", cursor: "pointer" }}>
                쓴 파일 {result.files.length}개
              </summary>
              <ul className="mono" style={{ fontSize: "var(--text-sm)", margin: "var(--s-2) 0 0" }}>
                {result.files.map((f) => (
                  <li key={f}>{f}</li>
                ))}
              </ul>
            </details>
          )}
        </div>
      )}

      <StageReview
        slug={slug}
        ep={ep}
        stage={stage}
        block={block}
        refreshToken={reviewTick}
        onRan={onRan}
        onPickCut={onPickCut}
        selectedPages={selectedPages}
        onTogglePage={pageScoped ? togglePage : undefined}
      />

      {promptOpen && (
        <div
          role="dialog"
          aria-modal="true"
          aria-label="AI 프롬프트"
          style={{
            position: "fixed",
            inset: 0,
            zIndex: 1000,
            background: "rgba(0,0,0,0.45)",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            padding: "var(--s-4)",
          }}
          onClick={(e) => {
            if (e.target === e.currentTarget) setPromptOpen(false);
          }}
        >
          <div
            className="card"
            style={{
              width: "min(1100px, 96vw)",
              maxHeight: "88vh",
              overflow: "auto",
              display: "flex",
              flexDirection: "column",
              gap: "var(--s-3)",
            }}
          >
            <div className="row" style={{ justifyContent: "space-between", alignItems: "center", gap: "var(--s-2)" }}>
              <strong style={{ fontSize: "var(--text-lg)" }}>
                {isModelStage ? "AI 프롬프트" : "단계 정보"} — {STAGE_LABEL[stage] ?? stage}
                {perBlock ? ` · 블록 ${block}` : ""}
              </strong>
              <button type="button" className="btn" onClick={() => setPromptOpen(false)}>
                닫기
              </button>
            </div>
            {promptBusy && <p className="muted">프롬프트를 불러오는 중…</p>}
            {promptError && <Note tone="bad">{promptError}</Note>}
            {promptData && (
              <div className="stack" style={{ gap: "var(--s-3)" }}>
                <div>
                  <div className="muted" style={{ fontSize: "var(--text-sm)", marginBottom: "var(--s-1)", fontWeight: 600 }}>
                    {isModelStage ? "시스템 (규칙/지시)" : "설명"}
                  </div>
                  <pre className="rules-pre" style={{ maxHeight: "32vh", overflow: "auto" }}>{promptData.system}</pre>
                </div>
                <div>
                  <div className="muted" style={{ fontSize: "var(--text-sm)", marginBottom: "var(--s-1)", fontWeight: 600 }}>
                    {isModelStage ? "사용자 (프로젝트/에피소드 자료)" : "대상/입출력"}
                  </div>
                  <pre className="rules-pre" style={{ maxHeight: "32vh", overflow: "auto" }}>{promptData.user}</pre>
                </div>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
