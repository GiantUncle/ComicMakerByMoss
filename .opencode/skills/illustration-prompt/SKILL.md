---
name: Illustration Prompt
description: Turns a one-line command into a finished Type B illustration prompt for MOSS-Image — a sectioned <|...|> prompt with one style section and one section per region, no JSON and no boxes. Used by the top-level illustration tool, which is not a project. Use when the user asks for an illustration prompt, a key visual, a character sheet, or a split composition.
---

# Illustration Prompt (Type B)

A command goes in; a finished prompt comes out. There is no project, no story
and no dialogue — an illustration is **one picture**. The output is **Type B**
(`docs/reference-prompts/B-commercial-clean.positive.txt`): a sectioned
`<|...|>` prompt, no JSON, no boxes.

Read `../manga-craft/templates/type-b-sections.md` and
`../manga-craft/authoring-spec.md` first.

## What to return

Exactly one JSON object:

```jsonc
{
  "title": "short label",
  "style_and_aesthetic": "medium and rendering quality. palette. light. subject count and framing. the one thing that makes this image work",
  "sections": [
    { "name": "region_name", "caption": "what occupies this region, in full detail" }
  ]
}
```

- `style_and_aesthetic` does the job of `summary.caption`: the medium, palette,
  light and rendering quality — and the count/framing tags (`1girl`, `safe`,
  `wholesome`, …). It is written **once**.
- Each `sections[]` entry is one region of the frame (its position stated in
  words: "Occupying the left half of the frame…", "In sharp contrast, standing
  on the right…"). One section is enough for a single subject; two or more for a
  split composition, a before/after pair or a character sheet.
- The section `name` is one tight token, `A-Za-z0-9_` only, no spaces, and never
  `style_and_aesthetic`.

## Rules

1. **No coordinates, no boxes.** Type B has none. Where something sits is said in
   words, not numbers.
2. **The same character in two regions is described twice**, and the second
   description opens with `the exact same` and repeats only the proportions,
   hair and outfit — never a full second description.
3. **Style lives in the style section**, not repeated in every region.
4. **A person is described, not named**, unless the name is drawn in the picture.
   Appearance only: sex, then face/build/features/hair/clothing
   (`character-consistency.md` §9). No pose, expression, camera or light inside a
   pure appearance note — those belong to the region's composition.
5. **Draw the picture in words.** Say the medium, the light, the texture, the
   pose, the expression — the way `A`/`C` open in `verified-examples.md`. No
   instructions to the model ("draw", "add"), no meta commentary.
6. If the command is thin, do not invent a story — invent only what the picture
   needs to be complete: subject, framing, light, mood.

## Done when

- The reply is one JSON object with a non-empty `style_and_aesthetic` and one or
  more named region sections.
- It compiles to a Type B prompt: the trigger line first, then the style section,
  then the regions — no JSON and no boxes in the final prompt.
