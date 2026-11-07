---
name: Start Wizard
description: Guided one-step-at-a-time setup for a MOSS-Image manga, comic or illustration project. Asks the output mode, where the story comes from, the language and reading direction, the cast, the reference sheets, the page plan and the panel layout — one phase per message, every question defaulted — records the answers in projects/<slug>/wizard.json, and hands each phase to its stage skill. Use when the user says "start", "start wizard", "make a manga / comic / illustration", "continue a project", or invokes the skill with nothing decided yet.
---

# Start Wizard

The front door. This skill **asks and records**; it does not build. It carries a
user who knows nothing from an empty folder to finished prompts by asking one
phase at a time, then hands each phase to the stage skill that owns it.

## 0. What this skill owns

**One file: `projects/<slug>/wizard.json`.** It is the wizard's memory — the
answers given and the phase reached — and nothing else. Every stage reads it;
only this skill writes it.

```jsonc
{
  "slug": "talk-show",
  "mode": "manga",                  // illustration | comic | manga
  "story_route": "provided",        // provided | premise | genre | outline
  "answers": {
    "languages": { "default": "ko", "all": ["ko", "en", "ja"] },
    "reading_direction": "rtl",
    "canvas_tier": "M",
    "art_style": "fkey_painterly",
    "panels": { "min": 3, "max": 4 },   // every page stays inside
    "detail_panels": false,              // allow small, detailed cuts (5+ / insets)
    "cut_mode": "balanced",
    "cast_source": "from_text",
    "sheet_source": "prompt_only",
    "layout_mode": "balanced"
  },
  "project_settled": ["bible", "sheets"],
  "episodes": [
    { "id": "ep01", "phase": 7, "settled": ["source", "plan", "conti"] }
  ],
  "updated": "2026-11-05"
}
```

Write it after every phase, before moving on. There are **two progress tracks**:
`project_settled` for the stages that run once, and one entry per episode for the
stages that run per episode. A resumed session reads it and knows where it is,
**why** each setting is what it is, and which episode is open.

## 1. Rules

1. **One phase per message.** Ask, then stop and wait. Never ask two phases at
   once, never start a phase whose stage gate is unapproved.
2. **Every question has a default.** A user who knows nothing answers `enter`
   and still reaches the end. Show the default in the option list.
3. **Say what is known.** Open each question with one line about the project's
   state, so a fresh session is not blind.
4. **Read the disk before asking.** `wizard.json` and the gates are the answers.
   Only ask what is missing.
5. **A gate is presented, then waited on.**
6. **Use the question tool for a single choice**, plain prose for something the
   user must type. One question per turn either way.
7. **Hand off, don't build.** Each phase names the stage skill that does the
   work. Do not restate that skill's pipeline.

## 2. Resume

Read `projects/*/wizard.json`, the project gates, and each episode's gates, and
open with what you found.

| On disk | State | Ask |
| --- | --- | --- |
| no `projects/` | fresh | Phase 1 |
| `wizard.json` only | the interview started | the phase it stopped at |
| no episodes yet | project open, no story | Phase 2 |
| an episode's `source/APPROVED` missing | that episode needs a story | Phase 2 for it |
| `bible/APPROVED` missing | cast not locked | Phase 4 |
| `bible/SHEETS_APPROVED` missing | sheets not settled | Phase 5 |
| an episode's `plan/APPROVED` missing | that episode needs a plan | Phase 6 |
| some pages built | building | Phase 7, first incomplete block |

```
I found one project:
  talk-show — manga
    project   set · bible approved (5) · sheets approved (5)
    ep01      12 pages — plan approved, 12 of 12 built
    ep02      16 pages — plan approved, 4 of 16 built

Continue ep02, or start a new episode?
  [continue ep02]
```

## 3. Phases

Each phase hands to exactly one stage skill.

| Phase | Scope | Asks | Hands to |
| --- | --- | --- | --- |
| 1 Mode | project | what kind of output | — |
| 2 Story | **episode** | the episode id and title, and where its story comes from | `manga-1-source` |
| 3 Settings | project | languages, reading, canvas, style, panel range, cut mode | `manga-2-project` |
| 4 Cast | project | who is in this episode — extends the pool | `manga-3-bible` |
| 5 Sheets | project | how references are made — draws only the missing ones | `manga-4-refsheets` |
| 6 Page plan | **episode** | confirm the pages and the rhythm | `manga-5-plan` |
| 7 Blocks | **episode** | confirm each 4-page block | `manga-6-conti` → `manga-7-sheets` → `manga-8-artwork` → `manga-9-prompts` |

Phases 1, 3, 4 and 5 run **once per project**. Phases 2, 6 and 7 run **once per
episode**: on the first episode they follow phase 1 in order, and on a later
episode they start again at phase 2.

When the last block of an episode is built, the wizard asks one thing:

```
Episode ep02 is built. Another episode, or stop here?
  a. another episode        → Phase 2 with a new id
  b. stop here              [default]
```

After that the wizard ends. Review and revision are ordinary follow-up requests,
not phases.

## 4. Questions

### Phase 1 — Mode

```
Q1.1 What are we making?
  1. manga        — multi-panel manuscript pages            [default]
  2. comic        — one illustration with dialogue and SFX
  3. illustration — one illustration, no dialogue (background text is fine)
```

### Phase 2 — Story route (per episode)

```
Q2.1 This is episode…?
      id:     ep02                [default: the next unused ep number]
      title:  ko / en / ja        (one short line each; you can skip)
```

```
Q2.2 Do you have this episode's story, or only an idea?
  1. I have it — I'll paste the text            [default]
  2. Only a premise — you write it
  3. Only a genre and mood — you invent it
  4. An outline — you expand it into prose
```

Then set `story_route` and hand to `manga-1-source`, which writes the episode
record and the source — pasting, or authoring a treatment and getting approval.
The wizard does not write the source.

### Phase 3 — Settings

```
Q3  Languages
    all:      ko, en, ja      [all three are authored together]
    default:  ko              [the one a new view shows]
```

```
Q4  Reading direction
    1. rtl — Japanese manga, right to left   [default]
    2. ltr — left to right
```

```
Q5  Canvas
    1. M  — 992x1408, A4 portrait, 1.4 MP    [default]
    2. S  — 704x992    3. L — 1248x1760    4. XL — 1408x1984
```

```
Q6  Art style
    1. fkey_painterly — selective-focus gouache   [default]
    2. fkey_clean     — crisp commercial lineart
    3. describe it myself
```

```
Q7  Panel count range          (manga only)
    min 3   max 4              [default]
    Every page in the project stays inside this range.
    A talky episode reads well at 3-4.

Q7b Detailed (small) cuts
    off                        [default]
    The model draws small, detailed cuts poorly. Five or more panels on a page
    means small cuts creep in, so the default keeps every page at four or fewer.
    Say this to the user, not just the option:

      "에/から 5 panels, a page starts to include small, detailed cuts — the model
       draws those poorly. Default stays at 4. Turn detailed cuts on to allow
       five or six."
```

Record `detail_panels` in `wizard.json` and `project.json`. It gates the layout
library: with it off, only 2-4 panel layouts (and no inset panels) are offered;
with it on, the 5-6 panel and inset layouts open too.

```
Q8  Default page strategy      (manga only)
    1. balanced   — whichever single moment the page turns on   [default]
    2. character  — the protagonist carries the page (a lead you sell)
    3. narrative  — the decisive, shocking or revealing moment carries the page

    This is a DEFAULT, not a rule. The agent re-chooses the strategy per page
    (routine · thought · character · space · pair · ensemble) — say that to the
    user. It is the strategy, not a setting, that decides where the big panel
    goes and whether a background is drawn.
```

Record `story_focus` in `wizard.json` and `project.json`. Stage 5 uses it to pick
each page's `strategy` and `background_panel`; there is no rule that all pages
follow one strategy.

Hand to `manga-2-project`.

### Phase 4 — Cast

```
Q4.1 Who is in it?
  1. draw the cast from the text        [default]
  2. I'll describe the characters
```

The stage skill lists the cast it finds and asks for confirmation; the wizard
only records the choice in `cast_source`.

Hand to `manga-3-bible`.

### Phase 5 — Sheets

```
Q5.1 How should the reference images be made?
  1. write the sheet prompt now; render later   [default]
  2. I'll provide the images myself
  3. no reference images — text descriptors only
```

Hand to `manga-4-refsheets`.

### Phase 6 — Page plan (per episode)

```
Q6.1 How long should this episode be?
    1. estimate it from the story   [default]
    2. aim for about N pages
```

```
Q6.2 Review the page plan.   (the stage skill prints it first)
  a. approve                                   [default]
  b. I want a different page count
  c. a page's job is wrong — tell me the number
  d. the pacing is off — which stretch?
```

Hand to `manga-5-plan`. The count lands on a multiple of 4 and every page stays
inside the panel range from Q7.

### Phase 7 — Blocks

```
Q7.1 How should the panels be laid out?
  1. balanced — the stage skill picks a template per page and may adjust  [default]
  2. template — it picks, without adjusting
  3. free     — it places the panels and validates
```

```
Q7.2 Review block N (pages A-D).   (the stage skill prints it first)
  a. build all four                 [default]
  b. change a page before building
  c. rebuild one page
```

Hand to `manga-6-conti`, then `manga-7-sheets`, then `manga-8-artwork` (the artist draws each page in words), then `manga-9-prompts`. Repeat per block until the last.

## 5. First message of a fresh run

```
This builds a MOSS-Image prompt set. I'll ask a few questions, one phase at a
time, and build as I go. Every question has a default, so you can just press
enter.

Nothing exists yet. Let's start.

Q1.1 What are we making?
  1. manga        — multi-panel manuscript pages            [default]
  2. comic        — one illustration with dialogue and SFX
  3. illustration — one illustration, no dialogue (background text is fine)
```

## 6. Phase to artifact map

The same map the stage skills use; the wizard only owns the first row.

```
projects/<slug>/
  wizard.json                          start-wizard       PROJECT
  project.json                         manga-2-project    PROJECT
  bible/characters.json                manga-3-bible      PROJECT
  bible/APPROVED                       manga-3-bible      gate
  bible/characters/<name-slug>/sheet.* manga-4-refsheets  PROJECT
  bible/SHEETS_APPROVED                manga-4-refsheets  gate
  episodes/<ep>/episode.json           manga-1-source     EPISODE
  episodes/<ep>/source/novel.txt       manga-1-source     EPISODE
  episodes/<ep>/source/APPROVED        manga-1-source     gate
  episodes/<ep>/plan/page-story-plan.json  manga-5-plan   EPISODE
  episodes/<ep>/plan/APPROVED          manga-5-plan       gate
  episodes/<ep>/pages/page-NNN.conti.json  manga-6-conti  EPISODE
  episodes/<ep>/pages/page-NNN.sheet.json  manga-7-sheets EPISODE
  episodes/<ep>/pages/page-NNN.art.json    manga-8-artwork EPISODE
  episodes/<ep>/prompts/page-NNN.prompt.txt    manga-9-prompts
  episodes/<ep>/prompts/page-NNN.negative.txt  manga-9-prompts
```
