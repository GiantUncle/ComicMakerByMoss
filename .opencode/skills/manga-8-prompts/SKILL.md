---
name: Manga 8 Prompts
description: Stage 8 of the manga pipeline, run once per episode block. Compiles one block of cut sheets into final prompts at projects/<slug>/episodes/<ep>/prompts/page-NNN.prompt.txt and negatives, with grammar validation. Use after the block's sheets exist, or when the wizard hands over stage 8.
---

# Stage 8 — Prompts

**Requires** — `episodes/<ep>/pages/page-NNN.sheet.json` for the block,
`project.json`.
**Produces** — `projects/<slug>/episodes/<ep>/prompts/page-NNN.prompt.txt`,
`projects/<slug>/episodes/<ep>/prompts/page-NNN.negative.txt`.
**Gate** — none; the block is done when every page validates with no warning.

## Steps

1. Read the sheets for the block.

2. Compile every sheet and attach the negative blocks:

   ```bash
   python ../manga-craft/scripts/compile_layout.py pages/page-NNN.sheet.json --output prompts/page-NNN.prompt.txt
   python ../manga-craft/scripts/build_negative.py --style painterly --age adult > prompts/page-NNN.negative.txt
   ```

3. Validate the compiled prompt; the build step re-runs to identical output from the sheet and the template library, and fails on a grammar warning.

## Done when

- Every prompt starts with the FKEY trigger when the adapter is in use, and
  carries no `ref_id`.
- Every negative file carries the three sectioned blocks.

## Hand over

Say the block's prompts are compiled, and ask for the next block, or start the review.
