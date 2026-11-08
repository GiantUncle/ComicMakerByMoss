import { useEffect, useMemo, useState, type ReactNode } from "react";
import {
  api,
  loadSample,
  type Lang,
  type PreviewModel,
  type PreviewShape,
} from "../api";
import ManuscriptPreview from "../components/ManuscriptPreview";
import TierPicker from "../components/TierPicker";
import { EmptyState, KV, Note } from "../components/ui";
import { pxLabel } from "../lib/canvas";
import { KIND_LABEL, countKinds, isVertical, letteringKind, tailDir } from "../lib/lettering";

/**
 * The manuscript preview — a step 8 tab, not a screen of its own.
 *
 * A page is drawn at its real pixel size from the compiled prompt: ruled panel
 * boxes with their prompt text, balloons with their tails, the tall narration
 * box, sound-effect lettering with no box at all. Nothing is rendered — the
 * page is judged from the words and the boxes before any image exists.
 */

const LANGS: { id: Lang; label: string }[] = [
  { id: "ko", label: "KO" },
  { id: "en", label: "EN" },
  { id: "ja", label: "JA" },
];

export default function Preview({
  lang,
  slug,
  ep,
  page,
  pages,
  onPage,
  tier,
  displayTier,
  onTier,
  onLang,
}: {
  lang: Lang;
  slug: string;
  ep: string;
  page: number;
  pages: number;
  onPage: (p: number) => void;
  /** Output/prompt resolution (recompiles prompt). */
  tier: string;
  /** Fixed preview display resolution — preview drawing stays stable. */
  displayTier: string;
  onTier: (t: string) => void;
  onLang: (l: Lang) => void;
}) {
  const [model, setModel] = useState<PreviewModel | null>(null);
  const [selected, setSelected] = useState<PreviewShape | null>(null);
  const [prompt, setPrompt] = useState<string>("");
  const [template, setTemplate] = useState<string>("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [note, setNote] = useState<string | null>(null);
  const [cutNote, setCutNote] = useState("");
  const [show, setShow] = useState({ borders: true, lettering: true, captions: true, grid: false });
  const [sample, setSample] = useState<PreviewModel | null>(null);

  const canLoad = !!slug && !!ep && page >= 1;

  useEffect(() => {
    setSelected(null);
    setError(null);
    if (!canLoad) return;
    // Preview drawing is always at a fixed display tier (stays the same).
    // Only the prompt/output is compiled at the selected `tier`.
    const base = displayTier || tier;
    Promise.all([
      api.pagePreview(slug, ep, page, lang, base),
      tier === base ? null : api.pagePreview(slug, ep, page, lang, tier),
    ])
      .then(([view, out]) => {
        setModel(view.preview);
        setPrompt((out ?? view).prompt);
        setTemplate(view.layout.template_id ?? (out ?? view).layout.template_id ?? "");
      })
      .catch((e) => setError(String(e)));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [slug, ep, page, lang, tier, displayTier]);

  // a first project has no pages yet: the shipped sample stands in
  useEffect(() => {
    if (canLoad) return;
    loadSample(lang)
      .then(setSample)
      .catch(() => setSample(null));
  }, [lang, canLoad]);

  const drawn = model ?? sample;
  const isSample = !model && !!sample;

  const counts = useMemo(() => (drawn ? countKinds(drawn.shapes) : []), [drawn]);

  async function retakeCut() {
    if (!selected || selected.kind !== "panel" || !selected.n) return;
    setBusy(true);
    setError(null);
    setNote(null);
    try {
      const r = await api.retakeCut({
        slug,
        episode: ep,
        page,
        panel: selected.n,
        feedback: cutNote,
      });
      setNote(`컷 ${page}p-${selected.n} 다시 만듦 — ${r.page?.note ?? ""}`);
      setCutNote("");
      const base = displayTier || tier;
      const [view, out] = await Promise.all([
        api.pagePreview(slug, ep, page, lang, base),
        tier === base ? null : api.pagePreview(slug, ep, page, lang, tier),
      ]);
      setModel(view.preview);
      if (out) setPrompt(out.prompt);
    } catch (e) {
      setError(String(e));
    } finally {
      setBusy(false);
    }
  }

  const kindOf = (s: PreviewShape) => {
    const k = letteringKind(s.caption, s.style);
    const vertical = s.kind === "text" && isVertical(s.h, s.w, (s.lines ?? []).length);
    return vertical ? `${KIND_LABEL[k]} · 세로` : KIND_LABEL[k];
  };

  const tailWord = (d: string) =>
    d === "left" ? "왼쪽" : d === "right" ? "오른쪽" : d === "up" ? "위" : "아래";

  const detailRows: [string, ReactNode][] = selected
    ? [
        [
          "좌표",
          <span className="mono">
            {Math.round(selected.x)},{Math.round(selected.y)} · {Math.round(selected.w)}×
            {Math.round(selected.h)}
          </span>,
        ],
        ["설명", <span style={{ fontSize: "var(--text-sm)" }}>{selected.caption || "—"}</span>],
      ]
    : [];
  if (selected && selected.kind === "text" && tailDir(selected.caption)) {
    detailRows.splice(1, 0, ["말풍선 꼬리", tailWord(tailDir(selected.caption)!)]);
  }

  return (
    <div className="stack" style={{ gap: "var(--s-4)", padding: "var(--s-4)" }}>
      <div className="pagebar">
        <div className="pagebar-title">원고 미리보기</div>
        <div className="pagebar-side" style={{ minWidth: 0, flex: "1 1 320px", justifyContent: "flex-end" }}>
          <div className="row" style={{ gap: "var(--s-1)", flexWrap: "wrap", justifyContent: "flex-end" }} role="group" aria-label="페이지 선택">
            {Array.from({ length: Math.max(1, pages) }, (_, i) => i + 1).map((p) => (
              <button
                key={p}
                className="btn toggle"
                aria-pressed={page === p}
                style={{ minHeight: 32, minWidth: 40, justifyContent: "center", padding: "0 var(--s-2)" }}
                onClick={() => onPage(p)}
                title={`${p}페이지`}
              >
                {p}
              </button>
            ))}
          </div>
        </div>
      </div>

      <div className="card stack-tight" style={{ gap: "var(--s-2)" }}>
        <div className="row" style={{ flexWrap: "wrap", alignItems: "center", gap: "var(--s-2)" }}>
          <span className="muted" style={{ fontSize: "var(--text-sm)" }}>언어</span>
          <div className="row" style={{ gap: "var(--s-1)" }} role="group" aria-label="출력 언어">
            {LANGS.map((l) => (
              <button
                key={l.id}
                className="btn toggle"
                aria-pressed={lang === l.id}
                onClick={() => onLang(l.id)}
                title={`${l.label} — 저장된 컷을 이 언어로 다시 컴파일`}
              >
                {l.label}
              </button>
            ))}
          </div>
          <span className="muted" style={{ fontSize: "var(--text-sm)", marginLeft: "var(--s-2)" }}>출력 해상도</span>
          <TierPicker value={tier} onChange={onTier} label="출력 해상도" />
        </div>
        <p className="muted" style={{ margin: 0, fontSize: "var(--text-sm)" }}>
          미리보기 그림은 고정되고, 언어·해상도는 복사·출력용 프롬프트에만 적용됩니다(번역 아님).
        </p>
      </div>


      {error && <Note tone="bad">{error}</Note>}
      {note && <Note tone="ok">{note}</Note>}

      <div className="twocol prompt-main">
        <div className="stack" style={{ gap: "var(--s-2)" }}>
          {prompt ? (
            <div className="card prompt-box">
              <div className="between">
                <strong style={{ fontSize: "var(--text-sm)" }}>MOSS-Image 프롬프트 — 복사해서 쓰세요</strong>
                <button
                  className="btn"
                  style={{ minHeight: 30 }}
                  onClick={() => {
                    navigator.clipboard.writeText(prompt);
                    setNote("프롬프트를 복사했습니다.");
                  }}
                >
                  복사
                </button>
              </div>
              <div className="row" style={{ flexWrap: "wrap", marginTop: "var(--s-1)" }}>
                <span className="chip">{pxLabel(tier)}</span>
                <span className="chip">{lang.toUpperCase()}</span>
                {template && <span className="chip mono">배치 {template}</span>}
                <span className="chip">컷 {drawn?.panel_count ?? 0}</span>
                <span className="muted" style={{ fontSize: "var(--text-sm)" }}>
                  이 프롬프트는 지금 언어({lang.toUpperCase()})와 해상도({tier})로 컴파일된 것입니다
                </span>
              </div>
              <pre className="rules-pre prompt-pre">{prompt}</pre>
            </div>
          ) : (
            !drawn && !error && <p className="muted">페이지를 그리는 중…</p>
          )}
          {!drawn && error && canLoad && (
            <EmptyState title="이 페이지는 아직 없습니다." hint="7단계 컷 시트와 8단계 프롬프트를 먼저 만드세요." />
          )}
        </div>

        <div className="stack" style={{ gap: "var(--s-4)" }}>
          <div className="card stack-tight">
            {drawn ? (
              <>
                <div className="between">
                  <strong style={{ fontSize: "var(--text-sm)" }}>미리보기</strong>
                  {selected ? (
                    <button className="btn" style={{ minHeight: 28 }} onClick={() => setSelected(null)}>
                      선택 해제
                    </button>
                  ) : (
                    <span className="muted" style={{ fontSize: "var(--text-sm)" }}>컷/글자 선택 가능</span>
                  )}
                </div>
                <div className="row" style={{ flexWrap: "wrap", gap: "var(--s-2)" }}>
                  {(
                    [
                      ["borders", "컷 테두리"],
                      ["lettering", "글자 (말풍선 · 내레이션 · 효과음 · 이름표)"],
                      ["captions", "컷 설명"],
                      ["grid", "좌표 눈금"],
                    ] as const
                  ).map(([k, label]) => (
                    <button
                      key={k}
                      className="btn toggle"
                      aria-pressed={show[k]}
                      onClick={() => setShow({ ...show, [k]: !show[k] })}
                    >
                      {label}
                    </button>
                  ))}
                </div>
                <ManuscriptPreview
                  model={drawn}
                  showBorders={show.borders}
                  showLettering={show.lettering}
                  showCaptions={show.captions}
                  showGrid={show.grid}
                  selected={selected?.id ?? null}
                  onSelect={setSelected}
                />
                <div className="legend">
                  <span>
                    컷 {drawn.panel_count}
                    {drawn.width && drawn.height ? ` · ${pxLabelOf(drawn.width, drawn.height)}` : ""}
                  </span>
                  {counts.map((c) => (
                    <span key={c.kind}>
                      {KIND_LABEL[c.kind]} {c.n}
                    </span>
                  ))}
                  {counts.length === 0 && <span>글자 없음</span>}
                  {template && <span className="mono">배치 {template}</span>}
                  {isSample && <span className="chip">샘플</span>}
                </div>
                {selected && (
                  <div className="stack-tight" style={{ marginTop: "var(--s-2)" }}>
                    <span className="detail-kind">
                      {selected.kind === "panel" ? `컷 ${selected.n} · ${selected.tag}` : kindOf(selected)}
                    </span>
                    <KV rows={detailRows} />
                    {selected.text && (
                      <div style={{ fontSize: "var(--text-sm)" }}>
                        <span className="muted">적힌 글자</span>
                        <div>“{selected.text}”</div>
                      </div>
                    )}
                  </div>
                )}
              </>
            ) : (
              <p className="muted" style={{ margin: 0, fontSize: "var(--text-sm)" }}>
                미리보기를 불러오는 중…
              </p>
            )}
          </div>

          {selected && selected.kind === "panel" && (
            <div className="card stack-tight">
              <strong style={{ fontSize: "var(--text-sm)" }}>컷 {selected.n}만 다시</strong>
              <div className="field" style={{ marginBottom: 0 }}>
                <textarea
                  value={cutNote}
                  onChange={(e) => setCutNote(e.target.value)}
                  placeholder="예: 클로즈업으로. 표정을 더 무표정하게. 대사를 한 줄로."
                  spellCheck={false}
                  style={{ minHeight: 56 }}
                />
              </div>
              <div className="row">
                <button className="btn btn--primary" onClick={retakeCut} disabled={busy}>
                  이 컷 리테이크
                </button>
                {busy && <span className="muted">실행 중…</span>}
              </div>
              <p className="muted" style={{ fontSize: "var(--text-sm)", margin: 0 }}>
                컷을 고쳐서 그 페이지만 다시 만듭니다. 나머지 컷은 그대로입니다.
              </p>
            </div>
          )}

        </div>
      </div>
    </div>
  );
}

function pxLabelOf(w: number, h: number): string {
  return `${w} × ${h} px`;
}
