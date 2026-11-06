const BASE = import.meta.env.VITE_API ?? "http://localhost:8000";

async function req<T>(path: string, init?: RequestInit): Promise<T> {
  const r = await fetch(BASE + path, {
    headers: { "Content-Type": "application/json" },
    ...init,
  });
  if (!r.ok) throw new Error(`${r.status} ${await r.text()}`);
  return r.json() as Promise<T>;
}

export type Lang = "ko" | "en" | "ja";

export interface EpisodeSummary {
  id: string;
  title: Record<string, string>;
  page_total: number | null;
  source: boolean;
  plan: boolean;
  pages: number;
}

export interface ProjectSummary {
  slug: string;
  title: Record<string, string>;
  mode: string;
  canvas: { tier: string; ratio: string };
  reading_direction: string;
  languages: { default: Lang; all: Lang[] };
  art_style: string;
  panels: { min: number; max: number };
  cut_mode?: string;
  detail_panels?: boolean;
  story_focus?: string;
  episode_pages?: number;
  episodes: EpisodeSummary[];
}

export interface WizardState {
  slug: string;
  mode: string;
  story_route: string | null;
  answers: Record<string, unknown>;
  project_settled: string[];
  episodes: { id: string; phase: number; settled: string[] }[];
  open_episode?: string;
  updated: string;
}

export interface NewProjectIn {
  slug: string;
  title: { ko: string; en: string; ja: string };
  mode: string;
  languages: { default: Lang; all: Lang[] };
  reading_direction: string;
  canvas: { tier: string; ratio: string };
  art_style: string;
  panels: { min: number; max: number };
  cut_mode: string;
  detail_panels: boolean;
  story_focus: string;
  episode_pages: number;
}

export interface NewEpisodeIn {
  id: string;
  title: { ko: string; en: string; ja: string };
  source_origin: string;
  story: string | null;
}

export interface StageStatus {
  id: string;
  n: number;
  scope: string;
  mode: string;
  state: "done" | "stale" | "ready" | "waiting" | "not-for-this-project";
  reason: string;
  gate: string | null;
  outputs: string[];
}

export interface ReviewIssue {
  level: "error" | "warning";
  code: string;
  where: string;
  message: string;
}

export interface StageRun {
  stage: string;
  dry?: boolean;
  note?: string;
  files?: string[];
  warnings?: string[];
  issues?: ReviewIssue[];
}

export interface Snapshot {
  id: string;
  stage: string;
  note: string;
  episode?: string | null;
  time: string;
  files: string[];
}

export interface StageReview {
  stage: string;
  exists: boolean;
  files: string[];
  issues: ReviewIssue[];
  error_count: number;
  warning_count: number;
  summary: Record<string, unknown>;
  history?: Snapshot[];
  updated_at?: string | null;
  stale?: boolean;
  stale_pages?: number[];
  stale_reason?: string | null;
}

export interface BibleCard {
  id: string;
  name?: Record<string, string>;
  role?: Record<string, string>;
  age_phrase?: string;
  anchors?: string[];
  signature?: string;
  body?: string;
  default_outfit?: string;
  descriptor?: string;
  identifier_label?: string;
  consistency_risk?: string;
  first_seen_episode?: string;
  reference?: { sheet?: string | null; approved?: boolean };
}

export interface BiblePool {
  characters: BibleCard[];
  objects: BibleCard[];
}

export interface BibleState {
  pool: BiblePool;
  issues: ReviewIssue[];
  error_count: number;
  warning_count: number;
}

export interface OrchestrateRow {
  stage: string;
  n: number;
  block?: number;
  status: "ok" | "done-skip" | "blocked" | "skipped" | "error";
  note?: string;
  errors?: number;
}

export interface OrchestrateResult {
  ok: boolean;
  episode?: string;
  stopped_at?: string;
  log: OrchestrateRow[];
}

export interface ProviderInfo {
  id: string;
  kind: string;
  label?: string;
  base_url: string;
  api_key_set: boolean;
  models: Record<string, string>;
  models_cache?: string[];
  models_fetched?: string | null;
  supports_json_mode?: boolean;
}

export interface ModelGroup {
  provider: string;
  label: string;
  configured: boolean;
  fetched: string | null;
  models: string[];
  favorites: string[];
  selected: string | null;
}

export interface ModelCatalog {
  groups: ModelGroup[];
  active: { provider?: string; model?: string };
}

export interface ProvidersPayload extends ModelCatalog {
  providers: ProviderInfo[];
}

export interface SkillAsset {
  path: string;
  kind: string;
  edited: boolean;
  bytes: number;
}

export interface SkillAssetBody {
  path: string;
  edited: boolean;
  origin: string;
  content: string;
}

export interface PreviewShape {
  id: number;
  kind: "panel" | "text";
  x: number;
  y: number;
  w: number;
  h: number;
  caption: string;
  // panel
  tag?: string;
  n?: number;
  // text
  style?: "balloon" | "rect" | "plain";
  text?: string;
  lines?: string[];
}

export interface PreviewModel {
  width: number;
  height: number;
  shape_count: number;
  panel_count: number;
  text_count: number;
  shapes: PreviewShape[];
}

/** The shipped sample page, drawn through the same endpoint a real prompt uses. */
export async function loadSample(lang: Lang): Promise<PreviewModel> {
  const prompt = await (await fetch(`${import.meta.env.BASE_URL}sample/${lang}.json`)).text();
  return api.preview(prompt, "M", 992, 1408);
}

export const api = {
  preview: (prompt: string, tier = "M", width?: number, height?: number) =>
    req<PreviewModel>("/api/derive/preview", {
      method: "POST",
      body: JSON.stringify({ prompt, tier, width, height }),
    }),

  projects: () => req<ProjectSummary[]>("/api/projects"),
  project: (slug: string) => req<ProjectSummary>(`/api/projects/${slug}`),
  patchProject: (slug: string, patch: object) =>
    req<ProjectSummary>(`/api/projects/${slug}`, { method: "PATCH", body: JSON.stringify(patch) }),
  createProject: (body: NewProjectIn) =>
    req<ProjectSummary>("/api/projects", { method: "POST", body: JSON.stringify(body) }),

  wizard: (slug: string) => req<WizardState>(`/api/projects/${slug}/wizard`),
  patchWizard: (slug: string, patch: object) =>
    req<WizardState>(`/api/projects/${slug}/wizard`, {
      method: "PATCH",
      body: JSON.stringify(patch),
    }),

  createEpisode: (slug: string, body: NewEpisodeIn) =>
    req<{ episode: unknown; source: boolean }>(`/api/projects/${slug}/episodes`, {
      method: "POST",
      body: JSON.stringify(body),
    }),
  episodeSource: (slug: string, ep: string) =>
    req<{ exists: boolean; text: string; approved: boolean; origin?: string | null; kind?: string | null }>(
      `/api/projects/${slug}/episodes/${ep}/source`
    ),
  saveEpisodeSource: (slug: string, ep: string, body: { text: string; mode?: "provided" | "brief"; origin?: string | null }) =>
    req<{ ok: boolean; mode: string; origin: string }>(`/api/projects/${slug}/episodes/${ep}/source`, {
      method: "PUT",
      body: JSON.stringify(body),
    }),

  pagePreview: (slug: string, episode: string, page: number, lang: Lang, tier: string) =>
    req<{
      lang: string;
      tier: string;
      prompt: string;
      preview: PreviewModel;
      layout: { template_id?: string; size_tier?: string; reading?: string };
      split: "even" | "single";
      panel_count: number;
    }>("/api/derive/page", {
      method: "POST",
      body: JSON.stringify({ slug, episode, page, lang, tier }),
    }),

  stages: (slug: string, episode?: string | null) =>
    req<StageStatus[]>(
      `/api/stages?slug=${encodeURIComponent(slug)}` +
        (episode ? `&episode=${encodeURIComponent(episode)}` : "")
    ),
  runStage: (body: { slug: string; stage: string; episode?: string | null; block?: number; dry?: boolean; episode_pages?: number | null }) =>
    req<StageRun>("/api/stages/run", { method: "POST", body: JSON.stringify(body) }),

  stageReview: (slug: string, stage: string, episode?: string | null, block = 1) =>
    req<StageReview>(
      `/api/stages/review?slug=${encodeURIComponent(slug)}&stage=${encodeURIComponent(stage)}` +
        `&block=${block}` +
        (episode ? `&episode=${encodeURIComponent(episode)}` : "")
    ),
  retakeStage: (body: {
    slug: string;
    stage: string;
    episode?: string | null;
    block?: number;
    feedback?: string;
    pages?: number[];
    ids?: string[];
    episode_pages?: number | null;
  }) => req<StageRun>("/api/stages/retake", { method: "POST", body: JSON.stringify(body) }),

  retakeCut: (body: { slug: string; episode: string; page: number; panel: number; feedback?: string }) =>
    req<{ conti: StageRun; sheet?: StageRun; page: StageRun }>("/api/stages/retake-cut", {
      method: "POST",
      body: JSON.stringify(body),
    }),
  orchestrate: (body: { slug: string; episode?: string | null; from_n?: number; to_n?: number }) =>
    req<OrchestrateResult>("/api/stages/orchestrate", { method: "POST", body: JSON.stringify(body) }),

  templates: (slug?: string) =>
    req<
      {
        id: string;
        name_en: string;
        name_ja: string;
        panels: number;
        tiers: number;
        source?: string;
        detail?: boolean;
        inset?: boolean;
        category?: string;
      }[]
    >("/api/derive/templates" + (slug ? `?slug=${encodeURIComponent(slug)}` : "")),
  retemplate: (body: { slug: string; episode: string; page: number; layout: Record<string, unknown> }) =>
    req<{ conti: StageRun; sheet?: StageRun; page: StageRun; prompt?: StageRun }>("/api/stages/retemplate", {
      method: "POST",
      body: JSON.stringify(body),
    }),

  planTemplate: (body: { slug: string; episode: string; page: number; template_id: string }) =>
    req<{ ok: boolean; page: number; template_id: string }>("/api/stages/plan-template", {
      method: "POST",
      body: JSON.stringify(body),
    }),

  bible: (slug: string) => req<BibleState>(`/api/projects/${slug}/bible`),
  saveCard: (slug: string, body: { bucket: string; card: BibleCard }) =>
    req<{ pool: BiblePool; saved: boolean; issues: ReviewIssue[] }>(
      `/api/projects/${slug}/bible/card`,
      { method: "PUT", body: JSON.stringify(body) }
    ),
  deleteCard: (slug: string, cid: string) =>
    req<{ pool: BiblePool; removed: string }>(`/api/projects/${slug}/bible/card/${cid}`, {
      method: "DELETE",
    }),

  history: (slug: string, stage?: string) =>
    req<Snapshot[]>(
      `/api/projects/${slug}/history` + (stage ? `?stage=${encodeURIComponent(stage)}` : "")
    ),
  restoreHistory: (slug: string, sid: string) =>
    req<{ id: string; stage: string; restored: string[] }>(
      `/api/projects/${slug}/history/${sid}/restore`,
      { method: "POST" }
    ),

  skills: () => req<SkillAsset[]>("/api/skills"),
  skill: (path: string) => req<SkillAssetBody>(`/api/skills/asset?path=${encodeURIComponent(path)}`),
  saveSkill: (path: string, content: string) =>
    req(`/api/skills/asset?path=${encodeURIComponent(path)}`, {
      method: "PUT",
      body: JSON.stringify({ content }),
    }),
  rollbackSkill: (path: string) =>
    req(`/api/skills/rollback?path=${encodeURIComponent(path)}`, { method: "POST" }),
  rollbackAllSkills: () => req("/api/skills/rollback-all", { method: "POST" }),

  providers: () => req<ProvidersPayload>("/api/providers"),
  saveProvider: (body: {
    id: string;
    label?: string;
    base_url: string;
    api_key?: string | null;
    models?: Record<string, string>;
    supports_json_mode?: boolean;
  }) => req<{ id: string; saved: boolean }>("/api/providers", { method: "PUT", body: JSON.stringify(body) }),
  testProvider: (body: { provider_id?: string; stage?: string; model?: string }) =>
    req<{ ok: boolean; reply?: string; error?: string }>("/api/providers/test", {
      method: "POST",
      body: JSON.stringify(body),
    }),

  refreshModels: (provider_id?: string) =>
    req<ProvidersPayload>("/api/providers/models", {
      method: "POST",
      body: JSON.stringify({ provider_id: provider_id ?? null }),
    }),
  models: () => req<ModelCatalog>("/api/models"),
  favoriteModel: (provider: string, model: string, on?: boolean) =>
    req<ModelCatalog>("/api/models/favorite", {
      method: "POST",
      body: JSON.stringify({ provider, model, on }),
    }),
  selectModel: (provider: string, model: string) =>
    req<ModelCatalog>("/api/models/select", {
      method: "POST",
      body: JSON.stringify({ provider, model }),
    }),
};
