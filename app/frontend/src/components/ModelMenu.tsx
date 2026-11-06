import { useEffect, useRef, useState } from "react";
import { api, type ModelCatalog, type ModelGroup } from "../api";

/**
 * The header model menu. Models come from every registered provider, favourites
 * pinned at the very top — grouped by provider so it is always clear which
 * provider a model is used from. The star moves a model into the favourites
 * block; pressing it again releases it. Refresh re-reads the provider's list.
 */
export default function ModelMenu({
  onChanged,
  onProviders,
}: {
  onChanged?: () => void;
  /** jumps to the provider screen — keys live there, not here */
  onProviders?: () => void;
}) {
  const [open, setOpen] = useState(false);
  const [cat, setCat] = useState<ModelCatalog | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const box = useRef<HTMLDivElement | null>(null);

  const load = () => api.models().then(setCat).catch((e) => setError(String(e)));
  useEffect(() => {
    load();
  }, []);

  useEffect(() => {
    if (!open) return;
    const onDoc = (e: MouseEvent) => {
      if (box.current && !box.current.contains(e.target as Node)) setOpen(false);
    };
    document.addEventListener("mousedown", onDoc);
    return () => document.removeEventListener("mousedown", onDoc);
  }, [open]);

  const active = cat?.active;
  const label = active?.model ? `${active.provider} · ${active.model}` : "모델 선택";
  const groups = cat?.groups ?? [];
  const withFavs = groups.filter((g) => g.favorites.length > 0);

  async function refresh() {
    setBusy(true);
    setError(null);
    try {
      await api.refreshModels();
      await load();
    } catch (e) {
      setError(String(e));
    } finally {
      setBusy(false);
    }
  }

  async function star(g: ModelGroup, model: string, e: React.MouseEvent) {
    e.stopPropagation();
    const on = !g.favorites.includes(model);
    try {
      setCat(await api.favoriteModel(g.provider, model, on));
    } catch (err) {
      setError(String(err));
    }
  }

  async function pick(g: ModelGroup, model: string) {
    try {
      setCat(await api.selectModel(g.provider, model));
      onChanged?.();
      setOpen(false);
    } catch (e) {
      setError(String(e));
    }
  }

  function Row({ g, model, fav }: { g: ModelGroup; model: string; fav: boolean }) {
    return (
      <div
        className="row"
        role="button"
        tabIndex={0}
        onClick={() => pick(g, model)}
        onKeyDown={(e) => e.key === "Enter" && pick(g, model)}
        style={{
          gap: "var(--s-2)",
          padding: "var(--s-2) var(--s-3)",
          cursor: "pointer",
          borderBottom: "1px solid var(--border-soft)",
          fontSize: "var(--text-sm)",
        }}
      >
        <span
          role="button"
          aria-label={fav ? "즐겨찾기 해제" : "즐겨찾기"}
          onClick={(e) => star(g, model, e)}
          style={{ color: fav ? "var(--warning)" : "var(--fg-muted)", width: 16, cursor: "pointer" }}
        >
          {fav ? "★" : "☆"}
        </span>
        <span style={{ flex: 1 }}>{model}</span>
        {active?.provider === g.provider && active?.model === model && <span className="chip chip--ok">사용</span>}
      </div>
    );
  }

  return (
    <div ref={box} style={{ position: "relative" }}>
      <button className="btn" onClick={() => setOpen(!open)} aria-expanded={open} title="모델 선택">
        <span aria-hidden>🤖</span>
        <span className="mono" style={{ maxWidth: 220, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
          {label}
        </span>
        <span aria-hidden>▾</span>
      </button>

      {open && (
        <div
          style={{
            position: "absolute",
            right: 0,
            top: "calc(100% + var(--s-2))",
            width: 380,
            maxHeight: "70vh",
            overflow: "auto",
            background: "var(--surface-2)",
            border: "1px solid var(--border)",
            borderRadius: "var(--radius)",
            boxShadow: "0 8px 30px rgba(0,0,0,0.25)",
            zIndex: 50,
          }}
        >
          <div className="between" style={{ padding: "var(--s-3)", borderBottom: "1px solid var(--border)" }}>
            <strong>모델</strong>
            <div className="row">
              <span className="muted" style={{ fontSize: "var(--text-sm)" }}>
                {groups.reduce((n, g) => n + g.models.length, 0)}개
              </span>
              <button className="btn" style={{ minHeight: 28 }} onClick={refresh} disabled={busy}>
                {busy ? "…" : "↻ 새로 고침"}
              </button>
            </div>
          </div>

          {/* keys and endpoints are set on the provider screen, not here */}
          {onProviders && (
            <button
              className="btn"
              style={{
                width: "100%",
                justifyContent: "flex-start",
                gap: "var(--s-2)",
                borderRadius: 0,
                border: 0,
                borderBottom: "1px solid var(--border)",
              }}
              onClick={() => {
                setOpen(false);
                onProviders();
              }}
            >
              <span aria-hidden>⚙️</span>
              프로바이더 설정 — API 키 · 엔드포인트
            </button>
          )}

          {error && (
            <div className="chip--bad" style={{ padding: "var(--s-2) var(--s-3)", fontSize: "var(--text-sm)" }}>
              {error}
            </div>
          )}

          {withFavs.length > 0 && (
            <div>
              <div className="muted" style={{ padding: "var(--s-2) var(--s-3)", fontSize: "var(--text-sm)" }}>
                ★ 즐겨찾기
              </div>
              {withFavs.map((g) => (
                <div key={`fav-${g.provider}`}>
                  <div style={{ padding: "var(--s-1) var(--s-3)", fontSize: "var(--text-sm)" }}>
                    <span className="chip">{g.label}</span>
                  </div>
                  {g.favorites.map((m) => (
                    <Row key={`f-${m}`} g={g} model={m} fav />
                  ))}
                </div>
              ))}
            </div>
          )}

          <div className="muted" style={{ padding: "var(--s-2) var(--s-3)", fontSize: "var(--text-sm)" }}>
            모든 모델 — 프로바이더별
          </div>
          {groups.map((g) => (
            <div key={g.provider}>
              <div className="between" style={{ padding: "var(--s-1) var(--s-3)" }}>
                <span className="chip">{g.label}</span>
                <span className="muted" style={{ fontSize: "var(--text-sm)" }}>
                  {g.configured ? (g.models.length ? `${g.models.length}개` : "목록 없음") : "키 없음"}
                </span>
              </div>
              {g.models.map((m) => (
                <Row key={`${g.provider}-${m}`} g={g} model={m} fav={g.favorites.includes(m)} />
              ))}
              {g.configured && g.models.length === 0 && (
                <div className="muted" style={{ padding: "var(--s-2) var(--s-3)", fontSize: "var(--text-sm)" }}>
                  ↻ 새로 고침으로 목록을 받아오세요
                </div>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
