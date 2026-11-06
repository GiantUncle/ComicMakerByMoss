import type { PreviewModel, PreviewShape } from "../api";
import { isVertical, tailDir } from "../lib/lettering";

/**
 * Draws a compiled prompt as a manuscript page.
 *
 * The reference pages this app has to produce are the reason for the shapes
 * here: a panel is a ruled box that can bleed or sit alone; a 말풍선 is a round
 * balloon with a tail that points at the speaker; a 세로 내레이션 box is a tall
 * rectangle its words run down; a 효과음 is lettering with no box at all, bold
 * enough to sit on the art; a 이름표 is a small tag by the speaker. Everything
 * comes from the prompt, so the page can be judged before anything is drawn.
 */

interface Props {
  model: PreviewModel;
  showBorders?: boolean;
  showLettering?: boolean;
  showCaptions?: boolean;
  showGrid?: boolean;
  selected?: number | null;
  onSelect?: (shape: PreviewShape) => void;
}

function letteringFont(w: number, h: number, lines: number, plain: boolean): number {
  const byLines = (h / Math.max(1, lines)) * 0.62;
  const byWidth = w / (plain ? 3.2 : 6.5);
  return Math.max(9, Math.min(plain ? 64 : 30, Math.min(byLines, byWidth)));
}

export default function ManuscriptPreview({
  model,
  showBorders = true,
  showLettering = true,
  showCaptions = true,
  showGrid = false,
  selected = null,
  onSelect,
}: Props) {
  const { width, height, shapes } = model;
  const step = Math.round(width / 10);

  return (
    <svg
      viewBox={`0 0 ${width} ${height}`}
      preserveAspectRatio="xMidYMid meet"
      style={{
        display: "block",
        width: "100%",
        height: "auto",
        maxHeight: "72vh",
        aspectRatio: `${width} / ${height}`,
        background: "var(--panel-preview-bg)",
        border: "1px solid var(--panel-preview-line)",
        borderRadius: "var(--radius)",
      }}
      role="img"
      aria-label={`원고 — ${width} × ${height} px, 컷 ${model.panel_count}, 글자 ${model.text_count}`}
    >
      {showGrid && (
        <g stroke="var(--panel-preview-line)" strokeWidth={0.5} opacity={0.35}>
          {Array.from({ length: 9 }, (_, i) => (
            <line key={`v${i}`} x1={step * (i + 1)} y1={0} x2={step * (i + 1)} y2={height} />
          ))}
          {Array.from({ length: 9 }, (_, i) => (
            <line key={`h${i}`} x1={0} y1={step * (i + 1)} x2={width} y2={step * (i + 1)} />
          ))}
        </g>
      )}

      {shapes.map((s) => {
        const isSel = s.id === selected;
        const stroke = isSel ? "var(--primary)" : "var(--panel-preview-line)";
        const sw = isSel ? 5 : s.kind === "panel" ? 2 : 2;

        if (s.kind === "panel") {
          return (
            <g key={s.id} onClick={() => onSelect?.(s)} style={{ cursor: "pointer" }}>
              <rect
                x={s.x}
                y={s.y}
                width={s.w}
                height={s.h}
                fill="var(--surface-2)"
                stroke={showBorders ? stroke : "transparent"}
                strokeWidth={showBorders ? sw : 0}
              />
              {showBorders && (
                <text
                  x={s.x + 10}
                  y={s.y + 24}
                  fontSize={15}
                  fill="var(--fg-muted)"
                  fontFamily="var(--font-mono)"
                >
                  {s.tag}
                  {s.n}
                </text>
              )}
              {showCaptions && (
                <foreignObject
                  x={s.x + 10}
                  y={s.y + (showBorders ? 32 : 8)}
                  width={Math.max(10, s.w - 20)}
                  height={Math.max(10, s.h - (showBorders ? 40 : 16))}
                >
                  <div
                    title={s.caption}
                    style={{
                      font: `${Math.max(8, Math.min(13, s.w / 30))}px/1.35 var(--font-sans)`,
                      color: "var(--fg-muted)",
                      overflow: "hidden",
                      height: "100%",
                      display: "-webkit-box",
                      WebkitLineClamp: 6,
                      WebkitBoxOrient: "vertical",
                    }}
                  >
                    {s.caption}
                  </div>
                </foreignObject>
              )}
            </g>
          );
        }

        /* ------------------------------------------------------ lettering */
        const lines = s.lines?.length ? s.lines : [s.text ?? ""];
        const plain = s.style === "plain";
        const fs = letteringFont(s.w, s.h, lines.length, plain);
        const vertical = isVertical(s.h, s.w, lines.length);
        const cx = s.x + s.w / 2;
        const cy = s.y + s.h / 2;
        const tail = tailDir(s.caption);
        const t = Math.min(18, Math.min(s.w, s.h) * 0.16);

        return (
          <g key={s.id} onClick={() => onSelect?.(s)} style={{ cursor: "pointer" }}>
            {/* the box a balloon or narration sits in */}
            {showBorders && s.style === "balloon" && (
              <>
                <ellipse
                  cx={cx}
                  cy={cy}
                  rx={s.w / 2}
                  ry={s.h / 2}
                  fill="var(--surface)"
                  stroke={stroke}
                  strokeWidth={sw}
                />
                {tail && (
                  <polygon
                    points={tailPoints(tail, cx, cy, s.w, s.h, t)}
                    fill="var(--surface)"
                    stroke={stroke}
                    strokeWidth={sw}
                  />
                )}
              </>
            )}
            {showBorders && s.style === "rect" && (
              <rect
                x={s.x}
                y={s.y}
                width={s.w}
                height={s.h}
                fill="var(--surface)"
                stroke={stroke}
                strokeWidth={sw}
              />
            )}

            {/* the words themselves */}
            {showLettering && (
              <foreignObject x={s.x} y={s.y} width={s.w} height={s.h}>
                <div
                  title={s.text}
                  style={{
                    height: "100%",
                    display: "flex",
                    flexDirection: vertical ? "row" : "column",
                    alignItems: "center",
                    justifyContent: "center",
                    gap: plain ? 0 : Math.max(2, fs * 0.18),
                    textAlign: "center",
                    font: `${plain ? 900 : 500} ${fs}px/${vertical ? 1.15 : 1.25} var(--font-sans)`,
                    color: "var(--fg)",
                    overflow: "hidden",
                    padding: 2,
                  }}
                >
                  {lines.map((l, i) => (
                    <span
                      key={i}
                      style={
                        plain
                          ? {
                              // sound-effect lettering: a halo so it reads on any art
                              paintOrder: "stroke",
                              WebkitTextStroke: `${Math.max(2, fs * 0.12)}px var(--panel-preview-bg)`,
                              letterSpacing: "0.02em",
                            }
                          : undefined
                      }
                    >
                      {l}
                    </span>
                  ))}
                </div>
              </foreignObject>
            )}

            {/* a plain box has no border, so its own place is shown faintly */}
            {showBorders && plain && (
              <rect
                x={s.x}
                y={s.y}
                width={s.w}
                height={s.h}
                fill="none"
                stroke={stroke}
                strokeWidth={isSel ? sw : 1}
                strokeDasharray="6 6"
                opacity={isSel ? 0.9 : 0.45}
              />
            )}
          </g>
        );
      })}
    </svg>
  );
}

/** The tail of a balloon, pointing where the caption says it points. */
function tailPoints(
  dir: "left" | "right" | "up" | "down",
  cx: number,
  cy: number,
  w: number,
  h: number,
  t: number
): string {
  const bx = cx + (dir === "left" ? -w / 2 : dir === "right" ? w / 2 : 0);
  const by = cy + (dir === "up" ? -h / 2 : dir === "down" ? h / 2 : 0);
  const p1 = [bx, by];
  const p2 = dir === "left" || dir === "right" ? [bx, by - t] : [bx - t, by];
  const p3 =
    dir === "left"
      ? [bx - t, by + t * 0.6]
      : dir === "right"
        ? [bx + t, by + t * 0.6]
        : dir === "up"
          ? [bx + t * 0.6, by - t]
          : [cx, by + t];
  return [...p1, ...p2, ...p3].join(",");
}
