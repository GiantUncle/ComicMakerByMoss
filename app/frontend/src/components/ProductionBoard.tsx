import type { StageStatus } from "../api";
import { stepsFor } from "../lib/steps";
import { RAIL_GLYPH, railRow } from "../lib/rail";

/**
 * Production board — the whole flow at a glance.
 *
 * A horizontal run of numbered step cards. Each card fills by state (done / in
 * progress / waiting / needs rework) with a glyph AND a word, so colour is never
 * the only signal. The current step is outlined. Clicking a card opens that
 * step's page below; nothing is edited here.
 *
 * This replaces the old vertical rail, which hid the flow: the order is the
 * point, so it reads left to right.
 */
export default function ProductionBoard({
  slug,
  mode,
  stages,
  current,
  onPick,
}: {
  slug: string | null;
  mode: string | null;
  stages: StageStatus[];
  current: number | null;
  onPick: (n: number) => void;
}) {
  const steps = stepsFor(mode);

  return (
    <nav className="board" aria-label="제작 흐름">
      <span className="board-title">제작 흐름</span>
      <ol className="board-track">
        {steps.map((s, i) => {
          const row = railRow(s.n, stages, slug, mode);
          const active = current === s.n;
          const blocked = row.state === "blocked" || row.state === "idle";
          return (
            <li key={s.n} className="board-cell">
              {i > 0 && <span className="board-arrow" aria-hidden>→</span>}
              <button
                type="button"
                className="board-card"
                data-state={row.state}
                aria-current={active ? "step" : undefined}
                title={`${s.n} · ${s.label} — ${row.note}`}
                onClick={() => onPick(s.n)}
                disabled={!slug || blocked}
              >
                <span className="board-card-top">
                  <span className="board-num">{String(s.n).padStart(2, "0")}</span>
                  <span className="board-glyph" aria-hidden>{RAIL_GLYPH[row.state]}</span>
                </span>
                <span className="board-label">{s.label}</span>
                <span className="board-state">{row.note}</span>
              </button>
            </li>
          );
        })}
      </ol>
    </nav>
  );
}
