---
name: Comic 5 Plan
description: Stage 5 of the comic pipeline, run once per episode. Turns the approved brief into a storyboard spec at episodes/<ep>/plan/comic-plan.json — the one place, the through-line, and per still frame the camera, who is in frame, the state carried in, the single change, the dialogue intent and any sound. No panels, layouts or templates. Stamps the plan gate.
---

# Stage 5 — Plan (the storyboard spec)

This is **not** the manga plan. A comic page is one still frame, so there are no
panels, no template, no split. This stage writes a **spec** every page is built
from: the camera, the place, who is on the page, the state carried over from the
previous frame, the one thing that changes, the line, and any sound.

Read `../manga-craft/twitter-comic.md` first — it is the mode brief.

**Requires** — `episodes/<ep>/source/APPROVED`, `bible/APPROVED`, `project.json`.
**Produces** — `episodes/<ep>/plan/comic-plan.json`.
**Gate** — `episodes/<ep>/plan/APPROVED`.

## Why this is a spec, not a list

Each page is drawn as an independent image, so **continuity can only come from
the plan**. If the plan does not say what carries over and what changes, the
artist invents a new mood each frame and the sequence dies. Write each frame so
another artist could draw it and get the same page.

## Output

```jsonc
{
  "slug": "…",
  "page_total": 4,                       // a multiple of 4
  "moment_basis": "why this many frames",

  // one place, fixed for the whole comic
  "setting": "a subway car interior at night — the silver pole left of centre, the blue seats, the lit route map above the far doors",
  // the through-line: the running situation and the emotional arc, frame to frame
  "through_line": "she drops an earbud; he stoops and returns it; a small thank-you; he steps off and she watches him go",

  "pages": [
    {
      "page": 1,
      "place": "subway_car",
      "camera": "from across the aisle, waist-up, eye level, the pole left of centre",
      "in_frame": [
        { "id": "young-woman", "where": "left of centre, one hand on the pole, earphones in her other hand" },
        { "id": "young-man", "where": "right, mid-turn, reaching down" }
      ],
      "props": ["a loose earbud on the floor"],
      "state_in": "easy, mid-listening, unaware",
      "state_out": "startled — an earbud has slipped from her hand",
      "moment": "the still the reader sees",
      "change": "page 2 onward: the ONE thing that changes from the previous frame",
      "dialogue_intent": "what is said, and by whom — the line's job, not its words",
      "sfx": "the sound at this moment, or null — a small click as the earbud lands"
    }
  ]
}
```

## Rules

- **One place.** `setting` fixes it once; every frame keeps the same seats,
  pole, props and light. `camera` holds roughly still — a small change, not a
  new angle (`twitter-comic.md` §2).
- **`in_frame` is every figure drawn on the page**, each with where they are. A
  voice off-frame is not in frame.
- **`state_in` is what continues from the previous frame** (the mood, the body,
  what just happened). **`change` is the single thing that differs now.** A frame
  that changes more than one thing is two frames.
- **`sfx`**: if the moment has a sound, name it; a comic with no sound effects is
  usually wrong — the earbud clicks, the doors hiss, a mug meets the table.
- `page_total` is a multiple of 4. No `template_suggestion`, `panel_target`,
  `split` or `focus` — those are manga cut fields and the validator rejects them.

## Done when

- `comic-plan.json` parses; `page_total` is a multiple of 4; `setting` and
  `through_line` are present; one page per frame with `camera`, `in_frame`,
  `state_in`, `moment` (and, from page 2, `change`).

## Hand over

Say the storyboard spec is written. **Stage 6 (`comic-6-scene`)** draws each
frame from it.
