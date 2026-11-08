import { useEffect, useState } from "react";
import { api, type Lang, type ProjectSummary } from "../api";
import { Note } from "../components/ui";

/**
 * The project list — what the main area shows when no project is open.
 *
 * The left rail stays empty except for "+ 새 프로젝트" until one is opened,
 * because a project's steps are the only thing that belongs there.
 */

function pick(text: Record<string, string> | undefined, lang: Lang): string {
  if (!text) return "";
  return text[lang] ?? text.en ?? Object.values(text)[0] ?? "";
}

export default function Projects({
  lang,
  onNew,
  onOpen,
}: {
  lang: Lang;
  onNew: () => void;
  onOpen: (slug: string) => void;
}) {
  const [items, setItems] = useState<ProjectSummary[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api.projects().then(setItems).catch((e) => setError(String(e)));
  }, []);

  if (error) {
    return (
      <Note tone="bad">
        백엔드에 연결하지 못했습니다. <span className="mono">{error}</span>
      </Note>
    );
  }
  if (!items) return <p className="muted">불러오는 중…</p>;

  return (
    <div className="wrap">
      <div className="between">
        <div className="stack-tight">
          <h1 style={{ margin: 0, fontSize: "var(--text-2xl)" }}>프로젝트</h1>
          <p className="step-blurb">
            프로젝트 설정 후 스토리 · 콘티 · 프롬프트 순서로 진행합니다. 프로젝트를 열면 위에 단계가
            나타나고, 어느 단계에서든 결과를 보고 고칠 수 있습니다.
          </p>
        </div>
        {/* the app bar already carries "+ 새 프로젝트"; one primary action per screen */}
      </div>

      {items.length === 0 && (
        <div className="empty">
          <span className="empty-title">아직 프로젝트가 없습니다.</span>
          <span className="muted" style={{ fontSize: "var(--text-sm)" }}>
            모든 질문에 기본값이 있어 그냥 계속 눌러도 끝까지 갑니다.
          </span>
          <button className="btn btn--primary" onClick={onNew}>
            + 새 프로젝트
          </button>
        </div>
      )}

      <div className="cards cards--wide">
        {items.map((p) => (
          <button
            key={p.slug}
            className="card"
            style={{ textAlign: "left", cursor: "pointer", color: "inherit" }}
            onClick={() => onOpen(p.slug)}
          >
            <div className="between">
              <strong style={{ fontSize: "var(--text-lg)" }}>{pick(p.title, lang) || p.slug}</strong>
              <span className="chip">{p.mode}</span>
            </div>

            <p className="muted" style={{ margin: "var(--s-3) 0 0", fontSize: "var(--text-sm)" }}>
              컷 {p.panels?.min}–{p.panels?.max}개 · {p.reading_direction?.toUpperCase()} ·{" "}
              {(p.languages?.all ?? []).map((l) => l.toUpperCase()).join(" / ")}
            </p>

            <div className="stack" style={{ marginTop: "var(--s-3)" }}>
              {p.episodes.length === 0 && (
                <span className="muted" style={{ fontSize: "var(--text-sm)" }}>
                  에피소드 없음 — 스토리 단계에서 추가하세요
                </span>
              )}
              {p.episodes.map((e) => (
                <div key={e.id} className="between" style={{ fontSize: "var(--text-sm)" }}>
                  <span>
                    <span className="mono">{e.id}</span>
                    {pick(e.title, lang) && <span className="muted"> · {pick(e.title, lang)}</span>}
                  </span>
                  <span className="row" style={{ gap: "var(--s-1)" }}>
                    {e.source ? (
                      <span className="chip chip--ok">소스</span>
                    ) : (
                      <span className="chip chip--warn">소스 필요</span>
                    )}
                    {e.plan && <span className="chip chip--ok">계획</span>}
                    <span className="muted mono">
                      {e.pages}
                      {e.page_total ? `/${e.page_total}` : ""}p
                    </span>
                  </span>
                </div>
              ))}
            </div>
          </button>
        ))}
      </div>
    </div>
  );
}
