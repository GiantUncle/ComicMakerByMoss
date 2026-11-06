---
name: Manga 4 Ref Sheets
description: Stage 4 of the manga pipeline. Writes one appearance-only reference-sheet prompt per character into projects/<slug>/bible/characters/<name-slug>/, or takes a supplied image, and stamps bible/SHEETS_APPROVED. Extends only for characters that have no sheet yet. Use after the bible is approved, or when the wizard hands over stage 4.
---

# Stage 4 — Reference sheets

**Requires** — `bible/APPROVED`, and the episode's `cast`.
**Produces** — `projects/<slug>/bible/characters/<name-slug>/sheet.prompt.txt` or
`sheet.png`, and the `reference` field on each card.
**Gate** — `bible/SHEETS_APPROVED`.

The sheet is the character's **appearance** written out as a picture brief. The
wiring rules are in `../manga-craft/character-consistency.md` §4.

## Steps

1. If `bible/SHEETS_APPROVED` exists and every character in this episode already
   has a sheet, report it and stop. **Only characters without a sheet get one.**
2. Ask how the sheets are made, and follow the branch:

   | Answer | Do |
   | --- | --- |
   | **prompt only** | write `cast/<name-slug>/sheet.prompt.txt`, leave `reference.sheet` null |
   | **the user supplies images** | ask for a path per character; set `reference.sheet` and `approved: true` |
   | **no references** | record that the fallback is in force; leave every `reference.sheet` null |

3. The sheet prompt has exactly two parts:

   ```
   A character reference sheet: one figure, front and three-quarter bust,
   plain flat neutral background, even light, nothing cropped.
   <the card's descriptor, verbatim>
   ```

   The framing line says it is a reference of one figure; the descriptor says
   what that figure looks like.

4. **The sheet prompt is appearance.** Style, medium, camera and lighting are
   **project settings** and are applied when the sheet is rendered. The sheet
   describes the character; the render supplies the look.

5. **A person is described, not named.** The prompt carries the description and
   nothing else — the name, the id, the folder and the episode stay in the files
   and on the card. A name the model has never seen draws nothing; the
   descriptor is what draws.

6. For **the user supplies images**, prefer a clean front view cropped to the
   character. A reference cut from a panel drags its props along.
7. Stamp `bible/SHEETS_APPROVED` with the branch taken.

## Done when

- Each new character has `bible/characters/<name-slug>/sheet.prompt.txt` or an approved image.
- Every sheet prompt is the framing line plus the descriptor.
- `bible/SHEETS_APPROVED` exists and records the branch.

## Hand over

Say which branch ran, and that **stage 5 (`manga-5-plan`)** is next.
