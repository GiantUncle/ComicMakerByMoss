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
import { EmptyState, IssueList, KV, Note } from "./ui";

/**
 * What you see on a step page is its current state, nothing more:
 *  - no artifact yet -> empty with the top action's job
 *  - artifact present -> the artifact, plus the validator's verdict inline
 *  - artifact invalid -> the failing issues and the same top action to redo
 *
 * Failures are the script's, never a guess: the same validator the runner
 * forces the model through decides what is listed here. Retake controls live
 * in the sticky top bar (StageRunner); this view does not duplicate them at
 * the page tail.
 */

const SPLIT_LABEL: Record<string, string> = {
  even: "순서 · 절차",
  single: "한 주제",
};

const FOCUS_LABEL: Record<string, string> = {
  person: "사람",
  place: "장면",
  moment: "순간",
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
  onPickCut: _onPickCut,
  selectedPages,
  onTogglePage,
}: {
  slug: string;
  ep: string | null;
  stage: string;
  block: number;
  refreshToken?: number;
  onRan?: () => void;
  /** Step 8: jump to the manuscript preview with this page open. */
  onPickCut?: (page: number) => void;
  selectedPages?: number[];
  onTogglePage?: (page: number) => void;
}) {
  const [review, setReview] = useState<StageReview | null>(null);
  const [pool, setPool] = useState<BiblePool | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [note, setNote] = useState<string | null>(null);

  const load = () => {
    api
      .stageReview(slug, stage, ep, block)
      .then((r) => {
        setReview(r);
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
  return (
    <div className="stack" style={{ gap: "var(--s-4)" }}>
      {error && <Note tone="bad">{error}</Note>}
      {note && <Note tone="ok">{note}</Note>}

      {review.stale && (
        <Note tone="warn">
          {review.stale_reason || "이전 단계가 바뀌어 현재 결과는 낡았습니다 — 위 버튼으로 다시 만드세요."}
        </Note>
      )}

      {!review.exists ? (
        <EmptyState
          title="현재 결과 없음"
          hint="위 버튼으로 만들기"
        />
      ) : (
        <>
          <div className="row" style={{ flexWrap: "wrap", alignItems: "center" }}>
            {review.updated_at && (
              <span className="chip">현재 · {review.updated_at.replace("T", " ")}</span>
            )}
            <span className={"chip " + (review.error_count > 0 ? "chip--bad" : "chip--ok")}>
              {review.error_count > 0 ? "검증 실패 · 오류 " + review.error_count : "검증 통과"}
            </span>
            {review.warning_count > 0 && <span className="chip">경고 {review.warning_count}</span>}
          </div>
          <IssueList issues={review.issues} />

          {stage === "manga-1-source" ? (
            <SourceMade review={review} />
          ) : stage === "manga-3-bible" ? (
            <CastMade
              cards={cards.length ? cards : castRowsToCards(castRows)}
              busy={busy}
              canRetake={!!ep}
              onSave={saveCard}
              onDelete={deleteCard}
              onRetake={retakeCard}
            />
          ) : stage === "manga-4-refsheets" ? (
            <SheetsMade cast={castRows} />
          ) : stage === "manga-5-plan" ? (
            <PlanMade
              rows={rows}
              pageTotal={review.summary.page_total as number | undefined}
              selectedPages={selectedPages}
              onTogglePage={onTogglePage}
              slug={slug}
              ep={ep}
              onChanged={() => {
                load();
                onRan?.();
              }}
            />
          ) : stage === "manga-6-conti" ? (
            <ContiBlockView rows={rows} block={block} selectedPages={selectedPages} onTogglePage={onTogglePage} />
          ) : stage === "manga-7-sheets" ? (
            <BlockMade rows={rows} label="컷 시트" block={block} selectedPages={selectedPages} onTogglePage={onTogglePage} />
          ) : stage === "manga-8-prompts" ? (
            <BlockMade rows={rows} label="프롬프트" block={block} selectedPages={selectedPages} onTogglePage={onTogglePage} />
          ) : (
            <BlockMade rows={rows} label="현재 결과" block={block} selectedPages={selectedPages} onTogglePage={onTogglePage} />
          )}

          {review.files.length > 0 && (
            <details>
              <summary className="muted" style={{ fontSize: "var(--text-sm)", cursor: "pointer" }}>
                현재 파일 {review.files.length}개
              </summary>
              <ul className="mono" style={{ fontSize: "var(--text-sm)", margin: "var(--s-2) 0 0" }}>
                {review.files.map((f) => (
                  <li key={f}>{f}</li>
                ))}
              </ul>
            </details>
          )}
        </>
      )}
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
              컷 {edit.panel_target ?? "?"}개 · {SPLIT_LABEL[edit.split || ""] ?? edit.split ?? "—"} 페이지에 맞는 레이아웃만 표시됩니다. 저장하면 계획의 template_suggestion이 바뀌고, 이미 만든 6·7·8단계 결과는 낡은 것으로 표시됩니다 — 저장 후 왼쪽 메뉴에서 ‘재작업 필요’를 확인하고 순서대로 다시 실행하세요.
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