import { useEffect, useState } from "react";
import {
  api,
  type BibleCard,
  type BiblePool,
  type ReviewIssue,
  type StageReview,
} from "../api";
import { CastCardView } from "./CastCards";
import LayoutPicker, { loadLayoutLibrary, Thumb, type LayoutBox } from "./LayoutPicker";
import { EmptyState, IssueList, KV, Note, StepSection, Verdict } from "./ui";

/**
 * The review half of a step: what it made, whether that is sound, and what to
 * redo. Every step screen shows all three, in that order — the retake is the
 * last thing on the page, not the only thing.
 *
 * The verdict is a script's, not a guess: the same validator the runner forces
 * the model through decides what is listed here.
 */

const PAGE_SCOPED = new Set(["manga-5-plan", "manga-6-conti", "manga-7-sheets", "manga-8-prompts"]);
const ID_SCOPED = new Set(["manga-3-bible", "manga-4-refsheets"]);
const PER_BLOCK = new Set(["manga-6-conti", "manga-7-sheets", "manga-8-prompts"]);

const SPLIT_LABEL: Record<string, string> = {
  even: "순서 · 절차",
  single: "한 주제",
};

const FOCUS_LABEL: Record<string, string> = {
  person: "사람",
  place: "장면",
  moment: "순간",
};

const MADE_HINT: Record<string, string> = {
  "manga-1-source": "이번 화의 소설 본문입니다. 그대로 저장되고 다음 단계가 읽습니다.",
  "manga-3-bible":
    "인물 카드 한 장에 외형 앵커 · 시그니처 · 묘사가 들어갑니다. 프로젝트 전체가 함께 씁니다.",
  "manga-4-refsheets": "인물마다 한 장의 기준 시트 문장입니다. 새 인물만 새로 만듭니다.",
  "manga-5-plan": "페이지마다 무슨 일을 하는지, 컷 수와 레이아웃(템플릿)을 정합니다.",
  "manga-6-conti": "AI가 페이지별 콘티(장면·대사·내레이션·효과음, KO/EN/JA)를 작성합니다.",
  "manga-7-sheets": "콘티를 바탕으로 컷 좌표/시트(sheet.json)를 생성합니다.",
  "manga-8-prompts": "컷 시트를 최종 이미지 프롬프트(.prompt.txt/.negative.txt)로 컴파일합니다.",
};

interface PageRow {
  page: number;
  page_function?: string;
  story_job?: string;
  panel_target?: number;
  template_suggestion?: string;
  split?: string;
  focus?: string;
  panels?: number;
  texts?: number;
  width?: number;
  height?: number;
  conti?: any;
}

interface CastRow {
  id: string;
  name?: Record<string, string>;
  identifier_label?: string;
  descriptor?: string;
  anchors?: string[];
  signature?: string;
  sheet?: string | null;
  approved?: boolean;
  reference?: { sheet?: string | null; approved?: boolean };
}

export default function StageReview({
  slug,
  ep,
  stage,
  block,
  refreshToken,
  onRan,
  onPickCut,
  selectedPages,
  onTogglePage,
}: {
  slug: string;
  ep: string | null;
  stage: string;
  block: number;
  refreshToken?: number;
  onRan?: () => void;
  /** Step 7: jump to the manuscript preview with this page open. */
  onPickCut?: (page: number) => void;
  selectedPages?: number[];
  onTogglePage?: (page: number) => void;
}) {
  const [review, setReview] = useState<StageReview | null>(null);
  const [pool, setPool] = useState<BiblePool | null>(null);
  const [pages, setPages] = useState<number[]>([]);
  const [ids, setIds] = useState<string[]>([]);
  const [feedback, setFeedback] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [note, setNote] = useState<string | null>(null);

  const pageScoped = PAGE_SCOPED.has(stage);
  const idScoped = ID_SCOPED.has(stage);

  const load = () => {
    api
      .stageReview(slug, stage, ep, block)
      .then((r) => {
        setReview(r);
        setPages([]);
        setIds([]);
      })
      .catch((e) => setError(String(e)));
    if (stage === "manga-3-bible") {
      api
        .bible(slug)
        .then((b) => setPool(b.pool))
        .catch(() => setPool(null));
    }
  };

  useEffect(() => {
    let alive = true;
    setError(null);
    setNote(null);
    setReview(null);
    api
      .stageReview(slug, stage, ep, block)
      .then((r) => {
        if (!alive) return;
        setReview(r);
        setPages([]);
        setIds([]);
      })
      .catch((e) => alive && setError(String(e)));
    if (stage === "manga-3-bible") {
      api
        .bible(slug)
        .then((b) => alive && setPool(b.pool))
        .catch(() => alive && setPool(null));
    }
    return () => {
      alive = false;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [slug, stage, ep, block, refreshToken]);

  async function retake(whole: boolean) {
    setNote(null);
    if (!whole && pageScoped && pages.length === 0) {
      setError("다시 만들 페이지를 고르세요. 전부 다시 만들려면 ‘이 단계 전체 다시’를 누르세요.");
      return;
    }
    if (!whole && idScoped && ids.length === 0) {
      setError("다시 만들 인물을 고르세요. 전부 다시 만들려면 ‘이 단계 전체 다시’를 누르세요.");
      return;
    }
    setBusy(true);
    setError(null);
    try {
      const r = await api.retakeStage({
        slug,
        stage,
        episode: ep,
        block,
        feedback: (feedback.trim() || (whole ? "전체 다시 실행" : "")),
        pages: whole ? undefined : pages,
        ids: whole ? undefined : ids,
      });
      setNote(r.note ?? "다시 만들었습니다");
      setFeedback("");
      await load();
      onRan?.();
    } catch (e) {
      setError(String(e));
    } finally {
      setBusy(false);
    }
  }



  async function saveCard(card: BibleCard) {
    setBusy(true);
    setError(null);
    setNote(null);
    try {
      await api.saveCard(slug, { bucket: "characters", card });
      setNote(`${card.id} 카드를 저장했습니다.`);
      await load();
      onRan?.();
    } catch (e) {
      setError(String(e));
    } finally {
      setBusy(false);
    }
  }

  async function deleteCard(cid: string) {
    setBusy(true);
    setError(null);
    setNote(null);
    try {
      await api.deleteCard(slug, cid);
      setNote(`${cid} 카드를 지웠습니다.`);
      await load();
      onRan?.();
    } catch (e) {
      setError(String(e));
    } finally {
      setBusy(false);
    }
  }

  async function retakeCard(cid: string, fb: string) {
    if (!ep) {
      setError("리테이크하려면 에피소드가 필요합니다. 2단계에서 만드세요.");
      return;
    }
    setBusy(true);
    setError(null);
    setNote(null);
    try {
      const r = await api.retakeStage({ slug, stage: "manga-3-bible", episode: ep, ids: [cid], feedback: fb });
      setNote(r.note ?? `${cid} 카드를 다시 썼습니다`);
      await load();
      onRan?.();
    } catch (e) {
      setError(String(e));
    } finally {
      setBusy(false);
    }
  }

  if (!review) {
    return (
      <div className="stack">
        {error && <Note tone="bad">{error}</Note>}
        <p className="muted">이 단계의 결과를 읽는 중…</p>
      </div>
    );
  }

  const rows: PageRow[] = Array.isArray(review.summary.pages)
    ? (review.summary.pages as PageRow[])
    : [];
  const castRows: CastRow[] = Array.isArray(review.summary.cast)
    ? (review.summary.cast as CastRow[])
    : [];
  const cards: BibleCard[] = pool?.characters ?? [];
  const pickValues: (string | number)[] = pageScoped
    ? rows.map((r) => r.page)
    : (cards.length ? cards : castRows).map((c) => c.id);

  return (
    <div className="stack" style={{ gap: "var(--s-6)" }}>
      {error && <Note tone="bad">{error}</Note>}
      {note && <Note tone="ok">{note}</Note>}

      {/* ---------------------------------------------- ① what it made -- */}
      <StepSection n={1} title="현재 결과" hint={MADE_HINT[stage]} accent="made">
        {!review.exists ? (
          <EmptyState
            title={PER_BLOCK.has(stage) ? `이 블록(${(block - 1) * 4 + 1}–${block * 4}p)에 아직 결과가 없습니다.` : "아직 결과가 없습니다."}
            hint={PER_BLOCK.has(stage)
              ? `위의 실행 버튼을 누르면 모든 블록을 순서대로 처리합니다. 현재 보고 있는 블록은 ${(block - 1) * 4 + 1}–${block * 4}p 입니다.`
              : "위의 실행 버튼을 누르면 결과가 만들어집니다."}
          />
        ) : stage === "manga-1-source" ? (
          <>
            {review.updated_at && (
              <div className="row" style={{ marginBottom: "var(--s-2)" }}>
                <span className="chip chip--ok" title="현재 화면에 반영된 마지막 결과">
                  현재 반영 · {review.updated_at.replace("T", " ")}
                </span>
              </div>
            )}
            <SourceMade review={review} />
          </>
        ) : stage === "manga-3-bible" ? (
          <>
            {review.updated_at && (
              <div className="row" style={{ marginBottom: "var(--s-2)" }}>
                <span className="chip chip--ok" title="현재 화면에 반영된 마지막 결과">
                  현재 반영 · {review.updated_at.replace("T", " ")}
                </span>
              </div>
            )}
            <CastMade
              cards={cards.length ? cards : castRowsToCards(castRows)}
              busy={busy}
              canRetake={!!ep}
              onSave={saveCard}
              onDelete={deleteCard}
              onRetake={retakeCard}
            />
          </>
        ) : stage === "manga-4-refsheets" ? (
          <>
            {review.updated_at && (
              <div className="row" style={{ marginBottom: "var(--s-2)" }}>
                <span className="chip chip--ok" title="현재 화면에 반영된 마지막 결과">현재 반영 · {review.updated_at.replace("T", " ")}</span>
              </div>
            )}
            <SheetsMade cast={castRows} />
          </>
        ) : stage === "manga-5-plan" ? (
          <>
            {review.updated_at && (
              <div className="row" style={{ marginBottom: "var(--s-2)" }}>
                <span className="chip chip--ok" title="현재 화면에 반영된 마지막 결과">현재 반영 · {review.updated_at.replace("T", " ")}</span>
              </div>
            )}
            <PlanMade
              rows={rows}
              pageTotal={review.summary.page_total as number | undefined}
              selectedPages={selectedPages}
              onTogglePage={onTogglePage}
              slug={slug}
              ep={ep}
              onChanged={() => { load(); onRan?.(); }}
            />
          </>
        ) : stage === "manga-6-conti" ? (
          <>
            {review.updated_at && (
              <div className="row" style={{ marginBottom: "var(--s-2)" }}>
                <span className="chip chip--ok" title="현재 화면에 반영된 마지막 결과">현재 반영 · {review.updated_at.replace("T", " ")}</span>
              </div>
            )}
            <ContiBlockView rows={rows} block={block} selectedPages={selectedPages} onTogglePage={onTogglePage} />
          </>
        ) : stage === "manga-7-sheets" ? (
          <>
            {review.updated_at && (
              <div className="row" style={{ marginBottom: "var(--s-2)" }}>
                <span className="chip chip--ok" title="현재 화면에 반영된 마지막 결과">현재 반영 · {review.updated_at.replace("T", " ")}</span>
              </div>
            )}
            <BlockMade rows={rows} label="컷 시트" block={block} selectedPages={selectedPages} onTogglePage={onTogglePage} />
          </>
        ) : stage === "manga-8-prompts" ? (
          <>
            {review.updated_at && (
              <div className="row" style={{ marginBottom: "var(--s-2)" }}>
                <span className="chip chip--ok" title="현재 화면에 반영된 마지막 결과">현재 반영 · {review.updated_at.replace("T", " ")}</span>
              </div>
            )}
            <BlockMade rows={rows} label="프롬프트" block={block} selectedPages={selectedPages} onTogglePage={onTogglePage} />
          </>
        ) : (
          <>
            {review.updated_at && (
              <div className="row" style={{ marginBottom: "var(--s-2)" }}>
                <span className="chip chip--ok" title="현재 화면에 반영된 마지막 결과">현재 반영 · {review.updated_at.replace("T", " ")}</span>
              </div>
            )}
            <BlockMade rows={rows} label="결과" block={block} selectedPages={selectedPages} onTogglePage={onTogglePage} />
          </>
        )}
      </StepSection>

      {/* ------------------------------------------------- ② is it sound -- */}
      <StepSection
        n={2}
        title="검증 — 정상인지"
        hint="같은 검증기가 저장 전에도 모델을 다시 부릅니다. 오류가 0이어야 다음 단계로 넘어갑니다."
      >
        {!review.exists ? (
          <EmptyState title="검증할 산출물이 아직 없습니다." hint="①을 먼저 만드세요." />
        ) : (
          <Verdict errorCount={review.error_count} warningCount={review.warning_count}>
            <IssueList issues={review.issues} />
            {review.files.length > 0 && (
              <details>
                <summary className="muted" style={{ fontSize: "var(--text-sm)", cursor: "pointer" }}>
                  이 단계의 파일 {review.files.length}개
                </summary>
                <ul className="mono" style={{ fontSize: "var(--text-sm)", margin: "var(--s-2) 0 0" }}>
                  {review.files.map((f) => (
                    <li key={f}>{f}</li>
                  ))}
                </ul>
              </details>
            )}
          </Verdict>
        )}
      </StepSection>

      {/* --------------------------------------------------- ③ what to do -- */}
      <StepSection
        n={3}
        title={onTogglePage ? "다시 실행" : "다시 만들기 — 일부 선택"}
        hint={onTogglePage ? "카드를 눌러 페이지를 선택하고, 위의 ‘선택한 페이지만 다시’ 또는 ‘이 단계 다시 실행’을 사용하세요." : "고른 범위만 다시 만들고 나머지는 그대로 둡니다."}
      >
        {!review.exists ? (
          <EmptyState title="다시 만들 것이 아직 없습니다." hint="①을 먼저 만드세요." />
        ) : (
          <div className="stack">
            {!onTogglePage && (pageScoped || idScoped) && (
              <div className="stack-tight">
                <span className="muted" style={{ fontSize: "var(--text-sm)" }}>
                  {pageScoped ? "다시 만들 페이지" : "다시 만들 인물"} — 누르면 선택됩니다
                </span>
                <div className="pick">
                  {pickValues.map((v) => (
                    <button
                      key={String(v)}
                      className="btn pick-item"
                      aria-pressed={pageScoped ? pages.includes(Number(v)) : ids.includes(String(v))}
                      onClick={() =>
                        pageScoped
                          ? setPages((pr) => pr.includes(Number(v)) ? pr.filter((x) => x !== Number(v)) : [...pr, Number(v)])
                          : setIds((pr) => pr.includes(String(v)) ? pr.filter((x) => x !== String(v)) : [...pr, String(v)])
                      }
                    >
                      {pageScoped ? `${v}p` : String(v)}
                    </button>
                  ))}
                </div>
              </div>
            )}
            {!onTogglePage && (pageScoped || idScoped) && (
              <>
                <div className="field" style={{ marginBottom: 0 }}>
                  <label htmlFor={`fb-${stage}`}>바꾸고 싶은 점 — 메모 (비워도 됩니다)</label>
                  <textarea id={`fb-${stage}`} value={feedback} onChange={(e) => setFeedback(e.target.value)} placeholder="예: 2페이지 대사를 더 짧게." spellCheck={false} style={{ minHeight: 72 }} />
                </div>
                <div className="row" style={{ flexWrap: "wrap" }}>
                  <button className="btn btn--primary" onClick={() => retake(false)} disabled={busy}>
                    고른 {pageScoped ? "페이지" : "인물"} 다시{(pageScoped ? pages.length : ids.length) > 0 ? ` (${pageScoped ? pages.length : ids.length})` : ""}
                  </button>
                  {busy && <span className="muted">실행 중…</span>}
                </div>
              </>
            )}
            {stage === "manga-6-conti" && onPickCut && (
              <p className="muted" style={{ fontSize: "var(--text-sm)", margin: 0 }}>
                한 컷만 고치고 싶으면 원고 미리보기에서 그 컷을 누르세요 —{" "}
                <button className="btn" style={{ minHeight: 26, fontSize: "var(--text-sm)" }} onClick={() => onPickCut(1)}>원고 미리보기 열기</button>
              </p>
            )}
            </div>
        )}
      </StepSection>
    </div>
  );
}

/* ------------------------------------------------------------------- ① bits */

function SourceMade({ review }: { review: StageReview }) {
  const s = review.summary as Record<string, unknown>;
  const road = String(s.road ?? "");
  const chars = Number(s.chars ?? 0);
  const excerpt = String(s.excerpt ?? "");
  const ROAD: Record<string, string> = {
    provided: "직접 붙여넣은 소설",
    premise: "전제 — 이 단계가 산문을 씀",
    genre: "장르 · 분위기 — 이 단계가 산문을 씀",
    outline: "개요 — 이 단계가 산문을 씀",
  };
  return (
    <div className="card stack-tight">
      <KV
        rows={[
          ["출처", ROAD[road] ?? road ?? "—"],
          ["분량", `${chars}자`],
          [
            "게이트",
            s.approved ? (
              <span className="chip chip--ok">승인됨</span>
            ) : (
              <span className="chip chip--warn">미승인</span>
            ),
          ],
        ]}
      />
      {excerpt && (
        <pre className="rules-pre" style={{ maxHeight: 220 }}>
          {excerpt}
          {chars > excerpt.length ? "\n…" : ""}
        </pre>
      )}
    </div>
  );
}

function CastMade({
  cards,
  busy,
  canRetake,
  onSave,
  onDelete,
  onRetake,
}: {
  cards: BibleCard[];
  busy: boolean;
  canRetake: boolean;
  onSave: (card: BibleCard) => void;
  onDelete: (id: string) => void;
  onRetake: (id: string, fb: string) => void;
}) {
  if (cards.length === 0) {
    return <EmptyState title="캐스트가 비어 있습니다." hint="실행 버튼을 누르면 소설에서 인물 카드를 만듭니다." />;
  }
  return (
    <div className="cards cards--wide">
      {cards.map((c) => (
        <CastCardView
          key={c.id}
          card={c}
          busy={busy}
          canRetake={canRetake}
          onSave={onSave}
          onDelete={onDelete}
          onRetake={onRetake}
        />
      ))}
    </div>
  );
}

function SheetsMade({ cast }: { cast: CastRow[] }) {
  if (cast.length === 0) {
    return <EmptyState title="시트를 만들 인물이 없습니다." hint="4단계 캐스트를 먼저 만드세요." />;
  }
  return (
    <div className="cards">
      {cast.map((c) => (
        <div key={c.id} className="card stack-tight">
          <div className="between">
            <span className="mono">{c.id}</span>
            {c.sheet ? (
              <span className="chip chip--ok">시트 있음</span>
            ) : (
              <span className="chip chip--warn">시트 없음</span>
            )}
          </div>
          <strong>{c.name?.ko || c.name?.en || c.id}</strong>
          <span className="muted" style={{ fontSize: "var(--text-sm)" }}>
            {c.identifier_label}
          </span>
        </div>
      ))}
    </div>
  );
}

function PlanMade({
  rows,
  pageTotal,
  selectedPages,
  onTogglePage,
  slug,
  ep,
  onChanged,
}: {
  rows: PageRow[];
  pageTotal?: number;
  selectedPages?: number[];
  onTogglePage?: (page: number) => void;
  slug?: string;
  ep?: string | null;
  onChanged?: () => void;
}) {
  const [layouts, setLayouts] = useState<Map<string, LayoutBox[]>>(new Map());
  const [edit, setEdit] = useState<PageRow | null>(null);
  const [pick, setPick] = useState("");
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState<string | null>(null);

  useEffect(() => {
    loadLayoutLibrary()
      .then((items) => setLayouts(new Map(items.map((it) => [it.id, it.boxes]))))
      .catch(() => setLayouts(new Map()));
  }, []);

  async function saveLayout() {
    if (!edit || !slug || !ep || !pick) return;
    setBusy(true);
    setErr(null);
    try {
      await api.planTemplate({ slug, episode: ep, page: edit.page, template_id: pick });
      setEdit(null);
      onChanged?.();
    } catch (e) {
      setErr(String(e));
    } finally {
      setBusy(false);
    }
  }

  if (rows.length === 0) {
    return <EmptyState title="계획이 비어 있습니다." hint="실행 버튼을 누르면 소설이 페이지로 쪼개집니다." />;
  }
  return (
    <div className="stack-tight">
      {pageTotal != null && (
        <span className="muted" style={{ fontSize: "var(--text-sm)" }}>
          전체 {pageTotal}페이지 · 아래는 그중 {rows.length}쪽. 카드 선택은 다시 실행용, ‘레이아웃’ 버튼으로 컷 분할을 바꿀 수 있습니다.
        </span>
      )}
      <div className="plan-grid">
        {rows.map((r) => {
          const split = r.split;
          const boxes = r.template_suggestion ? layouts.get(r.template_suggestion) : undefined;
          return (
            <article
              key={r.page}
              className="plan-card"
              onClick={onTogglePage ? () => onTogglePage(r.page) : undefined}
              aria-pressed={onTogglePage ? selectedPages?.includes(r.page) : undefined}
              style={onTogglePage ? { cursor: "pointer", outline: selectedPages?.includes(r.page) ? "2px solid var(--primary)" : undefined, outlineOffset: 1 } : undefined}
            >
              <div className="plan-card-head">
                <span className="plan-card-page mono">{r.page}p</span>
                <span className="row" style={{ gap: 4, flexWrap: "wrap", justifyContent: "flex-end" }}>
                  {r.panel_target != null && <span className="chip">컷 {r.panel_target}</span>}
                  {slug && ep && (
                    <button
                      type="button"
                      className="btn"
                      style={{ minHeight: 26, fontSize: "var(--text-sm)", padding: "0 8px" }}
                      onClick={(e) => { e.stopPropagation(); setEdit(r); setPick(r.template_suggestion || ""); setErr(null); }}
                      title="이 페이지의 컷 분할 레이아웃을 시각적으로 선택"
                    >
                      레이아웃
                    </button>
                  )}
                </span>
              </div>
              <div className="plan-card-body">
                <div className="plan-card-thumb">
                  {boxes ? (
                    <Thumb boxes={boxes} />
                  ) : (
                    <div className="plan-card-thumb-fallback muted mono" style={{ fontSize: "var(--text-sm)" }}>
                      {r.template_suggestion ?? "—"}
                    </div>
                  )}
                </div>
                <div className="plan-card-info">
                  <p className="plan-card-job">{r.story_job ?? r.page_function ?? "—"}</p>
                  {r.template_suggestion && (
                    <span className="mono muted" style={{ fontSize: "11px", wordBreak: "break-all" }}>
                      {r.template_suggestion}
                    </span>
                  )}
                  <div className="row" style={{ gap: "var(--s-1)", flexWrap: "wrap", marginTop: "auto" }}>
                    {split && <span className="chip">{SPLIT_LABEL[split] ?? split}</span>}
                    {r.focus && (
                      <span className="chip" title="한 주제를 담는 페이지가 그 주제를 어디에 두는지">
                        {FOCUS_LABEL[r.focus] ?? r.focus}
                      </span>
                    )}
                  </div>
                </div>
              </div>
            </article>
          );
        })}
      </div>

      {edit && (
        <div
          role="dialog"
          aria-modal="true"
          aria-label={`${edit.page}페이지 레이아웃 선택`}
          style={{ position: "fixed", inset: 0, zIndex: 1000, background: "rgba(0,0,0,0.45)", display: "flex", alignItems: "center", justifyContent: "center", padding: "var(--s-4)" }}
          onClick={(e) => { if (e.target === e.currentTarget && !busy) setEdit(null); }}
        >
          <div className="card" style={{ width: "min(980px, 96vw)", maxHeight: "88vh", overflow: "auto", display: "flex", flexDirection: "column", gap: "var(--s-3)" }}>
            <div className="row" style={{ justifyContent: "space-between", alignItems: "center", gap: "var(--s-2)", flexWrap: "wrap" }}>
              <strong style={{ fontSize: "var(--text-lg)" }}>{edit.page}p — 컷 분할 레이아웃 선택</strong>
              <button type="button" className="btn" onClick={() => setEdit(null)} disabled={busy}>닫기</button>
            </div>
            <p className="muted" style={{ margin: 0, fontSize: "var(--text-sm)" }}>
              컷 {edit.panel_target ?? "?"}개 · {SPLIT_LABEL[edit.split || ""] ?? edit.split ?? "—"} 페이지에 맞는 레이아웃만 표시됩니다. 선택 후 저장하면 계획의 template_suggestion이 바뀝니다.
            </p>
            {err && <div className="card chip--bad" style={{ padding: "var(--s-2)" }}>{err}</div>}
            <LayoutPicker
              split={(edit.split === "single" ? "single" : "even") as "even" | "single"}
              panels={Math.max(1, Number(edit.panel_target || 4))}
              value={pick}
              onPick={setPick}
            />
            <div className="row" style={{ justifyContent: "space-between", alignItems: "center", flexWrap: "wrap", gap: "var(--s-2)" }}>
              <span className="mono muted" style={{ fontSize: "var(--text-sm)" }}>선택: {pick || "—"}</span>
              <div className="row" style={{ gap: "var(--s-2)" }}>
                <button type="button" className="btn" onClick={() => setEdit(null)} disabled={busy}>취소</button>
                <button type="button" className="btn btn--primary" onClick={saveLayout} disabled={busy || !pick || pick === edit.template_suggestion}>
                  {busy ? "저장 중…" : "레이아웃 저장"}
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}



const KIND_KO: Record<string, string> = { dialogue: "대사", narration: "내레이션", sfx: "효과음", caption: "캡션" };

function ContiBlockView({
  rows,
  block,
  selectedPages,
  onTogglePage,
}: {
  rows: PageRow[];
  block: number;
  selectedPages?: number[];
  onTogglePage?: (page: number) => void;
}) {
  const [layouts, setLayouts] = useState<Map<string, LayoutBox[]>>(new Map());

  useEffect(() => {
    loadLayoutLibrary()
      .then((items) => setLayouts(new Map(items.map((it) => [it.id, it.boxes]))))
      .catch(() => setLayouts(new Map()));
  }, []);

  if (rows.length === 0) {
    return (
      <EmptyState
        title={`이 블록(${(block - 1) * 4 + 1}–${block * 4}p)에 아직 콘티가 없습니다.`}
        hint={`위의 실행 버튼을 누르면 이 블록(${(block - 1) * 4 + 1}–${block * 4}p)만 AI로 콘티(장면·대사·내레이션·효과음, KO/EN/JA)를 작성합니다.`}
      />
    );
  }
  return (
    <div className="stack" style={{ gap: "var(--s-3)" }}>
      <span className="muted" style={{ fontSize: "var(--text-sm)" }}>
        콘티 — 블록 {block} ({(block - 1) * 4 + 1}–{block * 4}p). 카드를 눌러 선택, 펼쳐서 실제 콘티 내용을 확인하세요.
      </span>
      {rows.map((r) => {
        const split = r.split;
        const boxes = r.template_suggestion ? layouts.get(r.template_suggestion) : undefined;
        const conti = r.conti;
        const panels: any[] = Array.isArray(conti?.panels) ? conti.panels : [];
        const texts: any[] = Array.isArray(conti?.texts) ? conti.texts : [];
        return (
          <article
            key={r.page}
            className="card"
            style={{
              padding: "var(--s-3)",
              cursor: onTogglePage ? "pointer" : undefined,
              outline: onTogglePage && selectedPages?.includes(r.page) ? "2px solid var(--primary)" : undefined,
              outlineOffset: 1,
            }}
          >
            <div className="row" style={{ justifyContent: "space-between", alignItems: "flex-start", gap: "var(--s-2)", flexWrap: "wrap" }} onClick={onTogglePage ? () => onTogglePage(r.page) : undefined}>
              <div className="row" style={{ gap: "var(--s-2)", alignItems: "center", flexWrap: "wrap" }}>
                <span className="plan-card-page mono">{r.page}p</span>
                <span className="chip">컷 {r.panels ?? panels.length}</span>
                <span className="chip">텍스트 {r.texts ?? texts.length}</span>
                {split && <span className="chip">{SPLIT_LABEL[split] ?? split}</span>}
                {r.template_suggestion && <span className="chip mono">{r.template_suggestion}</span>}
              </div>
              {boxes && <div style={{ width: 64 }}><Thumb boxes={boxes} /></div>}
            </div>
            {r.story_job && <p style={{ margin: "var(--s-2) 0 0", fontSize: "var(--text-sm)" }}><strong>장면:</strong> {r.story_job}</p>}
            <details style={{ marginTop: "var(--s-2)" }} onClick={(e) => e.stopPropagation()}>
              <summary style={{ cursor: "pointer", fontSize: "var(--text-sm)", fontWeight: 600 }}>콘티 내용 보기 (컷/대사/내레이션/효과음)</summary>
              <div className="stack" style={{ gap: "var(--s-3)", marginTop: "var(--s-2)" }}>
                {panels.length > 0 && (
                  <div>
                    <div className="muted" style={{ fontSize: "var(--text-sm)", fontWeight: 600, marginBottom: 4 }}>컷</div>
                    <div className="rows">
                      {panels.map((p: any) => (
                        <div key={p.n} className="card" style={{ padding: "8px 10px", fontSize: "var(--text-sm)" }}>
                          <div className="row" style={{ gap: 6, flexWrap: "wrap", marginBottom: 4 }}>
                            <span className="chip mono">#{p.n}</span>
                            {p.shot && <span className="chip">{p.shot}</span>}
                            {p.anchor_of && <span className="chip" title="앵커">앵커: {p.anchor_of}</span>}
                            {Array.isArray(p.characters) && p.characters.length > 0 && <span className="muted">등장: {p.characters.join(", ")}</span>}
                          </div>
                          {p.beat && <div>{p.beat}</div>}
                          {p.bg && <div className="muted" style={{ fontSize: "11px" }}>bg: {p.bg}</div>}
                        </div>
                      ))}
                    </div>
                  </div>
                )}
                {texts.length > 0 && (
                  <div>
                    <div className="muted" style={{ fontSize: "var(--text-sm)", fontWeight: 600, marginBottom: 4 }}>텍스트 (대사/내레이션/효과음)</div>
                    <div className="rows">
                      {texts.map((tx: any) => {
                        const ko = Array.isArray(tx.lines?.ko) ? tx.lines.ko.join(" / ") : "";
                        const en = Array.isArray(tx.lines?.en) ? tx.lines.en.join(" / ") : "";
                        const ja = Array.isArray(tx.lines?.ja) ? tx.lines.ja.join(" / ") : "";
                        return (
                          <div key={tx.id || Math.random()} className="card" style={{ padding: "8px 10px", fontSize: "var(--text-sm)" }}>
                            <div className="row" style={{ gap: 6, flexWrap: "wrap", marginBottom: 4 }}>
                              <span className="chip">{KIND_KO[tx.kind] ?? tx.kind ?? "텍스트"}</span>
                              {tx.panel_ref != null && <span className="chip mono">컷 {tx.panel_ref}</span>}
                              {tx.speaker && <span className="chip">{tx.speaker}</span>}
                              {tx.id && <span className="mono muted" style={{ fontSize: 11 }}>{tx.id}</span>}
                            </div>
                            {ko && <div><span className="muted">KO</span> {ko}</div>}
                            {en && <div><span className="muted">EN</span> {en}</div>}
                            {ja && <div><span className="muted">JA</span> {ja}</div>}
                          </div>
                        );
                      })}
                    </div>
                  </div>
                )}
                {!conti && <p className="muted" style={{ fontSize: "var(--text-sm)", margin: 0 }}>콘티 상세 데이터가 없습니다(새로고침 또는 다시 실행 후 확인).</p>}
              </div>
            </details>
          </article>
        );
      })}
    </div>
  );
}

function BlockMade({
  rows,
  label,
  block,
  selectedPages,
  onTogglePage,
}: {
  rows: PageRow[];
  label: string;
  block: number;
  selectedPages?: number[];
  onTogglePage?: (page: number) => void;
}) {
  const [layouts, setLayouts] = useState<Map<string, LayoutBox[]>>(new Map());

  useEffect(() => {
    loadLayoutLibrary()
      .then((items) => setLayouts(new Map(items.map((it) => [it.id, it.boxes]))))
      .catch(() => setLayouts(new Map()));
  }, []);

  if (rows.length === 0) {
    return (
      <EmptyState title={`이 블록(${(block - 1) * 4 + 1}–${block * 4}p)에 아직 결과가 없습니다.`} hint={`위의 실행 버튼으로 모든 블록을 순서대로 처리할 수 있습니다. 현재 보고 있는 블록은 ${(block - 1) * 4 + 1}–${block * 4}p 입니다.`} />
    );
  }
  return (
    <div className="stack-tight">
      <span className="muted" style={{ fontSize: "var(--text-sm)" }}>
        {label} — 블록 단위로 4페이지씩 만듭니다
      </span>
      <div className="plan-grid">
        {rows.map((r) => {
          const split = r.split;
          const boxes = r.template_suggestion ? layouts.get(r.template_suggestion) : undefined;
          return (
            <article
              key={r.page}
              className="plan-card"
              onClick={onTogglePage ? () => onTogglePage(r.page) : undefined}
              aria-pressed={onTogglePage ? selectedPages?.includes(r.page) : undefined}
              style={onTogglePage ? { cursor: "pointer", outline: selectedPages?.includes(r.page) ? "2px solid var(--primary)" : undefined, outlineOffset: 1 } : undefined}
            >
              <div className="plan-card-head">
                <span className="plan-card-page mono">{r.page}p</span>
                <span className="row" style={{ gap: "var(--s-1)", flexWrap: "wrap", justifyContent: "flex-end" }}>
                  <span className="chip">컷 {r.panels ?? 0}</span>
                  <span className="chip">글자 {r.texts ?? 0}</span>
                </span>
              </div>
              <div className="plan-card-body">
                <div className="plan-card-thumb">
                  {boxes ? (
                    <Thumb boxes={boxes} />
                  ) : (
                    <div className="plan-card-thumb-fallback muted mono" style={{ fontSize: "var(--text-sm)" }}>
                      {r.template_suggestion ?? `${r.panels ?? 0}컷`}
                    </div>
                  )}
                </div>
                <div className="plan-card-info">
                  <p className="plan-card-job" style={{ margin: 0 }}>
                    블록 {Math.floor((r.page - 1) / 4) + 1}
                    {r.width && r.height ? ` · ${r.width} × ${r.height} px` : ""}
                  </p>
                  {r.template_suggestion && (
                    <span className="mono muted" style={{ fontSize: "11px", wordBreak: "break-all" }}>
                      {r.template_suggestion}
                    </span>
                  )}
                  <div className="row" style={{ gap: "var(--s-1)", flexWrap: "wrap", marginTop: "auto" }}>
                    {split && <span className="chip">{SPLIT_LABEL[split] ?? split}</span>}
                  </div>
                </div>
              </div>
            </article>
          );
        })}
      </div>
      <p className="muted" style={{ fontSize: "var(--text-sm)", margin: 0 }}>
        글자 = 말풍선 · 내레이션 · 효과음 · 이름표. 원고 미리보기에서 종류별로 눌러 볼 수 있습니다.
      </p>
    </div>
  );
}

function castRowsToCards(rows: CastRow[]): BibleCard[] {
  return rows.map((r) => ({
    id: r.id,
    name: r.name,
    identifier_label: r.identifier_label,
    descriptor: r.descriptor,
    anchors: r.anchors,
    signature: r.signature,
    reference: r.reference ?? (r.sheet ? { sheet: r.sheet, approved: r.approved } : undefined),
  }));
}

export type { ReviewIssue };