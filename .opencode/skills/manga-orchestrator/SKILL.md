---
name: Manga Orchestrator
description: Autonomous driver for the whole manga pipeline. One invocation takes a project from nothing to finished prompts — it runs start-wizard, then drives stages 1 through 7 in order, dispatching each stage skill, verifying each artifact and gate, and pausing only where a human must decide. Use when the user says "run the whole thing", "just make it", "orchestrate", "manga orchestrator", "go end to end", or wants the pipeline advanced without naming each stage.
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
2. **An existing gate is the answer** — report it and move on.
3. **A decision a human owes is asked for**, then waited on.

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
[ep01]    pages    block 1/3 -> 4 prompts
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
| 7 | `manga-7-pages` | episode | `episodes/<ep>/pages/*.sheet.json`, `episodes/<ep>/prompts/` |

How to dispatch each:

| Stage | Dispatch |
| --- | --- |
| 0 `start-wizard` | load and run it here — it is interactive, so relay its questions |
| 1-5 | load the stage skill and follow it here, once each, in order |
| 6-7 | one worker per **block of 4 pages**, because stage 5 fixed what each page does |

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

## 3. Verify after every pass

A stage is not done because it said so. Check its artifact:

| Stage | Check |
| --- | --- |
| 1 source | `episodes/<ep>/episode.json` has an id and a 3-language title; `source/novel.txt` exists, non-empty; the gate exists |
| 2 project | `project.json` parses; the canvas tier is in the library; `panels.min` <= `panels.max` |
| 3 bible | every card has a name-slug `id`, a 3-language `name`, 2-4 anchors, one signature, an appearance-only `descriptor`; the episode's `cast` lists who appears |
| 4 sheets | every character in the episode's `cast` has a sheet prompt or an approved image; `bible/SHEETS_APPROVED` exists |
| 5 plan | `page_total` is a multiple of 4; every page's `panel_target` is inside `panels.min`..`panels.max`; every page has a `story_job` and a hook from page 2 |
| 6 conti | one `anchor_of` per character per page; every text entry has `lines.ko`, `lines.en` and `lines.ja` with matching line counts; no caption carries an id or a name |
| 7 pages | every sheet passes `../manga-craft/scripts/compile_layout.py --check` with no warning; every prompt carries the trigger and no `ref_id` |

On a failed check, fix within the stage: re-dispatch it with the failure named.
If it fails twice, stop and report.

## 4. When to stop

Stop, report, and wait in these cases — never push past them:

| Condition | Do |
| --- | --- |
| The wizard needs an answer | ask it, verbatim, one question |
| A stage asks for approval | show the artifact's summary, ask, continue on yes |
| A gate exists but the artifact is wrong | report both; do not silently rebuild |
| The same stage fails twice | report the failure and the check that failed |
| A boundary would be crossed (a stage wants to write another stage's file) | refuse and report |
| The user scoped the run to stop earlier | stop at that stage |

## 5. Scope

Default: run to the end. A user may narrow it:

```
Run the manga orchestrator for talk-show.
Run to the plan.               (stops after stage 5)
Run from the conti.            (starts at stage 6)
Only rebuild block 3 of ep02.
Just add episode 3.            (runs stages 1, 3, 4, 5, 6, 7 for the new episode)
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
