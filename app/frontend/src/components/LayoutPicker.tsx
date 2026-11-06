import { useEffect, useState } from "react";
import { TIERS } from "../lib/canvas";

/**
 * Pick a layout by looking at it.
 *
 * The library is 179 panel arrangements. Reading their names decides nothing,
 * so each one is drawn from its own boxes — the same boxes the page will be
 * built with. A page is one of two things, and the drawing shows which: an even
 * run of panels, or one panel carrying the rest.
 */

export interface LayoutBox {
  n: number;
  x: number;
  y: number;
  w: number;
  h: number;
}

export interface LayoutItem {
  id: string;
  name: string;
  nameEn: string;
  panels: number;
  detail: boolean;
  pageType: string;
  boxes: LayoutBox[];
}

let _layouts: Promise<LayoutItem[]> | null = null;

/** Load the full layout library (cached). */
export async function loadLayoutLibrary(): Promise<LayoutItem[]> {
  if (!_layouts) {
    _layouts = fetch(`${import.meta.env.BASE_URL}layouts.json`).then(
      (r) => r.json() as Promise<LayoutItem[]>,
    );
  }
  return _layouts;
}

async function loadPickableLibrary(): Promise<LayoutItem[]> {
  const rows = await loadLayoutLibrary();
  return rows.filter((x) => !x.detail);
}

export default function LayoutPicker({
  split,
  panels,
  value,
  onPick,
}: {
  /** what this page is doing — an even order, or one subject it carries */
  split: "even" | "single";
  panels: number;
  value: string;
  onPick: (id: string) => void;
}) {
  const [rows, setRows] = useState<LayoutItem[]>([]);
  const [pg, setPg] = useState(0);

  useEffect(() => {
    loadPickableLibrary().then(setRows).catch(() => setRows([]));
  }, []);

  const fits = (r: LayoutItem) => r.panels === panels && r.pageType === split;
  const shown = rows.filter(fits);
  const PER = 12;
  const pages = Math.max(1, Math.ceil(shown.length / PER));
  const page = Math.min(pg, pages - 1);
  const slice = shown.slice(page * PER, page * PER + PER);

  if (shown.length === 0) {
    return (
      <p className="muted" style={{ fontSize: "var(--text-sm)", margin: 0 }}>
        컷 {panels}개 · {split === "even" ? "순서" : "한 주제"} 조건의 배치가 없습니다. 컷 수를
        바꾸면 다른 배치가 나옵니다.
      </p>
    );
  }

  return (
    <div className="stack" style={{ gap: "var(--s-3)" }}>
      <div className="between">
        <span className="muted" style={{ fontSize: "var(--text-sm)" }}>
          {split === "even"
            ? "순서 페이지 — 컷이 고르게 이어집니다"
            : "한 주제 페이지 — 한 컷이 그 주제를 담습니다"}{" "}
          · 컷 {panels}개 · 총 {shown.length}종
        </span>
        <div className="row" style={{ gap: "var(--s-2)" }}>
          <button className="btn" style={{ minHeight: 30 }} onClick={() => setPg(Math.max(0, page - 1))} disabled={page <= 0}>
            ◀
          </button>
          <span className="muted" style={{ fontSize: "var(--text-sm)" }}>
            {page + 1}/{pages}
          </span>
          <button className="btn" style={{ minHeight: 30 }} onClick={() => setPg(Math.min(pages - 1, page + 1))} disabled={page >= pages - 1}>
            ▶
          </button>
        </div>
      </div>

      <div className="layout-grid">
        {slice.map((r) => (
          <button
            key={r.id}
            className="layout-cell"
            aria-pressed={value === r.id}
            onClick={() => onPick(r.id)}
          >
            <Thumb boxes={r.boxes} />
            <span className="layout-name">{r.id}</span>
          </button>
        ))}
      </div>
    </div>
  );
}

/** The page as boxes, in reading order, on a right-to-left page. */
export function Thumb({ boxes }: { boxes: LayoutBox[] }) {
  const PAD = 6;
  const w = 100 - PAD * 2;
  const h = 120 - PAD * 2;
  return (
    <svg viewBox={`0 0 100 120`} width="100%" style={{ display: "block" }} role="img">
      <rect x={0} y={0} width={100} height={120} fill="var(--surface)" rx={2} />
      {boxes.map((b) => (
        <g key={b.n}>
          <rect
            x={PAD + b.x * w}
            y={PAD + b.y * h}
            width={b.w * w}
            height={b.h * h}
            fill="var(--surface-2)"
            stroke={b.n === 1 ? "var(--primary)" : "var(--border)"}
            strokeWidth={b.n === 1 ? 1.6 : 1}
          />
          <text
            x={PAD + (b.x + b.w / 2) * w}
            y={PAD + (b.y + b.h / 2) * h + 3}
            fontSize={7}
            textAnchor="middle"
            fill="var(--fg-muted)"
            style={{ pointerEvents: "none" }}
          >
            {b.n}
          </text>
        </g>
      ))}
    </svg>
  );
}

export { TIERS };
