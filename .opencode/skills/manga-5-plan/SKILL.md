---
name: Manga 5 Plan
description: Stage 5 of the manga pipeline, run once per episode. Splits the approved source into a page plan at projects/<slug>/episodes/<ep>/plan/page-story-plan.json — page count, each page's job, reader state, page-turn hook, beats and panel target, all inside the project's panel range — and stamps the plan gate. Use after the bible is approved, or when the wizard hands over stage 5.
---

# Stage 5 — Page plan

**Requires** — `episodes/<ep>/source/APPROVED`, `bible/APPROVED`, `project.json`.
**Produces** — `projects/<slug>/episodes/<ep>/plan/page-story-plan.json`,
`projects/<slug>/episodes/<ep>/plan/APPROVED`.
**Gate** — `episodes/<ep>/plan/APPROVED`.

This stage owns the page count and the rhythm. Panel-count, eye-path and pacing
rules are in `../manga-craft/comic-planning.md` (R6, R17, R19, R20, R21).

## Steps

1. If `plan/APPROVED` exists, print the page list in one line each and stop.
2. Break the source into **beats** — the smallest units the reader must see one
   at a time. Narration lines, action steps and each exchange are beats.
3. Count them, divide by 5.5, clamp to a **multiple of 4**. Write the arithmetic
   into `page_total_basis`. Do not force the source into a budget that makes it
   choppy.
4. Plan in **spreads** — two pages at a time — and write the file:

```jsonc
{
  "slug": "talk-show",
  "page_total": 20,                          // THIS stage owns the page count
  "page_total_basis": "108 beats / 5.5 = 19.6 -> 20",
  "pages": [
    {
      "page": 1, "block": 1, "page_function": "opening",
      "story_job": "one concrete sentence: what the reader must understand here",
      "source_span": "which part of the source",
      "reader_state": { "knows": [], "learns": [], "question": "..." },
      "page_turn_hook": "from page 2 onward",
      "beats": ["...", "..."],
      "panel_target": 4,
      "template_suggestion": "DAN3"
    }
  ]
}
```

`project.json` carries only the page *budget policy*. The number lives here,
because this is the stage that counts the beats.

5. Panel targets stay **inside `project.json`'s `panels.min`..`panels.max`**.
   Within that range R6 holds: a climax or a turn takes the low end, because
   impact comes from cutting panels. The high end is for busy/dense pages only when needed.
6. For each page set `split` and `focus` deliberately: **default `single`** (one emphasized moment/subject with a dominant panel; `focus` = `person`/`place`/`moment`). Use `even` **only** for a true step-by-step sequence, an internal thought process unfolding in steps, or a repetitive/routine process (cleaning, work, training, time passing) where panels carry near-equal weight — `even` pages are rare. Ordinary dialogue/reactions/reveals/confrontations should be `single` anchored on the key beat.
7. Track the rhythm across the spread: every page moves the reader, and the last
   panel of each spread pulls into the next.
8. Write `page_total` into `episodes/<ep>/episode.json`.
9. Show the page list and wait for approval. Stamp `episodes/<ep>/plan/APPROVED`.

## Done when

- `page_total` is a multiple of 4 and `page_total_basis` records the arithmetic.
- Every page has a `story_job`, a `reader_state`, and a hook from page 2 on.
- `plan/APPROVED` exists.

## Hand over

Say the plan is locked, and that **stage 6 (`manga-6-conti`)** is next, one
4-page block at a time.
