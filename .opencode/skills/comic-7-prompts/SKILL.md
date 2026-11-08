---
name: Comic 7 Prompts
description: Stage 7 of the comic pipeline, run once per episode block. Compiles each page's still frame into a Type C prompt at episodes/<ep>/prompts/page-NNN.prompt.txt plus negatives, with grammar validation. Deterministic — it writes no prose. Use after the block's scenes exist.
---

# Stage 7 — Prompts (Type C)

**Requires** — `episodes/<ep>/pages/page-NNN.scene.json`, `project.json`.
**Produces** — `projects/<slug>/episodes/<ep>/prompts/page-NNN.prompt.txt`,
`projects/<slug>/episodes/<ep>/prompts/page-NNN.negative.txt`.
**Gate** — none; the block is done when every page validates with no error.

This stage is deterministic. It writes nothing itself: it joins the frame the
scene drew with the canvas, and emits the prompt.

## Steps

1. Read each page's `scene.json`.

2. Build the Layout JSON (**Type C**, `docs/reference-prompts/C-akiha-single.json`):
   - `summary.canvas` is `"single"`; `summary.meta` is
     `["comic", "single", "digital_painting"]`.
   - `summary.caption` is the page's style line plus the cast index (the
     `identifier_label` and anchors of every character in the page's
     `characters`).
   - one **frame item** (`character`/`object`) whose caption is, lead first,
     the full `descriptor` of every character in `characters`, then the page's
     `scene`;
   - one **text item** per lettering entry: `text` is `lines[lang]`, the caption
     is the treatment (`comic-planning.md` §6.0).

3. Compile the boxes to `abs_centralized` / `yxyx` and attach the three sectioned
   negative blocks (`../manga-craft/build_negative.py --style painterly`).

4. Validate the compiled prompt; it re-runs to identical output, and fails on a
   grammar error (a `ref_id` left in, a box off-canvas, panels overlapping).

## Done when

- Every prompt is a valid Type C Layout JSON with `canvas: "single"`.
- It carries the FKEY trigger when the adapter is in use, and no `ref_id`.
- Every negative file carries the three sectioned blocks.
