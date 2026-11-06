import { useState } from "react";
import type { NewProjectIn, ProjectSummary } from "../../api";
import { KV, Note } from "../../components/ui";
import { TIERS, pxLabel } from "../../lib/canvas";

/**
 * Step 1 — mode.
 *
 * State first: no project yet -> empty with the create action at the top;
 * project exists -> current facts with the one save action at the top.
 * No narrative about what the stage "made" or whether it is "sound".
 */

/**
 * Step 1 — 모드.
 *
 * One question: what is this project making. The answer decides how many of
 * the later steps exist at all, so it is asked first and then shown as the
 * fact it is. Everything else about the project has a default and is set in
 * step 3.
 */

const MODES = [
  {
    id: "manga",
    label: "만화",
    desc: "컷이 여러 개 있는 원고 페이지 — 6단계 계획과 7단계 컷까지 전부 갑니다.",
  },
  {
    id: "comic",
    label: "코믹스",
    desc: "대사와 효과음이 있는 일러스트 한 장 — 6단계까지만 갑니다.",
  },
  {
    id: "illustration",
    label: "일러스트",
    desc: "대사 없는 일러스트 한 장 — 5단계 레퍼런스 시트에서 끝납니다.",
  },
];

const STYLES = [
  { id: "fkey_painterly", label: "fkey_painterly — 선택적 포커스 구아슈" },
  { id: "fkey_clean", label: "fkey_clean — 깔끔한 상업 선화" },
];

interface Draft {
  slug: string;
  title: { ko: string; en: string; ja: string };
  mode: string;
  reading_direction: string;
  tier: string;
  art_style: string;
  min: number;
  max: number;
  cut_mode: string;
  detail_panels: boolean;
  story_focus: string;
  episode_pages: number;
}

const EMPTY: Draft = {
  slug: "",
  title: { ko: "", en: "", ja: "" },
  mode: "manga",
  reading_direction: "rtl",
  tier: "M",
  art_style: "fkey_painterly",
  min: 3,
  max: 4,
  cut_mode: "balanced",
  detail_panels: false,
  story_focus: "balanced",
  episode_pages: 12,
};

const slugify = (s: string) =>
  s
    .toLowerCase()
    .normalize("NFKD")
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/^-+|-+$/g, "");

const SLUG_OK = /^[a-z0-9]+(-[a-z0-9]+)*$/;

export default function StepMode({
  project,
  busy,
  error,
  note,
  onCreate,
  onSave,
}: {
  project: ProjectSummary | null;
  busy: boolean;
  error: string | null;
  note: string | null;
  onCreate: (body: NewProjectIn) => Promise<string>;
  onSave: (patch: Record<string, unknown>) => Promise<void>;
}) {
  const [draft, setDraft] = useState<Draft>(EMPTY);
  const [title, setTitle] = useState({ ...(project?.title ?? { ko: "", en: "", ja: "" }) });
  const set = (patch: Partial<Draft>) => setDraft({ ...draft, ...patch });

  // keep the title field in step with the project on disk
  const key = project ? `${project.slug}:${project.title?.ko ?? ""}:${project.title?.en ?? ""}:${project.title?.ja ?? ""}` : "none";
  const [seen, setSeen] = useState(key);
  if (key !== seen) {
    setSeen(key);
    setTitle({ ...(project?.title ?? { ko: "", en: "", ja: "" }) });
  }

  if (!project) {
    const slug = draft.slug.trim() || slugify(draft.title.en);
    const checks = [
      {
        ok: !slug || SLUG_OK.test(slug),
        text: "프로젝트 식별자 — 소문자 kebab-case (폴더 이름이 됩니다)",
        detail: slug || "영문 제목에서 자동으로 만들어집니다",
      },
      { ok: 1 <= draft.min && draft.min <= draft.max && draft.max <= 8, text: "페이지당 컷 수 — 1컷 이상, 최대 8컷 이하" },
      { ok: TIERS.some((t) => t.id === draft.tier), text: "캔버스 해상도 — " + pxLabel(draft.tier) },
      { ok: true, text: "제목 — 언거나 비워도 됩니다 (나중에 고칠 수 있습니다)", info: true },
    ];
    const ok = checks.every((c) => c.ok || c.info);

    return (
      <div className="stack" style={{ gap: "var(--s-4)" }}>
        <div className="actionbar">
          <div className="actionbar-state">
            <strong style={{ fontSize: "var(--text-lg)" }}>새 프로젝트</strong>
            <span className="chip">현재 결과 없음</span>
            <span className="actionbar-msg">{ok ? "만들 수 있음" : "아래 확인 — 조건 미충족"}</span>
          </div>
          <button
            className="btn btn--primary"
            disabled={busy || !ok}
            onClick={() =>
              onCreate({
                slug,
                title: draft.title,
                mode: draft.mode,
                languages: { default: "ko", all: ["ko", "en", "ja"] },
                reading_direction: draft.reading_direction,
                canvas: { tier: draft.tier, ratio: "a4_portrait" },
                art_style: draft.art_style,
                panels: { min: draft.min, max: draft.max },
                cut_mode: draft.cut_mode,
                detail_panels: draft.detail_panels,
                story_focus: draft.story_focus,
                episode_pages: draft.episode_pages,
              })
            }
          >
            프로젝트 만들고 계속
          </button>
        </div>

        <div className="card stack">
          <div className="cards">
            {MODES.map((m) => (
              <button
                key={m.id}
                className="rowitem rowitem--pick"
                aria-pressed={draft.mode === m.id}
                onClick={() => set({ mode: m.id })}
                style={{ alignItems: "flex-start", flexDirection: "column", gap: "var(--s-2)" }}
              >
                <strong>{m.label}</strong>
                <span className="muted" style={{ fontSize: "var(--text-sm)" }}>
                  {m.desc}
                </span>
              </button>
            ))}
          </div>

          <div className="field">
            <label htmlFor="n-slug">프로젝트 식별자 (폴더 이름 — 비우면 영문 제목에서 만들어집니다)</label>
            <input
              id="n-slug"
              value={draft.slug}
              placeholder="talk-show"
              onChange={(e) => set({ slug: e.target.value })}
            />
          </div>

          <div className="field">
            <label>제목 — 언어별로 한 줄씩 (비워도 됩니다)</label>
            <div className="row">
              {(["ko", "en", "ja"] as const).map((l) => (
                <input
                  key={l}
                  aria-label={"제목 " + l}
                  placeholder={l.toUpperCase()}
                  value={draft.title[l]}
                  onChange={(e) => {
                    const title = { ...draft.title, [l]: e.target.value };
                    if (l === "en" && !draft.slug) {
                      setDraft({ ...draft, title, slug: slugify(e.target.value) });
                    } else {
                      set({ title });
                    }
                  }}
                  style={{ flex: 1 }}
                />
              ))}
            </div>
          </div>

          <div className="rows">
            {checks.map((c, i) => (
              <div
                key={i}
                className="rowitem"
                style={c.ok ? undefined : { borderColor: "var(--danger)" }}
              >
                <span className={"chip " + (c.ok ? "chip--ok" : "chip--bad")}>{c.ok ? "✓" : "✕"}</span>
                <span style={{ flex: 1, fontSize: "var(--text-sm)" }}>
                  {c.text}
                  {c.detail && (
                    <span className="muted" style={{ display: "block" }}>
                      {c.detail}
                    </span>
                  )}
                </span>
              </div>
            ))}
          </div>

          <p className="muted" style={{ fontSize: "var(--text-sm)", margin: 0 }}>
            읽기 방향 오른쪽→왼쪽 · 해상도 {pxLabel("M")} · 화풍 {STYLES[0].label.split(" — ")[0]} · 페이지당 컷 3~4개.
            이 다섯은 2단계 설정에서 바꿉니다.
          </p>

          {error && <Note tone="bad">{error}</Note>}
          {note && <Note tone="ok">{note}</Note>}
        </div>
      </div>
    );
  }

  /* ------------------------------------------------------ the project exists */
  const dirty =
    title.ko !== (project.title?.ko ?? "") ||
    title.en !== (project.title?.en ?? "") ||
    title.ja !== (project.title?.ja ?? "");

  const facts: [string, string][] = [
    ["식별자", project.slug],
    ["모드", MODES.find((m) => m.id === project.mode)?.label ?? project.mode],
    ["제목", [title.ko, title.en, title.ja].filter(Boolean).join(" · ") || "—"],
    ["언어", (project.languages?.all ?? []).map((l) => l.toUpperCase()).join(" · ")],
    ["읽기 방향", project.reading_direction === "rtl" ? "오른쪽 → 왼쪽" : "왼쪽 → 오른쪽"],
    ["캔버스", pxLabel(project.canvas?.tier)],
    ["화풍", project.art_style],
    ["페이지당 컷 수", `${project.panels?.min}컷 ~ ${project.panels?.max}컷`],
  ];

  return (
    <div className="stack" style={{ gap: "var(--s-4)" }}>
      <div className="actionbar">
        <div className="actionbar-state">
          <strong style={{ fontSize: "var(--text-lg)" }}>프로젝트</strong>
          <span className={"chip " + (dirty ? "chip--warn" : "chip--ok")}>
            {dirty ? "변경됨 — 저장 필요" : "현재 상태"}
          </span>
          <span className="actionbar-msg">{dirty ? "제목을 고친 뒤 위 버튼으로 저장" : "현재 설정 — 아래 확인"}</span>
        </div>
        <button className="btn btn--primary" disabled={busy || !dirty} onClick={() => onSave({ title })}>
          제목 저장
        </button>
      </div>

      <div className="card">
        <KV rows={facts.map(([k, v]) => [k, v] as [string, string])} />
      </div>

      <div className="card stack">
        <div className="field" style={{ marginBottom: 0 }}>
          <label>제목 — 언어별</label>
          <div className="row">
            {(["ko", "en", "ja"] as const).map((l) => (
              <input
                key={l}
                aria-label={"제목 " + l}
                placeholder={l.toUpperCase()}
                value={title[l] ?? ""}
                onChange={(e) => setTitle({ ...title, [l]: e.target.value })}
                style={{ flex: 1 }}
              />
            ))}
          </div>
        </div>

        <p className="muted" style={{ fontSize: "var(--text-sm)", margin: 0 }}>
          모드는 프로젝트를 만들 때 정하기 때문에 바꿀 수 없습니다 — 일러스트 · 코믹스 · 만화는 뒤 단계의
          개수가 다릅니다. 바꾸고 싶으면 새 프로젝트를 만드세요. 해상도 · 컷 수 · 화풍은 2단계에서 바꿉니다.
        </p>

        {error && <Note tone="bad">{error}</Note>}
        {note && <Note tone="ok">{note}</Note>}
      </div>
    </div>
  );
}
