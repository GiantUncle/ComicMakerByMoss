import { useEffect, useState } from "react";
import { api, type Lang, type ProjectSummary, type StageStatus } from "./api";
import { applyTheme, loadTheme, THEMES, type Theme } from "./theme";
import { openEpisodeId } from "./lib/project";
import ProductionBoard from "./components/ProductionBoard";
import ModelMenu from "./components/ModelMenu";
import Projects from "./screens/Projects";
import Providers from "./screens/Providers";
import Illustration from "./screens/Illustration";
import Wizard from "./screens/Wizard";

/**
 * The shell.
 *
 * The flow is read left to right on the production board across the top: each
 * step fills by state, the current step is outlined, and clicking a card opens
 * that step's page below. There is no vertical rail — the order is the point, so
 * it reads as a run of steps, not a menu.
 *
 * `step` drives the main area: null is the project list, 1..N are the steps,
 * -1 is the provider screen, -2 is the illustration tool.
 */

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

export default function App() {
  const init = readUrl();
  const [theme, setTheme] = useState<Theme>(loadTheme);
  const [lang, setLang] = useState<Lang>(init.lang);
  const [slug, setSlug] = useState<string | null>(init.slug);
  const [step, setStep] = useState<number | null>(init.step);
  const [project, setProject] = useState<ProjectSummary | null>(null);
  const [stages, setStages] = useState<StageStatus[]>([]);
  const [saved, setSaved] = useState<string | null>(null);
  // the last project step, so toggling back from a tool returns where the user was
  const [lastStep, setLastStep] = useState<number>(2);
  // a light project switcher — a popover, not a trip to the home page
  const [switcherOpen, setSwitcherOpen] = useState(false);
  const [allProjects, setAllProjects] = useState<ProjectSummary[]>([]);
  // bumped when a step changes the disk (episode created, stage run) so the board refetches
  const [tick, setTick] = useState(0);

  useEffect(() => applyTheme(theme), [theme]);
  useEffect(() => {
    if (typeof step === "number" && step > 0) setLastStep(step);
  }, [step]);

  // Esc closes the project switcher
  useEffect(() => {
    if (!switcherOpen) return;
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") setSwitcherOpen(false);
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [switcherOpen]);

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

  // the board and the header both read the project's real state off the disk, so
  // saving a setting inside a step refreshes them on the way out. Stage states
  // are read for the newest episode, because that is the one a user is working on.
  useEffect(() => {
    if (!slug) {
      setProject(null);
      setStages([]);
      setSaved(null);
      return;
    }
    let alive = true;
    api
      .projects()
      .then((all) => {
        if (!alive) return;
        const p = all.find((x) => x.slug === slug) ?? null;
        setProject(p);
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
  }, [slug, step, tick]);

  const cycleTheme = () =>
    setTheme(THEMES[(THEMES.findIndex((t) => t.id === theme) + 1) % THEMES.length].id);

  const openProject = (s: string) => {
    setSlug(s);
    setStep(2); // 프로젝트 설정
  };
  const newProject = () => {
    setSwitcherOpen(false);
    setSlug(null);
    setStep(1); // 프로젝트 생성(모드 선택)
  };
  const openSwitcher = () => {
    setSwitcherOpen(true);
    api.projects().then(setAllProjects).catch(() => setAllProjects([]));
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

          {/* one workspace at a time — the project, or the illustration tool. A
              radio-style pair, not two loose buttons: the inactive side is dimmed
              and clicking it switches back. */}
          <div className="ws-switcher">
            <div className="ws-toggle" role="tablist" aria-label="작업 영역">
              {project && (
                <button
                  type="button"
                  role="tab"
                  aria-selected={step !== -2}
                  aria-haspopup="menu"
                  aria-expanded={switcherOpen}
                  className="ws-tab"
                  title={step === -2 ? "프로젝트로 돌아가기" : "다른 프로젝트 선택"}
                  onClick={() => {
                    // in the tool -> back to the project; already in the project ->
                    // open a light switcher. The project is never unselected here.
                    if (step === -2) setStep(lastStep);
                    else if (switcherOpen) setSwitcherOpen(false);
                    else openSwitcher();
                  }}
                >
                  <span className="ws-tab-kind">프로젝트 ▾</span>
                  <span className="ws-tab-name">{project.title?.ko || project.title?.en || project.slug}</span>
                </button>
              )}
              <button
                type="button"
                role="tab"
                aria-selected={step === -2}
                className="ws-tab"
                title="프로젝트 없이 일러스트 프롬프트를 즉석에서 만듭니다"
                onClick={() => { setSwitcherOpen(false); setStep(-2); }}
              >
                <span className="ws-tab-kind">도구</span>
                <span className="ws-tab-name">한 장 프롬프트</span>
              </button>
            </div>

            {switcherOpen && (
              <>
                <div className="ws-menu-backdrop" onClick={() => setSwitcherOpen(false)} />
                <div className="ws-menu" role="menu" aria-label="프로젝트 전환">
                  <div className="ws-menu-head">프로젝트 전환</div>
                  {allProjects.length === 0 && <div className="ws-menu-empty muted">프로젝트가 없습니다.</div>}
                  {allProjects.map((p) => (
                    <button
                      key={p.slug}
                      type="button"
                      role="menuitem"
                      className="ws-menu-item"
                      aria-current={p.slug === slug ? "true" : undefined}
                      onClick={() => { setSwitcherOpen(false); openProject(p.slug); }}
                    >
                      <span className="ws-menu-title">{p.title?.ko || p.title?.en || p.slug}</span>
                      <span className="ws-menu-meta">{p.mode} · {p.episodes.length}화</span>
                    </button>
                  ))}
                  <button
                    type="button"
                    className="ws-menu-all"
                    onClick={() => { setSwitcherOpen(false); setSlug(null); setStep(null); }}
                  >
                    전체 프로젝트 목록 →
                  </button>
                </div>
              </>
            )}
          </div>
        </div>

        <div className="appbar-right">
          {saved && (
            <span className="brand-sub" title="프로젝트 설정을 마지막으로 저장한 날짜" style={{ display: "inline-flex", alignItems: "center", gap: 4 }}>
              <span aria-hidden>💾</span> {saved}
            </span>
          )}
          <button className="btn btn--primary" onClick={newProject} title="새 프로젝트 만들기">
            <span aria-hidden>＋</span> 새 프로젝트
          </button>
          <button className="btn" onClick={cycleTheme} title="누르면 테마가 바뀝니다" aria-label="테마 전환">
            <span aria-hidden>{THEMES.find((t) => t.id === theme)?.icon ?? "🎨"}</span>
            {THEMES.find((t) => t.id === theme)?.label ?? theme}
          </button>
          <ModelMenu onChanged={() => window.location.reload()} onProviders={() => setStep(-1)} />
        </div>
      </header>

      {/* the board belongs to a project workspace only — hidden in the tools */}
      {project && typeof step === "number" && step > 0 && (
        <ProductionBoard
          slug={slug}
          mode={project.mode}
          stages={stages}
          current={step}
          onPick={(n) => setStep(n)}
        />
      )}

      <main className="main">
        {step === -1 && <Providers />}
        {step === -2 && <Illustration onProviders={() => setStep(-1)} />}
        {step === null && (
          <Projects lang={lang} onNew={newProject} onOpen={openProject} />
        )}
        {step !== null && step !== -1 && step !== -2 && (
          <Wizard
            lang={lang}
            slug={slug}
            step={step}
            onSlug={setSlug}
            onStep={setStep}
            onLang={setLang}
            onProviders={() => setStep(-1)}
            onChanged={() => setTick((t) => t + 1)}
          />
        )}
      </main>
    </div>
  );
}
