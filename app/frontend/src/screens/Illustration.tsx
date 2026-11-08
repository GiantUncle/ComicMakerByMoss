import { useEffect, useState } from "react";
import { api, type Favorite, type IllustrationResult } from "../api";
import { Note } from "../components/ui";
import { TIERS, pxLabel } from "../lib/canvas";

/**
 * Illustration — a project-free prompt maker (Type B).
 *
 * There is no project here: a command goes in, a sectioned prompt comes out, and
 * it is either starred into the shared favourites store or dropped when the next
 * one is made. Always reachable from the top bar.
 */

const STYLES = [
  { id: "fkey_painterly", label: "fkey_painterly — 선택적 포커스 구아슈" },
  { id: "fkey_clean", label: "fkey_clean — 깔끔한 상업 선화" },
];

function copy(text: string) {
  void navigator.clipboard?.writeText(text);
}

export default function Illustration({ onProviders }: { onProviders?: () => void }) {
  const [brief, setBrief] = useState("");
  const [tier, setTier] = useState("M");
  const [style, setStyle] = useState("fkey_painterly");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [note, setNote] = useState<string | null>(null);
  const [result, setResult] = useState<IllustrationResult | null>(null);
  const [favorites, setFavorites] = useState<Favorite[]>([]);
  const [copied, setCopied] = useState<string | null>(null);

  const loadFavorites = () => {
    api.favorites().then(setFavorites).catch(() => setFavorites([]));
  };
  useEffect(loadFavorites, []);

  const draft = (result?.draft ?? {}) as {
    title?: string;
    style_and_aesthetic?: string;
    sections?: { name: string; caption: string }[];
  };
  const sections = Array.isArray(draft.sections) ? draft.sections : [];

  async function generate() {
    if (!brief.trim()) return;
    setBusy(true);
    setError(null);
    setNote(null);
    setResult(null);
    try {
      const r = await api.generateIllustration({ brief: brief.trim(), canvas_tier: tier, art_style: style });
      setResult(r);
      if (!r.ok) setError("검증 경고가 있습니다 — 결과를 확인하세요.");
    } catch (e) {
      setError(String(e));
    } finally {
      setBusy(false);
    }
  }

  async function star() {
    if (!result) return;
    setBusy(true);
    setError(null);
    setNote(null);
    try {
      const fav = await api.saveFavorite({
        kind: "illustration",
        title: draft.title || brief.slice(0, 40) || "illustration",
        draft: result.draft,
        prompt: result.prompt,
        negative: result.negative,
        brief,
        source: "illustration",
        canvas_tier: tier,
        art_style: style,
      });
      setNote(`즐겨찾기에 저장했습니다 (${fav.id}).`);
      loadFavorites();
    } catch (e) {
      setError(String(e));
    } finally {
      setBusy(false);
    }
  }

  async function load(fid: string) {
    setBusy(true);
    setError(null);
    setNote(null);
    try {
      const f = await api.favorite(fid);
      setBrief(f.brief || "");
      setTier(f.canvas_tier || "M");
      setStyle(f.art_style || "fkey_painterly");
      setResult({
        draft: (f.draft ?? {}) as Record<string, unknown>,
        prompt: f.prompt ?? "",
        negative: f.negative ?? "",
        issues: [],
        ok: true,
        canvas_tier: f.canvas_tier,
        art_style: f.art_style,
      });
      setNote(`${fid} 를 불러왔습니다.`);
    } catch (e) {
      setError(String(e));
    } finally {
      setBusy(false);
    }
  }

  async function remove(fid: string) {
    setBusy(true);
    try {
      await api.deleteFavorite(fid);
      loadFavorites();
    } catch (e) {
      setError(String(e));
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="wrap">
      <div className="stack-tight">
        <h1 style={{ margin: 0, fontSize: "var(--text-2xl)" }}>Illustration</h1>
        <p className="step-blurb">
          프로젝트 없이 프롬프트 한 장을 즉석에서 만듭니다. 명령을 넣으면 Type B 섹션
          프롬프트가 나오고, <strong>★ 즐겨찾기</strong>로 담거나 다음 것을 만들면 버려집니다.
        </p>
      </div>

      <div className="card stack" style={{ marginTop: "var(--s-4)" }}>
        <div className="field" style={{ marginBottom: 0 }}>
          <label>명령 (무엇을 그릴까)</label>
          <textarea
            value={brief}
            onChange={(e) => setBrief(e.target.value)}
            placeholder="예: 비 오는 골목, 우산 쓴 소녀, 따뜻한 빛, 시네마틱"
            rows={3}
            style={{ width: "100%", resize: "vertical" }}
          />
        </div>

        <div className="row" style={{ gap: "var(--s-4)", flexWrap: "wrap" }}>
          <div className="field" style={{ margin: 0 }}>
            <label>캔버스</label>
            <div className="tierpick" style={{ flexWrap: "wrap" }}>
              {TIERS.map((t) => (
                <button key={t.id} type="button" className="btn toggle" aria-pressed={tier === t.id}
                  title={`${t.id} — ${pxLabel(t.id)}`} onClick={() => setTier(t.id)}>
                  {t.id} · {t.w}×{t.h}
                </button>
              ))}
            </div>
          </div>
          <div className="field" style={{ margin: 0 }}>
            <label htmlFor="ill-style">화풍</label>
            <select id="ill-style" value={style} onChange={(e) => setStyle(e.target.value)}>
              {STYLES.map((s) => <option key={s.id} value={s.id}>{s.label}</option>)}
            </select>
          </div>
        </div>

        <div className="row" style={{ justifyContent: "flex-end" }}>
          <button className="btn btn--primary" onClick={generate} disabled={busy || !brief.trim()}>
            {busy ? "만드는 중…" : "프롬프트 만들기"}
          </button>
        </div>

        {error && <Note tone={result && !result.ok ? "warn" : "bad"}>{error}</Note>}
        {note && <Note tone="ok">{note}</Note>}
        {onProviders && (
          <span className="muted" style={{ fontSize: "var(--text-sm)" }}>
            모델을 못 부르면 <button className="btn" style={{ marginLeft: 4 }} onClick={onProviders}>프로바이더 설정</button>
          </span>
        )}
      </div>

      {result && (
        <div className="card stack" style={{ marginTop: "var(--s-4)" }}>
          <div className="between">
            <strong style={{ fontSize: "var(--text-lg)" }}>{draft.title || "결과"}</strong>
            <div className="row" style={{ gap: "var(--s-2)" }}>
              <button className="btn" onClick={star} disabled={busy}>★ 즐겨찾기 저장</button>
              <button className="btn" onClick={() => { setResult(null); setBrief(""); }} disabled={busy}>다음 프롬프트</button>
            </div>
          </div>

          <div>
            <div className="muted" style={{ fontSize: "var(--text-sm)", fontWeight: 600, marginBottom: 4 }}>style_and_aesthetic</div>
            <pre className="rules-pre" style={{ whiteSpace: "pre-wrap", margin: 0 }}>{draft.style_and_aesthetic}</pre>
          </div>

          {sections.map((s, i) => (
            <div key={s.name + i}>
              <div className="muted" style={{ fontSize: "var(--text-sm)", fontWeight: 600, marginBottom: 4 }}>&lt;|{s.name}|&gt;</div>
              <pre className="rules-pre" style={{ whiteSpace: "pre-wrap", margin: 0 }}>{s.caption}</pre>
            </div>
          ))}

          <details>
            <summary className="muted" style={{ cursor: "pointer", fontSize: "var(--text-sm)" }}>prompt.txt / negative.txt</summary>
            <div className="row" style={{ gap: "var(--s-2)", margin: "var(--s-2) 0" }}>
              <button className="btn" onClick={() => { copy(result.prompt); setCopied("prompt"); }}>prompt 복사</button>
              <button className="btn" onClick={() => { copy(result.negative); setCopied("negative"); }}>negative 복사</button>
              {copied && <span className="muted" style={{ fontSize: "var(--text-sm)" }}>{copied} 복사됨</span>}
            </div>
            <pre className="rules-pre" style={{ whiteSpace: "pre-wrap", maxHeight: 240 }}>{result.prompt}</pre>
            <pre className="rules-pre" style={{ whiteSpace: "pre-wrap", maxHeight: 200 }}>{result.negative}</pre>
          </details>
        </div>
      )}

      <div className="card stack" style={{ marginTop: "var(--s-4)" }}>
        <strong style={{ fontSize: "var(--text-lg)" }}>즐겨찾기</strong>
        {favorites.length === 0 ? (
          <p className="muted" style={{ margin: 0 }}>아직 저장한 프롬프트가 없습니다.</p>
        ) : (
          <div className="rows">
            {favorites.map((f) => (
              <div key={f.id} className="rowitem" style={{ justifyContent: "space-between", alignItems: "center" }}>
                <span className="row" style={{ gap: "var(--s-2)", alignItems: "center", minWidth: 0 }}>
                  <span aria-hidden>★</span>
                  <span className="mono muted" style={{ fontSize: 11 }}>{f.id}</span>
                  <strong style={{ overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>{f.title}</strong>
                  <span className="chip">{f.kind}</span>
                  <span className="chip mono">{f.canvas_tier}</span>
                  <span className="muted" style={{ fontSize: 11 }}>{f.updated}</span>
                </span>
                <span className="row" style={{ gap: "var(--s-2)" }}>
                  <button className="btn" onClick={() => load(f.id)} disabled={busy}>불러오기</button>
                  <button className="btn" onClick={() => remove(f.id)} disabled={busy}>삭제</button>
                </span>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
