---
name: Comic 5 Plan
description: Stage 5 of the comic pipeline, run once per episode. Splits the approved brief into a page plan at episodes/<ep>/plan/comic-plan.json — page count and each still moment's change, dialogue intent and place, with no panels, layouts or templates — and stamps the plan gate. Use after the brief is approved, or when the wizard hands over the comic plan.
---

# Stage 5 — Plan (the moments)

This is **not** the manga plan. A comic page is one still frame, so there is no
panel count, no template, no split and no focus. This stage numbers the **still
moments** the brief contains and says what changes frame to frame.

Read `../manga-craft/twitter-comic.md` first — it is the mode brief.

**Requires** — `episodes/<ep>/source/APPROVED`, `bible/APPROVED`, `project.json`.
**Produces** — `episodes/<ep>/plan/comic-plan.json`.
**Gate** — `episodes/<ep>/plan/APPROVED`.

## Steps

1. Read the brief, `project.json`, and the cast subset on `episode.json`.

2. Set `page_total` (a multiple of 4; the project default is 4). A short exchange
   is 4 frames; use 8 only when the brief truly holds two movements.

3. Write one page per frame:

```jsonc
{
  "page": 1,
  "moment": "the still the reader sees — who is where and what the frame holds",
  "change": "page 2 onward: what shifted from the previous frame (a hand moves, the face changes, one small thing alters)",
  "dialogue_intent": "what is being said and by whom — the line's job, not its words",
  "place": "setting id, e.g. room_interior"
}
```

4. Keep the place steady across the frames and let each `change` be small — the
   reader is flipping film frames in one room, not cutting across the city.

## Rules

- **No** `panel_target`, `template_suggestion`, `split` or `focus` — those are
  manga cut fields; a comic page is one frame. The validator rejects them.
- Every page after the first names its `change`.
- `page_total` is a multiple of 4.

## Done when

- `comic-plan.json` parses, `page_total` is a multiple of 4, and one page exists
  per frame with a `moment` (and a `change` from page 2).

## Hand over

Say the frames are planned. **Stage 6 (`comic-6-scene`)** draws each frame and
writes its dialogue.
