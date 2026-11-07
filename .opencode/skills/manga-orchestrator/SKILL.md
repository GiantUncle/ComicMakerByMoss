---
name: Manga Orchestrator
description: Autonomous driver for the whole manga pipeline. One invocation takes a project from nothing to finished prompts — it runs start-wizard, then drives stages 1 through 8 in order, dispatching each stage skill, verifying each artifact and gate, and pausing only where a human must decide. Use when the user says "run the whole thing", "just make it", "orchestrate", "manga orchestrator", "go end to end", or wants the pipeline advanced without naming each stage.
---

# Manga Orchestrator

Drives the pipeline. It does **not** do the work: it dispatches the stage
skills, verifies what they left, records progress, and continues until the
project is finished or a human has to decide something.

The stage table, the artifact boundaries and the stage contract are in
`../manga-craft/pipeline.md`. Read it first, every run.

## 0. What this skill owns

**Nothing on disk.** It writes no artifact of its own. Progress lives in
`projects/<slug>/wizard.json` (written by `start-wizard`) and in the gate files
(written by the stage skills). The orchestrator only reads them, decides what
runs next, and reports.

Three rules it never breaks:

1. **Dispatch the stage skill and let it write its own artifact.**
2. **An existing gate skips the dispatch, never the validation** — report the
   gate, then run that stage's script check (see §3) before moving on.
3. **A decision a human owes is asked for**, then waited on.

After every dispatch the orchestrator **actively runs the validator scripts**
(the same `validate.py` / `compile_layout.py --check` /
`tools/check_episode.py` the GUI runs on the result) and prints the outcome
next to the pass line — `0 errors` to continue, the exact issue list to
re-dispatch.

## 1. The loop

```
read the disk
  │
  ├─ no projects/, or no wizard.json
  │     └─ run start-wizard until its settings are settled
  │
  ├─ a project stage incomplete          → dispatch it (runs once per project)
  ├─ an episode stage incomplete         → dispatch it (runs per episode)
  ├─ every episode built                 → wrap and stop
  └─ a gate needs approval               → present it, wait, then continue
```

A project stage runs once for the whole project; an episode stage runs for each
episode in turn. Print one line per pass so the pipeline is visible:

```
[project] project  set       -> project.json
[project] bible    approved  -> 5 characters
[project] sheets   approved  -> 5 sheet prompts
[ep01]    source   locked    -> episodes/ep01/source/APPROVED
[ep01]    plan     approved  -> 12 pages (3 blocks)
[ep01]    conti    block 1/3 -> pages 1-4
[ep01]    sheets   block 1/3 -> 4 sheets
[ep01]    prompts  block 1/3 -> 4 prompts
[ep02]    source   locked    -> episodes/ep02/source/APPROVED
[ep02]    bible    extended  -> 2 new characters, cast recorded
[ep02]    plan     approved  -> 16 pages (4 blocks)
```

## 2. How to dispatch a stage

The stage skills, in order. **Scope decides how often a stage runs**: a project
stage runs once, an episode stage runs once per episode.

| # | Skill | Scope | Owns |
| --- | --- | --- | --- |
| 0 | `start-wizard` | project | `wizard.json` |
| 1 | `manga-1-source` | episode | `episodes/<ep>/episode.json`, `episodes/<ep>/source/novel.txt` |
| 2 | `manga-2-project` | project | `project.json` |
| 3 | `manga-3-bible` | project | `bible/characters.json`, the episode's `cast` |
| 4 | `manga-4-refsheets` | project | `bible/characters/<name-slug>/` |
| 5 | `manga-5-plan` | episode | `episodes/<ep>/plan/page-story-plan.json` |
| 6 | `manga-6-conti` | episode | `episodes/<ep>/pages/page-NNN.conti.json` |
| 7 | `manga-7-sheets` | episode | `episodes/<ep>/pages/*.sheet.json` |
| 8 | `manga-8-artwork` | episode | `episodes/<ep>/pages/*.art.json` |
| 9 | `manga-9-prompts` | episode | `episodes/<ep>/prompts/` |

How to dispatch each:

| Stage | Dispatch |
| --- | --- |
| 0 `start-wizard` | load and run it here — it is interactive, so relay its questions |
| 1-5 | load the stage skill and follow it here, once each, in order |
| 6-9 | one worker per **block of 4 pages**, in order conti → sheets → artwork → prompts, because stage 5 fixed what each page does |
| 8 `manga-8-artwork` | the artist works **one page at a time** — one page is one finished drawing |

For a block, hand a worker exactly three lines — the skill, the project, the
block — and let it read the rest from disk:

```
Run the `manga-6-conti` skill.
Project: <slug>
Block: pages A-D
```

Do not restate the stage's steps in the hand-off; the stage skill owns them.

**Blocks run sequentially by default.** Parallel dispatch trips provider rate
limits; only run blocks concurrently when the environment tolerates it, and
never for stages 1-5, which must stay coherent.

## 3. Verify after every pass — run the scripts, not your eyes

A stage is not done because it said so. The GUI runs the deterministic
validator (`app/backend/app/stages/validate.py`) the moment a stage returns and
shows `[level] code where: message`. The orchestrator must run the **same
scripts itself, actively, after every dispatch and before moving on** — never
eyeball an artifact and call it checked. An existing gate skips the *dispatch*,
never the *validation* (that is what catches a stale plan, a duplicate layout,
or a hand-edited file).

Run from the repo root with `sys.path` set to `app/backend` so `app.stages`
imports resolve. Every check below must report **0 errors**. Hand the exact
issue list (`level` / `code` / `where` / `message`) back to the stage and
re-dispatch only that stage / block. Two failures in a row on the same stage:
stop and report.

| Stage | Script check (same as GUI) | Error / warning codes to enforce |
| --- | --- | --- |
| 1 source | `episode.json` parses, `id` + 3-lang `title` non-empty; `source/novel.txt` non-empty; `source/APPROVED` exists | gate / file presence |
| 2 project | `project.json` parses; `project.canvas.tier` in `app.stages.build.library()["sizes"]`; `panels.min <= panels.max` | file presence |
| 3 bible | `app.stages.validate.validate_bible(pool, episode_cast)` | `bible.bad-id` `bible.dup-id` `bible.no-descriptor` `bible.style-in-descriptor` `bible.anchors` `bible.no-signature` `bible.no-identifier` `bible.cast-unknown` (warn: `bible.name-langs`) |
| 4 ref sheets | every `cast` id has `bible/characters/<slug>/sheet.prompt.txt` or approved image; `bible/SHEETS_APPROVED` exists | file presence |
| 5 plan | `app.stages.validate.validate_plan(plan, project)` | `plan.no-page-total` `plan.not-multiple-of-4` `plan.page-count` `plan.no-story-job` `plan.no-reader-state` `plan.panel-target` `plan.bad-split` `plan.shape-mismatch` `plan.bad-template`(warn) `plan.no-hook` `plan.focus-on-even` `plan.missing-focus` `plan.repeat-layout` |
| 6 conti (per block) | `app.stages.validate.validate_conti(conti, project)` per page; after the block run `app.stages.validate.validate_episode(all_contis_in_episode, project)` | `conti.no-story-job` `conti.bad-tier` `conti.bad-reading` `conti.no-panels` `conti.bad-template` `conti.panel-mismatch` `layout.wrong-shape` `conti.panel-count` `conti.panel-no-beat` `conti.panel-no-tier` `conti.anchor-count` `conti.dup-text-id` `conti.bad-kind` `conti.bad-bubble` `conti.bad-panel-ref` `conti.missing-lang` `conti.line-count` `conti.text-box-off-canvas` `episode.no-layout` `episode.repeat-layout` |
| 7 sheets (per block) | `../manga-craft/scripts/compile_layout.py <sheet> --check` **and** `app.stages.validate.validate_draft(draft, project)` per `page-NNN.sheet.json` | `canvas.bad` `canvas.not-multiple-16` `summary.no-caption` `items.empty` `item.not-object` `item.unknown-field` `item.bad-label` `item.no-caption` `item.bad-bbox` `item.text-empty` `panels.overlap` `item.ref-id-leaked` (on prompt) — **no warning allowed** (`item.text-too-small` `page.panel-count` `page.detail-cuts` count as fail for build) |
| 8 artwork (per page) | `app.stages.validate.validate_artwork(art, conti)` per `page-NNN.art.json` | `art.missing-page` `art.no-summary` `art.panel-missing` `art.text-missing` `art.empty-caption` (warn: `art.position-prefix` `art.conti-copied` `art.names-a-person`) |
| 9 prompts (per block) | compile is re-run; `app.stages.validate.validate_prompt(prompt_obj, w, h, project)` per `page-NNN.prompt.txt`; `page-NNN.negative.txt` has the three blocks (`painterly`/`clean`/`lineart` + age) | `summary.no-caption` `prompt.coord-space` `item.*` (above, with `compiled=True`: **no `ref_id`** allowed — `item.ref-id-leaked`) FKEY trigger present; negative three sections present — **no warning allowed** |

Episode-wide net — after stages 5–9, and before the wrap, run the same tool the
GUI checks use so plan, conti, layout reuse and prompt geometry are checked together:

```
python tools/check_episode.py <slug> --ep <ep>
```

Demand `0 error(s)`. On any error, re-dispatch the owning stage for only the
failing pages (see `pipeline.md` §2.1 retake scope), re-run the script, and
only continue when it passes. Warnings (`item.text-too-small`,
`page.panel-count`, `page.detail-cuts`, `plan.bad-template`,
`bible.name-langs`, `conti.no-text-box`) must be **reported verbatim** in the
pass line, and for stages 7–9 they block the build exactly as the GUI build does.

Example invocations (run from repo root):

```
python -c "import sys; sys.path.insert(0,'app/backend'); import json; from app.stages import validate; plan=json.load(open('projects/<slug>/episodes/<ep>/plan/page-story-plan.json',encoding='utf-8')); project=json.load(open('projects/<slug>/project.json',encoding='utf-8')); print(validate.validate_plan(plan, project))"

python ../manga-craft/scripts/compile_layout.py projects/<slug>/episodes/<ep>/pages/page-001.sheet.json --check

python tools/check_episode.py <slug> --ep <ep>
```

Do not restate definitions of the codes here — read them from
`app/backend/app/stages/validate.py` (structure + geometry: “panel boxes never
overlap”, “a compiled prompt carries no `ref_id`”, “one layout per page per
episode”). When the script and this table ever disagree, the script wins.

## 4. When to stop

Stop, report, and wait in these cases — never push past them:

| Condition | Do |
| --- | --- |
| The wizard needs an answer | ask it, verbatim, one question |
| A stage asks for approval | show the artifact's summary, ask, continue on yes |
| A gate exists but script validation reports errors | report both and the issue list; do not silently rebuild, and do not advance past the stage |
| The same stage / block fails validation twice | report the failure, the codes, and where; hand the error list to the stage for a retake |
| A boundary would be crossed (a stage wants to write another stage's file) | refuse and report |
| The user scoped the run to stop earlier | stop at that stage |

## 5. Scope

Default: run to the end. A user may narrow it:

```
Run the manga orchestrator for talk-show.
Run to the plan.               (stops after stage 5)
Run from the conti.            (starts at stage 6)
Only rebuild block 3 of ep02.
Just add episode 3.            (runs stages 1, 3, 4, 5, 6, 7, 8, 9 for the new episode)
```

Honor the scope, and say at the top which stages this run will cover.

## 6. The wrap

When the last stage passes, report only what the user needs:

1. The project and its settings — canvas tier, reading direction, languages,
   style, panel range.
2. Each episode: its id, title, page count and block count.
3. Where the prompts are:
   `projects/<slug>/episodes/<ep>/prompts/`.
4. The open item, if any — for example reference sheets that are prompts only, so
   the wiring is dormant and the pages carry descriptors.
5. Nothing else. The files are the deliverable.

## 7. Inherited non-negotiables

From `../manga-craft/pipeline.md` §5 — the orchestrator enforces these when
verifying, and never overrides them:

- `page_total` is a multiple of 4.
- One page is one image and one compiled prompt.
- Character distribution follows R-A~R-E.
- Panels come from `instantiate_layout.py` and follow grammar R1-R21.
- A person is described, not named. A name appears only where the name itself is
  drawn, and then as `name[lang]`.
- Every text item takes a treatment from `comic-planning.md` §6.0.
- The build re-runs to identical output and fails on a grammar warning.
