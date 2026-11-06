import { useEffect, useState } from "react";
import { api, type SkillAsset } from "../api";

/**
 * The rules one step runs by, on that step's own screen.
 *
 * A step's behaviour IS its skill document, so the rule, the output and the
 * retake belong on one screen: a retake is the model running the rule you are
 * looking at. The shipped original is read-only; editing copies it, and the
 * copy is what every later run reads until it is rolled back.
 */

/** The craft documents each stage attaches to its prompt (mirrors registry.py). */
const CRAFT: Record<string, string[]> = {
  "manga-3-bible": ["manga-craft/character-consistency.md"],
  "manga-5-plan": ["manga-craft/comic-planning.md"],
  "manga-6-conti": ["manga-craft/comic-planning.md", "manga-craft/character-consistency.md"],
};

interface Body {
  path: string;
  edited: boolean;
  origin: string;
  content: string;
}

export default function StageRules({ stage }: { stage: string }) {
  const [open, setOpen] = useState(false);
  const [assets, setAssets] = useState<SkillAsset[] | null>(null);
  const [which, setWhich] = useState<string | null>(null);
  const [body, setBody] = useState<Body | null>(null);
  const [draft, setDraft] = useState("");
  const [editing, setEditing] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [note, setNote] = useState<string | null>(null);

  const skillPath = `${stage}/SKILL.md`;
  const paths = [skillPath, ...(CRAFT[stage] ?? [])];

  useEffect(() => {
    setWhich(null);
    setBody(null);
    setEditing(false);
    setNote(null);
    setError(null);
  }, [stage]);

  useEffect(() => {
    if (!open) return;
    api
      .skills()
      .then((a) => setAssets(a))
      .catch((e) => setError(String(e)));
  }, [open]);

  async function load(path: string) {
    setError(null);
    setNote(null);
    try {
      const b = await api.skill(path);
      setBody(b);
      setDraft(b.content);
      setWhich(path);
      setEditing(false);
    } catch (e) {
      setError(String(e));
    }
  }

  async function save() {
    if (!body) return;
    setBusy(true);
    setError(null);
    try {
      await api.saveSkill(body.path, draft);
      setNote("저장했습니다. 다음 실행부터 이 규칙씁니다.");
      setEditing(false);
      const [a, b] = await Promise.all([api.skills(), api.skill(body.path)]);
      setAssets(a);
      setBody(b);
    } catch (e) {
      setError(String(e));
    } finally {
      setBusy(false);
    }
  }

  async function rollback() {
    if (!body) return;
    setBusy(true);
    setError(null);
    try {
      await api.rollbackSkill(body.path);
      setNote("원본으로 되돌렸습니다.");
      const [a, b] = await Promise.all([api.skills(), api.skill(body.path)]);
      setAssets(a);
      setBody(b);
      setDraft(b.content);
      setEditing(false);
    } catch (e) {
      setError(String(e));
    } finally {
      setBusy(false);
    }
  }

  const assetOf = (p: string) => assets?.find((a) => a.path === p);

  if (!open) {
    return (
      <div>
        <button
          className="btn"
          style={{ color: "var(--fg-muted)" }}
          aria-expanded={false}
          onClick={() => {
            setOpen(true);
            load(skillPath);
          }}
        >
          이 단계의 규칙 보기
        </button>
      </div>
    );
  }

  return (
    <div className="rules">
      <div className="between">
        <strong style={{ fontSize: "var(--text-sm)" }}>이 단계의 규칙</strong>
        <button className="btn" style={{ minHeight: 28 }} onClick={() => setOpen(false)}>
          접기
        </button>
      </div>

      <div className="rules-list">
        {paths.map((p) => {
          const a = assetOf(p);
          const on = which === p;
          return (
            <button
              key={p}
              className="btn rules-item"
              aria-pressed={on}
              onClick={() => load(p)}
              disabled={!assets}
            >
              <span className="mono" style={{ overflow: "hidden", textOverflow: "ellipsis" }}>
                {p}
              </span>
              <span style={{ flex: 1 }} />
              {a?.edited ? (
                <span className="chip chip--warn">수정본</span>
              ) : a ? (
                <span className="chip">원본</span>
              ) : (
                <span className="chip">…</span>
              )}
            </button>
          );
        })}
      </div>

      {!body && <p className="muted">불러오는 중…</p>}

      {body && (
        <div className="rules-body">
          <div className="between">
            <div className="row">
              {body.edited ? (
                <span className="chip chip--warn">수정본 사용 중</span>
              ) : (
                <span className="chip chip--ok">원본 사용 중</span>
              )}
              <span className="muted" style={{ fontSize: "var(--text-sm)" }}>
                원본은 읽기 전용입니다 — 수정하면 복사본이 생깁니다
              </span>
            </div>
            <div className="row">
              <button
                className="btn"
                style={{ minHeight: 28 }}
                onClick={() => {
                  setEditing(!editing);
                  setDraft(body.content);
                }}
                disabled={busy}
              >
                {editing ? "취소" : "수정"}
              </button>
              {body.edited && (
                <button className="btn btn--danger" style={{ minHeight: 28 }} onClick={rollback} disabled={busy}>
                  원본으로 되돌리기
                </button>
              )}
            </div>
          </div>

          {editing ? (
            <>
              <textarea
                value={draft}
                onChange={(e) => setDraft(e.target.value)}
                spellCheck={false}
                style={{ minHeight: 320, font: "var(--text-sm)/1.6 var(--font-mono)" }}
              />
              <div className="row">
                <button className="btn btn--primary" onClick={save} disabled={busy || draft === body.content}>
                  저장
                </button>
                <span className="muted" style={{ fontSize: "var(--text-sm)" }}>
                  저장 즉시 다음 실행부터 적용됩니다
                </span>
              </div>
            </>
          ) : (
            <pre className="rules-pre">{body.content}</pre>
          )}

          {body.edited && (
            <details>
              <summary className="muted" style={{ fontSize: "var(--text-sm)", cursor: "pointer" }}>
                배포 원본 보기 (읽기 전용)
              </summary>
              <pre className="rules-pre" style={{ marginTop: "var(--s-2)" }}>
                {body.origin}
              </pre>
            </details>
          )}

          {note && <div className="chip chip--ok">{note}</div>}
          {error && (
            <div className="chip--bad" style={{ fontSize: "var(--text-sm)" }}>
              {error}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
