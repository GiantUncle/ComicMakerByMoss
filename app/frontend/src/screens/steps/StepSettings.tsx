import { useEffect, useState } from "react";
import { api, type ProjectSummary } from "../../api";
import { Note } from "../../components/ui";
import { TIERS, pxLabel } from "../../lib/canvas";

/**
 * Step 3 — 프로젝트 설정.
 * 사용자가 직접 보고 고치는 설정. AI 산출물/리테이크 프레임 없음.
 */

const STYLES = [
  { id: "fkey_painterly", label: "fkey_painterly — 선택적 포커스 구아슈" },
  { id: "fkey_clean", label: "fkey_clean — 깔끔한 상업 선화" },
];

const CUT_MODES = [
  { id: "balanced", label: "balanced — 템플릿을 고르고 조정" },
  { id: "template", label: "template — 조정 없이 고름" },
  { id: "free", label: "free — 직접 배치하고 검증" },
];

const FOCUS = [
  { id: "character", label: "캐릭터 중심", icon: "😊", desc: "주인공을 크게, 예쁘게. 인물을 파는 만화 (성인 · 로맨스)" },
  { id: "narrative", label: "이야기 중심", icon: "💬", desc: "결정적 · 충격적인 장면에 큰 컷 (스릴러 · 드라마 · 범죄)" },
  { id: "balanced", label: "균형", icon: "⚖️", desc: "페이지가 기대는 그 순간에 큰 컷 (기본)" },
];

interface Draft {
  title: { ko: string; en: string; ja: string };
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

const MODES: Record<string, string> = { manga: "만화", comic: "코믹스", illustration: "일러스트" };

function draftOf(p: ProjectSummary): Draft {
  return {
    title: { ko: p.title?.ko ?? "", en: p.title?.en ?? "", ja: p.title?.ja ?? "" },
    reading_direction: p.reading_direction ?? "rtl",
    tier: p.canvas?.tier ?? "M",
    art_style: p.art_style ?? "fkey_painterly",
    min: p.panels?.min ?? 3,
    max: p.panels?.max ?? 4,
    cut_mode: p.cut_mode ?? "balanced",
    detail_panels: p.detail_panels ?? false,
    story_focus: p.story_focus ?? "balanced",
    episode_pages: (p as any).episode_pages ?? 12,
  };
}

export default function StepSettings({
  slug,
  project,
  onSaved,
  busy,
  error,
  note,
}: {
  slug: string;
  project: ProjectSummary;
  onSaved: () => void;
  busy: boolean;
  error: string | null;
  note: string | null;
}) {
  const [draft, setDraft] = useState<Draft>(() => draftOf(project));
  const [local, setLocal] = useState<string | null>(null);

  const key = `${project.title?.ko}|${project.title?.en}|${project.title?.ja}|${project.reading_direction}|${project.canvas?.tier}|${project.art_style}|${project.panels?.min}|${project.panels?.max}|${project.cut_mode}|${project.detail_panels}|${project.story_focus}|${(project as any).episode_pages}`;
  useEffect(() => {
    setDraft(draftOf(project));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [key]);

  const set = (patch: Partial<Draft>) => setDraft((d) => ({ ...d, ...patch }));

  const lo = Math.max(1, Math.min(draft.min, 8));
  const hi = Math.max(lo, Math.min(draft.max, 8));
  const rangeOk = 1 <= lo && lo <= hi && hi <= 8;

  async function save() {
    setLocal(null);
    try {
      const detail_panels = hi > 4;
      await api.patchProject(slug, {
        title: draft.title,
        canvas: { tier: draft.tier, ratio: "a4_portrait" },
        reading_direction: draft.reading_direction,
        art_style: draft.art_style,
        panels: { min: lo, max: hi },
        detail_panels,
        story_focus: draft.story_focus,
        episode_pages: draft.episode_pages,
      });
      await api.patchWizard(slug, {
        answers: {
          canvas_tier: draft.tier,
          reading_direction: draft.reading_direction,
          art_style: draft.art_style,
          panels: { min: lo, max: hi },
          cut_mode: draft.cut_mode,
          detail_panels,
          story_focus: draft.story_focus,
          episode_pages: draft.episode_pages,
        },
      });
      onSaved();
    } catch (e) {
      setLocal(String(e));
    }
  }

  function setRangeMin(v: number) {
    const min = Math.max(1, Math.min(Math.round(v), 8));
    setDraft((d) => ({ ...d, min, max: Math.max(min, Math.min(d.max, 8)) }));
  }
  function setRangeMax(v: number) {
    const max = Math.max(1, Math.min(Math.round(v), 8));
    setDraft((d) => ({ ...d, max, min: Math.min(d.min, max) }));
  }

  const left = ((lo - 1) / 7) * 100;
  const right = ((hi - 1) / 7) * 100;

  const dirty =
    JSON.stringify(draft) !== JSON.stringify(draftOf(project)) ||
    !!error ||
    !!local;

  return (
    <div className="stack" style={{ gap: "var(--s-4)" }}>
      <div className="actionbar">
        <div className="actionbar-state">
          <strong style={{ fontSize: "var(--text-lg)" }}>프로젝트 설정</strong>
          <span className={`chip ${dirty ? "chip--warn" : "chip--ok"}`}>
            {dirty ? "변경됨 — 저장 필요" : "저장됨"}
          </span>
          <span className="actionbar-msg">
            {dirty ? "아래 값을 고친 뒤 위 버튼으로 저장" : "현재 설정 — 아래 확인"}
          </span>
        </div>
        <button type="button" className="btn btn--primary" onClick={save} disabled={busy || !rangeOk}>
          설정 저장
        </button>
      </div>
    <div className="card" style={{ padding: "var(--s-4)" }}>
      <div className="settings-grid">
        <div className="field settings-span-2" style={{ margin: 0 }}>
          <label>프로젝트 제목 (언어별)</label>
          <div className="row" style={{ gap: "var(--s-2)", flexWrap: "wrap" }}>
            {(["ko", "en", "ja"] as const).map((l) => (
              <input
                key={l}
                aria-label={`제목 ${l}`}
                placeholder={l.toUpperCase()}
                value={draft.title[l] ?? ""}
                onChange={(e) => set({ title: { ...draft.title, [l]: e.target.value } })}
                style={{ flex: "1 1 120px" }}
              />
            ))}
          </div>
          <span className="muted" style={{ fontSize: "var(--text-sm)" }}>
            모드: <strong>{MODES[project.mode] ?? project.mode}</strong> (프로젝트 생성 시 결정, 변경 불가)
          </span>
        </div>

        <div className="field" style={{ margin: 0 }}>
          <label>읽기 방향</label>
          <div className="row" style={{ gap: "var(--s-2)", flexWrap: "wrap" }}>
            <button type="button" className="dir-pick" aria-pressed={draft.reading_direction === "rtl"} onClick={() => set({ reading_direction: "rtl" })}>
              <span className="dir-pick__arrow" aria-hidden>← ← ←</span>
              <span className="dir-pick__label">오른쪽 → 왼쪽</span>
              <span className="dir-pick__sub">일본 만화식</span>
            </button>
            <button type="button" className="dir-pick" aria-pressed={draft.reading_direction === "ltr"} onClick={() => set({ reading_direction: "ltr" })}>
              <span className="dir-pick__arrow" aria-hidden>→ → →</span>
              <span className="dir-pick__label">왼쪽 → 오른쪽</span>
              <span className="dir-pick__sub">웹툰/일반</span>
            </button>
          </div>
        </div>

        <div className="field settings-span-2" style={{ margin: 0 }}>
          <label>캔버스 해상도</label>
          <div className="tierpick" style={{ flexWrap: "wrap" }}>
            {TIERS.map((t) => (
              <button
                key={t.id}
                type="button"
                className="btn toggle"
                aria-pressed={draft.tier === t.id}
                title={`${t.id} — ${pxLabel(t.id)}`}
                onClick={() => set({ tier: t.id })}
              >
                {t.id} · {t.w}×{t.h}
              </button>
            ))}
          </div>
        </div>

        <div className="field settings-span-2" style={{ margin: 0 }}>
          <div className="between">
            <label htmlFor="s-ep-pages">에피소드당 페이지 수</label>
            <span className="chip chip--ok" aria-live="polite">{draft.episode_pages}p</span>
          </div>
          <input
            id="s-ep-pages"
            type="range"
            min={1}
            max={32}
            step={1}
            value={draft.episode_pages}
            aria-label="에피소드당 페이지 수"
            onChange={(e) => setDraft((d) => ({ ...d, episode_pages: Math.max(1, Math.min(32, Math.round(Number(e.target.value)))) }))}
          />
          <span className="muted" style={{ fontSize: "var(--text-sm)" }}>1~32 (기본 12). 4의 배수 권장 — 저장 시 페이지 계획에 맞게 4의 배수로 맞춰집니다.</span>
        </div>

        <div className="field" style={{ margin: 0 }}>
          <label htmlFor="s-style">아트 스타일</label>
          <select id="s-style" value={draft.art_style} onChange={(e) => set({ art_style: e.target.value })}>
            {STYLES.map((s) => (
              <option key={s.id} value={s.id}>
                {s.label}
              </option>
            ))}
          </select>
        </div>

        <div className="field" style={{ margin: 0 }}>
          <label htmlFor="s-cut">컷 배치 방식</label>
          <select id="s-cut" value={draft.cut_mode} onChange={(e) => set({ cut_mode: e.target.value })}>
            {CUT_MODES.map((c) => (
              <option key={c.id} value={c.id}>
                {c.label}
              </option>
            ))}
          </select>
        </div>

        <div className="field settings-span-2" style={{ margin: 0 }}>
          <div className="between">
            <label>페이지당 컷 수 범위</label>
            <span className="chip chip--ok" aria-live="polite">{lo}컷 ~ {hi}컷</span>
          </div>
          <div className="range-dual" aria-label="페이지당 컷 수 범위">
            <div className="range-dual__track" />
            <div className="range-dual__fill" style={{ left: `${left}%`, width: `${Math.max(0, right - left)}%` }} />
            <input type="range" min={1} max={8} step={1} value={lo} aria-label="최소 컷 수" onChange={(e) => setRangeMin(Number(e.target.value))} />
            <input type="range" min={1} max={8} step={1} value={hi} aria-label="최대 컷 수" onChange={(e) => setRangeMax(Number(e.target.value))} />
          </div>
          <span className="muted" style={{ fontSize: "var(--text-sm)" }}>
            {hi > 4
              ? "5컷 이상은 컷이 작아집니다. AI가 아주 작은 컷을 안정적으로 그리기 어려우니, 가능하면 4컷 이하를 권장합니다."
              : "권장: 4컷 이하"}
          </span>
        </div>

        <div className="field settings-span-2" style={{ margin: 0 }}>
          <label>기본 전략</label>
          <div className="row" style={{ gap: "var(--s-2)", flexWrap: "wrap", alignItems: "stretch" }}>
            {FOCUS.map((f) => (
              <button
                key={f.id}
                type="button"
                className="rowitem rowitem--pick"
                aria-pressed={draft.story_focus === f.id}
                onClick={() => set({ story_focus: f.id })}
                style={{ flex: "1 1 180px", flexDirection: "row", alignItems: "flex-start", gap: 8, padding: "10px 12px", margin: 0 }}
              >
                <span aria-hidden style={{ fontSize: "1.35rem", lineHeight: 1 }}>{f.icon}</span>
                <span style={{ display: "flex", flexDirection: "column", gap: 2, minWidth: 0 }}>
                  <strong style={{ fontSize: "var(--text-sm)" }}>{f.label}</strong>
                  <span className="muted" style={{ fontSize: "11px", lineHeight: 1.35 }}>{f.desc}</span>
                </span>
              </button>
            ))}
          </div>
        </div>

        {error && <div className="settings-span-2"><Note tone="bad">{error}</Note></div>}
        {local && <div className="settings-span-2"><Note tone="bad">{local}</Note></div>}
        {note && <div className="settings-span-2"><Note tone="ok">{note}</Note></div>}
      </div>
    </div>
    </div>
  );
}
