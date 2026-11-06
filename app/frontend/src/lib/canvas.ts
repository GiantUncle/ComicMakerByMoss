/**
 * Canvas tiers.
 *
 * Resolution is core information, not a footnote: the header and the preview
 * both read it out in pixels, and the tier letters are only the small helper
 * beside it. The button is as long as a button should be; the information is
 * as long as the information is.
 */

export type Tier = "S" | "M" | "L" | "XL";

export interface TierInfo {
  id: Tier;
  w: number;
  h: number;
  /** What this size is for, in words a first-timer can use. */
  note: string;
}

export const TIERS: TierInfo[] = [
  { id: "S", w: 704, h: 992, note: "작게 — 화면에서 보기" },
  { id: "M", w: 992, h: 1408, note: "A4 세로 — 기본" },
  { id: "L", w: 1248, h: 1760, note: "크게 — 인쇄용" },
  { id: "XL", w: 1408, h: 1984, note: "아주 크게 — 대형 출력" },
];

export const DEFAULT_TIER: Tier = "M";

export function pxOf(tier: string | undefined | null): [number, number] {
  const t = TIERS.find((x) => x.id === tier) ?? TIERS.find((x) => x.id === DEFAULT_TIER)!;
  return [t.w, t.h];
}

/** "992 × 1408 px" — the readout itself, never shortened. */
export function pxLabel(tier: string | undefined | null): string {
  const [w, h] = pxOf(tier);
  return `${w} × ${h} px`;
}

export function tierNote(tier: string | undefined | null): string {
  const t = TIERS.find((x) => x.id === tier);
  return t?.note ?? "";
}
