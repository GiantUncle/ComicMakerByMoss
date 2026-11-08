import { useState } from "react";
import type { BibleCard } from "../api";
import { Chip, KV } from "./ui";

/**
 * One character card, as the cast step shows it.
 *
 * A card is data, not a prompt: it holds the anchors, the single signature and
 * the appearance-only descriptor, and stage 7 copies that descriptor onto the
 * page. Editing here edits what the pipeline reads, so the save runs the same
 * validation the model is held to and snapshots first.
 */
export function CastCardView({
  card,
  busy,
  canRetake,
  onSave,
  onDelete,
  onRetake,
}: {
  card: BibleCard;
  busy: boolean;
  canRetake: boolean;
  onSave: (card: BibleCard) => void;
  onDelete: (id: string) => void;
  onRetake: (id: string, feedback: string) => void;
}) {
  const [draft, setDraft] = useState<BibleCard>(card);
  const [open, setOpen] = useState(false);
  const [feedback, setFeedback] = useState("");
  const set = (patch: Partial<BibleCard>) => setDraft({ ...draft, ...patch });

  const anchors = draft.anchors ?? [];
  const name = draft.name ?? {};

  return (
    <div className="card stack">
      <div className="between" style={{ alignItems: "flex-start" }}>
        <div className="row" style={{ flexWrap: "wrap", minWidth: 0 }}>
          <span className="mono">{card.id}</span>
          <strong>{name.ko || name.en || name.ja || "—"}</strong>
          {card.reference?.sheet ? (
            <span className="chip chip--ok">시트 있음</span>
          ) : (
            <span className="chip chip--warn">시트 없음</span>
          )}
          {card.consistency_risk && <Chip>{card.consistency_risk}</Chip>}
        </div>
        <div className="row" style={{ flex: "0 0 auto", flexWrap: "nowrap", gap: "var(--s-1)" }}>
          <button
            className="btn"
            style={{ minHeight: 28, whiteSpace: "nowrap", padding: "0 var(--s-2)" }}
            onClick={() => setOpen(!open)}
          >
            {open ? "접기" : "편집"}
          </button>
          <button
            className="btn btn--primary"
            style={{ minHeight: 28, whiteSpace: "nowrap", padding: "0 var(--s-2)" }}
            onClick={() => onSave(draft)}
            disabled={busy}
          >
            저장
          </button>
          <button
            className="btn btn--danger"
            style={{ minHeight: 28, whiteSpace: "nowrap", padding: "0 var(--s-2)" }}
            onClick={() => onDelete(card.id)}
            disabled={busy}
          >
            삭제
          </button>
        </div>
      </div>

      <KV
        rows={[
          ["프롬프트가 이 인물을 부르는 말", draft.identifier_label || "—"],
          ["역할", [draft.role?.ko, draft.role?.en, draft.role?.ja].filter(Boolean).join(" · ") || "—"],
          [
            "외형 앵커",
            anchors.length ? (
              <span className="row" style={{ flexWrap: "wrap", gap: "var(--s-1)" }}>
                {anchors.map((a) => (
                  <span key={a} className="chip chip--ellipsis" title={a}>
                    {a}
                  </span>
                ))}
              </span>
            ) : (
              "—"
            ),
          ],
          ["시그니처 (한 개만)", draft.signature || "—"],
          ["체형", draft.body || "—"],
          ["기본 복장", draft.default_outfit || "—"],
          ["묘사 — 컷에 박히는 문장", <span style={{ fontSize: "var(--text-sm)" }}>{draft.descriptor || "—"}</span>],
        ]}
      />

      {open && (
        <div className="stack-tight" style={{ borderTop: "1px solid var(--border-soft)", paddingTop: "var(--s-3)" }}>
          <div className="field">
            <label>이름 — 이름표에 그릴 때만 쓰입니다</label>
            <div className="row">
              {(["ko", "en", "ja"] as const).map((l) => (
                <input
                  key={l}
                  aria-label={`이름 ${l}`}
                  placeholder={l.toUpperCase()}
                  value={name[l] ?? ""}
                  onChange={(e) => set({ name: { ...name, [l]: e.target.value } })}
                  style={{ flex: 1 }}
                />
              ))}
            </div>
          </div>
          <div className="field">
            <label>호칭 — 프롬프트가 인물을 가리키는 말</label>
            <input
              value={draft.identifier_label ?? ""}
              placeholder="the young woman"
              onChange={(e) => set({ identifier_label: e.target.value })}
            />
          </div>
          <div className="field">
            <label>외형 앵커 — 2~4개, 쉼표로 구분</label>
            <input
              value={anchors.join(", ")}
              onChange={(e) =>
                set({ anchors: e.target.value.split(",").map((s) => s.trim()).filter(Boolean) })
              }
            />
          </div>
          <div className="field">
            <label>시그니처 — 정확히 한 개</label>
            <input value={draft.signature ?? ""} onChange={(e) => set({ signature: e.target.value })} />
          </div>
          <div className="field">
            <label>체형</label>
            <input value={draft.body ?? ""} onChange={(e) => set({ body: e.target.value })} />
          </div>
          <div className="field">
            <label>기본 복장</label>
            <input
              value={draft.default_outfit ?? ""}
              onChange={(e) => set({ default_outfit: e.target.value })}
            />
          </div>
          <div className="field">
            <label>묘사 — 외형만. 화풍 · 매체 · 카메라 · 조명은 넣지 않습니다</label>
            <textarea
              value={draft.descriptor ?? ""}
              onChange={(e) => set({ descriptor: e.target.value })}
              spellCheck={false}
              style={{ minHeight: 96 }}
            />
          </div>

          {canRetake && (
            <div className="field" style={{ marginBottom: 0 }}>
              <label>이 인물만 다시 — 모델이 카드를 다시 씁니다</label>
              <div className="row">
                <input
                  value={feedback}
                  onChange={(e) => setFeedback(e.target.value)}
                  placeholder="예: 더 나이 들어 보이게. 앵커에 안경을 추가."
                  style={{ flex: 1 }}
                />
                <button className="btn" onClick={() => onRetake(card.id, feedback)} disabled={busy}>
                  리테이크
                </button>
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
