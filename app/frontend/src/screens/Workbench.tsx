import { useEffect, useState } from "react";
import { api, type Lang, type PreviewModel, type Snapshot } from "../api";
import ManuscriptPreview from "../components/ManuscriptPreview";
import { KV, Note } from "../components/ui";
import { TIERS, pxLabel, tierNote } from "../lib/canvas";

/* ---------------------------------------------------------------------------
   The page workbench — a step 8 tab, not a screen of its own.

   One page at a time. The boxes never come from free-hand drawing: they come
   from the layout library, so the levers here are the real ones — the template,
   the canvas, the language, and one cut at a time. The conti is the source of
   truth, so a template change is written there first and the page is rebuilt
   and re-validated.
--------------------------------------------------------------------------- */

export default function Workbench({
  lang,
  slug,
  ep,
  page,
  pages,
  onPage,
  tier,
  onTier,
  onLang,
}: {
  lang: Lang;
  slug: string;
  ep: string;
  page: number;
  pages: number;
  onPage: (p: number) => void;
  tier: string;
  onTier: (t: string) => void;
  onLang: (l: Lang) => void;
}) {
  const [model, setModel] = useState<PreviewModel | null>(null);
  const [prompt, setPrompt] = useState<string>("");
  const [templateId, setTemplateId] = useState("");
  const [panelCount, setPanelCount] = useState(0);
  const [cut, setCut] = useState<number | null>(null);
  const [cutNote, setCutNote] = useState("");
  const [history, setHistory] = useState<Snapshot[]>([]);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [note, setNote] = useState<string | null>(null);

  const canLoad = !!slug && !!ep && page >= 1;

  useEffect(() => {
    setCut(null);
    setError(null);
    if (!canLoad) return;
    Promise.all([api.pagePreview(slug, ep, page, lang, tier), api.history(slug)])
      .then(([r, h]) => {
        setModel(r.preview);
        setPrompt(r.prompt);
        setTemplateId(r.layout.template_id ?? "");
        setPanelCount(r.panel_count);
        setHistory(h.filter((s) => s.stage === "manga-6-conti" || s.stage === "manga-7-sheets" || s.stage === "manga-8-artwork" || s.stage === "manga-9-prompts"));
      })
      .catch((e) => setError(String(e)));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [slug, ep, page, lang, tier]);

  async function retakeCut() {
    if (cut === null) return;
    setBusy(true);
    setError(null);
    setNote(null);
    try {
      const r = await api.retakeCut({ slug, episode: ep, page, panel: cut, feedback: cutNote });
      setNote(`컷 ${page}p-${cut} 다시 만듦 — ${r.page?.note ?? ""}`);
      setCutNote("");
      setCut(null);
      const fresh = await api.pagePreview(slug, ep, page, lang, tier);
      setModel(fresh.preview);
    } catch (e) {
      setError(String(e));
    } finally {
      setBusy(false);
    }
  }

  async function restore(sid: string) {
    setBusy(true);
    setError(null);
    setNote(null);
    try {
      await api.restoreHistory(slug, sid);
      setNote("이전 버전으로 되돌렸습니다.");
      const fresh = await api.pagePreview(slug, ep, page, lang, tier);
      setModel(fresh.preview);
    } catch (e) {
      setError(String(e));
    } finally {
      setBusy(false);
    }
  }




  return (
    <div className="stack" style={{ gap: "var(--s-4)", padding: "var(--s-4)" }}>
      <div className="pagebar">
        <div className="pagebar-title">
          워크벤치
          <span className="res" title={`캔버스 ${tier} — ${tierNote(tier)}`}>
            <span className="res-px">{pxLabel(tier)}</span>
          </span>
          <span className="chip">{lang.toUpperCase()}</span>
          {model && <span className="muted">컷 {panelCount}</span>}
        </div>

        <div className="pagebar-side">
          <div className="stepper" role="group" aria-label="페이지">
            <button
              className="btn"
              style={{ minHeight: 32 }}
              onClick={() => onPage(Math.max(1, page - 1))}
              disabled={page <= 1}
              aria-label="이전 페이지"
            >
              ◀
            </button>
            <span className="stepper-value">
              {page}
              <span className="muted" style={{ fontWeight: 400 }}>
                /{pages}
              </span>
            </span>
            <button
              className="btn"
              style={{ minHeight: 32 }}
              onClick={() => onPage(Math.min(pages, page + 1))}
              disabled={page >= pages}
              aria-label="다음 페이지"
            >
              ▶
            </button>
          </div>

          <div className="tierpick" role="group" aria-label="해상도 — 보조 수단">
            {TIERS.map((t) => (
              <button
                key={t.id}
                className="btn toggle"
                aria-pressed={tier === t.id}
                title={`${t.id} — ${pxLabel(t.id)} · ${t.note}`}
                onClick={() => onTier(t.id)}
              >
                {t.id}
              </button>
            ))}
          </div>

          <div className="tierpick" role="group" aria-label="언어">
            {(["ko", "en", "ja"] as const).map((l) => (
              <button
                key={l}
                className="btn toggle"
                aria-pressed={lang === l}
                title={`${l.toUpperCase()} — 저장된 컷을 이 언어로 다시 컴파일합니다 (번역이 아닙니다)`}
                onClick={() => onLang(l)}
              >
                {l.toUpperCase()}
              </button>
            ))}
          </div>
        </div>
      </div>

      {error && <Note tone="bad">{error}</Note>}
      {note && <Note tone="ok">{note}</Note>}

      <div className="twocol">
        <div className="stack" style={{ gap: "var(--s-2)" }}>
          {model ? (
            <>
              <ManuscriptPreview
                model={model}
                selected={cut}
                onSelect={(s) => {
                  if (s.kind === "panel" && s.n) setCut(s.n);
                }}
              />
              <p className="legend" style={{ margin: 0 }}>
                컷을 누르면 그 컷만 다시 만듭니다. 말풍선 · 글자는 컷 위에 겹쳐도 되지만, 컷은 절대 겹치지
                않습니다.
              </p>
            </>
          ) : (
            <p className="muted">이 페이지를 불러오는 중…</p>
          )}
        </div>

        <div className="stack" style={{ gap: "var(--s-4)" }}>
          <div className="card stack-tight">
            <div className="between">
              <strong>컷 배치</strong>
              <span className="chip">이 페이지 컷 {panelCount}개</span>
            </div>
            <p className="muted" style={{ fontSize: "var(--text-sm)", margin: 0 }}>
              레이아웃(컷 분할)은 <strong>5단계 페이지 계획</strong>에서 페이지별 <strong>‘레이아웃’</strong> 버튼으로
              시각적으로 선택합니다. 여기서는 결과를 확인하고 컷 내용만 고칩니다.
            </p>
            {templateId && (
              <p className="mono" style={{ fontSize: "var(--text-sm)", margin: 0 }}>
                현재 배치: {templateId}
              </p>
            )}
          </div>

          {cut !== null && (
            <div className="card stack-tight">
              <strong>컷 {cut}만 다시</strong>
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
                <button className="btn" onClick={() => setCut(null)} disabled={busy}>
                  취소
                </button>
              </div>
            </div>
          )}

          <KV
            rows={[
              ["해상도", `${pxLabel(tier)} — ${tierNote(tier)}`],
              ["언어", `${lang.toUpperCase()} — 컷을 다시 컴파일합니다 (번역이 아닙니다)`],
              ["배치", templateId || "—"],
            ]}
          />

          {prompt && (
            <details className="card">
              <summary style={{ cursor: "pointer", fontWeight: 600 }}>이 페이지의 프롬프트 전문</summary>
              <pre className="rules-pre" style={{ marginTop: "var(--s-2)" }}>{prompt}</pre>
            </details>
          )}

          {history.length > 0 && (
            <div className="card stack-tight">
              <strong>이전 버전</strong>
              {history.slice(0, 6).map((s) => (
                <div key={s.id} className="between" style={{ fontSize: "var(--text-sm)" }}>
                  <span>
                    <span className="mono">{s.time.replace("T", " ")}</span>
                    <span className="muted"> · {s.note || s.stage}</span>
                  </span>
                  <button className="btn" style={{ minHeight: 28 }} onClick={() => restore(s.id)} disabled={busy}>
                    되돌리기
                  </button>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
