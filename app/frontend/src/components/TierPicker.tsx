import { TIERS, type Tier } from "../lib/canvas";

/**
 * The canvas resolution picker, one shape everywhere.
 *
 * The tier letter alone means nothing to a first-timer, so every button carries
 * its pixel size (`M · 992×1408`). Screens must not each invent their own
 * tier control — this is the one.
 */
export default function TierPicker({
  value,
  onChange,
  disabled = false,
  label = "해상도",
}: {
  value: string;
  onChange: (t: Tier) => void;
  disabled?: boolean;
  label?: string;
}) {
  return (
    <div className="tierpick" role="group" aria-label={label}>
      {TIERS.map((t) => (
        <button
          key={t.id}
          type="button"
          className="btn toggle"
          aria-pressed={value === t.id}
          disabled={disabled}
          title={`${t.id} — ${t.w}×${t.h}px · ${t.note}`}
          onClick={() => onChange(t.id)}
        >
          {t.id} · {t.w}×{t.h}
        </button>
      ))}
    </div>
  );
}
