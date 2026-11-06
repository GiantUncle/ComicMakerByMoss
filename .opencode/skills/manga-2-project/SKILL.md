---
name: Manga 2 Project
description: Stage 2 of the manga pipeline, run once per project. Writes projects/<slug>/project.json — output mode, canvas tier, reading direction, the three languages, art style and the panel-count range every page must stay inside. Use after the first episode's source is approved, or when the wizard hands over stage 2.
---

# Stage 2 — Project

**Requires** — `episodes/<ep>/source/APPROVED` for the first episode.
**Produces** — `projects/<slug>/project.json`.
**Gate** — none; an existing `project.json` is reported and left alone unless the
user asks to change it.

The stage table is in `../manga-craft/pipeline.md`. Canvas sizes come from
`../manga-craft/prompt-formats.md` §6 and `../manga-craft/templates/layouts.json`.

## Steps

1. If `project.json` exists, report its settings in one line and stop unless the
   user asked to change one.
2. Read `wizard.json` — it carries the answers already given. Ask only for what
   is missing.
3. Write `project.json`:

```jsonc
{
  "slug": "talk-show",
  "mode": "manga",                          // illustration | comic | manga
  "canvas": { "tier": "M", "ratio": "a4_portrait" },
  "reading_direction": "rtl",               // rtl | ltr
  "languages": { "default": "ko", "all": ["ko", "en", "ja"] },
  "art_style": "fkey_painterly",
  "panels": { "min": 3, "max": 5 },         // every page stays inside this range
  "page_unit": 4,
  "cut_mode": "balanced",                   // template | balanced | free
  "title": { "ko": "…", "en": "…", "ja": "…" },
  "episodes": ["ep01"]
}
```

4. `canvas.tier` is a key in the layout library's `sizes` table — `S`, `M`, `L`
   or `XL`. The pixel size is derived from it, so a tier change is a recompile,
   not a redraw.
5. `panels.min` and `panels.max` bound every page in the project. Stage 5 plans
   inside the range and stage 6 builds inside it. A page outside it does not
   save.
6. `languages.all` is the set every text entry is authored in. `default` is what
   a new view shows.

## Done when

- `project.json` parses and every key above is present.
- `panels.min` <= `panels.max`, both within 1..8.

## Hand over

Say the settings are locked. **Stage 3 (`manga-3-bible`)** is next.
