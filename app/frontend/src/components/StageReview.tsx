import { useEffect, useState } from "react";
import {
  api,
  type BibleCard,
  type BiblePool,
  type ReviewIssue,
  type StageReview,
} from "../api";
import { CastCardView } from "./CastCards";
import { loadLayoutLibrary, Thumb, type LayoutBox } from "./LayoutPicker";
import { EmptyState, IssueList, KV, Note, StepSection, Verdict } from "./ui";

/**
 * The review half of a step: what it made, whether that is sound, and what to
 * redo. Every step screen shows all three, in that order — the retake is the
 * last thing on the page, not the only thing.
 *
 * The verdict is a script's, not a guess: the same validator the runner forces
 * the model through decides what is listed here.
 */

const PAGE_SCOPED = new Set(["manga-5-plan", "manga-6-conti", "manga-7-pages"]);
const ID_SCOPED = new Set(["manga-3-bible", "manga-4-refsheets"]);

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
  "manga-5-plan": "페이지마다 무슨 일을 하는지, 컷을 몇 개로 할지가 정해집니다.",
  "manga-6-conti":
    "페이지마다 컷 구성 · 말풍선 · 내레이션 · 효과음 · 좌표가 3언어로 적혀 있습니다.",
  "manga-7-pages": "컷 시트와 컴파일된 프롬프트입니다. 좌표는 해상도에 물려 있습니다.",
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
    setError(null);
    setNote(null);
    setReview(null);
    load();
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
      <StepSection n={1} title="이 단계가 만든 것" hint={MADE_HINT[stage]} accent="made">
        {!review.exists ? (
          <EmptyState
            title="아직 만들어진 것이 없습니다."
            hint="위의 실행 버튼을 누르면 이 단계가 자신의 산출물을 씁니다."
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
            />
          </>
        ) : stage === "manga-6-conti" ? (
          <>
            {review.updated_at && (
              <div className="row" style={{ marginBottom: "var(--s-2)" }}>
                <span className="chip chip--ok" title="현재 화면에 반영된 마지막 결과">현재 반영 · {review.updated_at.replace("T", " ")}</span>
              </div>
            )}
            <BlockMade rows={rows} label="컷 구성과 글자" selectedPages={selectedPages} onTogglePage={onTogglePage} />
          </>
        ) : (
          <>
            {review.updated_at && (
              <div className="row" style={{ marginBottom: "var(--s-2)" }}>
                <span className="chip chip--ok" title="현재 화면에 반영된 마지막 결과">현재 반영 · {review.updated_at.replace("T", " ")}</span>
              </div>
            )}
            <BlockMade rows={rows} label="컷 시트와 프롬프트" selectedPages={selectedPages} onTogglePage={onTogglePage} />
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
}: {
  rows: PageRow[];
  pageTotal?: number;
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
    return <EmptyState title="계획이 비어 있습니다." hint="실행 버튼을 누르면 소설이 페이지로 쪼개집니다." />;
  }
  return (
    <div className="stack-tight">
      {pageTotal != null && (
        <span className="muted" style={{ fontSize: "var(--text-sm)" }}>
          전체 {pageTotal}페이지 · 아래는 그중 {rows.length}쪽
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
                {r.panel_target != null && <span className="chip">컷 {r.panel_target}</span>}
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
    </div>
  );
}

function BlockMade({
  rows,
  label,
  selectedPages,
  onTogglePage,
}: {
  rows: PageRow[];
  label: string;
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
      <EmptyState title="이 블록에 만들어진 페이지가 없습니다." hint="실행 버튼을 누르면 이 블록(4페이지)을 만듭니다." />
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