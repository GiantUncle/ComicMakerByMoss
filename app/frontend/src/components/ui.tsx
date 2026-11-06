import type { ReactNode } from "react";

/**
 * Small shared pieces every step screen is built from.
 *
 * A step always reads the same way — what it made, whether that is sound, what
 * to redo — so the three sections and the verdict are one component each, not
 * seven near-copies.
 */

export function Note({ tone, children }: { tone: "ok" | "bad" | "warn"; children: ReactNode }) {
  const cls = tone === "ok" ? "chip--ok" : tone === "bad" ? "chip--bad" : "chip--warn";
  return (
    <div className={`card ${cls}`} style={{ padding: "var(--s-3)" }} role="status">
      {tone === "ok" && <span aria-hidden>✓ </span>}
      {tone === "bad" && <span aria-hidden>✕ </span>}
      {tone === "warn" && <span aria-hidden>! </span>}
      {children}
    </div>
  );
}

export function StepSection({
  n,
  title,
  hint,
  accent,
  children,
}: {
  n: 1 | 2 | 3;
  title: string;
  hint?: ReactNode;
  /** "made" tints the rule with the primary role. */
  accent?: "made";
  children: ReactNode;
}) {
  return (
    <section className={`sec${accent === "made" ? " sec--made" : ""}`}>
      <div className="sec-head">
        <span className="sec-title">
          <span aria-hidden style={{ color: "var(--fg-muted)", fontFamily: "var(--font-mono)" }}>
            {["①", "②", "③"][n - 1]}{" "}
          </span>
          {title}
        </span>
        {hint && <p className="sec-hint">{hint}</p>}
      </div>
      {children}
    </section>
  );
}

/**
 * The validator's verdict. A script decides, never a colour: the chip names the
 * result in words and the issues are listed under it.
 */
export function Verdict({
  errorCount = 0,
  warningCount = 0,
  okText = "검증 통과",
  children,
}: {
  errorCount?: number;
  warningCount?: number;
  okText?: string;
  children?: ReactNode;
}) {
  const bad = errorCount > 0;
  return (
    <div className="stack-tight">
      <div className="row" style={{ flexWrap: "wrap" }}>
        <span className={`chip ${bad ? "chip--bad" : "chip--ok"}`}>
          {bad ? "✕ 오류 있음" : "✓ " + okText}
        </span>
        <span className="chip">오류 {errorCount}</span>
        <span className="chip">경고 {warningCount}</span>
        <span className="muted" style={{ fontSize: "var(--text-sm)" }}>
          판정은 검증기(스크립트)가 합니다
        </span>
      </div>
      {children}
    </div>
  );
}

export function IssueList({
  issues,
  limit = 12,
}: {
  issues: { level: string; where: string; message: string }[];
  limit?: number;
}) {
  if (issues.length === 0) return null;
  return (
    <div className="rows">
      {issues.slice(0, limit).map((i, k) => (
        <div
          key={k}
          className={`card ${i.level === "error" ? "chip--bad" : "chip--warn"}`}
          style={{ padding: "var(--s-2) var(--s-3)", fontSize: "var(--text-sm)" }}
        >
          {i.level === "error" ? "✕" : "!"} <span className="mono">{i.where}</span> — {i.message}
        </div>
      ))}
      {issues.length > limit && (
        <span className="muted" style={{ fontSize: "var(--text-sm)" }}>
          외 {issues.length - limit}건
        </span>
      )}
    </div>
  );
}

/** Nothing here yet — said plainly, with what to do about it. */
export function EmptyState({ title, hint }: { title: string; hint?: ReactNode }) {
  return (
    <div className="empty">
      <span className="empty-title">{title}</span>
      {hint && <span className="muted" style={{ fontSize: "var(--text-sm)" }}>{hint}</span>}
    </div>
  );
}

/** A label with a value, for the summary cards. */
export function KV({ rows }: { rows: [string, ReactNode][] }) {
  return (
    <dl className="kv">
      {rows.map(([k, v], i) => (
        <div key={i} style={{ display: "contents" }}>
          <dt>{k}</dt>
          <dd>{v}</dd>
        </div>
      ))}
    </dl>
  );
}

export function Chip({ children, title }: { children: ReactNode; title?: string }) {
  return (
    <span className="chip" title={title}>
      {children}
    </span>
  );
}
