---
name: Manga 7 Pages
description: Stage 7 of the manga pipeline, run once per episode block. Turns one block of 字コンテ into cut sheets at projects/<slug>/episodes/<ep>/pages/page-NNN.sheet.json and compiled prompts under episodes/<ep>/prompts/, with panel boxes from the layout templates and grammar validation. Use after the block's contis exist, or when the wizard hands over stage 7.
---

# Stage 7 — Cut sheets and prompts

**Requires** — `episodes/<ep>/pages/page-NNN.conti.json` for the block,
`project.json`.
**Produces** — `projects/<slug>/episodes/<ep>/pages/page-NNN.sheet.json`,
`projects/<slug>/episodes/<ep>/prompts/page-NNN.prompt.txt`,
`projects/<slug>/episodes/<ep>/prompts/page-NNN.negative.txt`.
**Gate** — none; the block is done when every page validates with no warning.

## Steps

1. Read the contis for the block and `bible/characters.json`.
2. Get the panel boxes from the tool rather than transcribing them:

   ```bash
   python ../manga-craft/scripts/instantiate_layout.py <TEMPLATE> --size M --emit-draft draft.json --canvas 992 1408
   ```

3. Merge each panel item with its conti beat. For a panel carrying `anchor_of`,
   append the card's `descriptor` to the caption and set the item's `ref_id`.
   Build `summary.caption` from the conti's `style`, then the cast index written
   as plain prose — the label and the anchors:

   ```
   the gaunt chief: gaunt, deep-set eyes, a blade-like stillness.
   the young woman: a soft oval face, calm dark eyes, a low ponytail.
   ```

   The cast index points at who is on the page and how to draw them. A name
   enters the prompt only inside a `text` item that draws it — a name tag, a
   sign, a title. `ref_id` carries the wiring and is dropped at compile time.
4. Add the `text` items with the treatment the conti chose, and size their boxes
   per `../manga-craft/comic-planning.md` §5.
5. Validate every sheet:

   ```bash
   python ../manga-craft/scripts/compile_layout.py pages/page-NNN.sheet.json --check
   ```

6. Compile, and attach the negative blocks:

   ```bash
   python ../manga-craft/scripts/compile_layout.py pages/page-NNN.sheet.json --output prompts/page-NNN.prompt.txt
   python ../manga-craft/scripts/build_negative.py --style painterly --age adult > prompts/page-NNN.negative.txt
   ```

7. Keep whatever produces the sheets as a checked-in step that re-runs to
   identical output from the conti and the template library, and fails on a
   grammar warning.

## Done when

- Every sheet passes `compile_layout.py --check` with no warning.
- Every prompt starts with the FKEY trigger when the adapter is in use, and
  carries no `ref_id`.
- Every negative file carries the three sectioned blocks.

## Hand over

Say the block is built, and ask for the next block, or start the review.
