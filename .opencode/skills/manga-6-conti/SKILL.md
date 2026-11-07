---
name: Manga 6 Conti
description: Stage 6 of the manga pipeline, run once per episode block. Writes the 字コンテ for one block of four pages at projects/<slug>/episodes/<ep>/pages/page-NNN.conti.json — panels, text treatments, dialogue in Korean, English and Japanese, and the anchor panel per character. Use after the episode's page plan is approved, or when the wizard hands over stage 6.
---

# Stage 6 — 字コンテ

**Requires** — `episodes/<ep>/plan/APPROVED`, `bible/APPROVED`, `project.json`.
**Produces** — `projects/<slug>/episodes/<ep>/pages/page-NNN.conti.json` for one
4-page block.
**Gate** — none per page; the block is done when all four contis exist and pass
their checks.

Text treatments are in `../manga-craft/comic-planning.md` §6.0; character
distribution is in `../manga-craft/character-consistency.md`.

## Steps

1. Read `project.json`, `bible/characters.json`, the plan slice for the block and
   the matching `source/` span.
2. Write one conti per page:

```jsonc
{
  "page": 1, "spread": 1,
  "story_job": "...", "page_turn_hook": "...",
  "style": "this page's style brief: medium, palette, light, mood, zero rough sketch lines",
  "layout": { "template_id": "DAN3", "size_tier": "M", "reading": "rtl" },
  "cast_index": [
    { "label": "the gaunt chief", "anchors": ["gaunt", "deep-set eyes"] }
  ],
  "panels": [
    {
      "n": 1, "tier": 0,
      "shot": "establishing|wide|medium|close|extreme_close|insert",
      "angle": "level|high|low|over_shoulder|dutch",
      "beat": "what the reader sees, WITHOUT the character's descriptor",
      "anchor_of": "lee-jaheon",
      "characters": ["lee-jaheon"], "ref_ids": ["lee-jaheon"],
      "bg": "setting id or short description",
      "eyeline": { "subject": "lee-jaheon", "dir": "left|right|none" },
      "transition": "start|cut|reaction|insert|match",
      "dialogue": ["p1-d1"],
      "sfx": ["p1-s1"]
    }
  ],
  "texts": [
    { "id": "p1-d1", "kind": "dialogue", "panel_ref": 1, "speaker": "lee-jaheon",
      "lines": {
        "ko": ["첫 줄", "둘째 줄"],
        "en": ["first line", "second line"],
        "ja": ["一行目", "二行目"]
      },
      "bubble": "round|jagged|rect|oval|none", "tail": "lee-jaheon",
      "bbox": [64, 52, 200, 148], "vertical": false }
  ],
  "validation": { "passed": false, "issues": [] }
}
```

3. `tier` is the panel's index in the template's `tiers` array, not the panel's
   position. `panels[].dialogue` and `sfx` hold text **ids**; `texts[]` holds the
   entries. One shape only.
4. Set `anchor_of` on exactly one panel per character per page. That panel's
   `beat` describes the scene and does **not** restate the descriptor; stage 7
   pastes the card's `descriptor` there. Every other appearance uses the
   character's `identifier_label`.
5. Choose a **treatment** per line from §6.0. A balloon is not the default: a
   throwaway line is floating lettering, and SFX sit on the art. A page with
   action carries at least one SFX.
6. Carve the page: only the panels that establish a place carry a `bg`. Reaction
   and insert panels frame the subject tight. Put the largest panel on the eye's
   entry or exit.
7. **Every text entry carries all three languages at once** — `lines.ko`,
   `lines.en`, `lines.ja` — written in parallel, not translated from each other.
   A language button later picks one; nothing is retranslated.
8. Write all four contis, then report the block and the gate that stage 7 needs.

## Done when

- Four `page-NNN.conti.json` files exist for the block.
- Each character present on a page has exactly one `anchor_of` panel.
- Every text entry has `lines.ko`, `lines.en` and `lines.ja`, each with the same
  number of lines.
- A name tag or a title draws `name[lang]` for the page's language.

## Hand over

Say the block's contis are written, and that **stage 7 (`manga-7-sheets`)** builds
that block's panels, **stage 8 (`manga-8-artwork`)** draws each page in words, and
stage 9 compiles them into prompts.
