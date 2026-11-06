import { useEffect, useState } from "react";
import { api, type NewEpisodeIn, type ProjectSummary } from "../../api";
import { Note } from "../../components/ui";

/**
 * Step 2 — 스토리.
 * 사용자가 붙여 넣거나 적은 내용을 보고 수정/저장하고, 필요하면 AI로 소설을 생성합니다.
 */

const ROUTES = [
  { id: "provided", label: "스토리가 있다 — 붙여넣기" },
  { id: "premise", label: "전제만 있다 — AI가 소설로 씀" },
  { id: "genre", label: "장르/분위기 — AI가 소설로 씀" },
  { id: "outline", label: "개요 — AI가 소설로 늘림" },
];

interface EpDraft {
  id: string;
  title: { ko: string; en: string; ja: string };
  route: string;
  story: string;
}

export default function StepStory({
  slug,
  project,
  ep,
  onEp,
  onCreated,
  busy,
  error,
  note,
}: {
  slug: string;
  project: ProjectSummary;
  ep: string | null;
  onEp: (id: string) => void;
  onCreated: (id: string) => void;
  busy: boolean;
  error: string | null;
  note: string | null;
}) {
  const [text, setText] = useState("");
  const [sourceKind, setSourceKind] = useState<string | null>(null);
  const [approved, setApproved] = useState(false);
  const [adding, setAdding] = useState(false);
  const [busyLocal, setBusyLocal] = useState(false);
  const [localNote, setLocalNote] = useState<string | null>(null);
  const [localError, setLocalError] = useState<string | null>(null);
  const [epDraft, setEpDraft] = useState<EpDraft>({
    id: `ep${String((project?.episodes.length ?? 0) + 1).padStart(2, "0")}`,
    title: { ko: "", en: "", ja: "" },
    route: "provided",
    story: "",
  });

  const episodes = project?.episodes ?? [];
  const current = ep ?? episodes[episodes.length - 1]?.id ?? null;
  const busyAll = busy || busyLocal;

  useEffect(() => {
    if (!current) {
      setText("");
      setSourceKind(null);
      setApproved(false);
      return;
    }
    let alive = true;
    api
      .episodeSource(slug, current)
      .then((s) => {
        if (!alive) return;
        setText(s.text ?? "");
        setSourceKind(s.kind ?? null);
        setApproved(!!s.approved);
      })
      .catch(() => {
        if (!alive) return;
        setText("");
        setSourceKind(null);
        setApproved(false);
      });
    return () => {
      alive = false;
    };
  }, [slug, current]);

  async function saveText() {
    if (!current) return;
    setBusyLocal(true);
    setLocalError(null);
    setLocalNote(null);
    try {
      await api.saveEpisodeSource(slug, current, { text, mode: "provided" });
      setSourceKind("novel");
      setApproved(true);
      setLocalNote("저장했습니다.");
      onCreated(current);
    } catch (e) {
      setLocalError(String(e));
    } finally {
      setBusyLocal(false);
    }
  }

  async function generateNovel() {
    if (!current) return;
    setBusyLocal(true);
    setLocalError(null);
    setLocalNote(null);
    try {
      await api.saveEpisodeSource(slug, current, { text, mode: "brief", origin: "premise" });
      const r = await api.runStage({ slug, stage: "manga-1-source", episode: current });
      if ((r as any).dry) {
        setLocalNote("프롬프트 확인만 했습니다.");
      } else {
        const s = await api.episodeSource(slug, current);
        setText(s.text ?? "");
        setSourceKind(s.kind ?? "novel");
        setApproved(!!s.approved);
        setLocalNote((r as any).note ? `AI 생성 완료: ${(r as any).note}` : "AI가 소설을 생성했습니다.");
        onCreated(current);
      }
    } catch (e) {
      setLocalError(String(e));
    } finally {
      setBusyLocal(false);
    }
  }

  async function createEpisode() {
    const body: NewEpisodeIn = {
      id: epDraft.id,
      title: epDraft.title,
      source_origin: epDraft.route,
      story: epDraft.story || null,
    };
    setBusyLocal(true);
    setLocalError(null);
    try {
      await api.createEpisode(slug, body);
      onCreated(epDraft.id);
      onEp(epDraft.id);
      setAdding(false);
      setEpDraft({
        id: `ep${String((project?.episodes.length ?? 0) + 2).padStart(2, "0")}`,
        title: { ko: "", en: "", ja: "" },
        route: "provided",
        story: "",
      });
    } catch (e) {
      setLocalError(String(e));
    } finally {
      setBusyLocal(false);
    }
  }

  if (!current) {
    return (
      <div className="stack" style={{ gap: "var(--s-4)" }}>
        <div className="card stack">
          <strong>에피소드가 없습니다</strong>
          <span className="muted" style={{ fontSize: "var(--text-sm)" }}>
            이번 화의 스토리를 붙여넣거나, 아이디어를 적고 AI로 소설을 생성할 수 있습니다.
          </span>
        </div>
        <EpisodeForm
          draft={epDraft}
          setDraft={setEpDraft}
          busy={busyAll}
          onCreate={() => createEpisode()}
          error={error || localError}
          note={note || localNote}
        />
      </div>
    );
  }

  return (
    <div className="stack" style={{ gap: "var(--s-4)" }}>
      <div className="actionbar">
        <div className="actionbar-state">
          <strong style={{ fontSize: "var(--text-lg)" }}>스토리</strong>
          <span className="chip">에피소드 {current}</span>
          {approved ? <span className="chip chip--ok">저장됨</span> : <span className="chip chip--warn">미저장</span>}
          {sourceKind === "brief" && <span className="chip">아이디어</span>}
          <span className="actionbar-msg">
            {approved ? "현재 원문 있음 — 아래 확인" : "현재 원문 없음 — 붙여넣고 저장"}
          </span>
        </div>
        <div className="row" style={{ flexWrap: "wrap", justifyContent: "flex-end" }}>
          {episodes.length > 1 && (
            <label className="row" style={{ gap: "var(--s-2)", fontSize: "var(--text-sm)" }}>
              <span className="muted">에피소드</span>
              <select value={current} onChange={(e) => onEp(e.target.value)}>
                {episodes.map((e) => (
                  <option key={e.id} value={e.id}>
                    {e.id}
                  </option>
                ))}
              </select>
            </label>
          )}
          <button type="button" className="btn" onClick={saveText} disabled={busyAll || !current || !text.trim()}>
            저장
          </button>
          <button type="button" className="btn btn--primary" onClick={generateNovel} disabled={busyAll || !current || !text.trim()}>
            {busyAll ? "생성 중…" : "AI로 소설 생성"}
          </button>
        </div>
      </div>

      <div className="card stack">
        <div className="field" style={{ marginBottom: 0 }}>
          <label htmlFor="story-text">현재 원문</label>
          <textarea
            id="story-text"
            value={text}
            onChange={(e) => setText(e.target.value)}
            placeholder={"소설 본문을 붙여넣거나, 어떤 이야기인지 적어주세요.\n예: 심야 토크쇼 진행자가 매일 밤 다른 손님을 맞는데, 어느 날 손님이 전부 퇴근 복장의 직장인이다."}
            spellCheck={false}
            style={{ minHeight: 320, fontFamily: "inherit", lineHeight: 1.6 }}
          />
        </div>

        {(error || localError) && <Note tone="bad">{error || localError}</Note>}
        {(note || localNote) && <Note tone="ok">{note || localNote}</Note>}
      </div>

      <div className="card stack-tight">
        <button type="button" className="btn" onClick={() => setAdding(!adding)} aria-expanded={adding} style={{ justifyContent: "flex-start" }}>
          {adding ? "접기" : "다른 에피소드 추가"}
        </button>
        {adding && (
          <div style={{ marginTop: "var(--s-3)" }}>
            <EpisodeForm
              draft={epDraft}
              setDraft={setEpDraft}
              busy={busyAll}
              onCreate={() => createEpisode()}
              error={localError}
              note={localNote}
            />
          </div>
        )}
      </div>
    </div>
  );
}

function EpisodeForm({
  draft,
  setDraft,
  busy,
  onCreate,
  error,
  note,
}: {
  draft: EpDraft;
  setDraft: (d: EpDraft) => void;
  busy: boolean;
  onCreate: () => void;
  error: string | null;
  note: string | null;
}) {
  const set = (patch: Partial<EpDraft>) => setDraft({ ...draft, ...patch });
  return (
    <div className="stack">
      <div className="field">
        <label htmlFor="e-id">에피소드 id</label>
        <input id="e-id" value={draft.id} onChange={(e) => set({ id: e.target.value })} />
      </div>

      <div className="field">
        <label>에피소드 제목 (선택)</label>
        <div className="row">
          {(["ko", "en", "ja"] as const).map((l) => (
            <input
              key={l}
              aria-label={`에피소드 제목 ${l}`}
              placeholder={l.toUpperCase()}
              value={draft.title[l]}
              onChange={(e) => set({ title: { ...draft.title, [l]: e.target.value } })}
              style={{ flex: 1 }}
            />
          ))}
        </div>
      </div>

      <div className="field">
        <label htmlFor="e-route">스토리 입력 방식</label>
        <select id="e-route" value={draft.route} onChange={(e) => set({ route: e.target.value })}>
          {ROUTES.map((r) => (
            <option key={r.id} value={r.id}>
              {r.label}
            </option>
          ))}
        </select>
      </div>

      <div className="field">
        <label htmlFor="e-story">내용</label>
        <textarea
          id="e-story"
          value={draft.story}
          onChange={(e) => set({ story: e.target.value })}
          placeholder={
            draft.route === "provided"
              ? "소설 본문을 그대로 붙여넣으세요."
              : "아이디어/전제/장르/개요를 적으세요. 만든 뒤 'AI로 소설 생성'을 사용할 수 있습니다."
          }
          spellCheck={false}
          style={{ minHeight: 180 }}
        />
      </div>

      {error && <Note tone="bad">{error}</Note>}
      {note && <Note tone="ok">{note}</Note>}

      <div className="row">
        <button type="button" className="btn btn--primary" disabled={busy || !draft.story.trim()} onClick={onCreate}>
          에피소드 만들기
        </button>
      </div>
    </div>
  );
}
