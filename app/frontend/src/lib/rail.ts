import type { StageStatus } from "../api";
import { stepMeta, stageState } from "./steps";

/**
 * What the board says about one step, read off the stage table.
 *
 * `done` / `stale` / `ready` / `blocked` / `idle` drive both the top board and any
 * other step summary. Kept here (not in App) so the board and the shell share it.
 */
export type RailState = "done" | "stale" | "ready" | "blocked" | "idle";

export interface RailRow {
  state: RailState;
  note: string;
}

export function railRow(
  n: number,
  stages: StageStatus[],
  slug: string | null,
  mode?: string | null,
): RailRow {
  const meta = stepMeta(n, mode);
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
  const stale = rows.find((r) => stageState(r.state) === "stale");
  if (stale) return { state: "stale", note: stale.reason || "이전 단계 변경됨 · 재작업 필요" };
  if (rows.every((r) => stageState(r.state) === "done")) return { state: "done", note: "완료" };
  const waiting = rows.find((r) => stageState(r.state) === "waiting");
  if (waiting) return { state: "blocked", note: waiting.reason || "다른 단계 먼저" };
  return { state: "ready", note: "실행할 수 있습니다" };
}

/** A single short glyph for the state, so colour is never the only signal. */
export const RAIL_GLYPH: Record<RailState, string> = {
  done: "✓",
  stale: "↻",
  ready: "○",
  blocked: "!",
  idle: "·",
};
