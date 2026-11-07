# Pipeline — the stage router

A story becomes prompts through nine stages: 1 source · 2 project · 3 bible ·
4 ref sheets · 5 plan · 6 conti (AI: scene · dialogue · narration · SFX in KO/EN/JA)
→ 7 cut sheets (deterministic: coordinates/sheets) → 8 artwork (AI: the artist
draws each page in words — captions, background budget, placement, light) →
9 prompts (deterministic: join captions to boxes and compile).
**One invocation runs one stage.**
Each stage reads the artifacts the stage before it left, writes its own, and
stamps a gate. Following the order is what produces a good prompt set; nothing
outside a stage's own artifact is that stage's business.

Three drivers sit on top of the table:

- **`start-wizard`** collects the decisions and records them in `wizard.json`.
- **`manga-orchestrator`** runs the table end to end, dispatching each stage and
  verifying each artifact, stopping only where a human must decide.
- A user may also run a single stage by hand, naming it.

## 0. Two scopes: the project and the episode

A **project** holds everything that outlives one story: the settings, the cast,
the world, the art style. An **episode** is one chapter — its source, its page
plan, its pages.

```
projects/<slug>/                     PROJECT scope
  project.json                       settings
  wizard.json                        the wizard's memory
  bible/characters.json              the cast pool, shared by every episode
  bible/characters/<name-slug>/      one reference sheet per character, shared
  episodes/<ep>/                     EPISODE scope
    episode.json                     title, cast subset, page budget
    source/novel.txt
    plan/page-story-plan.json
    pages/page-NNN.conti.json      the plan
    pages/page-NNN.sheet.json      the panel boxes
    pages/page-NNN.art.json        the artist's page (captions)
    prompts/page-NNN.prompt.txt    the drawable prompt
```

The cast pool is the reason episodes exist separately. A character is authored
**once**, drawn **once**, and reused by every episode they appear in:

| episode | appears | sheets |
| --- | --- | --- |
| ep01 | lead + A + B | lead, A, B |
| ep02 | lead + C + D | lead reused; **C, D new** |
| ep03 | lead + A + C | **both reused, none new** |

## 1. The artifact boundaries

Each artifact has exactly one owner, and one scope. No two stages write the same
file.

| Stage | Skill | Scope | Reads | Owns | Gate |
| --- | --- | --- | --- | --- | --- |
| 0 | `start-wizard` | project | — | `wizard.json` | — |
| 1 | `manga-1-source` | episode | `wizard.json` | `episodes/<ep>/episode.json`, `episodes/<ep>/source/novel.txt` | `episodes/<ep>/source/APPROVED` |
| 2 | `manga-2-project` | project | `wizard.json` | `project.json` | — |
| 3 | `manga-3-bible` | project | source, `project.json` | `bible/characters.json` | `bible/APPROVED` |
| 4 | `manga-4-refsheets` | project | `bible/APPROVED`, episode cast | `bible/characters/<name-slug>/` | `bible/SHEETS_APPROVED` |
| 5 | `manga-5-plan` | episode | source, `bible/APPROVED`, `project.json` | `episodes/<ep>/plan/page-story-plan.json` | `episodes/<ep>/plan/APPROVED` |
| 6 | `manga-6-conti` | episode | plan, cast, `project.json` | `episodes/<ep>/pages/page-NNN.conti.json` | — |
| 7 | `manga-7-sheets` | episode | contis, `project.json` | `episodes/<ep>/pages/page-NNN.sheet.json` | — |
| 8 | `manga-8-artwork` | episode | conti, sheet, cast, `project.json` | `episodes/<ep>/pages/page-NNN.art.json` | — |
| 9 | `manga-9-prompts` | episode | art, sheet, `project.json` | `episodes/<ep>/prompts/` | — |

Stages 2, 3 and 4 run **once per project**. Stage 3 extends the pool for each new
episode; stage 4 draws only the characters that have no sheet yet. Stages 1, 5–9
run **once per episode** (6–9 per 4-page block, in order conti → sheets → artwork → prompts).

Stages 4 and 5 are `manga`-only. `illustration` ends after stage 4; `comic` after
stage 5 with a single frame.

## 2. The stage contract

Every stage document states the same five things and does nothing outside them:

- **Requires** — the artifacts and gates that must already exist.
- **Produces** — the files it writes, and nothing else.
- **Gate** — the file it stamps when finished.
- **Steps** — the work, in order.
- **Done when** — the check that ends the stage.

A stage whose gate already exists reports that and stops. A stage whose
requirement is missing names the stage to run first and stops.

### 2.1 Validated before done, retaken by scope

**A stage is not done until its own checks pass.** The check is arithmetic, not
a judgement call: the schema's fields, the canvas bounds, and — the rule a comic
cannot bend — **panel boxes never overlap**. Balloons and lettering may sit over
each other and over a panel; two コマ may not share a pixel. When a check fails
the stage hands the exact list of problems back to the model and asks again,
until there is no error; it does not write a gate over a known error.

Because every artifact is checked and every stage owns exactly one, a **retake**
is the same run with a narrower scope. The unit of a retake is whatever that
stage works in:

| Stage | Retake scope |
| --- | --- |
| 1 source | the episode |
| 3 bible · 4 sheets | the selected characters (the pool's other cards stay) |
| 5 plan | the selected pages (the page count stays) |
| 6 conti | the selected pages, or a single cut (the other panels stay) |
| 7 sheets | the selected pages, or a single cut (rebuild and re-validate) |
| 8 artwork | the selected pages, or a single panel (redraw that panel) |
| 9 prompts | the selected pages, or a single cut (recompile and re-validate) |

A retake carries the user's note into the same prompt, changes only the selected
part, and re-runs the checks. Geometry is never the model's to place: stage 7
takes the boxes from `instantiate_layout.py`, so a panel cannot overlap by
construction, and the validator is what proves it.

## 3. Naming an episode

An episode id is a short kebab-case slug, `ep01`, `ep02`, or a title slug like
`first-night`. It is the folder name under `episodes/`.

`episode.json` is written by stage 1 and read by stages 4, 5 and 6:

```jsonc
{
  "id": "ep02",
  "title": { "ko": "두 번째 밤", "en": "The Second Night", "ja": "二夜目" },
  "source_origin": "provided",              // provided | premise | genre | outline
  "cast": ["lead", "masked-chief", "brown"], // the subset appearing in this episode
  "page_budget": "estimate",                 // estimate | N
  "page_total": 16                           // written by stage 5
}
```

## 4. Where the story comes from

Stage 1 has two roads, and they meet at the same artifact.

```
Does the user have the story?
│
├─ yes — prose, a script, a dialogue transcript
│     └─ stage 1 writes it verbatim to source/novel.txt
│
└─ no — only a premise, a genre, or an outline
      └─ stage 1 authors the prose from it,
         shows it, and writes the approved text to source/novel.txt
```

Either way the rest of the pipeline is identical: the source is split into pages
at stage 5. A provided story is **split**; a concept is **grown** into a story and
then split.

## 5. Work splitting

Stages 6–9 split by **block of 4 pages**, because stage 5 fixes what each page
must do. One worker per block, reading `project.json`, `bible/characters.json`,
its slice of the episode's `page-story-plan.json`, and the matching source span.
A block worker writes only its own pages. A block flows conti → sheets → artwork
→ prompts in that order; sheets need the conti, artwork needs the sheet, prompts
need the artwork.

Stage 8 is the artist and works **one page at a time** — one page is one finished
drawing, and an artist does not draw four pages in one breath. Stage 9 is code and
takes the whole block at once.

Stages 1 to 5 run once each, in order, by one worker, so the plan stays coherent.

## 6. Resume

Read `projects/*/`, the project gates, and each episode's gates, then report
before doing anything:

```
talk-show — manga
  wizard    phase 7
  project   set
  bible     approved (5 characters)      sheets approved (5 sheet prompts)
  ep01      12 pages — plan approved, pages 1-12 built
  ep02      16 pages — plan approved, pages 1-4 built
Next: stages 6-9 for ep02 pages 5-8.
```

## 7. Invariants across stages

- `page_total` is a multiple of 4, measured in spreads of two pages.
- One page is one image and one compiled prompt.
- Character distribution follows R-A~R-E (`character-consistency.md`).
- Panels come from `instantiate_layout.py` and follow grammar R1-R21
  (`comic-planning.md`).
- Coordinates are converted by the scripts.
- Dialogue and SFX are authored in all three languages at stage 6 —
  `lines.ko`, `lines.en`, `lines.ja` — written in parallel, not translated.
- **A person is described, not named.** A name enters a prompt only where the
  name itself is drawn — a name tag, a sign, a title — and then as `name[lang]`.
- **A prompt contains only what should be drawn.** An id is a wiring key: it
  lives in `ref_id` and in the conti, and is dropped at compile time.
- **A character sheet prompt is appearance only.** Style is a project setting
  applied at render.
- Every text item takes a treatment from `comic-planning.md` §6.0.
- **The conti is a plan; the prompt is a page.** Stage 8 rewrites the page as a
  drawing — it does not copy the conti's beats. The captions carry framing,
  placement inside the panel, the background (or its deliberate absence), light
  and figure; the boxes carry the geometry.
- **The background is the artist's decision per panel** (R19): only the panels
  that establish the place describe it.
- The build step re-runs to identical output from the artwork, the sheet and the
  template library, and fails on a grammar warning.

## 8. What lives where

| File | Contents |
| --- | --- |
| stage skills | `manga-1-source` … `manga-9-prompts`. |
| `authoring-spec.md` | The behavior spec for writing a prompt. |
| `comic-planning.md` | Panel grammar R1-R21, page geometry, box sizing, text treatments. |
| `character-consistency.md` | R-A~R-E and reference-image wiring. |
| `prompt-formats.md` | MOSS-Image input forms, schemas, coordinate maths, sampling. |
| `negative-prompts.md` | The three-block standard. |
| `verified-examples.md` | The reference prompts decomposed. |
| `scripts/` | `instantiate_layout.py`, `compile_layout.py`, `build_negative.py`. |
| `templates/` | `layouts.json` and the draft templates. |
