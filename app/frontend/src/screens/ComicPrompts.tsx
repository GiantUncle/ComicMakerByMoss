import { useEffect, useState } from "react";
import { api, type ComicPageResult, type Lang } from "../api";
import ManuscriptPreview from "../components/ManuscriptPreview";
import TierPicker from "../components/TierPicker";
import { EmptyState, Note } from "../components/ui";

/**
 * Step 7 (comic) — the finished prompt, per page.
 *
 * A comic scene already holds every line in ko/en/ja, so switching language here
 * is a **recompile**, never a translation: the same frame, the same boxes, only
 * the lettering swapped. The page is drawn from the compiled prompt (bboxes and
 * balloons), so what you will get is visible before anything is rendered — and
 * the prompt and its negative are here to copy.
 */

const LANGS: { id: Lang; label: string }[] = [
  { id: "ko", label: "KO" },
  { id: "en", label: "EN" },
  { id: "ja", label: "JA" },
];

export default function ComicPrompts({
  slug,
  ep,
  pages,
  lang,
  onLang,
  tier: initialTier,
}: {
  slug: string;
  ep: string;
  pages: number;
  lang: Lang;
  onLang: (l: Lang) => void;
  tier: string;
}) {
  const [page, setPage] = useState(1);
  const [tier, setTier] = useState(initialTier);
  const [data, setData] = useState<ComicPageResult | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [note, setNote] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [show, setShow] = useState({ borders: true, lettering: true, captions: true, grid: false });

  const total = Math.max(1, pages);
  const current = Math.min(page, total);

  useEffect(() => {
    if (!slug || !ep) return;
    let alive = true;
    setBusy(true);
    setError(null);
    api
      .comicPage(slug, ep, current, lang, tier)
      .then((d) => alive && setData(d))
      .catch((e) => {
        if (!alive) return;
        setData(null);
        setError(String(e));
      })
      .finally(() => alive && setBusy(false));
    return () => {
      alive = false;
    };
  }, [slug, ep, current, lang, tier]);

  function copy(text: string, what: string) {
    void navigator.clipboard?.writeText(text);
    setNote(`${what}를 복사했습니다.`);
  }

  if (error) {
    return (
      <div className="stack">
        <Note tone="warn">
          이 페이지의 프롬프트가 아직 없습니다. 6단계(장면)를 실행하면 이어서 프롬프트가 만들어집니다.
        </Note>
        <Note tone="bad">{error}</Note>
      </div>
    );
  }

  return (
    <div className="stack" style={{ gap: "var(--s-4)" }}>
      <div className="pagebar">
        <div className="pagebar-title">프롬프트</div>
        <div className="row" style={{ gap: "var(--s-1)", flexWrap: "wrap", justifyContent: "flex-end" }} role="group" aria-label="페이지">
          {Array.from({ length: total }, (_, i) => i + 1).map((p) => (
            <button
              key={p}
              className="btn toggle"
              aria-pressed={current === p}
              style={{ minHeight: 32, minWidth: 40, justifyContent: "center", padding: "0 var(--s-2)" }}
              onClick={() => setPage(p)}
              title={`${p}페이지`}
            >
              {p}
            </button>
          ))}
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
                title={`${l.label} — 저장된 장면을 이 언어로 다시 컴파일(번역 아님)`}
              >
                {l.label}
              </button>
            ))}
          </div>
          <span className="muted" style={{ fontSize: "var(--text-sm)", marginLeft: "var(--s-2)" }}>해상도</span>
          <TierPicker value={tier} onChange={setTier} />
          <div className="row" style={{ gap: "var(--s-2)", marginLeft: "auto" }}>
            <button className="btn" disabled={!data} onClick={() => data && copy(data.prompt, "프롬프트")}>프롬프트 복사</button>
            <button className="btn" disabled={!data} onClick={() => data && copy(data.negative, "네거티브")}>네거티브 복사</button>
          </div>
        </div>
        <p className="muted" style={{ margin: 0, fontSize: "var(--text-sm)" }}>
          언어·해상도를 바꾸면 저장된 장면을 그 값으로 다시 컴파일합니다(그림은 그대로, 번역 아님).
        </p>
        {note && <Note tone="ok">{note}</Note>}
      </div>

      <div className="twocol prompt-main">
        <div className="stack" style={{ gap: "var(--s-2)" }}>
          {data ? (
            <div className="card prompt-box">
              <div className="between">
                <strong style={{ fontSize: "var(--text-sm)" }}>MOSS-Image 프롬프트 — 복사해서 쓰세요</strong>
                <button className="btn" style={{ minHeight: 30 }} onClick={() => copy(data.prompt, "프롬프트")}>복사</button>
              </div>
              <pre className="rules-pre prompt-pre">{data.prompt}</pre>
            </div>
          ) : (
            <p className="muted">{busy ? "불러오는 중…" : "프롬프트가 없습니다."}</p>
          )}
          {data && (
            <details className="card">
              <summary style={{ cursor: "pointer", fontSize: "var(--text-sm)", fontWeight: 600 }}>네거티브 (복사용)</summary>
              <div className="between" style={{ marginTop: "var(--s-2)" }}>
                <span className="muted" style={{ fontSize: "var(--text-sm)" }}>3섹션 네거티브</span>
                <button className="btn" style={{ minHeight: 28 }} onClick={() => copy(data.negative, "네거티브")}>복사</button>
              </div>
              <pre className="rules-pre" style={{ whiteSpace: "pre-wrap", maxHeight: 240 }}>{data.negative}</pre>
            </details>
          )}
        </div>

        <div className="stack" style={{ gap: "var(--s-4)" }}>
          <div className="card stack-tight">
            <div className="between">
              <strong style={{ fontSize: "var(--text-sm)" }}>미리보기 — bbox·말풍선</strong>
              {data && <span className="muted" style={{ fontSize: "var(--text-sm)" }}>{data.preview.width} × {data.preview.height} px · 컷 {data.preview.panel_count} · 글자 {data.preview.text_count}</span>}
            </div>
            <div className="row" style={{ flexWrap: "wrap", gap: "var(--s-2)" }}>
              {([
                ["borders", "컷 테두리"],
                ["lettering", "글자"],
                ["captions", "설명"],
                ["grid", "좌표 눈금"],
              ] as const).map(([k, label]) => (
                <button key={k} className="btn toggle" aria-pressed={show[k]} onClick={() => setShow({ ...show, [k]: !show[k] })}>
                  {label}
                </button>
              ))}
            </div>
            {data ? (
              <ManuscriptPreview
                model={data.preview}
                showBorders={show.borders}
                showLettering={show.lettering}
                showCaptions={show.captions}
                showGrid={show.grid}
              />
            ) : (
              <EmptyState title="미리보기 없음" hint="6단계를 먼저 실행하세요." />
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
