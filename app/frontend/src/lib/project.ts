import type { EpisodeSummary, ProjectSummary } from "../api";

/**
 * Reading a project's episodes.
 *
 * The two endpoints disagree: `GET /api/projects/{slug}` hands back the raw
 * project.json, where `episodes` is a list of ids; `GET /api/projects` enriches
 * each one into an object with its page count and gate state. Both shapes are
 * accepted here so one project object works everywhere.
 */

type RawEpisode = string | EpisodeSummary;

export function episodeId(e: RawEpisode): string {
  return typeof e === "string" ? e : e.id;
}

export function episodeList(p: ProjectSummary | null | undefined): RawEpisode[] {
  return (p?.episodes ?? []) as unknown as RawEpisode[];
}

/** The episode a user is on: the newest one, which is what the API stores. */
export function openEpisodeId(p: ProjectSummary | null | undefined): string | null {
  const list = episodeList(p);
  return list.length ? episodeId(list[list.length - 1]) : null;
}

/** The stored episode, as the summary the rest of the app expects. */
export function episodeSummary(
  p: ProjectSummary | null | undefined,
  id: string | null
): EpisodeSummary | null {
  if (!p || !id) return null;
  const found = episodeList(p).find((e) => episodeId(e) === id);
  if (!found) return null;
  return typeof found === "string"
    ? { id, title: {}, page_total: null, source: false, plan: false, pages: 0 }
    : found;
}

/** True when the project has this episode. */
export function hasEpisode(p: ProjectSummary | null | undefined, id: string | null): boolean {
  if (!p || !id) return false;
  return episodeList(p).some((e) => episodeId(e) === id);
}
