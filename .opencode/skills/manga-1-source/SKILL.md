---
name: Manga 1 Source
description: Stage 1 of the manga pipeline, run once per episode. Creates the episode record at projects/<slug>/episodes/<ep>/episode.json and locks its story into episodes/<ep>/source/novel.txt — either the user's own prose, or prose authored from a premise, a genre or an outline — then stamps the source gate. Use when starting a new episode or replacing an episode's story.
---

# Stage 1 — Source

**Requires** — `wizard.json`, and an episode id.
**Produces** — `projects/<slug>/episodes/<ep>/episode.json`,
`projects/<slug>/episodes/<ep>/source/novel.txt`,
`projects/<slug>/episodes/<ep>/source/APPROVED`.
**Gate** — `episodes/<ep>/source/APPROVED`.

The stage table is in `../manga-craft/pipeline.md`. This stage owns one episode's
record and its source text, and nothing else.

## Steps

### 1 — Which road

Read `wizard.json` for the road already chosen, or ask if it is absent:

```
Do you have this episode's story, or only an idea?
  1. I have it — I'll paste the text            [default]
  2. Only a premise — you write it
  3. Only a genre and mood — you invent it
  4. An outline — you expand it into prose
```

Both roads end at the same artifact. A provided story is **split** later, at
stage 5; an idea is **grown** into a story here, then split the same way.

### 2 — Get the text

**Road 1 — the user has it.** Take the paste exactly as given, keeping the
separators, the scene breaks and the speaker labels. Go to step 4.

**Roads 2, 3, 4 — author it.** Write a **treatment** first: a one-paragraph
premise plus a beat list. Show it and wait.

```
Is this the story you want?
  a. yes, write it out in full      [default]
  b. change the premise
  c. change the beat list
  d. start over
```

On approval, expand the treatment into prose. Then show the prose and wait for
approval before writing.

### 3 — Length, for roads 2-4

```
How long should this episode be?
  1. let the story decide — you estimate    [default]
  2. I want about N pages
```

A page holds roughly 5.5 beats, so the answer sets a rough size, not a page
count. The page count is fixed at stage 5.

### 4 — Write and stamp

1. If the gate exists, say so and stop. Replace a source only when asked to.
2. Write `episodes/<ep>/episode.json`:

```jsonc
{
  "id": "ep02",
  "title": { "ko": "두 번째 밤", "en": "The Second Night", "ja": "二夜目" },
  "source_origin": "provided",
  "cast": [],
  "page_budget": "estimate",
  "page_total": null
}
```

`cast` is filled by stage 3 once the cast for this episode is known; stage 5
writes `page_total`.

3. Write `episodes/<ep>/source/novel.txt`.
4. Stamp `episodes/<ep>/source/APPROVED` with a one-line note: which road, and
   the date.

## Done when

- `episode.json` exists with an id and a 3-language title.
- `source/novel.txt` is the approved story.
- `source/APPROVED` exists and names the road.

## Hand over

Say the episode's source is locked. If this is the project's **first** episode,
**stage 2 (`manga-2-project`)** is next; otherwise the project settings already
exist and **stage 3 (`manga-3-bible`)** extends the cast for this episode.
