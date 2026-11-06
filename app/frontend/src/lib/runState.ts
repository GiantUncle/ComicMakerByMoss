import type { StageRun } from "../api";

export interface RunEntry {
  busy: boolean;
  result: StageRun | null;
  dry: { system: string; user: string } | null;
  error: string | null;
}

const store = new Map<string, RunEntry>();
const listeners = new Set<() => void>();

function emit() {
  for (const l of listeners) l();
}

export function runKey(slug: string, ep: string | null, stage: string, block: number): string {
  return `${slug}|${ep ?? ""}|${stage}|${block}`;
}

export function getRun(key: string): RunEntry {
  return store.get(key) ?? { busy: false, result: null, dry: null, error: null };
}

export function setRun(key: string, patch: Partial<RunEntry>) {
  store.set(key, { ...getRun(key), ...patch });
  emit();
}

export function subscribeRun(listener: () => void): () => void {
  listeners.add(listener);
  return () => listeners.delete(listener);
}
