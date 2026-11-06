/**
 * Lettering — the four kinds of words drawn inside a manuscript.
 *
 * There is no word "text" in a comic. A 말풍선 (balloon) holds dialogue, a
 * 내레이션 (narration) box holds the narrator, a 효과음 (sound effect) is
 * lettering with no box at all, and a 이름표 (name tag) sits by the speaker.
 * Every item drawn in the preview carries one of these four names.
 *
 * The kind comes from the compiled prompt's own caption, which is what the
 * build wrote; the fallback reads the box shape the prompt gave.
 */

export type LetteringKind = "balloon" | "narration" | "sfx" | "nametag" | "floating";

export const KIND_LABEL: Record<LetteringKind, string> = {
  balloon: "말풍선",
  narration: "내레이션",
  sfx: "효과음",
  nametag: "이름표",
  floating: "떠있는 글자",
};

/** Short form for a count line: "말풍선 2 · 효과음 1". */
export const KIND_SHORT: Record<LetteringKind, string> = {
  balloon: "말풍선",
  narration: "내레이션",
  sfx: "효과음",
  nametag: "이름표",
  floating: "떠있는 글자",
};

export function letteringKind(caption: string, style?: string): LetteringKind {
  const c = (caption ?? "").toLowerCase();
  if (c.includes("sound effect") || c.includes("sfx")) return "sfx";
  if (c.includes("name tag") || c.includes("name plate")) return "nametag";
  if (c.includes("narration") || c.includes("caption text")) return "narration";
  if (c.includes("balloon") || c.includes("bubble") || c.includes("speech")) return "balloon";
  if (style === "rect") return "narration";
  if (style === "balloon") return "balloon";
  return "floating";
}

/**
 * Vertical lettering — the tall narration box that reads top to bottom, the
 * way the reference pages do it. A box much taller than it is wide, holding
 * more than one line, is written down its side.
 */
export function isVertical(h: number, w: number, lines: number): boolean {
  return h > w * 1.7 && lines >= 2;
}

/** The tail direction a balloon's caption names, so the tail can be drawn. */
export function tailDir(caption: string): "left" | "right" | "up" | "down" | null {
  const m = (caption ?? "").toLowerCase().match(/tail pointing (left|right|up|down|above|below)/);
  if (!m) return null;
  const d = m[1];
  if (d === "above") return "up";
  if (d === "below") return "down";
  return d as "left" | "right" | "up" | "down";
}

export interface KindCount {
  kind: LetteringKind;
  n: number;
}

/** Count the lettering on a page by kind, in the order they are named. */
export function countKinds(
  shapes: { kind: string; style?: string; caption?: string }[]
): KindCount[] {
  const order: LetteringKind[] = ["balloon", "narration", "sfx", "nametag", "floating"];
  const tally: Record<string, number> = {};
  for (const s of shapes) {
    if (s.kind !== "text") continue;
    const k = letteringKind(s.caption ?? "", s.style);
    tally[k] = (tally[k] ?? 0) + 1;
  }
  return order.filter((k) => tally[k]).map((k) => ({ kind: k, n: tally[k] }));
}

/** "말풍선 2 · 효과음 1" — the count line under a page. */
export function kindLine(shapes: { kind: string; style?: string; caption?: string }[]): string {
  const parts = countKinds(shapes).map((c) => `${KIND_SHORT[c.kind]} ${c.n}`);
  return parts.length ? parts.join(" · ") : "없음";
}
