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
   - **Light and surface.** Fold them into the sentence the way a manga does:
     where the light comes from, and what catches it — skin, leather, glass,
     foil, dust. Never name the medium or the technique in a panel: `painterly`,
     `brushwork`, `watercolor`, `gouache`, `lineart`, `photographic` are the
     summary's words. A panel caption that says *rendered in textured brushwork*
     has said nothing about what is drawn.
   - **The figure.** The cast card's `descriptor` goes onto the anchor panel
     **word for word** — do not recompose it, do not lead with the pose, and keep
     its opening `Apparent age group:` head. One recomposed descriptor yields a
     different face every page.

     A part-only frame — an extreme close-up on a hand, the eyes, the mouth — is
     an `object`, never a `character`, and it carries only that part; it can grow
     a head. Leave the full descriptor to the frame where the figure is the
     subject (`authoring-spec.md` §10.6.1).

     A re-appearance carries the label and **at most one** anchor. Three anchors
     on the second appearance is a second descriptor by another name. Every other appearance carries the card's
     `identifier_label` **plus one of its anchors** — never a bare pronoun.
     Type A writes *the bald traveler*, *the petite 15-year-old
     sailor-uniform schoolgirl*; a pronoun with nothing to hold on to drifts
     from panel to panel.

     When the card carries an `age_phrase`, the anchor drawing carries the
     anti-drift clause too, the way Type A does — what the figure is **not**:
     *neither a big-headed 10-year-old child nor a mature 20-year-old woman*.
     It goes in the same sentence as the descriptor and uses the words
     "neither" and "nor". The card's `age_phrase`, `body` and `default_outfit`
     are part of the figure.

     State each attribute **once on the page**. The signature — the mole, the
     CRT head — is named in the descriptor and nowhere else; if the action clause
     already names an attribute (the dark suit, the ink markings), the descriptor
     that follows does not repeat it, and no other panel repeats the anchor.

     A person is described, **never named** — a name is only written where the
     name itself is drawn (a name tag, a sign), and then it is lettering, not
     caption.

3. Write the page's **summary brief** (`summary_caption`): one dense paragraph of
   medium, rendering, palette, light, subject count and **skin tone** — the way
   Type A/C in `verified-examples.md` opens. Two more things belong in it:

   - **How the lettering is rendered.** Type A fixes it here: *crisp Chinese
     comic dialogue text in clean speech bubbles*. Name this page's own
     language(s) from `project.json` → `languages.all`, by name (Korean,
     English, Japanese).
   - The page's **cast index** under it, one line per figure on the page in the
     form `the young woman: soft oval face, calm dark eyes, low ponytail, mole
     under left eye.` — the `identifier_label`, then the card's anchors. It is
     what keeps a face the same across pages.
   - The **render-tag run** that closes it, one comma-run: subject count as
     `1girl` / `1boy` / `1other` and what the page relies on, ending
     `uncensored` (the shape of Type A's tail: `1girl, 1boy, sailor uniform,
     traditional Japanese inn, uncensored`).

   Name the medium and the palette's hues (not just "cool palette"), the light,
   and the figures' skin tone. Do not repeat a phrase inside the summary.

   The summary is a **style and composition lock, not a synopsis**: it says what
   the page looks like, never what happens in it — no story beats, no emotional
   arc. The captions carry the action.

4. Write each **lettering box** in one line: carrier, direction, language, and
   the treatment the conti chose (`../manga-craft/comic-planning.md` §6.0). The
   text itself stays in the conti — you describe the box and how it is lettered,
   never restate the words.

   ```
   wrong: Small Korean SFX "탁" drawn on the table beside the button.
   right: Small bold Korean sound-effect lettering on the art at the source of
          the sound, white halo, no balloon.
   ```

   If a dialogue line or an SFX glyph appears in what you wrote, delete it. The
   caption says what the box *is*; the words are already in the conti and are
   read from there.

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

## Length

Calibrated to the reference prompts: a panel caption 80-150 words, the summary
brief 60-100 words, a lettering caption one sentence. Shorter leaves the model
guessing; longer buries the one thing the panel is about.

A figure's full description is the longest sentence on the page: A's lead runs
five sentences covering age, face, eyes with their colour, hair with its colour
and texture, skin tone, proportions and wardrobe. A two-sentence descriptor is
what makes the figure drift.

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
- **No style words in a caption.** `painterly`, `brushwork`, `gouache`,
  `watercolor`, `lineart`, `photograph`, `cel shading` belong in the summary;
  a panel caption says what the panel draws (`prompt-formats.md` §2).
- No lettering caption carries the words. Not a dialogue line, not an SFX
  glyph — the box is described, the text is not repeated.
- A lettering caption names its language (Korean, English, Japanese) — one of
  the project's languages, or all of them when the page is lettered in all.
- The summary carries the lettering-rendering clause and the render tags, and
  never narrates the story.

## Done when

- One `page-NNN.art.json` for the page.
- Every conti panel and every conti text has one caption.
- No caption names a person or states a coordinate.

## Hand over

Say the page is drawn, and that **stage 9 (`manga-9-prompts`)** will carry these
captions onto the panel boxes and compile the page's prompt files.
