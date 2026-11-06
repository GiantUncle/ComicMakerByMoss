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
 * One step at a time, chosen from the left rail. Steps 1-2 are forms; 3-5,6,7
 * are single pipeline stages; step 8 compiles prompts and hosts preview/workbench.
 * Pipeline: 콘티(6, AI) → 컷 시트(7) → 프롬프트(8).
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
  const [tab, setTab] = useState<Tab>(init.tab as Tab);
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

  useEffect(() => {
    if (!project) return;
    if (!hasEpisode(project, ep)) setEp(openEpisodeId(project));
  }, [project, ep]);

  useEffect(() => {
    if (!slug || !project) return;
    // legacy: old step 7 was combined cut/prompt; now prompts is step 8
    if (step > 8) onStep(8);
  }, [slug, project, step, onStep]);

  useEffect(() => {
    const fromUrl = new URLSearchParams(window.location.search).get("tier");
    if (fromUrl) return;
    if (project?.canvas?.tier) setTier(project.canvas.tier);
  }, [project?.canvas?.tier]);

  useEffect(() => {
    if (!slug) return;
    const q = new URLSearchParams(window.location.search);
    if (ep) q.set("ep", ep); else q.delete("ep");
    if (step === 8) q.set("tab", tab); else q.delete("tab");
    if (step === 8) q.set("page", String(Math.max(1, page))); else q.delete("page");
    if (step >= 3 && step <= 8) q.set("block", String(Math.max(1, block))); else q.delete("block");
    if (step === 8) q.set("tier", tier); else q.delete("tier");
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
    api.projects().then((all) => setProject(all.find((x) => x.slug === slug) ?? null)).catch((e) => setError(String(e)));
    if (ep) api.stages(slug, ep).then(setStages).catch(() => {});
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
  const headState: { text: string; cls: string } | null = (() => {
    if (!slug || !project) return { text: "현재 결과 없음", cls: "" };
    const stageId = meta?.stages?.[0];
    if (step === 2) return { text: "설정됨", cls: "chip--ok" };
    if (!stageId) return null;
    const st = stages.find((s) => s.id === stageId);
    if (!st) return { text: "현재 결과 없음", cls: "" };
    const s = stageState(st.state);
    if (s === "done") return { text: "현재 결과 있음", cls: "chip--ok" };
    if (s === "stale") return { text: "변경됨 — 다시 만들기", cls: "chip--warn" };
    if (s === "waiting") return { text: "먼저 필요한 단계", cls: "chip--warn" };
    if (s === "ready") return { text: "현재 결과 없음", cls: "" };
    return { text: st.reason ?? "이 프로젝트에는 없음", cls: "" };
  })();

  function renderStage(stageId: string, extra?: { onPickCut?: (p: number) => void }) {
    const st = stages.find((s) => s.id === stageId);
    if (st && stageState(st.state) === "skip") {
      return (
        <div className="card stack-tight">
          <strong>{stageId}</strong>
          <span className="muted" style={{ fontSize: "var(--text-sm)" }}>{st.reason}</span>
        </div>
      );
    }
    return (
      <StageRunner
        key={stageId}
        slug={slug!}
        ep={ep}
        stage={stageId}
        block={block}
        blocks={blocks}
        onBlock={setBlock}
            episodePages={(project as any)?.episode_pages ?? 12}
        onRan={refresh}
        onProviders={onProviders}
        onPickCut={extra?.onPickCut ?? ((p) => { setPage(p); setTab("preview"); onStep(8); })}
      />
    );
  }

  return (
    <div className="wrap">
      {meta && (
        <div className="step-head">
          <div className="step-title">
            {meta.n} · {meta.label}
            <span className="chip">{SCOPE_LABEL[meta.scope]}</span>
            {headState && <span className={"chip " + headState.cls}>{headState.text}</span>}
            {step > 1 && (
              <button className="btn" onClick={() => onStep(step - 1)} style={{ marginLeft: "auto" }}>
                ← {stepMeta(step - 1)?.label}
              </button>
            )}
          </div>
        </div>
      )}

      {error && <Note tone="bad">{error}</Note>}
      {note && <Note tone="ok">{note}</Note>}

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

      {slug && project && (step === 3 || step === 4) && renderStage(stepMeta(step)!.stages[0])}

      {slug && project && step === 5 && renderStage("manga-5-plan", { onPickCut: (p) => setPage(p) })}

      {slug && project && step === 6 && renderStage("manga-6-conti")}

      {slug && project && step === 7 && renderStage("manga-7-sheets")}

      {slug && project && step === 8 && (
        <div className="stack" style={{ gap: "var(--s-4)" }}>
          <div className="tabs" role="tablist" aria-label="프롬프트 단계">
            {(
              [
                ["make", "프롬프트 컴파일"],
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

          {tab === "make" && renderStage("manga-8-prompts")}

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
    </div>
  );
}
