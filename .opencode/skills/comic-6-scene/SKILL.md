---
name: Comic 6 Scene
description: Stage 6 of the comic pipeline, run once per episode block. Draws each page as ONE still frame plus its lettering in pages/page-NNN.scene.json — the frame drawing, where the figures sit, the light, the expression, and the dialogue in Korean, English and Japanese with boxes. Use after the comic plan is approved.
---

# Stage 6 — Scene (draw the still frame)

You are the artist. Read the plan's moment for each page and **draw that page as
one still frame, in words**, then write its lettering. There are no panels.

| | |
| --- | --- |
| **Requires** | `episodes/<ep>/plan/APPROVED`, `bible/APPROVED`, `project.json`, `source/brief.md` |
| **Produces** | `projects/<slug>/episodes/<ep>/pages/page-NNN.scene.json` for one block |
| **Gate** | none; the block is done when every scene validates with no error |

Read first, and obey: `../manga-craft/twitter-comic.md` (the mode brief),
`../manga-craft/authoring-spec.md` (§10 Layout engineering, §14 self-check),
`../manga-craft/character-consistency.md`.

## 1. Output

Return exactly one object and nothing else:

```jsonc
{
  "pages": [
    {
      "page": 1,
      "scene": "<the whole frame drawn in words>",
      "frame_bbox": [x1, y1, x2, y2],
      "style": "<one line: medium, palette, light, mood, subject count>",
      "anchor_of": "<character id whose descriptor this frame anchors>",
      "label": "character",
      "texts": [
        {
          "id": "p1-d1",
          "kind": "dialogue",          // dialogue | narration | sfx | thought | sign | title
          "speaker": "<character id or null>",
          "lines": { "ko": ["…"], "en": ["…"], "ja": ["…"] },
          "bubble": "round",           // round | jagged | rect | oval | none | solid
          "tail": "<character id or null>",
          "bbox": [x1, y1, x2, y2],
          "vertical": false
        }
      ]
    }
  ]
}
```

One `pages` entry per page in the block. **One frame a page** — never split a page
into panels.

## 2. `scene` — the frame, drawn in words

`scene` describes the **picture**, not the plot. Write it as a drawing an artist
could ink:

- **Framing and POV** — what the frame holds and whose eyes it belongs to
  (`seen across the table from his seat, waist-up at eye level`).
- **Placement** — where each figure sits and how they relate (who is foreground,
  who faces whom).
- **Background** — the frame that establishes the place describes it; a tight
  reaction frame may drop it and hold the figure.
- **Light and texture** — fold it into the sentence (where the light comes from,
  what catches it), never a settings list.
- **The moment** — the expression and the small change the plan named.

**Density, calibrated to the reference prompts (`docs/reference-prompts/`):** a
`scene` runs **80–150 words**. Shorter leaves the model guessing; longer buries
the one thing the frame is about. The `style` line is one clause-run of medium,
palette, light, mood and the subject count (`1girl, 1boy`, …), the way Type A/C
open.

## 3. Identity — described, never labelled

**This is the rule that keeps a character the same person across pages.**

- The frame's `anchor_of` names the character whose identity this frame fixes.
  **The build appends that character's full `descriptor` to the frame
  automatically** — so do **not** repeat their face, hair or clothing in `scene`.
  Spend `scene` on framing, placement, background, light, action and expression.
  (R-A: a figure's FULL description appears exactly once per page, and a comic
  page is one frame, so that frame always carries it.)
- A character who appears but is **not** the frame's `anchor_of` gets **no**
  automatic descriptor — so **you** must name their identity in `scene` with
  their card's `anchors` (e.g. `the tall man's forearm, a charcoal knit cuff`).
- **Never use an identifier label or a `ref_id` to stand in for a person.** A
  caption that carries only a label is not drawn. A person is described.
- A name (`name[lang]`) enters the image only where the name itself is drawn — a
  name tag, a sign, a title. Elsewhere, describe.

## 4. Lettering

One `texts` entry per spoken line, narration or SFX.

- `kind` decides the shape (`authoring-spec.md` §9, `comic-planning.md` §6.0):
  `dialogue` → a balloon with a tail pointing at the speaker; `narration` → a
  rectangle, no tail; `sfx` → lettering on the art, `bubble: "none"`; a
  speaker off-frame → an oval with no tail.
- Keep a line to ~2 lines of ~28 characters. **Author `ko`, `en`, `ja`
  together** — the same number of lines in each, written in parallel, never
  translated.
- **Every `bbox` stays inside the canvas** (`0 ≤ x1 < x2 ≤ W`, `0 ≤ y1 < y2 ≤ H`).
  A box that leaves the canvas is clipped. Keep a balloon clear of any other
  figure's head.

## 5. Rules that are not negotiable

- One frame a page; no panels, no layout, no template.
- Camera stays roughly still across the block: a small change frame to frame,
  not a new scene (`twitter-comic.md` §2).
- Described, not named; no coordinates in `scene`; no instructions to the model
  ("draw", "add a balloon").
- All three languages, equal line counts, boxes inside the canvas.

## 6. Before you return — self-check (`authoring-spec.md` §14)

For each page: is there a framing sentence, a placement sentence, a light
sentence, an expression sentence? Is every figure either the anchor (descriptor
appended by the build) or described by its anchors in `scene`? Is every text box
inside the canvas? One frame only?

## Done when

- One `page-NNN.scene.json` per page of the block.
- Each scene has a non-empty `scene` (80–150 words), a `style` line, an
  `anchor_of`, and three-language lettering with boxes inside the canvas.

## Hand over

Say the frames are drawn. **Stage 7 (`comic-7-prompts`)** compiles them into
`page-NNN.prompt.txt` + `negative.txt`.
