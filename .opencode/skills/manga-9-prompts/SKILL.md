---
name: Manga 9 Prompts
description: Stage 9 of the manga pipeline, run once per episode block. Carries stage 8's drawing captions onto the panel boxes and compiles each page into final prompt files at projects/<slug>/episodes/<ep>/prompts/page-NNN.prompt.txt plus negatives, with grammar validation. Use after the block's artwork exists.
---

# Stage 9 — Prompts

**Requires** — `episodes/<ep>/pages/page-NNN.art.json` (the captions),
`pages/page-NNN.sheet.json` (the boxes), `project.json`.
**Produces** — `projects/<slug>/episodes/<ep>/prompts/page-NNN.prompt.txt`,
`projects/<slug>/episodes/<ep>/prompts/page-NNN.negative.txt`.
**Gate** — none; the block is done when every page validates with no warning.

This stage is deterministic. It does not write anything: it takes the caption
the artist wrote (stage 8) and the box the layout gave (stage 7), joins them,
and emits the prompt.

## Steps

1. Read the artwork and the sheet for each page in the block.

2. Put the artist's words onto the boxes: the `summary_caption` becomes the
   page `summary.caption`; each `panels[].caption` replaces the caption of its
   box; each `texts[].caption` replaces the caption of its lettering item. The
   boxes (`bbox`) are the sheet's and never move.

3. Compile and attach the negative blocks:

   ```bash
   python ../manga-craft/scripts/compile_layout.py pages/page-NNN.sheet.json --output prompts/page-NNN.prompt.txt
   python ../manga-craft/scripts/build_negative.py --style painterly --age adult > prompts/page-NNN.negative.txt
   ```

4. Validate the compiled prompt; the build re-runs to identical output from the
   artwork and the template library, and fails on a grammar warning.

## Done when

- Every prompt starts with the FKEY trigger when the adapter is in use, carries
  the artist's captions, and carries no `ref_id`.
- Every negative file carries the three sectioned blocks.

## Hand over

Say the block's prompts are compiled, and ask for the next block, or start the
review.
