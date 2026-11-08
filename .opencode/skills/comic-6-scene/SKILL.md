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
      "characters": ["<every character id drawn on this page, lead first>"],
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

## 1.5. Draw from the plan — it is the spec

The plan (stage 5) is a storyboard spec, not a list. Each frame is built from it:

- **`camera`** — draw the shot the plan names, and hold it. The camera does not
  move between frames except where the plan changes it.
- **`in_frame`** — the figures drawn on this page, and where each is. Put them
  where the plan puts them; `characters` is exactly these ids, lead first.
- **`state_in` + `change`** — the frame **opens in the state carried over from the
  previous frame**, and only `change` differs. If `state_in` is a startled
  flinch, the face is *still* startled here; it must not become a fresh bright
  smile. The expression is the continuous emotion, not a new one.
- **`sfx`** — if the plan names a sound, put it in the frame's lettering (a `sfx`
  text). A comic with no sound effects where sounds happen is wrong.
- **`setting`/`place`** — the same seats, pole, props and light every frame.

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
the one thing the frame is about.

**The `style` line** is the page's art direction — a comma-run the way Type A/C
open, and it carries, in order: **medium** (a 2D digital painting comic), the
**rendering quality** (what is drawn finely — *finely rendered luminous facial
features, glistening highlights, delicate hair strands against breathable
painterly brushwork*), the **palette by hue** (not just "warm palette" — *muted
cream, rose-beige and amber*), the **light** (source, direction, softness), the
page's **mood**, the **lettering rendering** (*crisp dialogue text in clean
speech bubbles* — **do not name the language**; the compiler names the lettering
language from whichever of ko/en/ja the prompt is compiled for), and the
**count tags** (`1girl, 1boy`, …). Include
`selective focus` for painterly pages (`authoring-spec.md` §12 — centre rendered
fine, edges loose).

- **Never write the adapter or trigger name** (`FKEY`, `fkey`) — the compiler
  adds the `<|artist|>fkey` line itself. Naming it here duplicates it.
- **No annotating a count tag.** Write `1girl, 1boy`; never
  `1boy (hand only)`. The scene says who is on the page.
- No story beats in the style line — it is a look, not a synopsis.

## 3. Identity — described, never labelled

**This is the rule that keeps a character the same person across pages.**

- `characters` lists **every** character the frame draws, lead first. List a
  character only if they are actually in the frame — a voice off-frame is not a
  character on the page.
- **The build appends the full `descriptor` of every character in `characters`
  to the frame automatically.** So do **not** repeat any of their faces, hair or
  clothing in `scene` — spend `scene` on framing, placement, background, light,
  action and expression. (R-A: each character's FULL description appears exactly
  once per page, and a comic page is one frame, so that frame carries it.)
- Because every drawn figure is auto-described, `scene` should name a figure
  only by their `identifier_label` when it must point at them
  (`his angular face turns away` — not a second description of the face).
- **Never write an id, an `identifier_label` alone, or a `ref_id` as if it were
  the drawing.** A caption that carries only a label is not drawn; the drawing
  and the identity come from the descriptor.
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
- `frame_bbox` keeps about a **5% margin** from the canvas edge
  (`prompt-formats.md` §2) — on a 992×1408 page, roughly x 48..944, y 70..1338,
  rounded to multiples of 16. Do not run the box edge-to-edge.
- `characters` lists every figure the frame draws, lead first — no one left off,
  no one added who is not on the page.
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
