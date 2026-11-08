---
name: Comic 1 Brief
description: Stage 1 of the comic pipeline, run once per episode. Locks the episode's short moment-sequence into episodes/<ep>/source/brief.md — either the user's own few beats, or prose authored from a premise, a genre or an outline. Use when starting a comic episode or replacing its brief.
---

# Stage 1 — Brief

A comic is a short sequence of still moments (see `../manga-craft/twitter-comic.md`).
This stage fixes **what those moments are**, in a few lines of prose. It is the
comic's source: there is no long novel, only a brief.

**Requires** — `episodes/<ep>/episode.json`, the wizard's answer for where the
story comes from.
**Produces** — `episodes/<ep>/source/brief.md`.
**Gate** — `episodes/<ep>/source/APPROVED`.

## Steps

1. Read `wizard.json` and `episodes/<ep>/episode.json`. The road is
   `source_origin`: `provided | premise | genre | outline`.

2. **provided** — the user already wrote the beats. Keep their words verbatim:
   save them as `source/brief.md` and stamp the gate. Do not rewrite.

3. **premise / genre / outline** — author a short brief from the input:
   - Plain prose only: no title line, no JSON, no commentary.
   - Keep it to the moments that happen **in one place**: who is there, what each
     wants, what the small shift is (the beat that turns the exchange).
   - It is a storyboard seed, not a short story: a handful of sentences a
     storyboarder can cut into four still frames.
   - Write enough that stage 5 can number the frames, but do not spend a scene.

4. Save `source/brief.md` and stamp `source/APPROVED`.

## Done when

- `source/brief.md` exists and reads as a short moment-sequence in one place.
- `source/APPROVED` is stamped.

## Hand over

Say the brief is locked. **Stage 3 (`manga-3-bible`)** is next.
