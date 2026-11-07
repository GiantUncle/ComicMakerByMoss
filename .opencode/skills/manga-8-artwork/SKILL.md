---
name: Manga 8 Artwork
description: Stage 8 of the manga pipeline, run once per page. You are the manga artist: given the 字コンテ for one page and that page's panel geometry, you write the finished page as one MOSS-Image prompt — the summary brief and one drawing caption per panel and per lettering box — so the page can be drawn. Use after the block's contis and cut sheets exist, or when the wizard hands over stage 8.
---

# Stage 8 — Artwork (you are the manga artist)

A conti is a plan; it is not a page. Nobody takes a conti to a printer. This
stage is the artist sitting down with the conti and drawing the page: deciding
what each panel actually shows, which panels carry the place and which drop it
for the figure, where inside the panel each person stands, what the light is
doing, and how it is lettered.

**You write the page again in your own words. You do not copy the conti.**

| | |
| --- | --- |
| **Requires** | `episodes/<ep>/pages/page-NNN.conti.json`, `pages/page-NNN.sheet.json` (panel geometry), `bible/characters.json`, `project.json` |
| **Produces** | `projects/<slug>/episodes/<ep>/pages/page-NNN.art.json` |
| **Gate** | none; the page is done when it validates with no error |

The geometry is already decided (the sheet's panel boxes). You never invent
coordinates, and you never state them. You decide what is *drawn inside* them.

## Steps

1. Read the conti page, the sheet's panel boxes, the cast cards, `project.json`,
   and `../manga-craft/comic-planning.md` §6–§7 (text treatments, caption
   writing), `authoring-spec.md` (§10.1: no coordinates, no position words),
   `character-consistency.md`, and `verified-examples.md`.

2. For each panel, read the conti's `shot`, `angle`, `beat`, `anchor_of`,
   `characters`, `bg`, `eyeline`, `transition`. Those are the artist's notes.
   From them, **write the drawing**:

   - **Framing.** A `medium shot at eye level` is not a caption. Say what the
     frame holds: `seen from the waist up`, `a low angle that makes her tower`,
     `a tight close-up on the mouth and the candy between two fingers`.
   - **Placement inside the panel.** Say where the figure sits in the frame and
     how two people relate: `the man on the left, back to the camera, the girl
     facing him on the right`, `her shoulder large in the right foreground`.
   - **Background: the artist decides.** Only the panels that establish the place
     describe the place (comic-planning R19). Reaction, insert and close-up
     panels drop the background and hold the figure. The conti's `bg` is a hint
     id, not prose — turn it into a described setting when the panel carries it,
     and omit it when the panel drops it. Never write an id.
   - **Light, mood, texture.** Fold these into the sentence the way a manga does
     — where the light comes from, what catches it — not as a settings list.
   - **The figure.** Use the cast card: `descriptor` for the panel that anchors
     the character, `identifier_label` for every other appearance. A person is
     described, **never named** — a name is only written where the name itself is
     drawn (a name tag, a sign), and then it is lettering, not caption.

3. Write the page's **summary brief** (`summary_caption`): one dense paragraph of
   medium, rendering, palette, light, mood and subject count for the whole page,
   the way Type A/C in `verified-examples.md` opens. This is the page's art
   direction.

4. Write each **lettering box** in one line: carrier, direction, language, and
   the treatment the conti chose (`../manga-craft/comic-planning.md` §6.0). The
   text itself stays in the conti — you describe the box and how it is lettered,
   never restate the words.

5. Return one object:

```jsonc
{
  "page": 1,
  "summary_caption": "the page's art direction, one paragraph",
  "panels": [
    { "n": 1, "caption": "the drawing: framing, placement, background or its absence, light, figure" }
  ],
  "texts": [
    { "id": "p1-d1", "caption": "Clean vertical Korean dialogue in a rounded speech balloon with a tail pointing left." }
  ]
}
```

   One `panels` entry per conti panel (same `n`), one `texts` entry per conti
   text (same `id`). Nothing else changes: the sheet keeps the boxes.

## Rules that are not negotiable

- **Described, not named.** No character name in a caption unless the name is
  drawn.
- **No coordinates, no position words for the panel itself** (`authoring-spec.md`
  §10.1): the box already says where the panel is. Placement *inside* a panel is
  welcome; a `Top-left panel:` prefix is not.
- **No instructions to the model** ("draw", "add a box around"). Describe the
  picture.
- A caption answers: what, what shape, what light, what expression
  (`comic-planning.md` §7).
- Do not restate the conti's `beat` verbatim. Rewrite it as what is seen.

## Done when

- One `page-NNN.art.json` for the page.
- Every conti panel and every conti text has one caption.
- No caption names a person or states a coordinate.

## Hand over

Say the page is drawn, and that **stage 9 (`manga-9-prompts`)** will carry these
captions onto the panel boxes and compile the page's prompt files.
