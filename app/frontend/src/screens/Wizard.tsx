import { useEffect, useState } from "react";
import { api, type Lang, type ProjectSummary, type StageStatus } from "../api";
import StageRunner from "../components/StageRunner";
import { Note } from "../components/ui";
import { SCOPE_LABEL, stepMeta, stageState } from "../lib/steps";
import { episodeSummary, hasEpisode, openEpisodeId } from "../lib/project";
import StepMode from "./steps/StepMode";
import StepStory from "./steps/StepStory";
import StepSettings from "./steps/StepSettings";
import Preview from "./Preview";
import Workbench from "./Workbench";

/**
 * The step screen.
 *
 * One step at a time, chosen from the left rail, so any step is reachable again
 * — there is no one-way door. Steps 1-3 are forms that write the project's own
 * files; steps 4-7 are pipeline stages, so they are the stage runner with its
 * three sections: what it made, whether that is sound, what to redo. Step 7
 * carries the manuscript preview and the workbench as tabs inside it, because
 * they belong to that step and nowhere else.
 */

function readWizardUrl() {
  const q = new URLSearchParams(window.location.search);
  const tab = q.get("tab");
  const page = Number(q.get("page"));
  const block = Number(q.get("block"));
  const tier = q.get("tier");
  return {
    ep: q.get("ep"),
    tab: tab === "make" || tab === "preview" || tab === "bench" ? tab : "make",
    page: Number.isFinite(page) && page >= 1 ? Math.floor(page) : 1,
    block: Number.isFinite(block) && block >= 1 ? Math.floor(block) : 1,
    tier: tier === "S" || tier === "M" || tier === "L" || tier === "XL" ? tier : "M",
  };
}

export default function Wizard({
  lang,
  slug,
  step,
  onSlug,
  onStep,
  onLang,
  onProviders,
}: {
  lang: Lang;
  slug: string | null;
  step: number;
  onSlug: (slug: string | null) => void;
  onStep: (n: number) => void;
  onLang: (lang: Lang) => void;
  onProviders: () => void;
}) {
  const init = readWizardUrl();
  const [project, setProject] = useState<ProjectSummary | null>(null);
  const [stages, setStages] = useState<StageStatus[]>([]);
  const [ep, setEp] = useState<string | null>(init.ep);
  type Tab = "make" | "preview" | "bench";
  const isTab = (v: string): v is Tab => v === "make" || v === "preview" || v === "bench";
  const [tab, setTab] = useState<Tab>(isTab(init.tab) ? init.tab : "make");
  const [page, setPage] = useState(init.page);
  const [block, setBlock] = useState(init.block);
  const [tier, setTier] = useState(init.tier);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [note, setNote] = useState<string | null>(null);

  useEffect(() => {
    onSlug(slug);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [slug]);

  useEffect(() => {
    if (!slug) {
      setProject(null);
      setStages([]);
      setEp(null);
      return;
    }
    let alive = true;
    // the list endpoint enriches each episode with its page count and gates;
    // the single-project endpoint returns ids only
    api
      .projects()
      .then((all) => {
        if (!alive) return;
        setProject(all.find((x) => x.slug === slug) ?? null);
      })
      .catch((e) => alive && setError(String(e)));
    return () => {
      alive = false;
    };
  }, [slug, step]);

  useEffect(() => {
    if (!slug || !ep) {
      setStages([]);
      return;
    }
    api
      .stages(slug, ep)
      .then(setStages)
      .catch(() => setStages([]));
  }, [slug, ep, step]);

  // the open episode is the newest one; switching projects resets it
  useEffect(() => {
    if (!project) return; // wait for project load so URL-restored ep isn't wiped
    if (!hasEpisode(project, ep)) setEp(openEpisodeId(project));
  }, [project, ep]);

  // migrate legacy/hidden step numbers: old 1(mode)->2(settings), old 7->6 etc handled by direct use; step 1 now means story
  useEffect(() => {
    if (!slug || !project) return;
    // legacy step 7 (old cut/prompt) -> 6
    if (step === 7) onStep(6);
  }, [slug, project, step, onStep]);

  // the view tier follows the project until the user picks another size (unless URL specified)
  useEffect(() => {
    const fromUrl = new URLSearchParams(window.location.search).get("tier");
    if (fromUrl) return;
    if (project?.canvas?.tier) setTier(project.canvas.tier);
  }, [project?.canvas?.tier]);

  useEffect(() => {
    if (!slug) return;
    const q = new URLSearchParams(window.location.search);
    if (ep) q.set("ep", ep); else q.delete("ep");
    if (step === 6) q.set("tab", tab); else q.delete("tab");
    if (step === 6) q.set("page", String(Math.max(1, page))); else q.delete("page");
    if (step >= 3 && step <= 6) q.set("block", String(Math.max(1, block))); else q.delete("block");
    if (step === 6) q.set("tier", tier); else q.delete("tier");
    const next = `${window.location.pathname}${q.toString() ? `?${q.toString()}` : ""}${window.location.hash}`;
    const cur = `${window.location.pathname}${window.location.search}${window.location.hash}`;
    if (next !== cur) window.history.replaceState(null, "", next);
  }, [slug, step, ep, tab, page, block, tier]);

  const episode = episodeSummary(project, ep);
  const pageTotal = episode?.page_total ?? null;
  const pages = Math.max(1, pageTotal ?? 1);
  const blocks = Math.max(1, Math.ceil(pages / 4));

  function refresh() {
    setError(null);
    setNote(null);
    if (!slug) return;
    api.project(slug).then(setProject).catch((e) => setError(String(e)));
  }

  async function createProject(body: Parameters<typeof api.createProject>[0]) {
    setBusy(true);
    setError(null);
    try {
      const created = await api.createProject(body);
      onSlug(created.slug);
      setNote(`프로젝트 ${created.slug} 를 만들었습니다. 이제 2단계에서 스토리를 넣으세요.`);
      onStep(1);
      return created.slug;
    } catch (e) {
      setError(String(e));
      return "";
    } finally {
      setBusy(false);
    }
  }

  async function patchProject(patch: Record<string, unknown>) {
    if (!slug) return;
    setBusy(true);
    setError(null);
    try {
      await api.patchProject(slug, patch);
      setNote("저장했습니다.");
      refresh();
    } catch (e) {
      setError(String(e));
    } finally {
      setBusy(false);
    }
  }

  const meta = stepMeta(step);

  return (
    <div className="wrap">
      {meta && (
        <div className="step-head">
          <div className="step-title">
            {meta.n} · {meta.label}
            <span className="chip">{SCOPE_LABEL[meta.scope]}</span>
          </div>
          <p className="step-blurb">{meta.blurb}</p>
        </div>
      )}

      {error && <Note tone="bad">{error}</Note>}
      {note && <Note tone="ok">{note}</Note>}

      {/* no project yet: only step 1 can be on screen, so any step opens it */}
      {(!slug || !project) && (
        <StepMode
          project={null}
          busy={busy}
          error={error}
          note={note}
          onCreate={createProject}
          onSave={patchProject}
        />
      )}

      {/* ------------------------------------------------------------ steps */}
      {null}

      {slug && project && step === 1 && (
        <StepStory
          slug={slug}
          project={project}
          ep={ep}
          onEp={setEp}
          onCreated={refresh}
          busy={busy}
          error={error}
          note={note}
        />
      )}

      {slug && project && step === 2 && (
        <StepSettings
          slug={slug}
          project={project}
          onSaved={refresh}
          busy={busy}
          error={error}
          note={note}
        />
      )}

      {slug && project && (step === 3 || step === 4 || step === 5) && (
        <StageRunner
          slug={slug}
          ep={ep}
          stage={stepMeta(step)!.stages[0]}
          block={block}
          blocks={blocks}
          onBlock={setBlock}
          tier={tier}
          episodePages={(project as any).episode_pages ?? 12}
          onRan={refresh}
          onProviders={onProviders}
        />
      )}

      {slug && project && step === 6 && (
        <div className="stack" style={{ gap: "var(--s-4)" }}>
          <div className="tabs" role="tablist" aria-label="7단계 작업">
            {(
              [
                ["make", "컷 · 프롬프트 만들기"],
                ["preview", "원고 미리보기"],
                ["bench", "워크벤치"],
              ] as const
            ).map(([id, label]) => (
              <button
                key={id}
                role="tab"
                aria-selected={tab === id}
                className="tab"
                onClick={() => setTab(id)}
              >
                {label}
              </button>
            ))}
          </div>

          {tab === "make" && (
            <div className="stack" style={{ gap: "var(--s-6)" }}>
              {stepMeta(6)!.stages.map((id) => {
                const st = stages.find((s) => s.id === id);
                if (st && stageState(st.state) === "skip") {
                  return (
                    <div key={id} className="card stack-tight">
                      <strong>{id}</strong>
                      <span className="muted" style={{ fontSize: "var(--text-sm)" }}>
                        {st.reason}
                      </span>
                    </div>
                  );
                }
                return (
                  <StageRunner
                    key={id}
                    slug={slug}
                    ep={ep}
                    stage={id}
                    block={block}
                    blocks={blocks}
                    onBlock={setBlock}
                    tier={tier}
                    onRan={refresh}
                    onProviders={onProviders}
                    onPickCut={(p) => {
                      setPage(p);
                      setTab("preview");
                    }}
                  />
                );
              })}
            </div>
          )}

          {tab === "preview" && (
            <Preview
              lang={lang}
              slug={slug}
              ep={ep ?? ""}
              page={Math.min(page, pages)}
              pages={pages}
              onPage={setPage}
              tier={tier}
              displayTier={project?.canvas?.tier ?? "M"}
              onTier={setTier}
              onLang={onLang}
            />
          )}

          {tab === "bench" && (
            <Workbench
              lang={lang}
              slug={slug}
              ep={ep ?? ""}
              page={Math.min(page, pages)}
              pages={pages}
              onPage={setPage}
              tier={tier}
              onTier={setTier}
              onLang={onLang}
            />
          )}
        </div>
      )}

      {/* the rail is the way back; this is only a convenience */}
      {step > 1 && (
        <div className="row">
          <button className="btn" onClick={() => onStep(step - 1)}>
            ← {stepMeta(step - 1)?.label} 단계로
          </button>
          <span className="muted" style={{ fontSize: "var(--text-sm)" }}>
            왼쪽 목록에서 어느 단계로든 바로 갈 수 있습니다
          </span>
        </div>
      )}
    </div>
  );
}
