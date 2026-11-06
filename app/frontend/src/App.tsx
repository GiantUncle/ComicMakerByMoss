import { useEffect, useState } from "react";
import { api, type Lang, type ProjectSummary, type StageStatus } from "./api";
import { applyTheme, loadTheme, THEMES, type Theme } from "./theme";
import { pxLabel } from "./lib/canvas";
import { STEPS, stepMeta, stageState } from "./lib/steps";
import { openEpisodeId } from "./lib/project";
import ModelMenu from "./components/ModelMenu";
import Projects from "./screens/Projects";
import Providers from "./screens/Providers";
import Wizard from "./screens/Wizard";

/**
 * The shell.
 *
 * The left rail is one project's seven steps — the only thing a user came here
 * to do. Every step is reachable in both directions: open a project, click any
 * step, see what that step made, judge it, and retake it. The manuscript
 * preview and the workbench are tabs inside step 7, not screens of their own.
 * The provider is app setup, so it sits at the bottom of the rail and never
 * competes with the work.
 *
 * `step` drives the main area: null is the project list, 1..7 are the steps,
 * -1 is the provider screen.
 */

// the language toggle lives in the top bar; the list is in lib/langs

function readUrl() {
  const q = new URLSearchParams(window.location.search);
  const lang = q.get("lang");
  const slug = q.get("project");
  const stepRaw = q.get("step");
  const step = stepRaw === null || stepRaw === "" ? null : Number(stepRaw);
  return {
    lang: lang === "ko" || lang === "en" || lang === "ja" ? (lang as Lang) : ("ko" as Lang),
    slug: slug && slug.trim() ? slug : null,
    step: step !== null && Number.isFinite(step) ? step : null,
  };
}

type RailState = "done" | "ready" | "blocked" | "idle";

interface RailRow {
  state: RailState;
  note: string;
}

export default function App() {
  const init = readUrl();
  const [theme, setTheme] = useState<Theme>(loadTheme);
  const [lang, setLang] = useState<Lang>(init.lang);
  const [slug, setSlug] = useState<string | null>(init.slug);
  const [step, setStep] = useState<number | null>(init.step);
  const [project, setProject] = useState<ProjectSummary | null>(null);
  const [stages, setStages] = useState<StageStatus[]>([]);
  const [saved, setSaved] = useState<string | null>(null);

  useEffect(() => applyTheme(theme), [theme]);

  useEffect(() => {
    const q = new URLSearchParams(window.location.search);
    if (slug) q.set("project", slug); else q.delete("project");
    if (step !== null) q.set("step", String(step)); else q.delete("step");
    if (lang !== "ko") q.set("lang", lang); else q.delete("lang");
    // wizard-owned params (ep/tab/page/block/tier) are managed by Wizard; preserve them
    const next = `${window.location.pathname}${q.toString() ? `?${q.toString()}` : ""}${window.location.hash}`;
    const cur = `${window.location.pathname}${window.location.search}${window.location.hash}`;
    if (next !== cur) window.history.replaceState(null, "", next);
  }, [slug, step, lang]);

  // the rail and the header both read the project's real state off the disk,
  // so saving a setting inside a step refreshes them on the way out.
  // stage states are read for the newest episode, because that is the one a
  // user is working on
  useEffect(() => {
    if (!slug) {
      setProject(null);
      setStages([]);
      setSaved(null);
      return;
    }
    let alive = true;
    // the list endpoint enriches every episode with its gates and page count,
    // which the single-project endpoint does not — so the rail reads the list
    api
      .projects()
      .then((all) => {
        if (!alive) return;
        const p = all.find((x) => x.slug === slug) ?? null;
        setProject(p);
        // stage states are read for the newest episode, the one being worked on
        api
          .stages(slug, openEpisodeId(p))
          .then((rows) => alive && setStages(rows))
          .catch(() => alive && setStages([]));
        api
          .wizard(slug)
          .then((w) => alive && setSaved(w.updated ?? null))
          .catch(() => alive && setSaved(null));
      })
      .catch(() => alive && setProject(null));
    return () => {
      alive = false;
    };
  }, [slug, step]);

  const cycleTheme = () =>
    setTheme(THEMES[(THEMES.findIndex((t) => t.id === theme) + 1) % THEMES.length].id);

  const openProject = (s: string) => {
    setSlug(s);
    setStep(2); // 프로젝트 설정
  };
  const closeProject = () => {
    setSlug(null);
    setStep(null);
  };

  return (
    <div className="shell">
      <header className="appbar">
        <div className="appbar-left">
          <button
            type="button"
            className="brand-btn"
            onClick={() => { setSlug(null); setStep(null); }}
            title="홈(프로젝트 목록)으로"
          >
            <span className="brand-word">ComicMaker</span>
            <span className="brand-line">MOSS-Image 프롬프터</span>
          </button>
          {project && (
            <>
              <span aria-hidden style={{ color: "var(--border)" }}>
                │
              </span>
              <div style={{ display: "flex", flexDirection: "column", justifyContent: "center", lineHeight: 1.15, gap: 1, minWidth: 0 }}>
                <span style={{ fontSize: "0.68rem", fontWeight: 600, color: "var(--fg-muted)", letterSpacing: "0.05em" }}>프로젝트</span>
                <strong style={{ fontSize: "1.2rem", fontWeight: 800, letterSpacing: "-0.02em", whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis" }}>
                  {project.title?.ko || project.title?.en || project.slug}
                </strong>
              </div>
            </>
          )}
        </div>

        <div className="appbar-right">
          {saved && (
            <span className="brand-sub" title="프로젝트 설정을 마지막으로 저장한 날짜" style={{ display: "inline-flex", alignItems: "center", gap: 4 }}>
              <span aria-hidden>💾</span> {saved}
            </span>
          )}
          <button className="btn" onClick={cycleTheme} title="누르면 테마가 바뀝니다" aria-label="테마 전환">
            <span aria-hidden>{THEMES.find((t) => t.id === theme)?.icon ?? "🎨"}</span>
            {THEMES.find((t) => t.id === theme)?.label ?? theme}
          </button>
          <ModelMenu />
        </div>
      </header>

      <div className="body">
        <ProjectRail
          slug={slug}
          step={step}
          project={project}
          stages={stages}
          onStep={setStep}
          onClose={closeProject}
          onNew={() => {
            setSlug(null);
            setStep(1); // 프로젝트 생성(모드 선택) — 레일에 표시되지 않음
          }}
        />

        <main className="main">
          {step === -1 && <Providers />}
          {step === null && (
            <Projects
              lang={lang}
              onNew={() => { setSlug(null); setStep(1); }}
              onOpen={openProject}
            />
          )}
          {step !== null && step !== -1 && (
            <Wizard
              lang={lang}
              slug={slug}
              step={step}
              onSlug={setSlug}
              onStep={setStep}
              onLang={setLang}
              onProviders={() => setStep(-1)}
            />
          )}
        </main>
      </div>
    </div>
  );
}

function ProjectRail({
  slug,
  step,
  project,
  stages,
  onStep,
  onClose,
  onNew,
}: {
  slug: string | null;
  step: number | null;
  project: ProjectSummary | null;
  stages: StageStatus[];
  onStep: (n: number | null) => void;
  onClose: () => void;
  onNew: () => void;
}) {
  const done = STEPS.filter((s) => railRow(s.n, stages, slug).state === "done").length;

  return (
    <nav className="rail" aria-label="프로젝트 단계">
      <button className="btn btn--primary" style={{ width: "100%", justifyContent: "center" }} onClick={onNew}>
        + 새 프로젝트
      </button>

      {slug && (
        <>
          <div className="rail-head" style={{ marginTop: "var(--s-4)" }}>
            <span className="rail-title">{project?.title?.ko || project?.title?.en || slug}</span>
            <span className="rail-meta">
              {project ? project.mode : slug}
            </span>
            <span className="rail-meta">
              페이지당 컷 {project?.panels?.min ?? "?"}–{project?.panels?.max ?? "?"} · 완료 {done}/{STEPS.length} 단계
            </span>
          </div>

          <p className="rail-meta" style={{ margin: "var(--s-3) 0 0" }}>
            한 프로젝트를 만드는 순서입니다. 어디서든 눌러 이동하고, 각 단계의 결과를 보고 고칠 수 있습니다.
          </p>

          <StepGroup
            title="프로젝트 전체 — 한 번"
            steps={STEPS.filter((s) => s.scope === "project" && s.n !== 1)}
            step={step}
            stages={stages}
            slug={slug}
            onStep={onStep}
          />
          <StepGroup
            title="에피소드마다 — 새 화마다 다시"
            steps={STEPS.filter((s) => s.scope === "episode")}
            step={step}
            stages={stages}
            slug={slug}
            onStep={onStep}
          />

          <div className="rail-foot">
            <button
              className="btn"
              style={{ justifyContent: "flex-start", gap: "var(--s-2)" }}
              aria-current={step === -1 ? "true" : undefined}
              onClick={() => onStep(-1)}
              title="AI 프로바이더 설정"
            >
              <span aria-hidden>⚙️</span>
              AI 프로바이더 설정
            </button>
          </div>
        </>
      )}

      {!slug && (
        <p className="rail-meta" style={{ marginTop: "var(--s-4)" }}>
          프로젝트를 열거나 새로 만들면 여기에 단계 순서가 나타납니다.
        </p>
      )}
    </nav>
  );
}

function StepGroup({
  title,
  steps,
  step,
  stages,
  slug,
  onStep,
}: {
  title: string;
  steps: typeof STEPS;
  step: number | null;
  stages: StageStatus[];
  slug: string | null;
  onStep: (n: number) => void;
}) {  return (
    <>
      <div className="rail-group">{title}</div>
      {steps.map((s) => {
        const row = railRow(s.n, stages, slug);
        const active = step === s.n;
        return (
          <button
            key={s.n}
            className="rail-item"
            aria-current={active ? "step" : undefined}
            onClick={() => onStep(s.n)}
          >
            <span className="rail-num" aria-hidden>
              {s.n}
            </span>
            <span className="rail-text">
              <span className="rail-label">{s.label}</span>
              <span className="rail-state">{row.note}</span>
            </span>
          </button>
        );
      })}
    </>
  );
}

/** What the rail says about a step, read off the stage table. */
export function railRow(n: number, stages: StageStatus[], slug: string | null): RailRow {
  const meta = stepMeta(n);
  if (!meta || !slug) return { state: "idle", note: "프로젝트를 여세요" };

  // project settings (step 2) are stored in project.json; treated as done when project exists
  if (meta.stages.length === 0) return { state: "done", note: "저장되어 있습니다" };

  const rows = meta.stages
    .map((id) => stages.find((s) => s.id === id))
    .filter((r): r is StageStatus => !!r);

  if (rows.length === 0) return { state: "ready", note: "열어두었습니다" };

  if (rows.some((r) => stageState(r.state) === "skip")) {
    return { state: "blocked", note: "이 프로젝트 모드에는 없습니다" };
  }
  if (rows.every((r) => stageState(r.state) === "done")) return { state: "done", note: "완료" };
  const waiting = rows.find((r) => stageState(r.state) === "waiting");
  if (waiting) return { state: "blocked", note: waiting.reason || "다른 단계 먼저" };
  return { state: "ready", note: "실행할 수 있습니다" };
}
