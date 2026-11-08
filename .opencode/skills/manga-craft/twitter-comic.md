# Twitter-style comic — the mode brief

A `comic` project is **not** a manga page. It is a short sequence of **still
frames** read one after another — the way a twitter/Instagram comic is posted as
several images. This file is the shared brief for the comic stages (5 plan, 6
scene). It does not replace `comic-planning.md` (panel grammar) or
`authoring-spec.md` (prompt writing); it narrows them to this mode.

## 1. One page = one still frame

- A comic page is **a single frame**. There are no panels, no tiers, no gutters,
  no cut sheet, no layout template. Never plan or draw more than one frame on a
  page.
- The whole page is one picture: one framing, one moment. The camera does not
  move *within* a page.

## 2. A sequence of moments, not a story arc

- The pages are consecutive **moments in one place**: a cafe table, a doorway, a
  corridor. The place is set once and mostly holds.
- Each frame differs only a little from the one before — a hand moves, the
  expression changes, the zipper slips. The reader feels time pass by flipping
  frames, not by a cut to a new scene.
- **No big composition change between pages.** Do not jump wide → extreme
  close → new angle for effect; keep the camera roughly still and let the small
  change carry the beat.
- It is a **short moment**, not a saga. A four-frame comic is one exchange.

## 3. Dialogue carries the progression

- On a single frame the story is told by what is **said**, not by cut-to-cut
  action. Each frame's line(s) push the moment forward.
- Keep lines short enough for a bubble (~2 lines, ~28 chars each); a four-frame
  back-and-forth is the normal shape (speaker, reply, reaction, turn).
- Narration is rare and short — a single line to place time or an inner thought.
  SFX only where a sound is the point.

## 4. What a frame describes (for stage 6)

For each frame, describe the **drawing** — not the plot:

- the framing (e.g. "seen from across the table, waist-up, eye level"), and whose
  POV it is;
- where each figure sits in the frame and how the two relate (who faces whom,
  what is foreground);
- the background: the one establishing frame carries the place; a tight reaction
  frame may drop it and hold the figure;
- light, and the expression the moment turns on.

Use the cast card's `descriptor` on the frame that anchors a character and the
`identifier_label` elsewhere. A person is **described, never named** (a name is
only lettering where the name itself is drawn).

## 5. Format target

The compiled page is **Type C** (`docs/reference-prompts/C-akiha-single.json`):
`summary.canvas` is `"single"`; items are one frame item plus the lettering
items. The FKEY trigger line comes first when the adapter is in use. The
negative set is the three sectioned blocks (`negative-prompts.md`).
